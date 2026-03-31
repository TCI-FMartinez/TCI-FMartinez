from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

try:
    from modules.cnc_to_dxf import Contour, Entity, parse_cnc_contours, simplify_contour_geometry
except ImportError:
    from modules.cnc_to_dxf_combined import Contour, Entity, parse_cnc_contours, simplify_contour_geometry

META_PATTERN = re.compile(r"^\(\s*META\s+([A-Z0-9_]+)\s*:\s*(.*?)\s*\)$", re.IGNORECASE)


def _read_piece_info(cnc_path: str | Path) -> tuple[str, str, dict[str, str]]:
    path = Path(cnc_path)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip("\n") for line in f]

    piece_id = lines[0].strip() if len(lines) >= 1 else path.stem
    piece_name = lines[1].strip() if len(lines) >= 2 else path.stem
    meta: dict[str, str] = {}

    for line in lines[2:30]:
        match = META_PATTERN.match(line.strip())
        if match:
            meta[match.group(1).upper()] = match.group(2).strip()

    return piece_id, piece_name, meta


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _angle_rad(center: tuple[float, float], pt: tuple[float, float]) -> float:
    return math.atan2(pt[1] - center[1], pt[0] - center[0])


def _normalize_angle(angle: float) -> float:
    two_pi = 2.0 * math.pi
    while angle < 0:
        angle += two_pi
    while angle >= two_pi:
        angle -= two_pi
    return angle


def _sample_arc(entity: Entity, segments: int = 48) -> list[tuple[float, float]]:
    assert entity.start and entity.end and entity.center and entity.radius is not None
    start_a = _normalize_angle(_angle_rad(entity.center, entity.start))
    end_a = _normalize_angle(_angle_rad(entity.center, entity.end))

    if entity.clockwise:
        if end_a >= start_a:
            end_a -= 2.0 * math.pi
    else:
        if end_a <= start_a:
            end_a += 2.0 * math.pi

    pts: list[tuple[float, float]] = []
    for i in range(segments + 1):
        t = i / segments
        a = start_a + (end_a - start_a) * t
        x = entity.center[0] + entity.radius * math.cos(a)
        y = entity.center[1] + entity.radius * math.sin(a)
        pts.append((x, y))
    return pts


def contour_to_points(contour: Contour, arc_segments: int = 48, close_if_open: bool = True) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for entity in contour.entities:
        if entity.type == "LINE":
            if entity.start is None or entity.end is None:
                continue
            if not pts:
                pts.append(entity.start)
            pts.append(entity.end)
        elif entity.type == "ARC":
            arc_pts = _sample_arc(entity, segments=arc_segments)
            if not pts:
                pts.extend(arc_pts)
            else:
                pts.extend(arc_pts[1:])

    if close_if_open and len(pts) >= 2 and _distance(pts[0], pts[-1]) > 1e-3:
        pts.append(pts[0])
    return pts


def contours_bbox(contours: list[Contour], arc_segments: int = 48) -> tuple[float, float, float, float]:
    all_pts: list[tuple[float, float]] = []
    for contour in contours:
        all_pts.extend(contour_to_points(contour, arc_segments=arc_segments, close_if_open=False))

    if not all_pts:
        raise ValueError("No hay puntos para calcular el bounding box")

    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    return min(xs), min(ys), max(xs), max(ys)


def _fit_transform(
    bbox: tuple[float, float, float, float],
    out_wh: tuple[int, int],
    margin: int,
) -> tuple[float, float, float]:
    min_x, min_y, max_x, max_y = bbox
    width = max(max_x - min_x, 1e-6)
    height = max(max_y - min_y, 1e-6)
    usable_w = max(out_wh[0] - 2 * margin, 10)
    usable_h = max(out_wh[1] - 2 * margin, 10)
    scale = min(usable_w / width, usable_h / height)
    tx = margin - min_x * scale
    ty = margin - min_y * scale
    return scale, tx, ty


