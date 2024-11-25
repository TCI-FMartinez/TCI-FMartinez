import cv2
import numpy as np
import re
import math
from os import sep, _exit

if __name__ == "__main__":
    from discretiza_arco import DiscretizaArco
    from orientation import calculate_contour_orientation
    DEBUGGING = True
else:
    from modules.discretiza_arco import DiscretizaArco
    from modules.orientation import calculate_contour_orientation
    DEBUGGING = False

WITH = 400
HEIGHT = 400
ANGLE = 0
OX = 0
OY = 0

def draw_contours(pieces_files, output_filename="output_contours.png", out_WH=(400, 400), N=10):
    WITH, HEIGHT = out_WH
    x1, y1 = 0, 0
    offset_extra = 250
    cnc_path = "OUTPUT"
    files_processed = 0
    limit_files = 0     # 0 = no limits. For debugging purposes.
    N = 10               # Nº de segmentos para discretizacion

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
    P9104_pattern = re.compile(r'\s*P9104')

    # Funciones auxiliares ############################################################################################
    def log_debug(message):
        if DEBUGGING:
            print(message)

    def offset_y(y, extra=0, Oy=0):
        return (y - Oy) + extra
        #return (y - Oy)

    def offset_x(x, extra=0, Ox=0):
        return (x - Ox) + extra
        #return (x - OX)

    def transform_point(x, y, offset_x=0, offset_y=0, angle=0):
        """
        Aplica un desplazamiento (offset) y una rotación a un punto (x, y).

        Parámetros:
            x, y: Coordenadas originales del punto.
            offset_x, offset_y: Desplazamientos en los ejes X e Y.
            angle: Ángulo de rotación en grados (en sentido antihorario).

        Retorna:
            Una tupla con las nuevas coordenadas transformadas (x', y').
        """
        # Aplicar el offset
        #x_offset = float(x) - offset_x
        #y_offset = float(y) - offset_y
        x_offset = float(x) - offset_x
        y_offset = float(y) - offset_y

        # Convertir el ángulo a radianes
        angle = 0                               ################################## DESACTIVO LA ROTACIÓN!!!!!!!!
        rad = math.radians(angle)

        # Aplicar la rotación
        x_rotated = x_offset * math.cos(rad) - y_offset * math.sin(rad)
        y_rotated = x_offset * math.sin(rad) + y_offset * math.cos(rad)

        return x_rotated, y_rotated


    def create_canvas(points): 
        if points:
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)

            b_mix_X = max_x - min_x
            b_max_Y = max_y - min_y

            WITH = max(int(b_mix_X), 300)
            HEIGHT = max(int(b_max_Y), 300)
            canvas_size = max(WITH, HEIGHT) + offset_extra*2


            log_debug(f">>>>>>>>>>>>>>>>>>>>>>>>>Canvas size: {(canvas_size, canvas_size)} Bounding{((min_x, max_y), ( max_x, min_y))}")
            image = np.ones((canvas_size, canvas_size, 3), dtype=np.uint8) * 255
            return image, b_mix_X, b_max_Y

        return None, 0, 0

    def draw_piercing(image, x, y):
        cv2.circle(image, (int(x), int(y)), 2, piercing_dot[0], piercing_dot[1])

    def draw_contour(image, contour, cut_line_type, current_pos):
        log_debug("Drawing contour.")
        x1, y1 = current_pos
        area = calculate_contour_orientation(contour)
        clockwise = area < 0
        log_debug(f"Horario: {clockwise}")
        log_debug(f"Nº segmentos: {len(contour)}")
        log_debug(f"Offset origin: X{OX} Y{OY}")

        for segment in contour:
            Gx, point, i, j = segment
            #log_debug(f"    Antes del offset: x1={x1}, y1={y1}, x2={point[0]}, y2={point[1]}, min_x={min_x}, max_y={max_y}")
            #x2 = offset_x(point[0], min_x, OX)
            #y2 = offset_y(point[1], max_y, OY)
            x2 = point[0]
            y2 = point[1]
           
            if Gx == "G1" or Gx == "G01":
                log_debug(f"D G1 X{x2} Y{y2}")
                image = cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), cut_line_type[0], cut_line_type[1])

            elif Gx == "G2" or Gx == "G02":
                log_debug(f"D {Gx} X{x2} Y{y2} I{i} J{j}")
                G2_points = DiscretizaArco(x1, y1, x2, y2, i, j, N=N, G2=True ,horario=clockwise)
                
                for p in G2_points:
                    x2_, y2_ = p
                    #print("    p", p)
                    cv2.line(image, (int(x1), int(y1)), (int(p[0]), int(p[1])), cut_line_type[0], cut_line_type[1])
                    x1, y1 = p[0], p[1]

            elif Gx == "G3" or Gx == "G03":
                log_debug(f"D {Gx} X{x2} Y{y2} I{i} J{j}")
                arc_points = DiscretizaArco(x1, y1, point[0], point[1], i, j, N=N, G2=False, horario=clockwise)

                for p in arc_points:
                    #print("    p", p)
                    image = cv2.line(image, (int(x1), int(y1)), (int(p[0]), int(p[1])), cut_line_type[0], cut_line_type[1])
                    x1, y1 = p[0], p[1]

                #x2, y2 = p[0], p[1]

            elif Gx == "G0" or Gx == "G00":
                log_debug(f"D G0 X{x2} Y{y2}")
                image = cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), free_line[0], free_line[1])
            
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
                piece_offset = re.findall(r'[XYR]([-\d.]+)', piece_origin)
                OX, OY, ANGLE = float(piece_offset[0])-offset_extra, float(piece_offset[1])-offset_extra, float(piece_offset[2])

            log_debug(f"ID: {piece_id}, Name: {piece_name}, Origin: ({piece_offset}), Lines: {n_lines}")

            output_filename = f"OUTPUT{sep}{piece_name}.png"

            # Calculamos el tamaño del canvas
            for line in gcode_content:
                coordinates = re.findall(r'[XY]([-\d.]+)', line)
                if len(coordinates) >= 2:
                    x = float(coordinates[0])
                    y = float(coordinates[1])
                    points.append((x, y))

            # Creación del canvas.
            image, b_min_X, b_max_y = create_canvas(points)

            # Procesamiento inicial por línea.
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
                    contour = []            # Inicializamos el contorno

                elif G123_match:
                    if new_contour:
                        draw_piercing(image, x1, y1)            ###############<<<<<<<<<<<<< PIERCING
                        new_contour = False

                    if re.search(G3_pattern, line):
                        coordinates = re.findall(r'[XYIJ]([-\d.]+)', line)
                        if len(coordinates) >= 2:
                            x2, y2 = transform_point(coordinates[0], coordinates[1], OX, OY, ANGLE)
                            #x2 = offset_x(float(coordinates[0]), b_min_X+offset_extra, OX)
                            #y2 = offset_y(float(coordinates[1]), b_max_y+offset_extra, OY)
                            I = float(coordinates[2])
                            J = float(coordinates[3])
                            #print("G3 >>>>>>>>>>>>>>>>>>", current_line, (("G3", (x2, y2), I, J)))
                            contour.append(("G3", (x2, y2), I, J))

                    elif re.search(G2_pattern, line):
                        coordinates = re.findall(r'[XYIJ]([-\d.]+)', line)
                        if len(coordinates) >= 2:
                            x2, y2 = transform_point(coordinates[0], coordinates[1], OX, OY, ANGLE)
                            #x2 = offset_x(float(coordinates[0]), b_min_X+offset_extra, OX)
                            #y2 = offset_y(float(coordinates[1]), b_max_y+offset_extra, OY)
                            I = float(coordinates[2])
                            J = float(coordinates[3])
                            #print("G2 >>>>>>>>>>>>>>>>>>", current_line, (("G2", (x2, y2), I, J)))
                            contour.append(("G2", (x2, y2), I, J))

                    elif re.search(G1_pattern, line):
                        coordinates = re.findall(r'[XY]([-\d.]+)', line)
                        if len(coordinates) >= 2:
                            x2, y2 = transform_point(coordinates[0], coordinates[1], OX, OY, ANGLE)
                            #x2 = offset_x(float(coordinates[0]), b_min_X+offset_extra, OX)
                            #y2 = offset_y(float(coordinates[1]), b_max_y+offset_extra, OY)
                            #print("G1 >>>>>>>>>>>>>>>>>>", current_line, (("G1", (x2, y2), 0, 0)))
                            contour.append(("G1", (x2, y2), 0, 0))

                elif re.search(P9104_pattern, line):
                    new_contour = True
                    #contours.append([contour, clockwise])
                    #print("p9104 >>>>>>>>>>>>>>>>>>", current_line, len(contour))
                    if len(contour) > 0:
                        x1, y1, image = draw_contour(image, contour, cut_line_type, (x1, y1))
                    else:
                        print("Fin de contorno, sin segmentos!")

                elif re.search(G0_pattern, line):
                    coordinates = re.findall(r'[XY]([-\d.]+)', line)
                    if len(coordinates) >= 2:
                        x2, y2 = transform_point(coordinates[0], coordinates[1], OX, OY, ANGLE)
                        #x2 = offset_x(float(coordinates[0]), b_min_X+offset_extra, OX)
                        #y2 = offset_y(float(coordinates[1]), b_max_y+offset_extra, OY)
                        #print("G0 >>>>>>>>>>>>>>>>>>", current_line, (("G0", (x2, y2), 0, 0)))
                        x1, y1, image = draw_contour(image, [("G0", (x2, y2), 0, 0)], free_line, (x1, y1))


                current_line += 1

            # Guardar la imagen
            image = cv2.resize(image, out_WH)
            text = f"ID:{piece_id} [{piece_name}] Origin: {piece_origin}"
            cv2.putText(image, text, (3, out_WH[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.imwrite(output_filename, image)

            if __name__ == "__main__":
                cv2.imshow("Resultado", image)
                cv2.waitKey(0)

            files_processed += 1

#####################################################################################################################################
if __name__ == "__main__":

    #files = ["ID1_TEST80x80P101R.cnc"]
    #files = ["ID1_221785-7.cnc"]
    files = ["ID1_221785-7.cnc", "ID2_217701-8.cnc", "ID3_237730-1.cnc", "ID26_209183-2.cnc", "ID4_266822-5.cnc"]
    draw_contours(files)
