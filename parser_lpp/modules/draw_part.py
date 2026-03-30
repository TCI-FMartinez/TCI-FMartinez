import math
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


Point = Tuple[float, float]
ColorStyle = Tuple[Tuple[int, int, int], int]


@dataclass
class Segment:
    kind: str
    points: List[Point]
    style: ColorStyle


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _extract_xy(line: str) -> Optional[Point]:
    mx = re.search(r"X\s*([-+]?\d+(?:\.\d+)?)", line, re.IGNORECASE)
    my = re.search(r"Y\s*([-+]?\d+(?:\.\d+)?)", line, re.IGNORECASE)
    if not (mx and my):
        return None
    return float(mx.group(1)), float(my.group(1))


def _extract_xyij(line: str) -> Optional[Tuple[float, float, float, float]]:
    m = re.search(
        r"X\s*([-+]?\d+(?:\.\d+)?)\s*Y\s*([-+]?\d+(?:\.\d+)?)\s*I\s*([-+]?\d+(?:\.\d+)?)\s*J\s*([-+]?\d+(?:\.\d+)?)",
        line,
        re.IGNORECASE,
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))


def _arc_polyline(start: Point, end: Point, i: float, j: float, clockwise: bool, min_segments: int = 24) -> List[Point]:
    cx = start[0] + i
    cy = start[1] + j
    radius = math.hypot(start[0] - cx, start[1] - cy)
    if radius < 1e-9:
        return [start, end]

    a0 = math.atan2(start[1] - cy, start[0] - cx)
    a1 = math.atan2(end[1] - cy, end[0] - cx)

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
        points.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    return points


def _is_metadata_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    return not re.match(r"^(G\d+|M\d+|N\d+|\(|%)", s, re.IGNORECASE)


def _parse_piece_header(lines: List[str]) -> Tuple[str, str, int]:
    piece_id = ""
    piece_name = ""
    start_idx = 0

    if len(lines) >= 1 and _is_metadata_line(lines[0]):
        piece_id = lines[0].strip()
        start_idx = 1
    if len(lines) >= 2 and _is_metadata_line(lines[1]):
        piece_name = lines[1].strip()
        start_idx = 2

    if not piece_id:
        piece_id = "?"
    if not piece_name:
        piece_name = os.path.splitext(os.path.basename("piece"))[0]

    return piece_id, piece_name, start_idx


def _segment_style_from_b(line: str) -> ColorStyle:
    cut_q1 = ((48, 138, 252), 2)
    cut_q2 = ((45, 222, 82), 2)
    cut_q3 = ((255, 166, 82), 2)
    cut_q4 = ((255, 100, 100), 2)

    m = re.search(r"G65\s*P9102\s+A(\d+)\s+B(\d+)", line, re.IGNORECASE)
    if not m:
        return cut_q1
    b = m.group(2)
    return {
        "02": cut_q2,
        "03": cut_q3,
        "04": cut_q4,
    }.get(b, cut_q1)


def _parse_drawables(lines: List[str], auto_close_open: bool, arc_segments: int) -> Tuple[List[Segment], List[Point], str, str]:
    piece_id, piece_name, start_idx = _parse_piece_header(lines)

    free_line: ColorStyle = ((80, 80, 80), 1)
    piercing_style: ColorStyle = ((0, 0, 250), 2)

    segments: List[Segment] = []
    bbox_points: List[Point] = []

    current_pos: Optional[Point] = None
    contour_first_point: Optional[Point] = None
    contour_last_point: Optional[Point] = None
    contour_style: ColorStyle = ((48, 138, 252), 2)
    contour_active = False
    pierce_pending = False

    for raw_line in lines[start_idx:]:
        line = re.sub(r"^N\d+\s*", "", raw_line.strip(), flags=re.IGNORECASE)
        if not line:
            continue

        if re.search(r"G65\s*P9102", line, re.IGNORECASE):
            contour_active = True
            pierce_pending = True
            contour_style = _segment_style_from_b(line)
            contour_first_point = None
            contour_last_point = current_pos
            continue

        if re.search(r"G65\s*P9104", line, re.IGNORECASE):
            if auto_close_open and contour_active and contour_first_point and contour_last_point:
                if _distance(contour_first_point, contour_last_point) > 1e-3:
                    close_points = [contour_last_point, contour_first_point]
                    segments.append(Segment("line", close_points, contour_style))
                    bbox_points.extend(close_points)
                    contour_last_point = contour_first_point
            contour_active = False
            pierce_pending = False
            contour_first_point = None
            contour_last_point = None
            continue

        if re.match(r"G0+", line, re.IGNORECASE):
            xy = _extract_xy(line)
            if xy is None:
                continue
            if current_pos is not None:
                rapid_points = [current_pos, xy]
                segments.append(Segment("line", rapid_points, free_line))
                bbox_points.extend(rapid_points)
            else:
                bbox_points.append(xy)
            current_pos = xy
            if contour_active:
                contour_last_point = current_pos
            continue

        if re.match(r"G1+", line, re.IGNORECASE):
            xy = _extract_xy(line)
            if xy is None:
                continue
            if current_pos is None:
                current_pos = xy
                bbox_points.append(xy)
                continue
            if contour_active and contour_first_point is None:
                contour_first_point = current_pos
                if pierce_pending:
                    segments.append(Segment("pierce", [current_pos], piercing_style))
                    bbox_points.append(current_pos)
                    pierce_pending = False
            pts = [current_pos, xy]
            segments.append(Segment("line", pts, contour_style if contour_active else free_line))
            bbox_points.extend(pts)
            current_pos = xy
            if contour_active:
                contour_last_point = current_pos
            continue

        if re.match(r"G2+", line, re.IGNORECASE) or re.match(r"G3+", line, re.IGNORECASE):
            data = _extract_xyij(line)
            if data is None:
                continue
            x, y, i, j = data
            end = (x, y)
            if current_pos is None:
                current_pos = end
                bbox_points.append(end)
                continue
            if contour_active and contour_first_point is None:
                contour_first_point = current_pos
                if pierce_pending:
                    segments.append(Segment("pierce", [current_pos], piercing_style))
                    bbox_points.append(current_pos)
                    pierce_pending = False
            arc_points = _arc_polyline(
                current_pos,
                end,
                i,
                j,
                clockwise=bool(re.match(r"G2+", line, re.IGNORECASE)),
                min_segments=arc_segments,
            )
            segments.append(Segment("arc", arc_points, contour_style if contour_active else free_line))
            bbox_points.extend(arc_points)
            current_pos = end
            if contour_active:
                contour_last_point = current_pos
            continue

    return segments, bbox_points, piece_id, piece_name


