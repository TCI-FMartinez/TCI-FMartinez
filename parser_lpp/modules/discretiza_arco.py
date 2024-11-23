
###### EJEMPLO DE DISCRETIZACION DE ARCO ######

import numpy as np
import cv2


codigo_g = """
G65 P9102 A101 B01  ;
G1X19.59Y191.54  ;
G3X21.34Y193.29I0J1.75  ;
G1X21.34Y373.15  ;
G2X28.59Y380.4I7.25J0  ;
G1X95.59Y380.4  ;
G2X102.84Y373.15I0J-7.25  ;
G1X102.84Y359.15  ;
G2X99.59Y355.9I-3.25J0  ;
G1X68.59Y355.9  ;
G3X65.84Y353.15I0J-2.75  ;
"""


def DiscretizaArco (X_start, Y_start, X_end, Y_end, I, J, N = 10, is_G3 = True) -> list:

    # Centro absoluto
    C_x = X_start + I
    C_y = Y_start + J

    # Radio
    R = np.sqrt(I**2 + J**2)

    # Ángulos inicial y final
    theta_start = np.arctan2(Y_start - C_y, X_start - C_x)
    theta_end = np.arctan2(Y_end - C_y, X_end - C_x)


    ##vvvvvvvvvvvv AQUI HAY QUE DISTINGUIR SI ES INTERIOR O EXTERIOR PARA GIRAR A DERECHAS O IZQ  vvvvvvvvv
    # Asegurarse de que theta_end es mayor que theta_start para un arco antihorario (G3)
    if theta_end < theta_start and is_G3:
        theta_end += 2 * np.pi
        # Si es horario, asegurarse de que theta_end es menor que theta_start
    else:
        #theta_start < theta_end:         ## and not is_G3
        theta_start += 2 * np.pi

    # Discretización
    #N = 10  # Número de segmentos
    delta_theta = (theta_end - theta_start) / N

    # Cálculo de puntos discretos
    points = []
    for k in range(N + 1):
        theta = theta_start + k * delta_theta
        X_k = C_x + R * np.cos(theta)
        Y_k = C_y + R * np.sin(theta)
        points.append((X_k, Y_k))

    return points  # Lista de puntos discretos


######################################################################


if __name__ == "__main__":

    codigo_g = """
    G65 P9102 A101 B01  ;
    G1X19.59Y191.54  ;
    G3X21.34Y193.29I0J1.75  ;
    G1X21.34Y373.15  ;
    G2X28.59Y380.4I7.25J0  ;
    G1X95.59Y380.4  ;
    G2X102.84Y373.15I0J-7.25  ;
    G1X102.84Y359.15  ;
    G2X99.59Y355.9I-3.25J0  ;
    G1X68.59Y355.9  ;
    G3X65.84Y353.15I0J-2.75  ;
    """
    escala = 1
    segmentos = 5
    x_ini, y_ini, x_fin, y_fin, I1, J1 = 50.5, 200.5, 70.5, 200.5, 0, 20
    
    segmentos_G3 = DiscretizaArco(x_ini, y_ini, x_fin, y_fin, I1, J1, segmentos)
    #segmentos_G2 = DiscretizaArco(21.34, 373.15, 28.59, 380.4, 7.25, 0, segmentos, False)
    
    print("G03",segmentos_G3)
    #print("G02",segmentos_G2)
    
    # Crear una nueva imagen en blanco con un tamaño adecuado
    image = np.ones((800, 800, 3), dtype=np.uint8) * 255  # Agregar margen
    image = cv2.circle(image, (int(x_ini*escala),int(y_ini+J1*escala)), 2, (0,250,0), 2) 
    #image = cv2.circle(image, (int((x_ini + I1)*escala),int((y_ini+J1)*escala)), int(J1*escala), (0,0,0), 2) 
    x1, y1 = x_ini, x_fin
    color = (0,50,0)
    for segment in segmentos_G3:
        print(segment)
        color = (color[0], color[1]+int(200/segmentos), color[2])
        image = cv2.line(image, (int(x1*escala),int(y1*escala)), (int(segment[0]*escala), int(segment[1]*escala)), (0,0,250), 1)
        x1, y1 = int(segment[0]*escala), int(segment[1]*escala)
                
    cv2.imshow("IMAGEN RESULTADO", image)
    cv2.waitKey(0)