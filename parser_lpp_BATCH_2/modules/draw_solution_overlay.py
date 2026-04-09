from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
import sys

import cv2
import numpy as np

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.draw_part import contour_to_points, contours_bbox
from modules.cnc_to_dxf import parse_cnc_contours, simplify_contour_geometry


def _load_json(path: str | Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _flatten_tool_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if payload and all(isinstance(item, dict) and 'diameter' in item and 'position' in item for item in payload):
            return payload
        if payload and isinstance(payload[0], dict) and isinstance(payload[0].get('tool'), list):
            tool_items = payload[0]['tool']
            if all(isinstance(item, dict) and 'diameter' in item and 'position' in item for item in tool_items):
                return tool_items
    if isinstance(payload, dict) and isinstance(payload.get('tool'), list):
        tool_items = payload['tool']
        if all(isinstance(item, dict) and 'diameter' in item and 'position' in item for item in tool_items):
            return tool_items
    raise ValueError('Formato de herramienta JSON no soportado')


def _read_tool_positions(tool_json_path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json(tool_json_path)
    tools = _flatten_tool_payload(payload)
    result: list[dict[str, Any]] = []
    for idx, item in enumerate(tools):
        pos = item.get('position', [0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = [0.0, 0.0]
        result.append(
            {
                'index': idx,
                'position': [float(pos[0]), float(pos[1])],
                'diameter': float(item.get('diameter', 0.0) or 0.0),
                'type': item.get('type'),
                'force': item.get('force'),
            }
        )
    return result


def _extract_first_xy(value: Any) -> list[float] | None:
    if isinstance(value, dict):
        if 'x' in value and 'y' in value:
            return [float(value['x']), float(value['y'])]
        for key in ('position', 'point', 'center', 'location'):
            out = _extract_first_xy(value.get(key))
            if out is not None:
                return out
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
            return [float(value[0]), float(value[1])]
        for item in value:
            out = _extract_first_xy(item)
            if out is not None:
                return out
    return None


def _extract_xy_list(value: Any) -> list[list[float]]:
    out: list[list[float]] = []
    if isinstance(value, dict):
        if 'x' in value and 'y' in value:
            return [[float(value['x']), float(value['y'])]]
        for v in value.values():
            out.extend(_extract_xy_list(v))
        return out
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            return [[float(value[0]), float(value[1])]]
        for item in value:
            out.extend(_extract_xy_list(item))
    return out


def _read_tool_outline(tool_json_path: str | Path) -> list[list[float]]:
    payload = _load_json(tool_json_path)
    candidates: list[Any] = []
    if isinstance(payload, dict):
        candidates.extend([payload.get('geometry'), payload.get('polygon')])
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                candidates.extend([item.get('geometry'), item.get('polygon')])

    for geom in candidates:
        if isinstance(geom, dict) and geom.get('type') == 'Polygon':
            coords = geom.get('coordinates') or []
            if coords and isinstance(coords[0], list):
                pts = []
                for pt in coords[0]:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        pts.append([float(pt[0]), float(pt[1])])
                if len(pts) >= 2:
                    return pts
        if isinstance(geom, list):
            pts = []
            for pt in geom:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2 and all(isinstance(v, (int, float)) for v in pt[:2]):
                    pts.append([float(pt[0]), float(pt[1])])
            if len(pts) >= 2:
                if pts[0] != pts[-1]:
                    pts.append(pts[0][:])
                return pts
    return []


def _extract_tool_active(value: Any, expected_len: int) -> list[int]:
    result: list[int] = []
    if isinstance(value, (list, tuple)):
        flat_ok = all(isinstance(v, (int, float, bool)) for v in value)
        if flat_ok:
            if expected_len and len(value) == expected_len:
                return [idx for idx, v in enumerate(value) if bool(v)]
            if all(isinstance(v, (int, bool)) for v in value):
                ints = [int(v) for v in value]
                if all(0 <= v < expected_len for v in ints) if expected_len else True:
                    return sorted(set(ints))
        for item in value:
            result.extend(_extract_tool_active(item, expected_len))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(_extract_tool_active(item, expected_len))
    return sorted({idx for idx in result if isinstance(idx, int) and idx >= 0})


def _infer_solution_pose(solution_payload: Any) -> tuple[list[float] | None, float]:
    if isinstance(solution_payload, dict):
        for key in ('toolLocation', 'location', 'bestLocation', 'solutionLocation', 'center', 'position'):
            if key not in solution_payload:
                continue
            value = solution_payload[key]
            if isinstance(value, (list, tuple)) and len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
                angle = float(value[2]) if len(value) >= 3 and isinstance(value[2], (int, float)) else 0.0
                return [float(value[0]), float(value[1])], angle
            out = _extract_first_xy(value)
            if out is not None:
                return out, 0.0
        for value in solution_payload.values():
            center, angle = _infer_solution_pose(value)
            if center is not None:
                return center, angle
    elif isinstance(solution_payload, list):
        for item in solution_payload:
            center, angle = _infer_solution_pose(item)
            if center is not None:
                return center, angle
    return None, 0.0


def _infer_solution_points(solution_payload: Any) -> list[list[float]]:
    if isinstance(solution_payload, dict):
        for key in ('points', 'locations', 'activePoints'):
            if key in solution_payload:
                pts = _extract_xy_list(solution_payload[key])
                if pts:
                    return pts
        for value in solution_payload.values():
            pts = _infer_solution_points(value)
            if pts:
                return pts
    elif isinstance(solution_payload, list):
        for item in solution_payload:
            pts = _infer_solution_points(item)
            if pts:
                return pts
    return []


def _infer_solution_active(solution_payload: Any, expected_len: int) -> list[int]:
    if isinstance(solution_payload, dict):
        for key in ('toolActive', 'active', 'activeTools', 'activeIndexes'):
            if key in solution_payload:
                indexes = _extract_tool_active(solution_payload[key], expected_len)
                if indexes:
                    return indexes
        for value in solution_payload.values():
            indexes = _infer_solution_active(value, expected_len)
            if indexes:
                return indexes
    elif isinstance(solution_payload, list):
        for item in solution_payload:
            indexes = _infer_solution_active(item, expected_len)
            if indexes:
                return indexes
    return []


def _distance_xy(a: list[float] | None, b: list[float] | None) -> float | None:
    if a is None or b is None:
        return None
    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])
    return (dx * dx + dy * dy) ** 0.5


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ''):
            return None
        return float(value)
    except Exception:
        return None


def _short_status(status: str | None) -> str:
    mapping = {
        'valid': 'valida',
        'infeasible_cannot_lift': 'inviable: no levanta',
        'solver_error': 'solver error',
        'completed_without_geometry': 'sin geometria',
        'completed_without_solution': 'sin solucion',
        'execution_error': 'error ejecucion',
    }
    return mapping.get(str(status), str(status) if status else 'desconocido')


def _metadata_active_indexes(metadata: dict[str, Any] | None, expected_len: int) -> list[int]:
    md = metadata or {}
    for key in ('tool_active_indexes', 'active_indexes', 'toolActive', 'toolActiveIndexes'):
        if key in md:
            indexes = _extract_tool_active(md.get(key), expected_len)
            if indexes:
                return indexes
    return []


def _metadata_piece_center(metadata: dict[str, Any] | None) -> list[float] | None:
    md = metadata or {}
    for key in ('piece_center_sheet_approx', 'piece_center_approx', 'pieceCenter', 'piece_center', 'pieceCenterApprox'):
        if key in md:
            center = _extract_first_xy(md.get(key))
            if center is not None:
                return center
    return None



def _normalize_bbox_points(value: Any) -> list[list[float]]:
    points: list[list[float]] = []
    if not isinstance(value, (list, tuple)):
        return points
    for pt in value:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            try:
                points.append([float(pt[0]), float(pt[1])])
            except Exception:
                continue
    return points



def _metadata_piece_pose(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    md = metadata or {}
    if str(md.get('coord_frame') or '').strip().lower() != 'load_slot_local_to_sheet':
        return None

    local_bbox = _normalize_bbox_points(md.get('reference_bbox_local'))
    sheet_bbox = _normalize_bbox_points(md.get('piece_sheet_bbox'))
    local_origin = _extract_first_xy(md.get('reference_origin_local'))
    sheet_origin = _extract_first_xy(md.get('piece_sheet_origin'))
    if not local_bbox or not sheet_bbox or local_origin is None or sheet_origin is None:
        return None

    local_angle = _safe_float(md.get('reference_angle_local_rad')) or 0.0
    sheet_angle = _safe_float(md.get('piece_sheet_angle_rad')) or 0.0
    return {
        'local_bbox': local_bbox,
        'sheet_bbox': sheet_bbox,
        'local_origin': local_origin,
        'sheet_origin': sheet_origin,
        'local_angle': local_angle,
        'sheet_angle': sheet_angle,
        'delta_angle': sheet_angle - local_angle,
    }


def _solution_is_reliable(
    metadata: dict[str, Any] | None,
    has_active_info: bool,
    has_geometry: bool,
) -> bool:
    """Decide si la solucion es lo bastante fiable como para pintarla como encontrada."""
    md = metadata or {}
    if 'solution_valid' in md:
        try:
            return bool(md.get('solution_valid'))
        except Exception:
            pass
    status = str(md.get('status') or '').strip().lower()
    if status:
        return status == 'valid'
    return bool(has_geometry and has_active_info)


def _build_info_lines(
    metadata: dict[str, Any] | None,
    piece_stem: str,
    tool_stem: str,
    piece_center: list[float],
    drawn_tool_center: list[float] | None,
    active_count: int,
    total_count: int,
) -> list[str]:
    md = metadata or {}
    lines = [
        f'pieza: {md.get("piece_reference") or piece_stem}',
        f'herramienta: {Path(str(md.get("tool_file") or tool_stem)).stem.replace("_with_polygons", "")}',
    ]
    if md.get('piece_material'):
        material = str(md['piece_material'])
        thickness = _safe_float(md.get('piece_thickness'))
        if thickness is not None:
            lines.append(f'material: {material}  |  espesor: {thickness:.2f} mm')
        else:
            lines.append(f'material: {material}')

    lines.append(f'estado: {_short_status(md.get("status"))}')
    lines.append(f'activos: {active_count}/{total_count}')

    distance = _safe_float(md.get('center_distance_approx'))
    if distance is None:
        distance = _distance_xy(piece_center, drawn_tool_center)
    if distance is not None:
        lines.append(f'dist centros ~ {distance:.2f} mm')

    fxmin = _safe_float(md.get('solver_fxmin'))
    if fxmin is not None:
        lines.append(f'fxmin: {fxmin:.3f}')

    flag = md.get('solver_error_flag')
    if flag is None:
        flag = md.get('returncode_signed')
    if flag not in (None, ''):
        lines.append(f'flag solver: {flag}')

    if bool(md.get('time_limit_hit')):
        lines.append('corte por tiempo: si')

    return lines


def _draw_info_panel(canvas: np.ndarray, lines: list[str], origin: tuple[int, int] = (10, 10)) -> None:
    if not lines:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.56
    thickness = 1
    line_gap = 8
    margin = 10

    sizes = [cv2.getTextSize(line, font, scale, thickness)[0] for line in lines]
    max_w = max((w for w, _ in sizes), default=0)
    line_h = max((h for _, h in sizes), default=16)
    panel_w = max_w + 2 * margin
    panel_h = len(lines) * line_h + (len(lines) - 1) * line_gap + 2 * margin

    x0, y0 = origin
    x1 = min(canvas.shape[1] - 1, x0 + panel_w)
    y1 = min(canvas.shape[0] - 1, y0 + panel_h)

    overlay = canvas.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (255, 255, 255), -1)
    cv2.addWeighted(overlay, 0.72, canvas, 0.28, 0, canvas)
    cv2.rectangle(canvas, (x0, y0), (x1, y1), (60, 60, 60), 1)

    y = y0 + margin + line_h
    for line in lines:
        cv2.putText(canvas, line, (x0 + margin, y), font, scale, (15, 15, 15), thickness, cv2.LINE_AA)
        y += line_h + line_gap


def _rotate_translate_point(local_xy: list[float] | tuple[float, float], center_xy: list[float], angle_rad: float) -> list[float]:
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    x = float(local_xy[0])
    y = float(local_xy[1])
    return [center_xy[0] + c * x - s * y, center_xy[1] + s * x + c * y]



def _transform_local_point_to_sheet(local_xy: list[float] | tuple[float, float], pose: dict[str, Any] | None) -> list[float]:
    if pose is None:
        return [float(local_xy[0]), float(local_xy[1])]
    x_rel = float(local_xy[0]) - float(pose['local_origin'][0])
    y_rel = float(local_xy[1]) - float(pose['local_origin'][1])
    c = math.cos(float(pose['delta_angle']))
    s = math.sin(float(pose['delta_angle']))
    x_rot = c * x_rel - s * y_rel
    y_rot = s * x_rel + c * y_rel
    return [float(pose['sheet_origin'][0]) + x_rot, float(pose['sheet_origin'][1]) + y_rot]


def _draw_solution_not_found_banner(canvas: np.ndarray, text: str = 'Solucion no encontrada') -> None:
    """Dibuja un aviso muy visible cuando la solucion no es fiable."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.1
    thickness = 2
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    margin_x = 18
    margin_y = 14
    x0 = 22
    y0 = 20
    x1 = min(canvas.shape[1] - 1, x0 + tw + 2 * margin_x)
    y1 = min(canvas.shape[0] - 1, y0 + th + baseline + 2 * margin_y)

    overlay = canvas.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (240, 240, 240), -1)
    cv2.addWeighted(overlay, 0.80, canvas, 0.20, 0, canvas)
    cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 0, 180), 2)
    text_org = (x0 + margin_x, y0 + margin_y + th)
    cv2.putText(canvas, text, text_org, font, scale, (0, 0, 180), thickness, cv2.LINE_AA)


def draw_solution_overlay_png(
    piece_cnc: str | Path,
    processed_tool_json: str | Path,
    solution_json: str | Path,
    output_png: str | Path,
    out_wh: tuple[int, int] = (1100, 950),
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Dibuja la herramienta solucionada sobre la pieza.

    Regla visual:
    - actuador activo: circulo relleno + contorno
    - actuador inactivo: solo contorno

    Además añade un panel con la información útil para revisar la calidad de la solución.
    """
    contours = parse_cnc_contours(piece_cnc)
    contours = [simplify_contour_geometry(c) for c in contours]
    contours = [c for c in contours if c.entities]
    if not contours:
        return False

    solution_payload = _load_json(solution_json)
    tool_positions = _read_tool_positions(processed_tool_json)
    tool_outline = _read_tool_outline(processed_tool_json)
    active_indexes = set(_infer_solution_active(solution_payload, len(tool_positions)))
    if not active_indexes:
        active_indexes = set(_metadata_active_indexes(metadata, len(tool_positions)))
    has_active_info = bool(active_indexes)
    tool_center, tool_angle = _infer_solution_pose(solution_payload)
    explicit_points = _infer_solution_points(solution_payload)
    has_geometry = bool(explicit_points or tool_center is not None)
    solution_is_reliable = _solution_is_reliable(metadata, has_active_info, has_geometry)

    min_x, min_y, max_x, max_y = contours_bbox(contours, arc_segments=72)
    width = max(max_x - min_x, 1e-6)
    height = max(max_y - min_y, 1e-6)
    margin = 40
    info_panel_w = 300
    usable_w = max(out_wh[0] - 2 * margin - info_panel_w, 10)
    usable_h = max(out_wh[1] - 2 * margin, 10)
    scale = min(usable_w / width, usable_h / height)
    tx = margin - min_x * scale
    ty = margin - min_y * scale

    canvas = np.ones((out_wh[1], out_wh[0], 3), dtype=np.uint8) * 245

    def canvas_xy(pt: list[float] | tuple[float, float]) -> tuple[int, int]:
        x = float(pt[0]) * scale + tx
        y = float(pt[1]) * scale + ty
        return int(round(x)), int(round(out_wh[1] - y))

    p1 = canvas_xy((min_x, min_y))
    p2 = canvas_xy((max_x, max_y))
    left = min(p1[0], p2[0])
    right = max(p1[0], p2[0])
    top = min(p1[1], p2[1])
    bottom = max(p1[1], p2[1])
    cv2.rectangle(canvas, (left, top), (right, bottom), (0, 0, 0), 1)

    for contour in contours:
        pts = contour_to_points(contour, arc_segments=72, close_if_open=True)
        if len(pts) < 2:
            continue
        mapped = [canvas_xy(pt) for pt in pts]
        for a, b in zip(mapped[:-1], mapped[1:]):
            cv2.line(canvas, a, b, (0, 140, 255), 2)

    piece_center = [0.5 * (min_x + max_x), 0.5 * (min_y + max_y)]
    metadata_piece_center = _metadata_piece_center(metadata)
    piece_pose = _metadata_piece_pose(metadata)
    frame_offset = [0.0, 0.0]
    if piece_pose is None and metadata_piece_center is not None:
        frame_offset = [piece_center[0] - metadata_piece_center[0], piece_center[1] - metadata_piece_center[1]]

    def project_solution_point(local_pt: list[float] | tuple[float, float]) -> list[float]:
        if piece_pose is not None:
            return _transform_local_point_to_sheet(local_pt, piece_pose)
        return [float(local_pt[0]) + frame_offset[0], float(local_pt[1]) + frame_offset[1]]

    pc = canvas_xy(piece_center)
    cv2.drawMarker(canvas, pc, (0, 0, 0), markerType=cv2.MARKER_CROSS, markerSize=18, thickness=2)

    drawn_tool_center = None
    if explicit_points and len(explicit_points) > 1:
        projected_points = [project_solution_point(pt) for pt in explicit_points]
        if solution_is_reliable:
            for idx, absolute_pt in enumerate(projected_points):
                mapped = canvas_xy(absolute_pt)
                radius_px = 10
                is_active = idx in active_indexes
                if is_active:
                    cv2.circle(canvas, mapped, radius_px, (0, 180, 0), -1)
                    cv2.circle(canvas, mapped, radius_px, (0, 90, 0), 2)
                else:
                    cv2.circle(canvas, mapped, radius_px, (150, 150, 150), 2)
        drawn_tool_center = [
            sum(p[0] for p in projected_points) / len(projected_points),
            sum(p[1] for p in projected_points) / len(projected_points),
        ]
    elif tool_center is not None:
        local_tool_center = [float(tool_center[0]), float(tool_center[1])]
        if solution_is_reliable and tool_outline:
            mapped_outline = [
                canvas_xy(project_solution_point(_rotate_translate_point(pt, local_tool_center, tool_angle)))
                for pt in tool_outline
            ]
            for a, b in zip(mapped_outline[:-1], mapped_outline[1:]):
                cv2.line(canvas, a, b, (90, 90, 90), 1, cv2.LINE_AA)
        for tool in tool_positions:
            absolute_local = _rotate_translate_point(tool['position'], local_tool_center, tool_angle)
            absolute = project_solution_point(absolute_local)
            mapped = canvas_xy(absolute)
            radius_px = max(4, int(round((tool.get('diameter') or 0.0) * 0.5 * scale)))
            is_active = tool['index'] in active_indexes if solution_is_reliable else False
            if solution_is_reliable and is_active:
                cv2.circle(canvas, mapped, radius_px, (0, 180, 0), -1)
                cv2.circle(canvas, mapped, radius_px, (0, 90, 0), 2)
            else:
                cv2.circle(canvas, mapped, radius_px, (150, 150, 150), 2)
        drawn_tool_center = project_solution_point(local_tool_center)

    if drawn_tool_center is None:
        ref_payload = solution_payload if isinstance(solution_payload, dict) else {}
        drawn_tool_center, _ = _infer_solution_pose(ref_payload)

    if drawn_tool_center is not None:
        tc = canvas_xy(drawn_tool_center)
        cv2.drawMarker(canvas, tc, (20, 20, 220), markerType=cv2.MARKER_TILTED_CROSS, markerSize=18, thickness=2)
        cv2.line(canvas, pc, tc, (90, 90, 90), 1, cv2.LINE_AA)

    active_count = len(active_indexes) if solution_is_reliable else 0
    lines = _build_info_lines(
        metadata=metadata,
        piece_stem=Path(piece_cnc).stem,
        tool_stem=Path(processed_tool_json).stem,
        piece_center=piece_center,
        drawn_tool_center=drawn_tool_center,
        active_count=active_count,
        total_count=len(tool_positions),
    )
    _draw_info_panel(canvas, lines, origin=(out_wh[0] - info_panel_w + 8, 12))
    if not solution_is_reliable:
        _draw_solution_not_found_banner(canvas)

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(output_png), canvas))


