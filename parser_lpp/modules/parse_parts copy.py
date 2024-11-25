import re

def parse_gcode_parts(file_content):
    pieces = {}
    current_piece = None
    current_contour = []
    
    # Regular expressions para identificar piezas, comandos de corte y el fin de una pieza
    piece_pattern = r'\(P\d+:ID\d+:(.*?)\)'  # Para identificar piezas
    gcode_pattern = r'^N\d+\s+G[123]'  # Comandos de corte (G1, G2, G3) con el numerador
    end_part_call_pattern = r'M98 P9104'  # Para detectar el fin de una pieza
    line_number_pattern = r'^N\d+\s+'  # Para eliminar el numerador 'Nxx'
    clean_line_pattern = r'\s*;?\s*$'  # Para eliminar los espacios y el punto y coma al final

    # Parsear el archivo línea por línea
    for line in file_content:
        line = line.strip()
        
        # Identificar el nombre de la pieza (por ejemplo, P1:ID1:test20mmINOX)
        piece_match = re.match(piece_pattern, line)
        if piece_match:
            piece_name = piece_match.group(1)
            # Si ya había una pieza en progreso, guardar su contorno
            if current_piece:
                pieces[current_piece] = current_contour
            # Iniciar una nueva pieza
            current_piece = piece_name
            current_contour = []
        
        # Identificar comandos de corte
        elif re.match(gcode_pattern, line):
            # Eliminar el numerador 'Nxx'
            clean_line = re.sub(line_number_pattern, '', line)
            # Eliminar espacios y punto y coma al final de la línea
            clean_line = re.sub(clean_line_pattern, '', clean_line)
            current_contour.append(clean_line)
        
        # Detectar el fin de una pieza
        elif re.match(end_part_call_pattern, line) and current_piece:
            pieces[current_piece] = current_contour
            current_piece = None
            current_contour = []

    # Guardar la última pieza si aún no ha sido almacenada
    if current_piece:
        pieces[current_piece] = current_contour

    return pieces
