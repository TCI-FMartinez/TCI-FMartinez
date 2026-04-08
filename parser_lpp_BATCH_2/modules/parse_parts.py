import re
from pathlib import Path
from os import path


def parse_gcode_parts(file_content, output_dir="OUT_cnc"):
    """Extrae piezas del G-code y las escribe en el directorio indicado.

    Devuelve la lista ordenada de nombres de archivo CNC generados.
    """
    print("\nInicida la busqueda de piezas...")
    current_line = 0
    procesed_id = []
    generated_files = []
    current_piece_id = -1
    current_contour = []
    piece_id = None
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Regular expressions para identificar piezas y el fin de una pieza
    piece_pattern = r'^\(P(\d+):ID(\d+):(.*?)\)'
    n_pattern = r'^N\d+\s'
    end_part_call_pattern = re.compile(r"\bP9103\b")

    n_lines = len(file_content)

    while current_line <= n_lines - 1:
        piece_match = re.match(piece_pattern, file_content[current_line])

        if piece_match:
            piece_id = piece_match.group(2)
            piece_name = piece_match.group(3)
            if procesed_id.count(piece_id) == 0:
                procesed_id.append(piece_id)
                current_piece_id = piece_id
                current_piece_name = piece_name
                output_filename = output_dir / f"ID{current_piece_id}_{current_piece_name}.cnc"
                print(f"    --> {file_content[current_line]}")

        else:
            if end_part_call_pattern.search(file_content[current_line]) and current_piece_id == piece_id:
                nxxx_match = re.match(n_pattern, file_content[current_line])
                if nxxx_match and current_piece_id == piece_id:
                    _, n_characters = nxxx_match.span()
                    current_contour.append(file_content[current_line][n_characters:])
                else:
                    current_contour.append(file_content[current_line])

                with open(output_filename, "w", encoding="utf-8", newline="\n") as archivo:
                    archivo.write(f"{current_piece_id}\n")
                    archivo.write(f"{current_piece_name}\n")
                    for c in current_contour:
                        archivo.write(f"{c}\n")
                generated_files.append(output_filename.name)

                current_piece_id = None
                current_piece_name = None
                current_contour = []

            else:
                nxxx_match = re.match(n_pattern, file_content[current_line])
                if nxxx_match and current_piece_id == piece_id:
                    _, n_characters = nxxx_match.span()
                    current_contour.append(file_content[current_line][n_characters:])
                else:
                    if current_piece_id == piece_id:
                        current_contour.append(file_content[current_line])

        current_line += 1

    print(len(procesed_id), "piezas encontradas")
    generated_files.sort()
    return generated_files


if __name__ == "__main__":
    filename = "SKRLJ-INOX-10.cnc"

    if not path.exists(filename):
        print(f"Archivo {filename} no encontrado.")
    else:
        with open(filename, "r", encoding="utf-8") as text_r_file:
            gcode_content = text_r_file.read()

        file_lines = gcode_content.splitlines()
        parse_gcode_parts(file_lines)
