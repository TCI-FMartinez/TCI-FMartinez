import cv2
import numpy as np
import re
from os import sep, _exit
if __name__ == "__main__":
    from discretiza_arco import DiscretizaArco
    from orientation import calculate_contour_orientation
    debuguing = True
else:
    from modules.discretiza_arco import DiscretizaArco
    from modules.orientation import calculate_contour_orientation
    debuguing = False


def draw_contours(pieces_files, output_filename="output_contours.png", out_WH:tuple=(400,400), N=10):
    cnc_path = "OUTPUT"
    files_procesed = 0
    n_lines = 0
    current_line = 0

    # Colores
    cut_Q1_line = ((48, 138, 252), 2)   # Color azul, grosor 2
    cut_Q2_line = ((45, 222, 82), 2)   # Color verde, grosor 2
    cut_Q3_line = ((255, 166, 82), 2)   # Color naranja, grosor 2
    cut_Q4_line = ((255, 100, 100), 2)   # Color rojo, grosor 2
    free_line = ((80, 80, 80), 1)   # Color negro, grosor 1
    prircing_dot = ((0, 0, 250), 2)   # Color rojo, radio 2

    # REGULAR EXPRESIONS
    G0_pattern = re.compile(r"\s*G0")
    G1_pattern = re.compile(r"\s*G1")
    G2_pattern = re.compile(r"\s*G2")
    G3_pattern = re.compile(r"\s*G3")
    G123_pattern = re.compile(r"\s*G[123]")

    P9102_pattern = re.compile(r'G65\s*P9102\s+A(\d+)\s+B(\d+)')
    P9103_pattern = re.compile(r'\s*P9103')


    limit_files = 0         # 0 = sin límites.              <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<############## DEBUG LIMITE !!
    

    def offset_y(y2, min_y=0):
        #return int(y2-(height-Oy))
        return (y2- min_y - Oy)+35
    
    def offset_x(x2, min_x=0):
        return x2-min_x-Ox+25

    def create_canvas():
        # Calcular el bounding box de los puntos
        if points:
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)

            # Calcular el tamaño de la imagen 
            width = max(int(max_x-min_x), 300)                #max(int(max_x - min_x), 400)
            height = max(int(max_y-min_y), 300)               #max(int(max_y - min_y), 400)
            canvas_size = (max(width, height)) + 50

            if debuguing: print("Canvas size:", (canvas_size, canvas_size))
            # Crear una nueva imagen en blanco con un tamaño adecuado
            image = np.ones((canvas_size, canvas_size, 3), dtype=np.uint8) * 255  # Agregar margen

        return image


    for file_name in pieces_files:              ######################################################>>>>>>>>>>> PIEZA
        
        current_line = 0
        points = []
        contourns = []
        horario = True
        x1 = 0
        y1 = 0

        #print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",files_procesed < limit_files, limit_files == 0)   ############## DEBUG
        if files_procesed < limit_files or limit_files == 0:
            with open(f"{cnc_path}{sep}{file_name}", "r") as text_r_file:
                gcode_file = text_r_file.read()
                gcode_content = gcode_file.splitlines()
                n_lines = len(gcode_content)
                piece_id = gcode_content[0]
                piece_name = gcode_content[1]
                piece_origin = gcode_content[2]
                piece_origin = re.findall(r'[XY]([-\d.]+)', piece_origin)
                Ox, Oy = float(piece_origin[0]), float(piece_origin[1])
                #piece_cotrouns = gcode_content[3:]

            print("ID:", piece_id)
            print("Name:", piece_name)
            print("Origin:", (Ox, Oy))
            print("Nº lines:", n_lines)
            #print(gcode_content)                ############## DEBUG

            output_filename = f"OUTPUT{sep}{piece_name}.png"

            ########## Parsear las coordenadas 
            for line in gcode_content:
                coordinates = re.findall(r'[XY]([-\d.]+)', line)
                if len(coordinates) >= 2:
                    x = float(coordinates[0])
                    y = float(coordinates[1])
                    points.append((x-Ox, y-Oy))  # Almacenar los puntos

                                                             ############################>>>>>>>>>>> CONTORNO
            # Busqueda de contornos                   ####### así no. debe hacerse por contornos.
            #print("Nº de lineas:", n_lines)
            
            while current_line < n_lines:
                line = gcode_content[current_line]
                match_P9102 = re.search(P9102_pattern, line)
                match_G0 = re.search(G0_pattern, line)

                if match_P9102:
                    new_contourn = True
                    A_value = match_P9102.group(1)
                    B_value = match_P9102.group(2)
                    if debuguing: print(f">>>>>>>>>>>>>>>>>>> P9102 A={A_value} B={B_value}")
                    c_points=[]
                    if B_value == "02":
                        cut_line_type = cut_Q2_line
                    elif B_value == "03":
                        cut_line_type = cut_Q3_line
                    elif B_value == "04":
                        cut_line_type = cut_Q4_line
                    elif B_value == "05":
                        cut_line_type = cut_Q4_line
                    else:
                        cut_line_type = cut_Q1_line

                    contourn = [A_value, B_value, c_points, cut_line_type, horario]
                    current_line += 1
                else:
                    line = gcode_content[current_line]
                    G123_match = re.search(G123_pattern, line)
                    P9103_match = re.search(P9103_pattern, line)
                    G0_match = re.search(G0_pattern, line)

                    if G123_match:
                        x2 = float(G123_match[0])
                        y2 = float(G123_match[1])
                        c_points.append((x2, y2))
                        if debuguing: print(f">>>>>>>>>>>>>>>>>>> X{x2} Y{y2}")
                        current_line += 1
                    elif P9103_match:
                        area = calculate_contour_orientation(c_points)
                        if area > 0:
                            horario = True
                        else:
                            orario = False
                        contourn = [A_value, B_value, c_points, horario]
                        contourns.append[contourn]
                        current_line += 1
                    elif G0_pattern:
                        draw_G0()

                    else:
                        print("No MATCH")











