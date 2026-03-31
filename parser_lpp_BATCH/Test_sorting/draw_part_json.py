import json
import math
import os
from dataclasses import dataclass
from glob import glob
from typing import Iterable, List, Optional, Tuple

import cv2
import numpy as np


Point = Tuple[float, float]
ColorStyle = Tuple[Tuple[int, int, int], int]


@dataclass
class Drawable:
    kind: str
    points: List[Point]
    style: ColorStyle


@dataclass
class JsonPart:
    reference: str
    material: str
    thickness: float
    drawables: List[Drawable]
    bbox_points: List[Point]
    source_json: str


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _safe_name(text: str) -> str:
    keep = []
    for ch in str(text):
        if ch.isalnum() or ch in ("-", "_", "."):
            keep.append(ch)
        else:
            keep.append("_")
    value = "".join(keep).strip("_")
    return value or "part"


def _arc_polyline(start: Point, end: Point, center: Point, clockwise: bool, min_segments: int = 24) -> List[Point]:
    radius = math.hypot(start[0] - center[0], start[1] - center[1])
    if radius < 1e-9:
        return [start, end]

    a0 = math.atan2(start[1] - center[1], start[0] - center[0])
    a1 = math.atan2(end[1] - center[1], end[0] - center[0])

    same_end = _distance(start, end) <= max(1e-6, radius * 1e-5)
    if same_end:
        sweep = -2.0 * math.pi if clockwise else 2.0 * math.pi
    else:
        delta = a1 - a0
        if clockwise:
            if delta >= 0:
                delta -= 2.0 * math.pi
        else:
            if delta <= 0:
                delta += 2.0 * math.pi
        sweep = delta

    steps = max(min_segments, int(math.ceil(abs(sweep) / (2.0 * math.pi) * 72.0)))
    points = [start]
    for step in range(1, steps + 1):
        t = step / steps
        ang = a0 + sweep * t
        points.append((center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang)))
    return points


def _map_point(
    p: Point,
    scale: float,
    min_x: float,
    min_y: float,
    off_x: float,
    off_y: float,
    canvas_h: int,
) -> Tuple[int, int]:
    x = off_x + (p[0] - min_x) * scale
    y = off_y + (p[1] - min_y) * scale
    return int(round(x)), int(round(canvas_h - y))


def _fit_transform(points: List[Point], out_size: Tuple[int, int], margin: int) -> Tuple[float, float, float, float]:
    width, height = out_size
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)

    world_w = max(max_x - min_x, 1.0)
    world_h = max(max_y - min_y, 1.0)

    usable_w = max(width - 2 * margin, 10)
    usable_h = max(height - 2 * margin, 10)
    scale = min(usable_w / world_w, usable_h / world_h)

    drawn_w = world_w * scale
    drawn_h = world_h * scale

    extra_x = (usable_w - drawn_w) * 0.5
    extra_y = (usable_h - drawn_h) * 0.5

    return scale, min_x, min_y, margin + extra_x, margin + extra_y


def _extract_parts(raw_data, source_json: str, arc_segments: int) -> List[JsonPart]:
    if isinstance(raw_data, dict):
        if isinstance(raw_data.get("parts"), list):
            items = raw_data["parts"]
        else:
            items = [raw_data]
    elif isinstance(raw_data, list):
        items = raw_data
    else:
        raise ValueError(f"Formato JSON no soportado en {source_json}")

    parts: List[JsonPart] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        geometry = item.get("geometry") or {}
        contours = geometry.get("contours") or []
        if isinstance(contours, dict):
            contours = [contours]
        elif not isinstance(contours, list):
            contours = []
        if not contours:
            continue

        reference = str(item.get("reference") or f"part_{idx + 1:03d}")
        material = str(item.get("material") or "")
        thickness = float(item.get("thickness") or 0.0)

        drawables: List[Drawable] = []
        bbox_points: List[Point] = []

        for contour_index, contour in enumerate(contours):
            contour_type = int(contour.get("type", 0))
            is_outer = contour_type == 0
            if is_outer:
                style: ColorStyle = ((48, 138, 252), 2)
            else:
                style = ((255, 166, 82), 2)

            if contour.get("microJoint"):
                style = ((45, 222, 82), style[1])

            raw_segments = contour.get("segments", [])
            if isinstance(raw_segments, dict):
                raw_segments = [raw_segments]
            elif not isinstance(raw_segments, list):
                raw_segments = []

            for segment in raw_segments:
                start = tuple(segment.get("initialPos", []))
                end = tuple(segment.get("finalPos", []))
                if len(start) != 2 or len(end) != 2:
                    continue
                p0 = (float(start[0]), float(start[1]))
                p1 = (float(end[0]), float(end[1]))
                seg_type = int(segment.get("type", 1))

                if seg_type == 1:
                    pts = [p0, p1]
                    drawables.append(Drawable("line", pts, style))
                    bbox_points.extend(pts)
                elif seg_type in (2, 3):
                    center_data = segment.get("arcCenter")
                    if isinstance(center_data, (list, tuple)) and len(center_data) == 2:
                        center = (float(center_data[0]), float(center_data[1]))
                    else:
                        off = segment.get("arcCenterOff", [0.0, 0.0])
                        center = (p0[0] + float(off[0]), p0[1] + float(off[1]))

                    arc_sense = int(segment.get("arcSense", 1 if seg_type == 2 else -1))
                    clockwise = arc_sense > 0 or seg_type == 2
                    pts = _arc_polyline(p0, p1, center, clockwise=clockwise, min_segments=arc_segments)
                    drawables.append(Drawable("arc", pts, style))
                    bbox_points.extend(pts)
                else:
                    pts = [p0, p1]
                    drawables.append(Drawable("line", pts, style))
                    bbox_points.extend(pts)

            if contour.get("microJoint"):
                mj_start = contour.get("microJointStart")
                mj_end = contour.get("microJointEnd")
                if isinstance(mj_start, (list, tuple)) and len(mj_start) == 2:
                    p = (float(mj_start[0]), float(mj_start[1]))
                    drawables.append(Drawable("micro_joint", [p], ((0, 0, 250), 2)))
                    bbox_points.append(p)
                if isinstance(mj_end, (list, tuple)) and len(mj_end) == 2:
                    p = (float(mj_end[0]), float(mj_end[1]))
                    drawables.append(Drawable("micro_joint", [p], ((0, 0, 250), 2)))
                    bbox_points.append(p)

        if bbox_points:
            parts.append(
                JsonPart(
                    reference=reference,
                    material=material,
                    thickness=thickness,
                    drawables=drawables,
                    bbox_points=bbox_points,
                    source_json=source_json,
                )
            )

    return parts