def _canvas_xy(pt: tuple[float, float], scale: float, tx: float, ty: float, out_wh: tuple[int, int]) -> tuple[int, int]:
    x = pt[0] * scale + tx
    y = pt[1] * scale + ty
    return int(round(x)), int(round(out_wh[1] - y))


def _safe_float(meta: dict[str, str], key: str) -> float | None:
    raw = meta.get(key)
    if raw is None or raw == "":
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def draw_contours(
    pieces_files: Iterable[str | Path],
    output_filename: str | Path | None = None,
    out_WH: tuple[int, int] = (800, 800),
    N: int = 72,
    out_path: str | Path = "OUT_png",
    auto_close_open: bool = True,
    draw_bounding: bool = True,
    show_metrics: bool = True,
) -> bool:
    piece_files = [Path(p) for p in pieces_files]
    result = False

    for idx, cnc_path in enumerate(piece_files):
        piece_id, piece_name, meta = _read_piece_info(cnc_path)

        contours = parse_cnc_contours(cnc_path)
        contours = [simplify_contour_geometry(c) for c in contours]
        contours = [c for c in contours if c.entities]
        if not contours:
            print(f"No se detectaron contornos en '{cnc_path}'")
            continue

        bbox = contours_bbox(contours, arc_segments=N)
        min_x, min_y, max_x, max_y = bbox
        bbox_x = max_x - min_x
        bbox_y = max_y - min_y

        canvas = np.ones((out_WH[1], out_WH[0], 3), dtype=np.uint8) * 245
        scale, tx, ty = _fit_transform(bbox, out_WH, margin=40)

        if draw_bounding:
            p1 = _canvas_xy((min_x, min_y), scale, tx, ty, out_WH)
            p2 = _canvas_xy((max_x, max_y), scale, tx, ty, out_WH)
            left = min(p1[0], p2[0])
            right = max(p1[0], p2[0])
            top = min(p1[1], p2[1])
            bottom = max(p1[1], p2[1])
            cv2.rectangle(canvas, (left, top), (right, bottom), (0, 0, 0), 1)

        color = (0, 140, 255)
        for contour in contours:
            pts = contour_to_points(contour, arc_segments=N, close_if_open=auto_close_open)
            if len(pts) < 2:
                continue
            for a, b in zip(pts[:-1], pts[1:]):
                p1 = _canvas_xy(a, scale, tx, ty, out_WH)
                p2 = _canvas_xy(b, scale, tx, ty, out_WH)
                cv2.line(canvas, p1, p2, color, 2)

        if show_metrics:
            material = meta.get("MATERIAL", "")
            thickness = meta.get("THICKNESS", "")
            ferromagnetic = meta.get("FERROMAGNETIC", "")
            area_mm2 = _safe_float(meta, "AREA_MM2")
            weight_kg = _safe_float(meta, "WEIGHT_KG")

            overlay_lines = [
                f"ID:{piece_id}  NAME:{piece_name}",
                f"BBOX: {bbox_x:.2f} x {bbox_y:.2f} mm",
            ]
            if material or thickness:
                overlay_lines.append(f"MAT:{material}  THK:{thickness} mm")
            if area_mm2 is not None:
                overlay_lines.append(f"AREA: {area_mm2:.2f} mm2")
            if weight_kg is not None:
                overlay_lines.append(f"PESO: {weight_kg:.4f} kg")
            if ferromagnetic:
                overlay_lines.append(f"FERRO: {ferromagnetic}")

            y = 24
            for line in overlay_lines:
                cv2.putText(canvas, line, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
                y += 20

        if output_filename is not None and len(piece_files) == 1:
            save_path = Path(output_filename)
        elif output_filename is not None and len(piece_files) > 1 and idx == 0:
            save_path = Path(output_filename)
        else:
            save_path = Path(out_path) / f"{cnc_path.stem}_contours.png"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        ok = cv2.imwrite(str(save_path), canvas)
        result = result or ok

    return result
