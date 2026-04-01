"""Pipeline principal del parser LPP/CNC.

Este script hace dos trabajos encadenados:

1. Separa los programas de entrada en piezas individuales y genera sus salidas
   geométricas básicas (CNC por pieza, PNG y DXF).
2. Lanza el optimizador compute_ref.exe para cada combinación pieza +
   herramienta, guarda la solución obtenida y normaliza la metadata para poder
   comparar resultados después.

Notas importantes:
- compute_ref.exe espera un JSON de referencia de pieza, no un archivo .cnc.
- En Windows el ejecutable se invoca directamente. En Linux/macOS solo funcionará
  si hay wine disponible.
- Un retorno distinto de cero no siempre significa fallo de ejecución. Por
  ejemplo, el flag -6 indica solución inviable, no un error del proceso.
"""

from __future__ import annotations

import ast
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from shutil import rmtree
from typing import Any

from modules.parse_head import parse_gcode_head
from modules.parse_parts import parse_gcode_parts
from modules.draw_part import contour_to_points, contours_bbox, draw_contours
from modules.scara_router import route_piece_outputs
from modules.draw_solution_overlay import draw_solution_overlay_png
from modules.generate_tool_report import generate_tool_report_files

try:
    from modules.cnc_to_dxf import parse_cnc_contours, simplify_contour_geometry
except ImportError:
    from modules.cnc_to_dxf_combined import parse_cnc_contours, simplify_contour_geometry

try:
    from modules.cnc_to_dxf import cnc_to_single_dxf
except ImportError:
    from modules.cnc_to_dxf_combined import cnc_to_single_dxf

# -----------------------------------------------------------------------------
# Configuración general y filtros de clasificación
# -----------------------------------------------------------------------------

META_PATTERN = re.compile(r"^\(\s*META\s+([A-Z0-9_]+)\s*:\s*(.*?)\s*\)$", re.IGNORECASE)

# Configura aqui los filtros de SCARA.
SCARA_FILTERS = {
    "max_bbox_x": 500.0,
    "max_bbox_y": 500.0,
    "max_weight_kg": 6.0,
    "ferromagnetic": None,
    # "material_family_any": ["STEEL", "STAINLESS"],
    # "material_contains_any": ["INOX", "S235"],
}


def ensure_clean_dir(directory: str) -> None:
    """Borra y recrea un directorio para arrancar desde un estado limpio."""
    if os.path.exists(directory):
        rmtree(directory)
    os.makedirs(directory, exist_ok=True)


def ensure_clean_scara_dirs(scara_root: str = "SCARA") -> None:
    """Prepara la estructura de salida específica para SCARA."""
    ensure_clean_dir(os.path.join(scara_root, "OUT_cnc"))
    ensure_clean_dir(os.path.join(scara_root, "OUT_dxf"))
    ensure_clean_dir(os.path.join(scara_root, "OUT_png"))


def change_extension(directory: str = "INPUT") -> int:
    """Renombra archivos .lpp a .cnc dentro del directorio de entrada."""
    if not os.path.exists(directory):
        print(f"No existe el directorio '{directory}'")
        return 0

    renamed = 0
    for name in os.listdir(directory):
        old_path = os.path.join(directory, name)
        if os.path.isfile(old_path) and name.lower().endswith(".lpp"):
            new_path = os.path.join(directory, os.path.splitext(name)[0] + ".cnc")
            os.rename(old_path, new_path)
            renamed += 1
    return renamed


def files_finder(directory: str, extensions=(".cnc",)) -> list[str]:
    """Devuelve los ficheros del directorio que coinciden con las extensiones dadas."""
    if not os.path.exists(directory):
        return []
    files = []
    for name in os.listdir(directory):
        full_path = os.path.join(directory, name)
        if os.path.isfile(full_path) and name.lower().endswith(extensions):
            files.append(name)
    files.sort()
    return files


def _safe_float(value):
    """Convierte valores numéricos tolerando comas decimales y nulos."""
    try:
        if value is None:
            return None
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return None


def material_profile(material_raw: str) -> dict[str, object]:
    """Clasifica material, densidad aproximada y ferromagnetismo de forma heurística."""
    material = (material_raw or "").upper().strip()

    if any(token in material for token in ["ALUM", "ALUMINIO", "ALMG", "5083", "5754", "1050"]):
        return {"density_g_cm3": 2.70, "ferromagnetic": False, "family": "ALUMINUM"}
    if any(token in material for token in ["LATON", "BRASS"]):
        return {"density_g_cm3": 8.50, "ferromagnetic": False, "family": "BRASS"}
    if any(token in material for token in ["COBRE", "COPPER"]):
        return {"density_g_cm3": 8.96, "ferromagnetic": False, "family": "COPPER"}
    if "INOX" in material or "STAINLESS" in material or "AISI 304" in material or "AISI304" in material or "AISI 316" in material or "AISI316" in material:
        ferro = False
        if any(token in material for token in ["430", "409", "441"]):
            ferro = True
        return {"density_g_cm3": 7.90, "ferromagnetic": ferro, "family": "STAINLESS"}
    if any(token in material for token in ["S235", "S275", "S355", "FE", "ACERO", "STEEL", "HIERRO", "GALV", "DC01", "DD11"]):
        return {"density_g_cm3": 7.85, "ferromagnetic": True, "family": "STEEL"}
    return {"density_g_cm3": 7.85, "ferromagnetic": None, "family": material or "UNKNOWN"}