def _render_part(
    part: JsonPart,
    save_path: str,
    out_WH: Tuple[int, int] = (400, 400),
    margin_px: int = 20,
    draw_bounding: bool = True,
) -> bool:
    if not part.bbox_points:
        return False

    width, height = int(out_WH[0]), int(out_WH[1])
    image = np.ones((height, width, 3), dtype=np.uint8) * 245

    scale, min_x, min_y, off_x, off_y = _fit_transform(part.bbox_points, (width, height), int(margin_px))

    if draw_bounding:
        min_px = _map_point((min(p[0] for p in part.bbox_points), min(p[1] for p in part.bbox_points)), scale, min_x, min_y, off_x, off_y, height)
        max_px = _map_point((max(p[0] for p in part.bbox_points), max(p[1] for p in part.bbox_points)), scale, min_x, min_y, off_x, off_y, height)
        cv2.rectangle(
            image,
            (min(min_px[0], max_px[0]), min(min_px[1], max_px[1])),
            (max(min_px[0], max_px[0]), max(min_px[1], max_px[1])),
            (0, 0, 0),
            1,
        )

    for drawable in part.drawables:
        color, thickness = drawable.style
        if drawable.kind == "micro_joint":
            x, y = _map_point(drawable.points[0], scale, min_x, min_y, off_x, off_y, height)
            cv2.circle(image, (x, y), 2, color, thickness)
            continue

        mapped = [_map_point(p, scale, min_x, min_y, off_x, off_y, height) for p in drawable.points]
        for p0, p1 in zip(mapped[:-1], mapped[1:]):
            cv2.line(image, p0, p1, color, thickness)

    label_1 = f"REF:{part.reference}"
    label_2 = os.path.basename(part.source_json)
    if part.material:
        label_2 += f" | {part.material}"
    if part.thickness:
        label_2 += f" | {part.thickness:g} mm"

    cv2.putText(image, label_1, (6, height - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(image, label_2[:70], (6, height - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    return bool(cv2.imwrite(save_path, image))


def draw_json_parts(
    json_files: Iterable[str],
    out_path: str = "OUT_png",
    out_WH: Tuple[int, int] = (400, 400),
    arc_segments: int = 24,
    margin_px: int = 20,
    draw_bounding: bool = True,
) -> bool:
    result = False

    for json_file in json_files:
        json_file = os.path.normpath(str(json_file))
        if not os.path.exists(json_file):
            print(f"Archivo no encontrado: {json_file}")
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as fh:
                raw_data = json.load(fh)
        except Exception as exc:
            print(f"No se pudo leer {json_file}: {exc}")
            continue

        try:
            parts = _extract_parts(raw_data, json_file, arc_segments=max(8, int(arc_segments)))
        except Exception as exc:
            print(f"No se pudo interpretar {json_file}: {exc}")
            continue

        if not parts:
            print(f"Sin piezas dibujables: {json_file}")
            continue

        json_stem = _safe_name(os.path.splitext(os.path.basename(json_file))[0])

        for part in parts:
            ref = _safe_name(part.reference)
            save_path = os.path.join(out_path, f"{json_stem}__{ref}.png")
            ok = _render_part(
                part,
                save_path=save_path,
                out_WH=out_WH,
                margin_px=margin_px,
                draw_bounding=draw_bounding,
            )
            if ok:
                result = True
            else:
                print(f"No se pudo guardar: {save_path}")

    return result


def draw_json_folder(
    input_dir: str = "OUT_json",
    out_path: str = "OUT_png",
    out_WH: Tuple[int, int] = (400, 400),
    arc_segments: int = 24,
    margin_px: int = 20,
    draw_bounding: bool = True,
    recursive: bool = False,
) -> bool:
    pattern = "**/*.json" if recursive else "*.json"
    json_files = sorted(glob(os.path.join(input_dir, pattern), recursive=recursive))
    if not json_files:
        print(f"No se encontraron JSON en: {input_dir}")
        return False

    print(f"JSON encontrados: {len(json_files)}")
    return draw_json_parts(
        json_files,
        out_path=out_path,
        out_WH=out_WH,
        arc_segments=arc_segments,
        margin_px=margin_px,
        draw_bounding=draw_bounding,
    )


if __name__ == "__main__":
    INPUT_DIR = "OUT_json"
    OUTPUT_DIR = "OUT_png_json"

    if not os.path.isdir(INPUT_DIR):
        fallback = "OUT_png_json"
        print(f"No existe {INPUT_DIR}. Uso carpeta alternativa: {fallback}")
        INPUT_DIR = fallback

    draw_json_folder(
        input_dir=INPUT_DIR,
        out_path=OUTPUT_DIR,
        out_WH=(500, 500),
        arc_segments=32,
        margin_px=24,
        draw_bounding=True,
        recursive=False,
    )
