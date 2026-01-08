
import re
from os import sep, path

def parse_gcode_parts(file_content):
    print("\nInicida la busqueda de piezas...")
    current_line = 0
    procesed_id = []
    current_piece_id = -1
    current_contour = []
    piece_id = None
    
    # Regular expressions para identificar piezas, comandos de corte y el fin de una pieza
    piece_pattern = r'^\(P(\d+):ID(\d+):(.*?)\)'  # Para identificar piezas al inicio de la línea
    gcode_pattern = r'^N\d+\s+G[123]'  # Comandos de corte (G1, G2, G3) con el numerador
    N_pattern = r'^N\d+\s'  # N de línea
    end_part_call_pattern = re.compile(r"\bP9103\b")  # Para detectar el fin de una pieza
    clean_line_pattern = r'\s*;?\s*$'  # Para eliminar los espacios y el punto y coma al final

    # Parsear el archivo línea por línea
    n_lines = len(file_content)

    while current_line <= n_lines - 1:
        # Identificar el nombre de la pieza (por ejemplo, P1:ID1:test20mmINOX)
        piece_match = re.match(piece_pattern, file_content[current_line])
        
        if piece_match:
            piece_id = piece_match.group(2)
            piece_name = piece_match.group(3)
            if procesed_id.count(piece_id) == 0:  # Pieza nueva
                procesed_id.append(piece_id)
                current_piece_id = piece_id
                current_piece_name = piece_name
                output_filename = f"OUTPUT{sep}ID{current_piece_id}_{current_piece_name}.cnc"
                                
                print(f"    --> {file_content[current_line]}")
        
        else:
            # Si se detecta final de pieza o inicio de una nueva se guarda la pieza.
            if end_part_call_pattern.search(file_content[current_line]) and current_piece_id == piece_id:
                #print("----> Final de pieza encontrado.", file_content[current_line])

                Nxxx_match = re.match(N_pattern, file_content[current_line])
                if Nxxx_match and current_piece_id == piece_id:
                    _, n_caracters = Nxxx_match.span()                  
                    current_contour.append(file_content[current_line][n_caracters:])
                else:
                    current_contour.append(file_content[current_line])
                                       
                # Se guarda la pieza:
                with open(output_filename, "w") as archivo:
                    archivo.write(f"{current_piece_id}\n")
                    archivo.write(f"{current_piece_name}\n")
                    for c in current_contour:
                        archivo.write(f"{c}\n")

                current_piece_id = None
                current_piece_name = None
                current_contour = []
                
            else:  # Si no se detecta final de pieza
                Nxxx_match = re.match(N_pattern, file_content[current_line])
                if Nxxx_match and current_piece_id == piece_id:
                    _, n_caracters = Nxxx_match.span()                  
                    current_contour.append(file_content[current_line][n_caracters:])
                else:
                    if current_piece_id == piece_id:
                        current_contour.append(file_content[current_line])

        if current_line < n_lines:
            current_line += 1
  
    print(len(procesed_id), "piezas encontradas")

######################

if __name__ == "__main__":
    
    filename = "SKRLJ-INOX-10.cnc"

    # Verificación de existencia del archivo
    if not path.exists(filename):
        print(f"Archivo {filename} no encontrado.")
    else:
        # Lectura del archivo
        with open(filename, "r") as text_r_file:
            gcode_content = text_r_file.read()

        # Dividir el contenido en líneas
        file_lines = gcode_content.splitlines()

        parse_gcode_parts(file_lines)