def _fit_transform(points: List[Point], out_size: Tuple[int, int], margin: int) -> Tuple[float, float, float, float]:
    width, height = out_size
    if not points:
        return 1.0, 0.0, 0.0, 0.0

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


def _map_point(p: Point, scale: float, min_x: float, min_y: float, off_x: float, off_y: float, canvas_h: int) -> Tuple[int, int]:
    x = off_x + (p[0] - min_x) * scale
    y = off_y + (p[1] - min_y) * scale
    return int(round(x)), int(round(canvas_h - y))


def _default_output_path(file_name: str, out_path: str) -> str:
    base = os.path.splitext(os.path.basename(file_name))[0] + "_contours.png"
    return os.path.join(out_path, base)


def draw_contours(
    pieces_files,
    output_filename="output_contours.png",
    out_WH=(400, 400),
    N=24,
    out_path="OUT_png",
    auto_close_open=True,
    margin_px=20,
    draw_bounding=True,
):
    """
    Dibuja los contornos encontrados en uno o varios .cnc y genera PNGs encuadrando la geometría.

    - No depende de un origen X/Y/R en la tercera línea del fichero.
    - Calcula el bounding real a partir de líneas y arcos discretizados.
    - Ajusta la pieza al canvas con escala uniforme y margen, sin recortar.
    - Si un contorno queda abierto, puede cerrarlo automáticamente con una línea.
    """
    result = False

    if isinstance(pieces_files, (str, os.PathLike)):
        pieces_files = [pieces_files]

    explicit_single_output = len(pieces_files) == 1 and bool(output_filename)

    for file_name in pieces_files:
        file_name = os.path.normpath(str(file_name))
        if not os.path.exists(file_name):
            print(f"Archivo no encontrado: {file_name}")
            continue

        with open(file_name, "r", encoding="utf-8", errors="ignore") as text_r_file:
            gcode_content = text_r_file.read().splitlines()

        if not gcode_content:
            print(f"Archivo vacío: {file_name}")
            continue

        segments, bbox_points, piece_id, piece_name = _parse_drawables(
            gcode_content,
            auto_close_open=auto_close_open,
            arc_segments=max(8, int(N)),
        )

        if not bbox_points:
            print(f"Sin geometría dibujable: {file_name}")
            continue

        width, height = int(out_WH[0]), int(out_WH[1])
        image = np.ones((height, width, 3), dtype=np.uint8) * 245

        scale, min_x, min_y, off_x, off_y = _fit_transform(bbox_points, (width, height), int(margin_px))

        if draw_bounding:
            min_px = _map_point((min(p[0] for p in bbox_points), min(p[1] for p in bbox_points)), scale, min_x, min_y, off_x, off_y, height)
            max_px = _map_point((max(p[0] for p in bbox_points), max(p[1] for p in bbox_points)), scale, min_x, min_y, off_x, off_y, height)
            cv2.rectangle(
                image,
                (min(min_px[0], max_px[0]), min(min_px[1], max_px[1])),
                (max(min_px[0], max_px[0]), max(min_px[1], max_px[1])),
                (0, 0, 0),
                1,
            )

        for seg in segments:
            color, thickness = seg.style
            if seg.kind == "pierce":
                x, y = _map_point(seg.points[0], scale, min_x, min_y, off_x, off_y, height)
                cv2.circle(image, (x, y), 2, color, thickness)
                continue

            mapped = [_map_point(p, scale, min_x, min_y, off_x, off_y, height) for p in seg.points]
            for p0, p1 in zip(mapped[:-1], mapped[1:]):
                cv2.line(image, p0, p1, color, thickness)

        label = f"ID:{piece_id} [{piece_name}]"
        cv2.putText(image, label, (6, height - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

        if explicit_single_output:
            save_path = os.path.normpath(str(output_filename))
        else:
            save_path = _default_output_path(file_name, out_path)

        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        if not cv2.imwrite(save_path, image):
            print(f"No se pudo guardar la imagen: {save_path}")
            continue

        result = True

    return result


if __name__ == "__main__":
    files = [
        "/mnt/data/ID9_W86011504.cnc",
        "/mnt/data/ID9_W56197519.cnc",
        "/mnt/data/ID9_W56244403.cnc",
    ]
    draw_contours(files, out_path="/mnt/data/out_png")
