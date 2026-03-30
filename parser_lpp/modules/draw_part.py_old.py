import math
import re
from os import makedirs, path

import cv2
import numpy as np

if __name__ == "__main__":
    from discretiza_arco import DiscretizaArco
    from orientation import calculate_contour_orientation
    DEBUGGING = True
else:
    from modules.discretiza_arco import DiscretizaArco
    from modules.orientation import calculate_contour_orientation
    DEBUGGING = False

ANGLE = 0.0
OX = 0.0
OY = 0.0


def draw_contours(
    pieces_files,
    output_filename=None,
    out_WH=(400, 400),
    N=10,
    out_path="OUT_png",
    auto_close_open=True,
    draw_bounding=True,
):
    """
    Dibuja los contornos de uno o varios archivos CNC y guarda una imagen PNG.

    pieces_files:
        Lista de rutas o nombres de archivo .cnc.
    output_filename:
        Ruta completa del PNG de salida. Si hay varios archivos, se sobrescribirá en cada iteración.
        Si es None, se guardará en out_path con el nombre de la pieza.
    out_WH:
        Tamaño final de la imagen de salida.
    N:
        Número de segmentos para discretizar arcos.
    out_path:
        Carpeta por defecto cuando output_filename es None.
    auto_close_open:
        Si True, cierra contornos abiertos añadiendo una línea al primer punto.
    draw_bounding:
        Si True, dibuja el bounding box.
    """
    result = False
    offset_extra = 250
    files_processed = 0
    limit_files = 0  # 0 = sin límite. Solo para depuración.

    # Colores
    cut_Q1_line = ((48, 138, 252), 2)   # Azul
    cut_Q2_line = ((45, 222, 82), 2)    # Verde
    cut_Q3_line = ((255, 166, 82), 2)   # Naranja
    cut_Q4_line = ((255, 100, 100), 2)  # Rojo
    free_line = ((80, 80, 80), 1)       # Gris
    piercing_dot = ((0, 0, 250), 2)     # Rojo

    # Expresiones regulares
    G0_pattern = re.compile(r"\s*G0")
    G1_pattern = re.compile(r"\s*G1")
    G2_pattern = re.compile(r"\s*G2")
    G3_pattern = re.compile(r"\s*G3")
    G123_pattern = re.compile(r"\s*G[123]")
    P9102_pattern = re.compile(r"G65\s*P9102\s+A(\d+)\s+B(\d+)")
    P9104_pattern = re.compile(r"\s*P9104")

    def log_debug(message):
        if DEBUGGING:
            print(message)

    def transform_point(x, y, offset_x=0.0, offset_y=0.0, angle=0.0):
        x_offset = float(x) - float(offset_x)
        y_offset = float(y) - float(offset_y)

        rad = math.radians(float(angle))
        x_rotated = x_offset * math.cos(rad) - y_offset * math.sin(rad)
        y_rotated = x_offset * math.sin(rad) + y_offset * math.cos(rad)

        return x_rotated, y_rotated

    def draw_boundingbox(image, points, draw_it=True, ox=0.0, oy=0.0, angle=0.0):
        (min_x, min_y), (max_x, max_y) = points
        min_x, min_y = transform_point(min_x, min_y, ox, oy, angle)
        max_x, max_y = transform_point(max_x, max_y, ox, oy, angle)

        if max_x > min_x and draw_it:
            image = cv2.rectangle(
                image,
                (int(min_x), int(min_y)),
                (int(max_x), int(max_y)),
                (0, 0, 0),
                1,
            )
        return image

    def create_canvas(points, ox=0.0, oy=0.0, angle=0.0, draw_bounding_local=True):
        if not points:
            return None, 0, 0

        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        bbox_w = max_x - min_x
        bbox_h = max_y - min_y
        canvas_edge = max(int(bbox_w), int(bbox_h), 300) + offset_extra * 2

        log_debug(
            f">>>>>>>>>>>>>>>>>>>>>>>> Canvas size: {(canvas_edge, canvas_edge)} "
            f"Bounding {((min_x, min_y), (max_x, max_y))}"
        )

        image = np.ones((canvas_edge, canvas_edge, 3), dtype=np.uint8) * 255
        image = draw_boundingbox(
            image,
            ((min_x, min_y), (max_x, max_y)),
            draw_it=draw_bounding_local,
            ox=ox,
            oy=oy,
            angle=angle,
        )
        return image, bbox_w, bbox_h

    def draw_piercing(image, x, y):
        cv2.circle(image, (int(x), int(y)), 2, piercing_dot[0], piercing_dot[1])

    def points_close(p1, p2, tol=1e-3):
        return abs(p1[0] - p2[0]) <= tol and abs(p1[1] - p2[1]) <= tol

    def draw_contour(image, contour, cut_line_type, current_pos):
        log_debug("Drawing contour.")
        x1, y1 = current_pos

        area = calculate_contour_orientation(contour)
        clockwise = area < 0
        log_debug(f"Horario: {clockwise}")
        log_debug(f"Nº segmentos: {len(contour)}")

        for segment in contour:
            Gx, point, i, j = segment
            x2 = point[0]
            y2 = point[1]

            if Gx in ("G1", "G01"):
                log_debug(f"D G1 X{x2} Y{y2}")
                image = cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), cut_line_type[0], cut_line_type[1])

            elif Gx in ("G2", "G02"):
                log_debug(f"D {Gx} X{x2} Y{y2} I{i} J{j}")
                arc_points = DiscretizaArco(x1, y1, x2, y2, i, j, N=N, G2=True, horario=clockwise)
                for p in arc_points:
                    image = cv2.line(image, (int(x1), int(y1)), (int(p[0]), int(p[1])), cut_line_type[0], cut_line_type[1])
                    x1, y1 = p[0], p[1]

            elif Gx in ("G3", "G03"):
                log_debug(f"D {Gx} X{x2} Y{y2} I{i} J{j}")
                arc_points = DiscretizaArco(x1, y1, x2, y2, i, j, N=N, G2=False, horario=clockwise)
                for p in arc_points:
                    image = cv2.line(image, (int(x1), int(y1)), (int(p[0]), int(p[1])), cut_line_type[0], cut_line_type[1])
                    x1, y1 = p[0], p[1]

            elif Gx in ("G0", "G00"):
                log_debug(f"D G0 X{x2} Y{y2}")
                image = cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), free_line[0], free_line[1])

            x1, y1 = x2, y2

        return x1, y1, image

    for file_name in pieces_files:
        current_line = 0
        points = []
        contour = []
        new_contour = True
        cut_line_type = cut_Q1_line
        x1 = y1 = x2 = y2 = I = J = 0.0

        file_name = path.normpath(file_name)

        if not (files_processed < limit_files or limit_files == 0):
            continue

        try:
            with open(file_name, "r", encoding="utf-8", errors="ignore") as text_r_file:
                gcode_content = text_r_file.read().splitlines()
        except FileNotFoundError:
            print(f"No se encuentra el archivo: {file_name}")
            continue

        n_lines = len(gcode_content)
        if n_lines < 3:
            print(f"Archivo inválido o incompleto: {file_name}")
            continue

        piece_id = gcode_content[0]
        piece_name = gcode_content[1]
        piece_origin = gcode_content[2]

        piece_offset = re.findall(r"[XYR]([-\d.]+)", piece_origin)
        if len(piece_offset) >= 3:
            OX_local = float(piece_offset[0]) - offset_extra
            OY_local = float(piece_offset[1]) - offset_extra
            ANGLE_local = float(piece_offset[2])
        else:
            OX_local = -offset_extra
            OY_local = -offset_extra
            ANGLE_local = 0.0
            log_debug(f"Origen no válido en {file_name}. Se usa origen por defecto.")

        log_debug(f"ID: {piece_id}, Name: {piece_name}, Origin: ({piece_offset}), Lines: {n_lines}")

        for line in gcode_content:
            coordinates = re.findall(r"[XY]([-\d.]+)", line)
            if len(coordinates) >= 2:
                x = float(coordinates[0])
                y = float(coordinates[1])
                points.append((x, y))

        image, _, _ = create_canvas(points, ox=OX_local, oy=OY_local, angle=ANGLE_local, draw_bounding_local=draw_bounding)
        if image is None:
            print(f"No se pudo crear el canvas para {file_name}")
            continue

        while current_line < n_lines:
            line = gcode_content[current_line]
            P9102_match = re.search(P9102_pattern, line)
            G123_match = re.search(G123_pattern, line)

            if P9102_match:
                new_contour = True
                B_value = P9102_match.group(2)
                cut_line_type = {
                    "02": cut_Q2_line,
                    "03": cut_Q3_line,
                    "04": cut_Q4_line,
                }.get(B_value, cut_Q1_line)
                contour = []

            elif G123_match:
                if new_contour:
                    draw_piercing(image, x1, y1)
                    new_contour = False

                if re.search(G3_pattern, line):
                    coordinates = re.findall(r"[XYIJ]([-\d.]+)", line)
                    if len(coordinates) >= 4:
                        x2, y2 = transform_point(coordinates[0], coordinates[1], OX_local, OY_local, ANGLE_local)
                        I = float(coordinates[2])
                        J = float(coordinates[3])
                        contour.append(("G3", (x2, y2), I, J))

                elif re.search(G2_pattern, line):
                    coordinates = re.findall(r"[XYIJ]([-\d.]+)", line)
                    if len(coordinates) >= 4:
                        x2, y2 = transform_point(coordinates[0], coordinates[1], OX_local, OY_local, ANGLE_local)
                        I = float(coordinates[2])
                        J = float(coordinates[3])
                        contour.append(("G2", (x2, y2), I, J))

                elif re.search(G1_pattern, line):
                    coordinates = re.findall(r"[XY]([-\d.]+)", line)
                    if len(coordinates) >= 2:
                        x2, y2 = transform_point(coordinates[0], coordinates[1], OX_local, OY_local, ANGLE_local)
                        contour.append(("G1", (x2, y2), 0, 0))

            elif re.search(P9104_pattern, line):
                new_contour = True
                if contour:
                    if auto_close_open:
                        first_point = contour[0][1]
                        last_point = contour[-1][1]
                        if not points_close(first_point, last_point):
                            contour.append(("G1", first_point, 0, 0))
                    x1, y1, image = draw_contour(image, contour, cut_line_type, (x1, y1))
                else:
                    print("Fin de contorno, sin segmentos")

            elif re.search(G0_pattern, line):
                coordinates = re.findall(r"[XY]([-\d.]+)", line)
                if len(coordinates) >= 2:
                    x2, y2 = transform_point(coordinates[0], coordinates[1], OX_local, OY_local, ANGLE_local)
                    x1, y1, image = draw_contour(image, [("G0", (x2, y2), 0, 0)], free_line, (x1, y1))

            current_line += 1
            result = True

        image = cv2.resize(image, out_WH)
        text = f"ID:{piece_id} [{piece_name}] Origin: {piece_origin}"
        cv2.putText(image, text, (3, out_WH[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)

        if output_filename:
            save_path = path.normpath(output_filename)
        else:
            safe_piece_name = path.splitext(path.basename(file_name))[0] + ".png"
            save_path = path.join(out_path, safe_piece_name)

        save_dir = path.dirname(save_path)

        if save_dir and not path.exists(save_dir):
            makedirs(save_dir)

        try:
            print(f"Guardando imagen en: {save_path}")
            cv2.imwrite(save_path, image)
        except Exception as e_write:
            print(f"Error al guardar la imagen: {e_write}")
            continue

        if __name__ == "__main__":
            cv2.imshow("Resultado", image)
            cv2.waitKey(0)

        files_processed += 1
        result = True

    return result


if __name__ == "__main__":
    files = [
        "ID1_221785-7.cnc",
        "ID2_217701-8.cnc",
        "ID3_237730-1.cnc",
        "ID26_209183-2.cnc",
        "ID4_266822-5.cnc",
    ]
    draw_contours(files)