def polygon_signed_area(points: list[tuple[float, float]]) -> float:
    """Calcula el área firmada de un polígono 2D cerrado."""
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def compute_piece_metrics(piece_path: str | Path, density_g_cm3: float | None, thickness_mm: float | None) -> dict[str, object]:
    """Reconstruye la pieza desde CNC y calcula métricas geométricas básicas."""
    contours = parse_cnc_contours(piece_path)
    contours = [simplify_contour_geometry(c) for c in contours]
    contours = [c for c in contours if c.entities]
    if not contours:
        return {"bbox_x": 0.0, "bbox_y": 0.0, "area_mm2": 0.0, "weight_kg": None}

    min_x, min_y, max_x, max_y = contours_bbox(contours, arc_segments=72)
    bbox_x = max_x - min_x
    bbox_y = max_y - min_y

    signed_total = 0.0
    for contour in contours:
        pts = contour_to_points(contour, arc_segments=72, close_if_open=True)
        signed_total += polygon_signed_area(pts)

    area_mm2 = abs(signed_total)
    weight_kg = None
    if density_g_cm3 is not None and thickness_mm is not None:
        density_kg_mm3 = density_g_cm3 * 1e-6
        volume_mm3 = area_mm2 * thickness_mm
        weight_kg = volume_mm3 * density_kg_mm3

    return {"bbox_x": bbox_x, "bbox_y": bbox_y, "area_mm2": area_mm2, "weight_kg": weight_kg}


def format_meta_lines(meta: dict[str, object]) -> list[str]:
    """Convierte el diccionario de metadata en líneas META para la cabecera CNC."""
    lines = []
    order = [
        "SOURCE_FILE",
        "MATERIAL",
        "THICKNESS",
        "DENSITY_G_CM3",
        "FERROMAGNETIC",
        "BBOX_X",
        "BBOX_Y",
        "AREA_MM2",
        "WEIGHT_KG",
        "FORMAT_X",
        "FORMAT_Y",
    ]
    for key in order:
        if key not in meta:
            continue
        value = meta[key]
        if value is None:
            continue
        if isinstance(value, float):
            text = f"{value:.6f}".rstrip("0").rstrip(".")
        else:
            text = str(value)
        lines.append(f"( META {key} : {text} )")
    return lines


def rewrite_piece_header(piece_path: str | Path, source_file: str, head_info: dict[str, object]) -> dict[str, object]:
    """Reescribe la cabecera de una pieza con metadata calculada y heredada."""
    piece_path = Path(piece_path)
    with open(piece_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip("\n") for line in f]

    if len(lines) < 2:
        return {}

    piece_id = lines[0]
    piece_name = lines[1]
    body = [line for line in lines[2:] if not META_PATTERN.match(line.strip())]

    material = str(head_info.get("MATERIAL", "")).strip()
    thickness_mm = _safe_float(head_info.get("THICKNESS"))
    format_xy = head_info.get("FORMAT", (0, 0))
    if not isinstance(format_xy, tuple) or len(format_xy) != 2:
        format_xy = (0, 0)

    profile = material_profile(material)
    metrics = compute_piece_metrics(piece_path, profile["density_g_cm3"], thickness_mm)

    meta = {
        "SOURCE_FILE": source_file,
        "MATERIAL": material,
        "THICKNESS": thickness_mm,
        "DENSITY_G_CM3": profile["density_g_cm3"],
        "FERROMAGNETIC": "YES" if profile["ferromagnetic"] is True else "NO" if profile["ferromagnetic"] is False else "UNKNOWN",
        "BBOX_X": metrics["bbox_x"],
        "BBOX_Y": metrics["bbox_y"],
        "AREA_MM2": metrics["area_mm2"],
        "WEIGHT_KG": metrics["weight_kg"],
        "FORMAT_X": format_xy[0],
        "FORMAT_Y": format_xy[1],
    }

    new_lines = [piece_id, piece_name]
    new_lines.extend(format_meta_lines(meta))
    new_lines.extend(body)

    with open(piece_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(new_lines) + "\n")

    return {
        "material": material,
        "material_family": profile["family"],
        "ferromagnetic": profile["ferromagnetic"],
        "density_g_cm3": profile["density_g_cm3"],
        "thickness_mm": thickness_mm,
        "bbox_x": metrics["bbox_x"],
        "bbox_y": metrics["bbox_y"],
        "area_mm2": metrics["area_mm2"],
        "weight_kg": metrics["weight_kg"],
    }


def process_generated_pieces(piece_files: list[str], source_filename: str, head_info: dict[str, object]) -> None:
    """Procesa cada pieza nueva: cabecera, routing SCARA, PNG y DXF."""
    for pf in piece_files:
        original_piece_path = os.path.join("OUT_cnc", pf)
        piece_meta = rewrite_piece_header(original_piece_path, source_filename, head_info)
        route = route_piece_outputs(
            original_piece_path,
            piece_meta,
            SCARA_FILTERS,
            default_cnc_dir="OUT_cnc",
            default_dxf_dir="OUT_dxf",
            default_png_dir="OUT_png",
            scara_root="SCARA",
            move_cnc=True,
        )

        if route["passed"]:
            print(f"    SCARA OK -> {pf}")
        else:
            print(f"    SCARA NO -> {pf} | {'; '.join(route['reasons'])}")

        piece_path = route["piece_path"]
        png_path = route["png_path"]
        dxf_path = route["dxf_path"]

        draw_ok = draw_contours([piece_path], output_filename=png_path, out_WH=(800, 800), N=72, auto_close_open=True)
        if draw_ok:
            print(f"    PNG creado: {os.path.basename(png_path)}")
        else:
            print(f"    No se pudo crear el PNG de '{pf}'")

        try:
            cnc_to_single_dxf(piece_path, dxf_path, geometry_only=True, separate_layers=False)
            print(f"    DXF creado: {os.path.basename(dxf_path)}")
        except TypeError:
            try:
                cnc_to_single_dxf(piece_path, dxf_path, geometry_only=True)
                print(f"    DXF creado: {os.path.basename(dxf_path)}")
            except Exception as e:
                print(f"    Error al crear DXF de '{pf}': {e}")
        except Exception as e:
            print(f"    Error al crear DXF de '{pf}': {e}")


