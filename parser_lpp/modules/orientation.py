
####### Cálculo del producto vectorial. Si el área es negativa el contorno es horario. ######

# Función para calcular el área del polígono (orientación del contorno)
def calculate_contour_orientation(contour):
    """
    Calcula el área orientada del polígono definido por los puntos.
    Devuelve el área y determina el sentido:
    - Positiva: antihorario.
    - Negativa: horario.
    """
    points = []
    for c in contour:
        #print("Orientation:", c)
        _, point, _, _ = c
        points.append(point)
    n = len(points)
    area = 0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]  # Cicla al primer punto al final
        area += x1 * y2 - y1 * x2
    return area / 2

if __name__ == "__main__":
    # Lista de puntos obtenida del código G (extraídos manualmente para este ejemplo)
    contour_points = [
        
        ("G1", (19.59, 191.54), 0, 0),
        ("G1", (21.34, 193.29), 0, 0),
        ("G1", (21.34, 373.15), 0, 0),
        ("G1", (28.59, 380.4), 0, 0),
        ("G1", (95.59, 380.4), 0, 0),
        ("G1", (102.84, 373.15), 0, 0),
        ("G1", (102.84, 359.15), 0, 0),
        ("G1", (99.59, 355.9), 0, 0),
        ("G1", (68.59, 355.9), 0, 0),
        ("G1", (65.84, 353.15), 0, 0),
        ("G1", (65.84, 167.15), 0, 0),
        ("G1", (58.59, 159.9), 0, 0),
        ("G1", (28.59, 159.9), 0, 0),
        ("G1", (21.34, 167.15), 0, 0),
        ("G1", (21.34, 193.29), 0, 0)
    ]

    # Cálculo del área orientada
    area = calculate_contour_orientation(contour_points)

    # Determinación del sentido del contorno
    orientation = "antihorario" if area > 0 else "horario"

    print(round(area,2), orientation)