def draw_contourn(points):

                

            ########### Por lineas ###############################################>>>>>>>>>>> LINEA

            #print("Nº de lineas:", n_lines)
            while current_line < n_lines:
                if debuguing: print("Current line:", current_line)
                #print(gcode_content[current_line])
                line = gcode_content[current_line]

                match_P9102 = re.search(P9102_pattern, line)
                match_G0 = re.search(G0_pattern, line)
                match_G1 = re.search(G1_pattern, line)
                match_G2 = re.search(G2_pattern, line)
                match_G3 = re.search(G3_pattern, line)

                if match_P9102:
                    A_value = match_P9102.group(1)
                    B_value = match_P9102.group(2)
                    if debuguing: print(f">>>>>>>>>>>>>>>>>>> P9102 A={A_value} B={B_value}")

                elif match_G0:

                        y1 = y2

                elif match_G1:
                    coordinates = re.findall(r'[XY]([-\d.]+)', line)
                    if len(coordinates) >= 2:
                        x2 = offset_x(int(float(coordinates[0])), min_x)
                        y2 = offset_y(int(float(coordinates[1])))
                        if debuguing: print("G1:", (x1, y1), (x2, y2))      #>>>>>>>>>>>>>>>>>>>>>>>>>>>>><< DEBUG
                        cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), cut_line_type[0], cut_line_type[1])

                        # Pongo el punto final en el inicio para el siguiente segmento.
                        x1 = x2
                        y1 = y2

                elif match_G2:
                    coordinates = re.findall(r'[XYIJ]([-\d.]+)', line)
                    if len(coordinates) >= 2:
                        x2 = offset_x(int(float(coordinates[0])), min_x)
                        y2 = offset_y(int(float(coordinates[1])))
                        I = int(float(coordinates[2]))
                        J = int(float(coordinates[3]))
                        if debuguing: print(f"G2 X{x2} Y{y2} I{I} J{J}")
                        puntos = DiscretizaArco(x1, y1, x2, y2, I, J, N, False)

                        for punto in puntos:
                            if debuguing: print("    G2:", (x1, y1), (x2, y2))
                            cv2.line(image, (int(x1), int(y1)), (int(punto[0]), int(punto[1])), cut_line_type[0], cut_line_type[1])

                            # Pongo el punto final en el inicio para el siguiente segmento.
                            x1 = punto[0]
                            y1 = punto[1]

                elif match_G3:
                    coordinates = re.findall(r'[XYIJ]([-\d.]+)', line)
                    if len(coordinates) >= 2:
                        x2 = offset_x(int(float(coordinates[0])), min_x)
                        y2 = offset_y(int(float(coordinates[1])))
                        I = int(float(coordinates[2]))
                        J = int(float(coordinates[3]))
                        if debuguing: print("G3 X{x2} Y{y2} I{I} J{J}")
                        if abs(I) > 50 or abs(J) > 50: N*2
                        puntos = DiscretizaArco(x1, y1, x2, y2, I, J, N, True)

                        for punto in puntos:
                            if debuguing: print("    G3:", (x1, y1), (x2, y2))
                            cv2.line(image, (int(x1), int(y1)), (int(punto[0]), int(punto[1])), cut_line_type[0], cut_line_type[1])

                            # Pongo el punto final en el inicio para el siguiente segmento.
                            x1 = punto[0]
                            y1 = punto[1]
                else:
                    print("No MATCH")
   
                current_line += 1

            # Guardar la imagen
            image = cv2.resize(image, out_WH)
            image = cv2.putText(image, f"ID:{piece_id} [{piece_name}] {piece_origin} {(int(x2), int(y2))}",(3, out_WH[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0,0,0), 1, cv2.LINE_AA)
            
            cv2.imwrite(output_filename, image)

            if __name__ == "__main__":
                cv2.imshow("IMAGEN RESULTADO", image)
                cv2.waitKey(0)
            files_procesed += 1


######################################################
if __name__ == "__main__":
    files = ["ID1_221785-7.cnc", "ID2_217701-8.cnc", "ID3_237730-1.cnc", "ID26_209183-2.cnc", "ID7_207499-2.cnc", "ID4_266822-5.cnc"]
    draw_contours(files)