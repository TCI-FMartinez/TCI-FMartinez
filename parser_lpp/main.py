import os
import sys
from shutil import rmtree

from modules.draw_part import draw_contours
from modules.parse_parts import parse_gcode_parts
from modules.cnc_to_dxf import cnc_to_single_dxf


def ensure_clean_dir(directory):
    if os.path.exists(directory):
        rmtree(directory)
    os.makedirs(directory, exist_ok=True)


def change_extension(directory="INPUT"):
    renamed = 0

    if not os.path.exists(directory):
        print(f"'CAMBIO DE EXTENSIÓN' --> No existe el directorio '{directory}'")
        return 0

    for name in os.listdir(directory):
        old_path = os.path.join(directory, name)
        if os.path.isfile(old_path) and name.lower().endswith(".lpp"):
            new_name = os.path.splitext(name)[0] + ".cnc"
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            renamed += 1

    return renamed


def files_finder(directory, extensions=(".cnc",)):
    if not os.path.exists(directory):
        print(f"No existe el directorio '{directory}'")
        return []

    files = []
    for name in os.listdir(directory):
        full_path = os.path.join(directory, name)
        if os.path.isfile(full_path) and name.lower().endswith(extensions):
            files.append(name)

    files.sort()
    return files


def read_gcode_file(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Archivo '{filename}' no encontrado.")

    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().splitlines()


def process_piece_files(piece_files, output_dir="OUTPUT", dxf_dir="OUT_dxf"):
    for pf in piece_files:
        piece_path = os.path.join(output_dir, pf)

        png_path = os.path.join("OUT_png", f"{os.path.splitext(pf)[0]}.png")

        try:
            ok = draw_contours([piece_path], output_filename=png_path, out_WH=(800, 800), auto_close_open=False)
            if ok:
                print(f"    Imagen creada: '{os.path.basename(png_path)}'")
            else:
                print(f"    No se pudo dibujar '{pf}'")
        except Exception as e:
            print(f"    Error al dibujar '{pf}': {e}")

        dxf_path = os.path.join(dxf_dir, f"{os.path.splitext(pf)[0]}.dxf")

        try:
            result = cnc_to_single_dxf(piece_path, dxf_path)
            if result:
                print(f"    DXF creado: '{os.path.basename(dxf_path)}'")
            else:
                print(f"    No se pudo crear el DXF de '{pf}'")
        except Exception as e:
            print(f"    Error al crear DXF de '{pf}': {e}")


def main():
    ensure_clean_dir("OUTPUT")
    ensure_clean_dir("OUT_dxf")
    ensure_clean_dir("OUT_png")

    renamed = change_extension("INPUT")
    if renamed > 0:
        print(f"Archivos renombrados de .lpp a .cnc: {renamed}")


    files = files_finder("INPUT", extensions=(".cnc",))
    if not files:
        print("No hay archivos .cnc en INPUT")
        sys.exit(0)

    print(f"{len(files)} archivos .cnc encontrados en 'INPUT'.")

    for f in files:
        print(f"\nProcesando '{f}'...")

        before = set(files_finder("OUTPUT", extensions=(".cnc",)))

        file_lines = read_gcode_file(os.path.join("INPUT", f))
        parse_gcode_parts(file_lines)

        after = set(files_finder("OUTPUT", extensions=(".cnc",)))
        new_piece_files = sorted(after - before)

        if not new_piece_files:
            print(f"    No se generaron piezas en 'OUTPUT' para '{f}'.")
            continue

        print(f"    {len(new_piece_files)} piezas generadas en 'OUTPUT' para '{f}'.")
        for pf in new_piece_files:
            print(f"    {pf}")

        process_piece_files(new_piece_files, output_dir="OUTPUT", dxf_dir="OUT_dxf")
        #draw_contours(new_piece_files, out_path="OUT_png", auto_close_open=False)

        for x in new_piece_files:
            print("   ", repr(x))


if __name__ == "__main__":
    main()