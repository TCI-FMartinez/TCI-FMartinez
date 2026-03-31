from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from shutil import rmtree

from modules.parse_head import parse_gcode_head
from modules.parse_parts import parse_gcode_parts
from modules.draw_part import contour_to_points, contours_bbox, draw_contours
from modules.scara_router import route_piece_outputs

try:
    from modules.cnc_to_dxf import parse_cnc_contours, simplify_contour_geometry
except ImportError:
    from modules.cnc_to_dxf_combined import parse_cnc_contours, simplify_contour_geometry

try:
    from modules.cnc_to_dxf import cnc_to_single_dxf
except ImportError:
    from modules.cnc_to_dxf_combined import cnc_to_single_dxf

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
    if os.path.exists(directory):
        rmtree(directory)
    os.makedirs(directory, exist_ok=True)


def ensure_clean_scara_dirs(scara_root: str = "SCARA") -> None:
    ensure_clean_dir(os.path.join(scara_root, "OUT_cnc"))
    ensure_clean_dir(os.path.join(scara_root, "OUT_dxf"))
    ensure_clean_dir(os.path.join(scara_root, "OUT_png"))


def change_extension(directory: str = "INPUT") -> int:
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
    if not os.path.exists(directory):
        return []
    files = []
    for name in os.listdir(directory):
        full_path = os.path.join(directory, name)
        if os.path.isfile(full_path) and name.lower().endswith(extensions):
            files.append(name)
    files.sort()
    return files


def build_tool_polygons(input_tool_path: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    tool_name = os.path.basename(input_tool_path)
    base_name = os.path.splitext(tool_name)[0]
    output_tool_path = os.path.join(output_dir, f"{base_name}_with_polygons.json")
    if not os.path.exists(output_tool_path):
        try:
            from module_ai2.compute_tool import compute_tool as compute_tool_script
            compute_tool_script(input_tool_path, output_tool_path)
        except Exception as exc:
            print(f"Error procesando herramienta '{input_tool_path}': {exc}")
            raise
    return output_tool_path


def run_computeref(ref_file: str, tool_file: str, material_file: str, max_compute_time: int = 60, enhance_opti: int = 1) -> bool:
    exe_path = Path.joinpath("module_ai2", "compute_ref.exe")
    if not os.path.exists(exe_path):
        print(f"Aviso: '{exe_path}' no encontrado en '{os.getcwd()}'. No se ejecutará compute_ref para {ref_file}")
        return False

    cmd = [exe_path, ref_file, tool_file, material_file, str(max_compute_time), str(enhance_opti)]
    print(f"    Ejecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"    Error en compute_ref.exe ({result.returncode})")
        if result.stdout:
            print(f"    stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"    stderr: {result.stderr.strip()}")
        return False

    if result.stdout:
        print(f"    salida: {result.stdout.strip()}")
    return True


def process_out_cnc_with_tools(
    cnc_dir: str = "OUT_cnc",
    tools_dir: str = "TOOLS",
    material_file: str = "module_ai2/material.json",
    processed_tools_subdir: str = "processed",
    max_compute_time: int = 60,
    enhance_opti: int = 1,
) -> None:
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

    tool_names = [name for name in files_finder(tools_dir, extensions=(".json",)) if not name.lower().endswith("_with_polygons.json")]
    if not tool_names:
        print(f"No se encontraron herramientas JSON en '{tools_dir}'")
        return

    processed_tools_dir = os.path.join(tools_dir, processed_tools_subdir)
    os.makedirs(processed_tools_dir, exist_ok=True)

    print(f"Procesando {len(cnc_files)} CNC(s) con {len(tool_names)} herramienta(s) usando compute_ref.exe...")

    for tool_name in tool_names:
        tool_path = os.path.join(tools_dir, tool_name)
        try:
            processed_tool_path = build_tool_polygons(tool_path, processed_tools_dir)
        except Exception:
            print(f"    Saltando herramienta '{tool_name}' por error en el paso de generación de polígonos")
            continue

        for cnc_path in cnc_files:
            print(f"  CNC: {cnc_path}  |  Herramienta: {tool_name}")
            run_computeref(cnc_path, processed_tool_path, material_file, max_compute_time, enhance_opti)


def read_gcode_file(filename: str) -> list[str]:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Archivo '{filename}' no encontrado")
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return None


def material_profile(material_raw: str) -> dict[str, object]:
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
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def compute_piece_metrics(piece_path: str | Path, density_g_cm3: float | None, thickness_mm: float | None) -> dict[str, object]:
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

        draw_ok = draw_contours([piece_path], output_filename=png_path, out_WH=(900, 900), N=72, auto_close_open=True)
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


def main() -> None:
    ensure_clean_dir("OUT_cnc")
    ensure_clean_dir("OUT_dxf")
    ensure_clean_dir("OUT_png")
    ensure_clean_scara_dirs("SCARA")

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

    print("\nProcesamiento completo. Iniciando paso adicional con compute_ref.exe...")
    process_out_cnc_with_tools(
        cnc_dir="OUT_cnc",
        tools_dir="TOOLS",
        material_file=os.path.join("module_ai2", "material.json"),
        processed_tools_subdir="processed",
        max_compute_time=60,
        enhance_opti=1,
    )


if __name__ == "__main__":
    main()
