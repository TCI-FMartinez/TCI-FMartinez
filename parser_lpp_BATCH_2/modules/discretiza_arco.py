
###### EJEMPLO DE DISCRETIZACION DE ARCO ######

import numpy as np

def DiscretizaArco(x1, y1, x2, y2, i, j, N=10, G2 = True, horario=True):
    """
    Discretiza un arco en N puntos intermedios.
    
    :param x1, y1: Coordenadas del punto inicial del arco.
    :param x2, y2: Coordenadas del punto final del arco.
    :param i, j: Coordenadas relativas del centro del arco.
    :param N: Número de segmentos a discretizar.
    :param horario: Sentido del arco (True: horario, False: antihorario).
    :return: Lista de puntos [(x, y), ...] que discretizan el arco.
    """
    # Calcular el centro absoluto del arco
    cx = x1 + i
    cy = y1 + j

    # Calcular el radio del arco
    r = np.sqrt(i**2 + j**2)

    # Garantizamos que el numero mínimo de segmentos sea 3.
    if N < 3: N = 3

    if r > 5: N * 2    # Aumentamos en numero de discretización si se supera cierto radio

    # Calcular los ángulos inicial y final
    theta1 = np.arctan2(y1 - cy, x1 - cx)
    theta2 = np.arctan2(y2 - cy, x2 - cx)

    # Ajustar los ángulos para el sentido correcto
    if G2:
        if horario:
            if theta2 > theta1: theta1 += 2 * np.pi  # Asegurar recorrido horario
        else:
            if theta2 < theta1:theta2 += 2 * np.pi  # Asegurar recorrido antihorario
    elif not G2:
        if horario:
            if theta2 < theta1:
                theta2 += 2 * np.pi  # Asegurar recorrido antihorario
        else:
            if theta2 > theta1: theta1 += 2 * np.pi  # Asegurar recorrido horario


    # Generar los valores de theta discretizados
    theta_values = []
    step = (theta2 - theta1) / N
    for k in range(N + 1):
        theta_values.append(theta1 + k * step)

    # Generar los puntos discretizados
    points = []
    for theta in theta_values:
        x = cx + r * np.cos(theta)
        y = cy + r * np.sin(theta)
        points.append((x, y))

    return points


######################################################################


if __name__ == "__main__":
    import cv2

    codigo_g = """
    G1X10Y4.75  ;
    G2X4.75Y10I0J5.25  ;
    G1X4.75Y50  ;
    """
    escala = 1
    segmentos = 15
    x_ini, y_ini, x_fin, y_fin, I1, J1 = 50, 50, 51, 51, 0, 50
    
    
    segmentos_G3 = DiscretizaArco(x_ini, y_ini, x_fin, y_fin, I1, J1, segmentos, True)
    #segmentos_G2 = DiscretizaArco(21.34, 373.15, 28.59, 380.4, 7.25, 0, segmentos, False)
    
    
    # Crear una nueva imagen en blanco con un tamaño adecuado
    image = np.ones((800, 800, 3), dtype=np.uint8) * 255  # Agregar margen
    image = cv2.circle(image, (int(x_ini*escala),int(y_ini+J1*escala)), 2, (0,250,0), 2)
    image = cv2.line(image,  (50, 50), (int(x_ini*escala),int(y_ini+J1*escala)), (0,0,250), 1)
    x1, y1 = 50, 50
    #image = cv2.circle(image, (int((x_ini + I1)*escala),int((y_ini+J1)*escala)), int(J1*escala), (0,0,0), 2) 
    x1, y1 = x_ini, y_ini
    color = (0,0,0)
    for segment in segmentos_G3:
        color = (color[0], color[1]+int(200/segmentos), color[2])
        image = cv2.line(image, (int(x1*escala),int(y1*escala)), (int(segment[0]*escala), int(segment[1]*escala)), (0,0,250), 1)
        x1, y1 = int(segment[0]*escala), int(segment[1]*escala)
              
    cv2.imshow("IMAGEN RESULTADO", image)
    cv2.waitKey(0)