def _infer_paths_from_combo_dir(combo_dir: str | Path) -> tuple[Path, Path, Path, Path, dict[str, Any] | None]:
    combo_dir = Path(combo_dir)
    metadata_path = combo_dir / 'metadata.json'
    metadata = _load_json(metadata_path) if metadata_path.exists() else None
    project_root = combo_dir.parent.parent.parent
    if not (project_root / 'TOOLS').exists() and (project_root.parent / 'TOOLS').exists():
        project_root = project_root.parent

    if metadata:
        piece_file = metadata.get('piece_file')
        tool_file = metadata.get('tool_file')
        solution_json = metadata.get('solution_json') or next((p.name for p in combo_dir.glob('*solution*.json')), None) or next((p.name for p in combo_dir.glob('ref_*.json')), None)
    else:
        piece_file = None
        tool_file = None
        solution_json = next((p.name for p in combo_dir.glob('*solution*.json')), None) or next((p.name for p in combo_dir.glob('ref_*.json')), None)

    if not piece_file:
        piece_file = f'OUT_cnc/{combo_dir.parent.name}.cnc'
    if not tool_file:
        processed = list((project_root / 'TOOLS' / 'processed').glob(f'{combo_dir.name}*_with_polygons.json'))
        raw = list((project_root / 'TOOLS').glob(f'{combo_dir.name}.json'))
        tool_file = str(processed[0].relative_to(project_root).as_posix()) if processed else (str(raw[0].relative_to(project_root).as_posix()) if raw else None)

    if not piece_file or not tool_file or not solution_json:
        raise ValueError(f'No se pudieron inferir las rutas desde {combo_dir}')

    piece_cnc = project_root / str(piece_file)
    tool_json = project_root / str(tool_file)
    solution_json_path = combo_dir / Path(solution_json).name if not Path(solution_json).is_absolute() else Path(solution_json)
    output_png = combo_dir / f'{combo_dir.parent.name}__{combo_dir.name}.png'
    return piece_cnc, tool_json, solution_json_path, output_png, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description='Dibuja la solucion de una herramienta sobre la pieza.')
    parser.add_argument('--piece-cnc', help='Ruta al CNC de la pieza')
    parser.add_argument('--tool-json', help='Ruta al JSON de herramienta, preferiblemente *_with_polygons.json')
    parser.add_argument('--solution-json', help='Ruta al JSON de solucion o ref json con toolLocation/toolActive')
    parser.add_argument('--output', help='PNG de salida')
    parser.add_argument('--metadata-json', help='Metadata opcional para rotular el PNG')
    parser.add_argument('--combo-dir', help='Carpeta OUT_solutions/<pieza>/<herramienta> para inferir rutas automaticamente')
    args = parser.parse_args()

    metadata = _load_json(args.metadata_json) if args.metadata_json else None

    if args.combo_dir:
        piece_cnc, tool_json, solution_json, output_png, inferred_metadata = _infer_paths_from_combo_dir(args.combo_dir)
        if metadata is None:
            metadata = inferred_metadata
    else:
        missing = [
            name
            for name, value in [
                ('--piece-cnc', args.piece_cnc),
                ('--tool-json', args.tool_json),
                ('--solution-json', args.solution_json),
                ('--output', args.output),
            ]
            if not value
        ]
        if missing:
            parser.error('Faltan argumentos: ' + ', '.join(missing))
        piece_cnc = Path(args.piece_cnc)
        tool_json = Path(args.tool_json)
        solution_json = Path(args.solution_json)
        output_png = Path(args.output)

    ok = draw_solution_overlay_png(piece_cnc, tool_json, solution_json, output_png, metadata=metadata)
    if not ok:
        print('No se pudo dibujar la solucion.')
        return 1

    print(f'PNG generado: {output_png}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