def read_gcode_file(filename: str) -> list[str]:
    """Lee un archivo CNC completo y lo devuelve como lista de líneas."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Archivo '{filename}' no encontrado")
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()


# -----------------------------------------------------------------------------
# Construcción del ref JSON que consume compute_ref.exe
# -----------------------------------------------------------------------------

def _read_piece_header(piece_path: str | Path) -> tuple[str, str, dict[str, str]]:
    """Lee ID, referencia y bloques META de una pieza ya separada."""
    piece_path = Path(piece_path)
    with open(piece_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip("\n") for line in f]

    piece_id = lines[0].strip() if len(lines) >= 1 else piece_path.stem
    piece_name = lines[1].strip() if len(lines) >= 2 else piece_path.stem
    meta: dict[str, str] = {}

    for line in lines[2:80]:
        match = META_PATTERN.match(line.strip())
        if match:
            meta[match.group(1).upper()] = match.group(2).strip()

    return piece_id, piece_name, meta


def _sanitize_name(value: str) -> str:
    """Normaliza un nombre para usarlo como parte de un fichero o carpeta."""
    text = str(value or "").strip()
    safe = []
    for ch in text:
        if ch.isalnum() or ch in ("-", "_", "."):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "item"


def _segment_to_ref(entity, shift_x: float, shift_y: float) -> dict[str, Any]:
    """Convierte una entidad geométrica interna al formato esperado por ref JSON."""
    start = [float(entity.start[0] - shift_x), float(entity.start[1] - shift_y)]
    end = [float(entity.end[0] - shift_x), float(entity.end[1] - shift_y)]

    if entity.type == "LINE":
        return {
            "type": 1,
            "initialPos": start,
            "finalPos": end,
            "arcCenter": start,
            "arcCenterOff": [0.0, 0.0],
            "arcSense": 0,
        }

    center = [float(entity.center[0] - shift_x), float(entity.center[1] - shift_y)]
    arc_center_off = [float(entity.center[0] - entity.start[0]), float(entity.center[1] - entity.start[1])]
    if entity.clockwise:
        seg_type = 2
        arc_sense = 1
    else:
        seg_type = 3
        arc_sense = -1

    return {
        "type": seg_type,
        "initialPos": start,
        "finalPos": end,
        "arcCenter": center,
        "arcCenterOff": arc_center_off,
        "arcSense": arc_sense,
    }


def _compute_circumcenter(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> tuple[float, float] | None:
    """Calcula el circuncentro de un triángulo o devuelve None si es degenerado."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None

    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return float(ux), float(uy)


def _build_polyshape_from_contours(contours) -> tuple[Any | None, list[list[float]]]:
    """Intenta construir una polyShape y una nube Voronoi aproximada desde contornos CNC."""
    try:
        from shapely.geometry import LineString, Point, Polygon
        from shapely.ops import polygonize, triangulate, unary_union
    except Exception as exc:
        raise RuntimeError(f"Shapely no disponible para construir la referencia JSON: {exc}")

    lines = []
    raw_rings = []
    for contour in contours:
        pts = contour_to_points(contour, arc_segments=64, close_if_open=True)
        if len(pts) < 4:
            continue
        raw_rings.append(pts)
        try:
            lines.append(LineString(pts))
        except Exception:
            continue

    if not lines:
        return None, []

    merged = unary_union(lines)
    polygons = [poly for poly in polygonize(merged) if poly.area > 1e-6]

    polyout = None
    if polygons:
        polyout = unary_union(polygons)
        if hasattr(polyout, "geom_type") and polyout.geom_type == "MultiPolygon":
            polyout = max(polyout.geoms, key=lambda geom: geom.area)
    else:
        candidate_polys = []
        for pts in raw_rings:
            try:
                poly = Polygon(pts)
                if poly.is_valid and poly.area > 1e-6:
                    candidate_polys.append(poly)
            except Exception:
                continue
        if candidate_polys:
            polyout = max(candidate_polys, key=lambda geom: geom.area)

    if polyout is None:
        return None, []

    voronoi = []
    try:
        for tri in triangulate(polyout):
            center = _compute_circumcenter(*list(tri.exterior.coords)[:3])
            if center is None:
                continue
            pt = Point(center)
            if polyout.buffer(1e-9).contains(pt):
                voronoi.append([float(center[0]), float(center[1])])
    except Exception:
        voronoi = []

    return polyout, voronoi


