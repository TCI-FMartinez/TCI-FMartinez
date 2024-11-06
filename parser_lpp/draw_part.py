import cv2
import numpy as np
import re
from os import sep

def draw_contours(pieces_info, output_filename="output_contours.png"):
    output_filename = f"OUTPUT{sep}{output_filename}"

    # Colores
    cut_color = (0, 0, 0)  # Negro para los contornos de corte (G1, G2, G3)
    move_color = (50, 200, 50)  # Verde para los movimientos rápidos (G0)
    line_thickness = 2  # Grosor de la línea

    for piece_name, contours in pieces_info.items():
        points = []  # Lista para almacenar los puntos del contorno
        for contour in contours:
            # Determinar el tipo de comando y color
            if "G0" in contour:
                color = move_color  # Movimiento rápido
            elif "G1" in contour:
                color = cut_color  # Corte
            elif "G2" in contour:
                color = (255,0 ,0 ) # Corte radios
            elif "G3" in contour:
                color = (255,0 ,0 ) # Corte radios
            else:
                continue  # Si no es un tipo de comando que manejamos, continuar

            # Parsear las coordenadas
            coordinates = re.findall(r'[XY]([-\d.]+)', contour)
            if len(coordinates) >= 2:
                x = float(coordinates[0])
                y = float(coordinates[1])
                points.append((x, y, color))  # Almacenar los puntos y su color

        # Calcular el bounding box de los puntos
        if points:
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)

            # Calcular el tamaño de la imagen
            width = int(max_x - min_x)
            height = int(max_y - min_y)
            canvas_size = max(width, height)

            # Crear una nueva imagen en blanco con un tamaño adecuado
            image = np.ones((canvas_size + 50, canvas_size + 50, 3), dtype=np.uint8) * 255  # Agregar margen

            # Dibujar los contornos
            for point in points:
                x_scaled = int((point[0]) - min_x + 25)  # Escalar y desplazar
                y_scaled = int((point[1]) - min_y + 25)  # Escalar y desplazar
                cv2.circle(image, (x_scaled, y_scaled), 3, point[2], -1)  # Dibujar cada punto

            # Dibujar líneas entre los puntos
            for i in range(len(points) - 1):
                x1 = int((points[i][0]) - min_x + 25)
                y1 = int((points[i][1]) - min_y + 25)
                x2 = int((points[i + 1][0]) - min_x + 25)
                y2 = int((points[i + 1][1]) - min_y + 25)
                cv2.line(image, (x1, y1), (x2, y2), points[i][2], line_thickness)

            # Guardar la imagen generada con los contornos
            cv2.imwrite(f"{output_filename}.png", image)
            print(f"Imagen guardada como {output_filename}.png")

# Ejemplo de uso
# draw_contours(pieces_info)  # Descomentar esta línea en el archivo principal después de parsear el G-code.
