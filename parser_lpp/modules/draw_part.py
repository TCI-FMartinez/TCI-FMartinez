import cv2
import numpy as np
import re
from os import sep, _exit

if __name__ == "__main__":
    from discretiza_arco import DiscretizaArco
    from orientation import calculate_contour_orientation
    DEBUGGING = True
else:
    from modules.discretiza_arco import DiscretizaArco
    from modules.orientation import calculate_contour_orientation
    DEBUGGING = False


def draw_contours(pieces_files, output_filename="output_contours.png", out_WH=(400, 400), N=10):
    x1, y1 = 0, 0
    cnc_path = "OUTPUT"
    files_processed = 0
    limit_files = 1  # 0 = no limits. For debugging purposes.

    # Colores
    cut_Q1_line = ((48, 138, 252), 2)  # Azul
    cut_Q2_line = ((45, 222, 82), 2)  # Verde
    cut_Q3_line = ((255, 166, 82), 2)  # Naranja
    cut_Q4_line = ((255, 100, 100), 2)  # Rojo
    free_line = ((80, 80, 80), 1)  # Negro
    piercing_dot = ((0, 0, 250), 2)  # Rojo pequeño

    # Expresiones regulares
    G0_pattern = re.compile(r"\s*G0")
    G1_pattern = re.compile(r"\s*G1")
    G2_pattern = re.compile(r"\s*G2")
    G3_pattern = re.compile(r"\s*G3")
    G123_pattern = re.compile(r"\s*G[123]")
    P9102_pattern = re.compile(r'G65\s*P9102\s+A(\d+)\s+B(\d+)')
    P9103_pattern = re.compile(r'\s*P9103')

    # Funciones auxiliares ############################################################################################
    def log_debug(message):
        if DEBUGGING:
            print(message)

    def offset_y(y, min_y=0):
        return int((y - min_y - Oy) + 35 )

    def offset_x(x, min_x=0):
        return int((x - min_x - Ox) + 25)

    def create_canvas(points):
        if points:
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)

            width = max(int(max_x - min_x), 300)
            height = max(int(max_y - min_y), 300)
            canvas_size = max(width, height) + 50

            log_debug(f"Canvas size: {(canvas_size, canvas_size)}")
            image = np.ones((canvas_size, canvas_size, 3), dtype=np.uint8) * 255
            return image, min_x, min_y

        return None, 0, 0

    def draw_piercing(image, x, y):
        cv2.circle(image, (int(x), int(y)), 2, piercing_dot[0], piercing_dot[1])

    def draw_contour(image, contour, cut_line_type, current_pos, min_x, min_y):
        log_debug("Drawing contour.")
        x1, y1 = current_pos
        area = calculate_contour_orientation(contour)
        clockwise = area < 0
        print("Horario:", clockwise)
    
        for segment in contour:
            Gx, point, i, j = segment
            #log_debug(f"    Antes del offset: x1={x1}, y1={y1}, x2={point[0]}, y2={point[1]}, min_x={min_x}, min_y={min_y}")
            Gx =  Gx[0]
            x2 = offset_x(point[0], min_x)
            y2 = offset_y(point[1], min_y)
           
            if Gx == "G1" or Gx == "G01":
                log_debug(f"D G1 X{x2} Y{y2}")
                image = cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), cut_line_type[0], cut_line_type[1])

            elif Gx in {"G2", "G02", "G3", "G03"}:
                log_debug(f"D {Gx} X{x2} Y{y2} I{i} J{j}")
                arc_points = DiscretizaArco(x1, y1, point[0], point[1], i, j, N, clockwise)

                for p in arc_points:
                    image = cv2.line(image, (int(x1), int(y1)), (int(p[0]), int(p[1])), cut_line_type[0], cut_line_type[1])
                    x1, y1 = p[0], p[1]

            elif Gx in {"G0", "G00"}:
                log_debug(f"D G0 X{x2} Y{y2}")
                image = cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), free_line[0], free_line[1])
                x1, y1 = x2, y2
            
            x1, y1 = x2, y2
        return x1, y1, image

    # Proceso principal ############################################################################################
    for file_name in pieces_files:
        current_line = 0
        points = []
        contour = []
        contours = []
        new_contour = True
        x1, y1, x2, y2, I, J = 0, 0, 0, 0, 0, 0

        if files_processed < limit_files or limit_files == 0:
            with open(f"{cnc_path}{sep}{file_name}", "r") as text_r_file:
                gcode_file = text_r_file.read()
                gcode_content = gcode_file.splitlines()
                n_lines = len(gcode_content)
                piece_id = gcode_content[0]
                piece_name = gcode_content[1]
                piece_origin = gcode_content[2]
                piece_origin = re.findall(r'[XY]([-\d.]+)', piece_origin)
                Ox, Oy = float(piece_origin[0]), float(piece_origin[1])

            log_debug(f"ID: {piece_id}, Name: {piece_name}, Origin: ({Ox}, {Oy}), Lines: {n_lines}")

            output_filename = f"OUTPUT{sep}{piece_name}.png"

            for line in gcode_content:
                coordinates = re.findall(r'[XY]([-\d.]+)', line)
                if len(coordinates) >= 2:
                    x = float(coordinates[0])
                    y = float(coordinates[1])
                    points.append((x - Ox, y - Oy))

            image, min_x, min_y = create_canvas(points)

            while current_line < n_lines:
                line = gcode_content[current_line]
                P9102_match = re.search(P9102_pattern, line)
                G123_match = re.search(G123_pattern, line)

                if P9102_match:
                    new_contour = True
                    match = re.search(P9102_pattern, line)
                    A_value = match.group(1)
                    B_value = match.group(2)
                    cut_line_type = {
                        "02": cut_Q2_line,
                        "03": cut_Q3_line,
                        "04": cut_Q4_line
                    }.get(B_value, cut_Q1_line) # Esto asigna a 'cut_line_type' el valor correspondiente de 'B_value. si es 03 devuelve 'cut_3_line'
                                                #  si no esta la clave, .get() devuelve el segundo argumento.
                    contour = []
                    current_line += 1
                elif G123_match:
                    if new_contour:
                        draw_piercing(image, x1, y1)            ###############<<<<<<<<<<<<< PIERCING
                        new_contour = False

                    if re.search(G3_pattern, line):
                        coordinates = re.findall(r'[XYIJ]([-\d.]+)', line)
                        if len(coordinates) >= 2:
                            x2 = offset_x(int(float(coordinates[0])), min_x)
                            y2 = offset_y(int(float(coordinates[1])), min_y)
                            I = int(float(coordinates[2]))
                            J = int(float(coordinates[3]))
                            contour.append((G123_match, (x2, y2), I, J))

                    elif re.search(G2_pattern, line):
                        coordinates = re.findall(r'[XYIJ]([-\d.]+)', line)
                        if len(coordinates) >= 2:
                            x2 = offset_x(int(float(coordinates[0])), min_x)
                            y2 = offset_y(int(float(coordinates[1])), min_y)
                            I = int(float(coordinates[2]))
                            J = int(float(coordinates[3]))
                            log_debug(f"G2 X{x2} Y{y2} I{I} J{J}")
                            contour.append((G123_match, (x2, y2), I, J))

                    elif re.search(G1_pattern, line):
                        coordinates = re.findall(r'[XY]([-\d.]+)', line)
                        if len(coordinates) >= 2:
                            x2 = offset_x(int(float(coordinates[0])), min_x)
                            y2 = offset_y(int(float(coordinates[1])), min_y)
                            contour.append((G123_match, (x2, y2), 0, 0))

                    current_line += 1

                elif re.search(P9103_pattern, line):
                    new_contour = True
                    #contours.append([contour, clockwise])
                    if len(contour) > 0:
                        x1, y1, image = draw_contour(image, contour, cut_line_type, (x1, y1), min_x, min_y)
                    else:
                        print("Fin de contorno, sin segmentos!")

                    current_line += 1

                elif re.search(G0_pattern, line):
                    coordinates = re.findall(r'[XY]([-\d.]+)', line)
                    if len(coordinates) >= 2:
                        x2 = offset_x(int(float(coordinates[0])), min_x)
                        y2 = offset_y(int(float(coordinates[1])), min_y)
                        x1, y1, image = draw_contour(image, [("G0", (x2, y2), 0, 0)], free_line, (x1, y1), min_x, min_y)

                    current_line += 1
                else:
                    current_line += 1

            # Guardar la imagen
            image = cv2.resize(image, out_WH)
            text = f"ID:{piece_id} [{piece_name}] Origin: {piece_origin}"
            cv2.putText(image, text, (3, out_WH[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.imwrite(output_filename, image)

            if __name__ == "__main__":
                cv2.imshow("Resultado", image)
                cv2.waitKey(0)

            files_processed += 1

#####################################################################################################################################
if __name__ == "__main__":
    files = ["ID1_221785-7.cnc", "ID2_217701-8.cnc", "ID3_237730-1.cnc", "ID26_209183-2.cnc", "ID7_207499-2.cnc", "ID4_266822-5.cnc"]
    draw_contours(files)