def build_ref_json_for_piece(piece_cnc: str | Path, output_json: str | Path) -> Path:
    """Genera el ref JSON de una pieza para pasárselo a compute_ref.exe."""
    try:
        from shapely import affinity
        from shapely.geometry import mapping
    except Exception as exc:
        raise RuntimeError(f"Shapely no disponible para exportar ref JSON: {exc}")

    piece_cnc = Path(piece_cnc)
    output_json = Path(output_json)
    piece_id, piece_name, meta = _read_piece_header(piece_cnc)

    contours = parse_cnc_contours(piece_cnc)
    contours = [simplify_contour_geometry(c) for c in contours]
    contours = [c for c in contours if c.entities]
    if not contours:
        raise ValueError(f"No se detectaron contornos en '{piece_cnc}'")

    min_x, min_y, max_x, max_y = contours_bbox(contours, arc_segments=72)
    shift_x = min_x
    shift_y = min_y

    polyout, voronoi = _build_polyshape_from_contours(contours)
    if polyout is not None:
        polyout = affinity.translate(polyout, xoff=-shift_x, yoff=-shift_y)
        bbox_bounds = polyout.bounds
        bbox_points = [
            [float(bbox_bounds[0]), float(bbox_bounds[1])],
            [float(bbox_bounds[2]), float(bbox_bounds[1])],
            [float(bbox_bounds[2]), float(bbox_bounds[3])],
            [float(bbox_bounds[0]), float(bbox_bounds[3])],
        ]
        voronoi_shifted = [[float(p[0] - shift_x), float(p[1] - shift_y)] for p in voronoi]
        polyshape_data = mapping(polyout)
        computable = 1
    else:
        bbox_points = [
            [0.0, 0.0],
            [float(max_x - min_x), 0.0],
            [float(max_x - min_x), float(max_y - min_y)],
            [0.0, float(max_y - min_y)],
        ]
        voronoi_shifted = []
        polyshape_data = None
        computable = 0

    contour_items = []
    for contour in contours:
        pts = contour_to_points(contour, arc_segments=72, close_if_open=True)
        signed_area = polygon_signed_area([(float(x), float(y)) for x, y in pts])
        contour_type = 0 if signed_area >= 0 else 1
        sense = 1 if signed_area >= 0 else -1

        segments = [_segment_to_ref(entity, shift_x, shift_y) for entity in contour.entities]
        contour_entry = {
            "totalSegments": len(segments),
            "type": contour_type,
            "sense": sense,
            "segments": segments[0] if len(segments) == 1 else segments,
        }
        contour_items.append(contour_entry)

    material = meta.get("MATERIAL", "")
    thickness = _safe_float(meta.get("THICKNESS")) or 0.0

    payload = {
        "reference": piece_name or piece_cnc.stem,
        "pieceId": piece_id,
        "sourceCnc": str(piece_cnc.as_posix()),
        "boundingBox": bbox_points,
        "angle": 0,
        "computable": computable,
        "toolLocation": [],
        "toolActive": [],
        "thickness": float(thickness),
        "material": material,
        "geometry": {
            "totalContours": len(contour_items),
            "contours": contour_items[0] if len(contour_items) == 1 else contour_items,
            "voronoi": voronoi_shifted,
            "polyShape": polyshape_data,
        },
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return output_json


# -----------------------------------------------------------------------------
# Utilidades de herramientas y solver
# -----------------------------------------------------------------------------

def _load_json(path: str | Path) -> Any:
    """Carga un JSON desde disco."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: str | Path, payload: Any) -> None:
    """Guarda un JSON en disco creando carpetas intermedias si hace falta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _flatten_tool_payload(payload: Any) -> list[dict[str, Any]]:
    """Normaliza diferentes variantes del JSON de herramienta a una lista plana."""
    if isinstance(payload, list):
        if payload and all(isinstance(item, dict) and "diameter" in item and "position" in item for item in payload):
            return payload
        if payload and isinstance(payload[0], dict) and isinstance(payload[0].get("tool"), list):
            tool_items = payload[0]["tool"]
            if all(isinstance(item, dict) and "diameter" in item and "position" in item for item in tool_items):
                return tool_items
    if isinstance(payload, dict) and isinstance(payload.get("tool"), list):
        tool_items = payload["tool"]
        if all(isinstance(item, dict) and "diameter" in item and "position" in item for item in tool_items):
            return tool_items
    raise ValueError("Formato de herramienta JSON no soportado")


def build_tool_polygons(input_tool_path: str, output_dir: str) -> str:
    """Genera la herramienta enriquecida con polígonos para compute_ref."""
    os.makedirs(output_dir, exist_ok=True)
    tool_name = os.path.basename(input_tool_path)
    base_name = os.path.splitext(tool_name)[0]
    output_tool_path = os.path.join(output_dir, f"{base_name}_with_polygons.json")
    if os.path.exists(output_tool_path):
        return output_tool_path

    payload = _load_json(input_tool_path)
    flat_tools = _flatten_tool_payload(payload)

    try:
        from module_ai2.compute_tool import compute_tool as compute_tool_script
        compute_tool_script_data = compute_tool_script
    except Exception as exc:
        raise RuntimeError(f"No se pudo importar compute_tool.py: {exc}")

    temp_input_path = os.path.join(output_dir, f"{base_name}__flat.json")
    _dump_json(temp_input_path, flat_tools)
    compute_tool_script_data(temp_input_path, output_tool_path)
    return output_tool_path


def _tool_candidates(tools_dir: str) -> list[str]:
    """Lista las herramientas base candidatas, excluyendo salidas ya procesadas."""
    if not os.path.isdir(tools_dir):
        return []

    items = []
    for name in sorted(os.listdir(tools_dir)):
        full = os.path.join(tools_dir, name)
        if not os.path.isfile(full):
            continue
        low = name.lower()
        if not low.endswith(".json"):
            continue
        if low.endswith("_with_polygons.json"):
            continue
        items.append(name)
    return items


def _read_tool_positions(tool_json_path: str | Path) -> list[dict[str, Any]]:
    """Lee posiciones, diámetros y datos útiles de una herramienta JSON."""
    payload = _load_json(tool_json_path)
    tools = _flatten_tool_payload(payload)
    result = []
    for idx, item in enumerate(tools):
        pos = item.get("position", [0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = [0.0, 0.0]
        result.append(
            {
                "index": idx,
                "position": [float(pos[0]), float(pos[1])],
                "diameter": float(item.get("diameter", 0.0) or 0.0),
                "type": item.get("type"),
                "force": item.get("force"),
            }
        )
    return result


def _find_compute_ref_executable() -> tuple[list[str] | None, str | None]:
    """Resuelve cómo ejecutar compute_ref.exe según el sistema operativo."""
    exe_path = Path("module_ai2") / "compute_ref.exe"
    if not exe_path.exists():
        return None, f"No existe '{exe_path.as_posix()}'"

    exe_abs = str(exe_path.resolve())
    if os.name == "nt":
        return [exe_abs], None

    wine_path = shutil.which("wine")
    if wine_path:
        return [wine_path, exe_abs], None

    return None, "compute_ref.exe es un binario Windows y no hay 'wine' disponible en este entorno"


def _normalize_signed_returncode(returncode: int) -> int:
    """Convierte códigos de retorno Windows sin signo a enteros con signo."""
    if returncode > 0x7FFFFFFF:
        return returncode - 0x100000000
    return returncode


def _parse_compute_ref_report(text: str) -> dict[str, Any]:
    """Extrae del log del solver datos como xmin, fxmin, flag y time limit."""
    info: dict[str, Any] = {
        "time_limit_hit": False,
        "xmin": None,
        "fxmin": None,
        "error_flag": None,
        "solution_saved_to": None,
    }
    if not text:
        return info

    if re.search(r"time limit\s*\([^)]+\)\s*exceeded", text, flags=re.IGNORECASE):
        info["time_limit_hit"] = True

    xmin_match = re.search(r"^\s*xmin:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if xmin_match:
        raw_xmin = xmin_match.group(1).strip()
        try:
            parsed = ast.literal_eval(raw_xmin)
            if isinstance(parsed, (list, tuple)):
                info["xmin"] = [float(v) for v in parsed]
            else:
                info["xmin"] = raw_xmin
        except Exception:
            info["xmin"] = raw_xmin

    fxmin_match = re.search(r"^\s*fxmin:\s*([^\r\n]+)", text, flags=re.MULTILINE)
    if fxmin_match:
        try:
            info["fxmin"] = float(fxmin_match.group(1).strip())
        except Exception:
            info["fxmin"] = fxmin_match.group(1).strip()

    flag_matches = re.findall(r"^\s*(?:Error flag|Flag):\s*(-?\d+)", text, flags=re.MULTILINE)
    if flag_matches:
        try:
            info["error_flag"] = int(flag_matches[-1])
        except Exception:
            pass

    saved_match = re.search(r"Solution saved to:\s*([^\r\n]+)", text, flags=re.IGNORECASE)
    if saved_match:
        info["solution_saved_to"] = saved_match.group(1).strip()

    return info


def run_computeref(
    ref_file: str,
    tool_file: str,
    material_file: str,
    workdir: str,
    max_compute_time: int = 60,
    enhance_opti: int = 1,
) -> dict[str, Any]:
    """Ejecuta compute_ref y devuelve un resultado rico, no solo el returncode."""
    cmd_prefix, error = _find_compute_ref_executable()
    if cmd_prefix is None:
        return {
            "ok": False,
            "executed": False,
            "reason": error,
            "stdout": "",
            "stderr": "",
            "new_files": [],
            "returncode_raw": None,
            "returncode_signed": None,
            "report": _parse_compute_ref_report(""),
        }

    ref_abs = str(Path(ref_file).resolve())
    tool_abs = str(Path(tool_file).resolve())
    material_abs = str(Path(material_file).resolve())
    workdir_path = Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)

    before = {str(p.name) for p in workdir_path.iterdir() if p.is_file()}
    cmd = cmd_prefix + [ref_abs, tool_abs, material_abs, str(max_compute_time), str(enhance_opti)]
    print(f"    Ejecutando: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=str(workdir_path), capture_output=True, text=True)
    except Exception as exc:
        return {
            "ok": False,
            "executed": False,
            "reason": str(exc),
            "stdout": "",
            "stderr": "",
            "new_files": [],
            "returncode_raw": None,
            "returncode_signed": None,
            "report": _parse_compute_ref_report(""),
        }

    after_files = sorted(str(p.name) for p in workdir_path.iterdir() if p.is_file())
    new_files = [str(workdir_path / name) for name in after_files if name not in before]
    signed_returncode = _normalize_signed_returncode(int(result.returncode))
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    report = _parse_compute_ref_report("\n".join(part for part in (stdout, stderr) if part))

    return {
        "ok": signed_returncode == 0,
        "executed": True,
        "reason": None if signed_returncode == 0 else f"compute_ref devolvió código {signed_returncode}",
        "stdout": stdout,
        "stderr": stderr,
        "new_files": new_files,
        "returncode_raw": int(result.returncode),
        "returncode_signed": signed_returncode,
        "report": report,
    }


def _contains_solution_keys(payload: Any) -> bool:
    """Comprueba si un JSON contiene una solución real y no solo la plantilla base."""
    if isinstance(payload, dict):
        if "toolLocation" in payload:
            locs = _extract_xy_list(payload.get("toolLocation"))
            if locs:
                return True
        if "toolActive" in payload:
            active_raw = payload.get("toolActive")
            if isinstance(active_raw, (list, tuple)) and len(active_raw) > 0:
                if any(bool(v) for v in active_raw):
                    return True
        return any(_contains_solution_keys(v) for v in payload.values())
    if isinstance(payload, list):
        return any(_contains_solution_keys(item) for item in payload)
    return False


def discover_solution_json(
    combo_dir: str | Path,
    ref_json_path: str | Path,
    run_result: dict[str, Any] | None = None,
) -> str | None:
    """Localiza el JSON de solución priorizando la pista del propio solver."""
    combo_dir = Path(combo_dir)
    ref_json_path = Path(ref_json_path)
    report = (run_result or {}).get("report") or {}
    saved_path = report.get("solution_saved_to")
    if saved_path:
        candidate = Path(saved_path)
        if not candidate.is_absolute():
            candidate = combo_dir / candidate
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    named_candidates = []
    for path in sorted(combo_dir.glob("*solution*.json")):
        if path.exists() and path.is_file():
            named_candidates.append((0, -path.stat().st_mtime, str(path)))
    if named_candidates:
        named_candidates.sort()
        return named_candidates[0][2]

    candidates = []
    for path in sorted(combo_dir.glob("*.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        if _contains_solution_keys(payload):
            priority = 0 if path.name != ref_json_path.name else 1
            candidates.append((priority, -path.stat().st_mtime, str(path)))

    if not candidates:
        return None

    candidates.sort()
    return candidates[0][2]


# -----------------------------------------------------------------------------
# Lectura e interpretación de soluciones del solver
# -----------------------------------------------------------------------------

def _extract_first_xy(value: Any) -> list[float] | None:
    """Busca el primer punto XY reconocible dentro de una estructura anidada."""
    if isinstance(value, dict):
        if "x" in value and "y" in value:
            return [float(value["x"]), float(value["y"])]
        for key in ("position", "point", "center", "location"):
            out = _extract_first_xy(value.get(key))
            if out is not None:
                return out
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            return [float(value[0]), float(value[1])]
        for item in value:
            out = _extract_first_xy(item)
            if out is not None:
                return out
    return None


def _extract_xy_list(value: Any) -> list[list[float]]:
    """Extrae todos los puntos XY posibles de una estructura anidada."""
    out: list[list[float]] = []
    if isinstance(value, dict):
        if "x" in value and "y" in value:
            return [[float(value["x"]), float(value["y"])] ]
        for v in value.values():
            out.extend(_extract_xy_list(v))
        return out
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            return [[float(value[0]), float(value[1])]]
        for item in value:
            out.extend(_extract_xy_list(item))
    return out


def _extract_tool_active(value: Any, expected_len: int) -> list[int]:
    """Normaliza distintas codificaciones de útiles activos a índices enteros."""
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


def _piece_center_from_ref(ref_payload: dict[str, Any]) -> list[float]:
    """Calcula el centro aproximado de la pieza a partir de su bounding box."""
    bbox = ref_payload.get("boundingBox") or []
    points = [p for p in bbox if isinstance(p, (list, tuple)) and len(p) == 2]
    if not points:
        return [0.0, 0.0]
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return [0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys))]


def _infer_solution_location(solution_payload: Any) -> list[float] | None:
    """Intenta inferir el centro de colocación de herramienta desde la solución."""
    if isinstance(solution_payload, dict):
        for key in ("toolLocation", "location", "bestLocation", "solutionLocation", "center", "position"):
            if key in solution_payload:
                out = _extract_first_xy(solution_payload[key])
                if out is not None:
                    return out
        for value in solution_payload.values():
            out = _infer_solution_location(value)
            if out is not None:
                return out
    elif isinstance(solution_payload, list):
        for item in solution_payload:
            out = _infer_solution_location(item)
            if out is not None:
                return out
    return None


def _infer_solution_points(solution_payload: Any) -> list[list[float]]:
    """Extrae los puntos de herramienta que el solver haya dejado en la solución."""
    if isinstance(solution_payload, dict):
        for key in ("toolLocation", "points", "locations", "activePoints"):
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
    """Intenta recuperar qué ventosas/imanes quedaron activos en la solución."""
    if isinstance(solution_payload, dict):
        for key in ("toolActive", "active", "activeTools", "activeIndexes"):
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
    """Calcula la distancia euclídea entre dos puntos XY."""
    if a is None or b is None:
        return None
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _build_solution_metadata(
    piece_cnc: str | Path,
    ref_json_path: str | Path,
    tool_json_path: str | Path,
    solution_json_path: str | None,
    combo_dir: str | Path,
    run_result: dict[str, Any],
) -> dict[str, Any]:
    """Construye la metadata normalizada de una combinación pieza + herramienta."""
    piece_cnc = Path(piece_cnc)
    ref_payload = _load_json(ref_json_path)
    tool_positions = _read_tool_positions(tool_json_path)
    solution_payload = _load_json(solution_json_path) if solution_json_path and os.path.exists(solution_json_path) else {}
    piece_id, piece_name, piece_meta = _read_piece_header(piece_cnc)
    report = run_result.get("report") or {}

    piece_center = _piece_center_from_ref(ref_payload)
    tool_center = _infer_solution_location(solution_payload)
    solution_points = _infer_solution_points(solution_payload)
    if tool_center is None and solution_points:
        tool_center = [
            sum(p[0] for p in solution_points) / len(solution_points),
            sum(p[1] for p in solution_points) / len(solution_points),
        ]

    active_indexes = _infer_solution_active(solution_payload, len(tool_positions))
    center_distance = _distance_xy(piece_center, tool_center)
    solution_geometry_found = _contains_solution_keys(solution_payload)
    error_flag = report.get("error_flag")
    returncode_signed = run_result.get("returncode_signed")

    if error_flag is None and isinstance(returncode_signed, int) and returncode_signed != 0:
        error_flag = returncode_signed

    # Ojo: un returncode no cero no siempre es un fallo de ejecución.
    # Aquí se distingue entre error real del proceso, solución inviable y
    # solución válida o incompleta.
    status = "execution_error"
    if run_result.get("executed"):
        if error_flag in (None, 0):
            if solution_geometry_found:
                status = "valid"
            elif solution_json_path:
                status = "completed_without_geometry"
            else:
                status = "completed_without_solution"
        elif error_flag == -6:
            status = "infeasible_cannot_lift"
        else:
            status = "solver_error"

    return {
        "piece_file": str(piece_cnc.as_posix()),
        "piece_id": piece_id,
        "piece_reference": piece_name,
        "piece_material": piece_meta.get("MATERIAL", ""),
        "piece_thickness": _safe_float(piece_meta.get("THICKNESS")),
        "piece_center_approx": piece_center,
        "tool_file": str(Path(tool_json_path).as_posix()),
        "tool_elements_total": len(tool_positions),
        "solution_json": str(Path(solution_json_path).as_posix()) if solution_json_path else None,
        "solution_found": bool(solution_json_path),
        "solution_geometry_found": solution_geometry_found,
        "solution_valid": status == "valid",
        "status": status,
        "tool_center_approx": tool_center,
        "center_distance_approx": center_distance,
        "score_distance_centers_approx": center_distance,
        "tool_active_indexes": active_indexes,
        "tool_active_count": len(active_indexes),
        "run_ok": bool(run_result.get("ok")),
        "run_executed": bool(run_result.get("executed")),
        "run_reason": run_result.get("reason"),
        "returncode_raw": run_result.get("returncode_raw"),
        "returncode_signed": returncode_signed,
        "solver_error_flag": error_flag,
        "time_limit_hit": bool(report.get("time_limit_hit")),
        "solver_xmin": report.get("xmin"),
        "solver_fxmin": report.get("fxmin"),
        "solver_solution_saved_to": report.get("solution_saved_to"),
        "stdout": (run_result.get("stdout") or "").strip(),
        "stderr": (run_result.get("stderr") or "").strip(),
        "combo_dir": str(Path(combo_dir).as_posix()),
    }


# -----------------------------------------------------------------------------
# Generación de metadata y overlays de solución
# -----------------------------------------------------------------------------

def _draw_solution_overlay(
    piece_cnc: str | Path,
    processed_tool_json: str | Path,
    solution_json: str | Path,
    output_png: str | Path,
    metadata: dict[str, Any] | None = None,
    out_wh: tuple[int, int] = (900, 900),
) -> bool:
    """Dibuja el overlay delegando en el modulo reutilizable.

    La decisión de pintar o no la herramienta debe salir del metadata.json
    generado por compute_ref. Si solution_valid=True, se pinta encima de la
    pieza. Si es False, el renderer deja el texto de "Solución no encontrada".
    """
    return draw_solution_overlay_png(
        piece_cnc=piece_cnc,
        processed_tool_json=processed_tool_json,
        solution_json=solution_json,
        output_png=output_png,
        metadata=metadata,
        out_wh=out_wh,
    )


def process_out_cnc_with_tools(
    cnc_dir: str = "OUT_cnc",
    tools_dir: str = "TOOLS",
    material_file: str = "module_ai2/material.json",
    processed_tools_subdir: str = "processed",
    max_compute_time: int = 60,
    enhance_opti: int = 1,
    solutions_dir: str = "OUT_solutions",
) -> None:
    """Ejecuta todas las combinaciones CNC x herramienta y consolida sus resultados."""
    cnc_dirs = [cnc_dir]
    scara_cnc_dir = os.path.join("SCARA", "OUT_cnc")
    if os.path.isdir(scara_cnc_dir) and scara_cnc_dir != cnc_dir:
        cnc_dirs.append(scara_cnc_dir)

    if not os.path.exists(material_file):
        print(f"No existe el archivo de material requerido: '{material_file}'")
        return

    cnc_files = []
    for directory in cnc_dirs:
        cnc_files.extend([os.path.join(directory, name) for name in files_finder(directory, extensions=(".cnc",))])

    if not cnc_files:
        print("No se encontraron CNCs en OUT_cnc para procesar con compute_ref.exe")
        return

    tool_names = _tool_candidates(tools_dir)
    if not tool_names:
        print(f"No se encontraron herramientas JSON en '{tools_dir}'")
        return

    processed_tools_dir = os.path.join(tools_dir, processed_tools_subdir)
    os.makedirs(processed_tools_dir, exist_ok=True)
    ensure_clean_dir(solutions_dir)
    png_dir = os.path.join(solutions_dir, "png")
    os.makedirs(png_dir, exist_ok=True)

    print(f"Procesando {len(cnc_files)} CNC(s) con {len(tool_names)} herramienta(s) usando compute_ref.exe...")

    summary: list[dict[str, Any]] = []

    for cnc_path in cnc_files:
        piece_stem = Path(cnc_path).stem
        piece_dir = os.path.join(solutions_dir, piece_stem)
        os.makedirs(piece_dir, exist_ok=True)

        for tool_name in tool_names:
            tool_path = os.path.join(tools_dir, tool_name)
            tool_stem = Path(tool_name).stem
            combo_dir = os.path.join(piece_dir, tool_stem)
            os.makedirs(combo_dir, exist_ok=True)

            try:
                processed_tool_path = build_tool_polygons(tool_path, processed_tools_dir)
            except Exception as exc:
                print(f"    Saltando herramienta '{tool_name}' por error en el paso de generación de polígonos: {exc}")
                summary.append(
                    {
                        "piece_file": cnc_path,
                        "tool_file": tool_path,
                        "solution_found": False,
                        "run_ok": False,
                        "run_reason": f"Error generando polígonos: {exc}",
                        "combo_dir": combo_dir,
                    }
                )
                continue

            ref_json_path = os.path.join(combo_dir, f"ref_{piece_stem}.json")
            try:
                build_ref_json_for_piece(cnc_path, ref_json_path)
            except Exception as exc:
                print(f"    No se pudo generar ref JSON para '{cnc_path}': {exc}")
                summary.append(
                    {
                        "piece_file": cnc_path,
                        "tool_file": tool_path,
                        "solution_found": False,
                        "run_ok": False,
                        "run_reason": f"Error generando ref JSON: {exc}",
                        "combo_dir": combo_dir,
                    }
                )
                continue

            print(f"  CNC: {cnc_path}  |  Herramienta: {tool_name}")
            run_result = run_computeref(
                ref_file=ref_json_path,
                tool_file=processed_tool_path,
                material_file=material_file,
                workdir=combo_dir,
                max_compute_time=max_compute_time,
                enhance_opti=enhance_opti,
            )

            if not run_result["ok"]:
                print(f"    compute_ref no completado: {run_result.get('reason')}")
                if run_result.get("stdout"):
                    print(f"    stdout: {run_result['stdout'].strip()}")
                if run_result.get("stderr"):
                    print(f"    stderr: {run_result['stderr'].strip()}")
            elif run_result.get("stdout"):
                print(f"    salida: {run_result['stdout'].strip()}")

            solution_json_path = discover_solution_json(combo_dir, ref_json_path, run_result=run_result)
            metadata = _build_solution_metadata(
                piece_cnc=cnc_path,
                ref_json_path=ref_json_path,
                tool_json_path=processed_tool_path,
                solution_json_path=solution_json_path,
                combo_dir=combo_dir,
                run_result=run_result,
            )

            # compute_ref puede dejar su propio metadata.json en la carpeta de la
            # combinación, pero a menudo la metadata más completa la construye este
            # parser. Para dibujar el overlay se usa una mezcla de ambas, dando
            # prioridad a los valores del solver cuando existan.
            solver_metadata_path = os.path.join(combo_dir, "metadata.json")
            solver_metadata = None
            if os.path.exists(solver_metadata_path):
                try:
                    solver_metadata = _load_json(solver_metadata_path)
                except Exception:
                    solver_metadata = None

            overlay_name = f"{piece_stem}__{tool_stem}.png"
            combo_overlay_path = os.path.join(combo_dir, overlay_name)
            global_overlay_path = os.path.join(png_dir, overlay_name)

            should_render = bool(solution_json_path and os.path.exists(solution_json_path))
            metadata_for_draw = dict(metadata)
            if solver_metadata is not None:
                metadata_for_draw.update(solver_metadata)

            if should_render:
                try:
                    overlay_ok_combo = _draw_solution_overlay(
                        cnc_path,
                        processed_tool_path,
                        solution_json_path,
                        combo_overlay_path,
                        metadata=metadata_for_draw,
                    )
                    overlay_ok_global = _draw_solution_overlay(
                        cnc_path,
                        processed_tool_path,
                        solution_json_path,
                        global_overlay_path,
                        metadata=metadata_for_draw,
                    )
                    metadata["solution_png"] = combo_overlay_path if overlay_ok_combo else None
                    metadata["solution_png_global"] = global_overlay_path if overlay_ok_global else None
                except Exception as exc:
                    metadata["solution_png"] = None
                    metadata["solution_png_global"] = None
                    metadata["png_error"] = str(exc)
                    print(f"    Error dibujando overlay: {exc}")
            else:
                metadata["solution_png"] = None
                metadata["solution_png_global"] = None

            # Guardar metadata propia sin sobrescribir la del solver.
            parser_metadata_path = os.path.join(combo_dir, "metadata_parser.json")
            _dump_json(parser_metadata_path, metadata)
            summary.append(metadata)

    _dump_json(os.path.join(solutions_dir, "summary.json"), summary)


# -----------------------------------------------------------------------------
# Punto de entrada
# -----------------------------------------------------------------------------

def main() -> None:
    """Orquesta el pipeline completo: separación, salidas geométricas y optimización."""
    ensure_clean_dir("OUT_cnc")
    ensure_clean_dir("OUT_dxf")
    ensure_clean_dir("OUT_png")
    ensure_clean_scara_dirs("SCARA")
    ensure_clean_dir("OUT_solutions")

    renamed = change_extension("INPUT")
    if renamed > 0:
        print(f"Archivos renombrados de .lpp a .cnc: {renamed}")

    files = files_finder("INPUT", extensions=(".cnc",))
    if not files:
        print("No hay archivos .cnc en INPUT")
        sys.exit(0)

    print(f"{len(files)} archivos .cnc encontrados en INPUT")

    for filename in files:
        print(f"\nProcesando '{filename}'...")
        source_path = os.path.join("INPUT", filename)
        file_lines = read_gcode_file(source_path)
        head_info = parse_gcode_head(file_lines)

        before = set(files_finder("OUT_cnc", extensions=(".cnc",)))
        parse_gcode_parts(file_lines)
        after = set(files_finder("OUT_cnc", extensions=(".cnc",)))
        new_piece_files = sorted(after - before)

        if not new_piece_files:
            print(f"    No se generaron piezas en OUT_cnc para '{filename}'")
            continue

        print(f"    {len(new_piece_files)} piezas generadas")
        process_generated_pieces(new_piece_files, filename, head_info)

    print("\n")
    print("=" * 70)
    print("Procesamiento completo. Iniciando paso adicional con compute_ref.exe...")
    process_out_cnc_with_tools(
        cnc_dir="OUT_cnc",
        tools_dir="TOOLS",
        material_file=os.path.join("module_ai2", "material.json"),
        processed_tools_subdir="processed",
        max_compute_time=2,
        enhance_opti=1,
        solutions_dir="OUT_solutions",
    )
    
    print("\n")
    print("=" * 70)
    print("\nGenerando informe de estadísticas desde summary.json")
    summary_path = os.path.join("OUT_solutions", "summary.json")
    if os.path.exists(summary_path):
        try:
            generate_tool_report_files(summary_path, output_dir=os.path.join("OUT_solutions", "report"))

        except Exception as exc:
            print(f"Error generando informe de estadísticas: {exc}")
    else:
        print(f"No se encontró '{summary_path}' para generar el informe de estadísticas.")

if __name__ == "__main__":
    main()
