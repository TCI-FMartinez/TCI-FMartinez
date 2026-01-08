import cv2
import numpy as np

from modulos.lienzo import Lienzo

W, H = 800, 600             #Resolución
GH = int(H * 0.3)           #Alto gratícula

nombre_archivo_entrada = 'imagen2.jpg'
nombre_archivo_salida = f'imagen_procesada_{W}x{H}.jpg'

color = (70, 200, 200)          #BGR
sub_color = (70, 200, 200)      #BGR
color_center = (0, 165, 255)    #BGR


lienzo = Lienzo(W, H, 0)
#imAux = np.zeros(shape=(lienzo.shape[:2]), dtype=np.uint8)
paso = 10

pt1 = (int((W/2)-(GH)), int((H/2)-(GH)))
pt2 = (int((W/2)+(GH)), int((H/2)+(GH)))
rango = np.arange(-GH, GH+paso, paso)
sub_rango = np.arange(-GH, GH+paso, paso*6)

alpha = 0.6 # <<<<<<<<<<<< Peso de la imagen contra la graticula (Trasparencia graticula)

if 0 in rango:
    print(rango)
else:
    print("Rango impar sin ZERO!!")


def centrar_y_escalar(ruta_imagen, ancho_objetivo, alto_objetivo):
    """
    Carga una imagen, calcula un recorte centrado para igualar la relación de aspecto
    del objetivo y redimensiona a las dimensiones objetivo.

    Args:
        ruta_imagen (str): Ruta al archivo de imagen.
        ancho_objetivo (int): Ancho deseado para la imagen final.
        alto_objetivo (int): Alto deseado para la imagen final.

    Returns:
        numpy.ndarray: La imagen procesada o None si hay un error.
    """
    # Cargar la imagen
    imagen = cv2.imread(ruta_imagen)

    # Obtener dimensiones originales
    alto_original, ancho_original = imagen.shape[:2]

    # Calcular la relación de aspecto original y objetivo
    relacion_aspecto_original = ancho_original / alto_original
    relacion_aspecto_objetivo = ancho_objetivo / alto_objetivo

    if relacion_aspecto_original > relacion_aspecto_objetivo:
        alto_recorte = alto_original
        ancho_recorte = int(alto_original * relacion_aspecto_objetivo)
    else:
        ancho_recorte = ancho_original
        alto_recorte = int(ancho_original / relacion_aspecto_objetivo)

    #print(f"Dimensiones del recorte calculado: {ancho_recorte}x{alto_recorte}")

    # Calcular las coordenadas de inicio para el recorte centrado
    inicio_x = (ancho_original - ancho_recorte) // 2
    inicio_y = (alto_original - alto_recorte) // 2

    # Calcular las coordenadas de fin para el recorte
    fin_x = inicio_x + ancho_recorte
    fin_y = inicio_y + alto_recorte

    # Realizar el recorte
    imagen_recortada = imagen[inicio_y:fin_y, inicio_x:fin_x]

    # Redimensionar la imagen recortada al tamaño objetivo
    imagen_final = cv2.resize(imagen_recortada, (ancho_objetivo, alto_objetivo), interpolation=cv2.INTER_LINEAR)
    
    return imagen_final

### Cargar imagen de fondo.
imagen = cv2.imread(nombre_archivo_entrada)

## Procesa la imagen
imagen_procesada = centrar_y_escalar(nombre_archivo_entrada, W, H)
#imagen_procesada_gray = cv2.cvtColor(imagen_procesada, cv2.COLOR_BGR2GRAY)

####### CREAMOS LA GRATICULA
### Líneas finas
for x in rango:
    graticula = cv2.line(lienzo, (x+int(W/2), pt1[1]), (x+int(W/2), pt2[1]), color, 1)

for y in rango:
    cv2.line(graticula, (pt1[0], y+int(H/2)), (pt2[0], y+int(H/2)), color, 1)

### Líneas gruesas
sub_paso = int(paso*5)
for x in sub_rango:
    cv2.line(graticula, (x+int(W/2), pt1[1]), (x+int(W/2), pt2[1]), sub_color, 2)

for y in sub_rango:
    cv2.line(graticula, (pt1[0], y+int(H/2)), (pt2[0], y+int(H/2)), sub_color, 2)

### Líneas Centro
cv2.line(graticula, (0, int(H/2)), (W, int(H/2)), color_center, 3 )
cv2.line(graticula, (int(W/2), 0), (int(W/2), H), color_center, 3 )

### Creamos el fichero para debug
#cv2.imwrite("graticula.png", graticula)

graticula_gray = cv2.cvtColor(graticula, cv2.COLOR_BGR2GRAY)

suma_canales = graticula.sum(axis=2)    # Sumar los canales B, G, R. Un píxel negro (0,0,0) sumará 0.

# Crear la máscara: 255 donde la suma > 0 (no es negro), 0 donde la suma == 0 (es negro)
mascara = (suma_canales > 0).astype(np.uint8) * 255

### Realizar la fusión ponderada.
# La fórmula es: resultado = imagen1 * alpha + imagen2 * (1 - alpha) + gamma
# donde gamma es un valor constante a añadir (normalmente 0).
# `alpha` es el peso de la primera imagen.
# `1 - alpha` es el peso de la segunda imagen (para que los pesos sumen 1).
# 0 es el valor 'gamma' (offset o ajuste de brillo/color).

#imagen_fusionada = cv2.addWeighted(imagen_procesada, alpha, graticula, 1 - alpha, 0)
#imagen_fusionada = cv2.bitwise_and(graticula, imagen_procesada, mask=bin_graticula)

# Convertir imágenes a float para cálculos de ponderación precisos
imagen1_float = imagen_procesada.astype(np.float32)
imagen2_float = graticula.astype(np.float32)
mascara_float = mascara.astype(np.float32) / 255.0 # Máscara con valores 0.0 o 1.0

peso_para_imagen1 = 1.0 - mascara_float + alpha * mascara_float 
peso_para_imagen2 = (1.0 - alpha) * mascara_float
peso_para_imagen1_3chan = peso_para_imagen1[:, :, np.newaxis] # Formato (alto, ancho, 1)
peso_para_imagen2_3chan = peso_para_imagen2[:, :, np.newaxis] # Formato (alto, ancho, 1)

parte_imagen1 = imagen1_float * peso_para_imagen1_3chan
parte_imagen2 = imagen2_float * peso_para_imagen2_3chan

# Sumar las dos partes para obtener la imagen final
imagen_fusionada_float = parte_imagen1 + parte_imagen2

# Convertir el resultado de vuelta a uint8 y asegurar que los valores estén en el rango 0-255
imagen_fusionada = np.clip(imagen_fusionada_float, 0, 255).astype(np.uint8)

### mostrar resultados
cv2.imwrite(nombre_archivo_salida, imagen_fusionada)
cv2.imshow('IMAGEN', imagen_procesada)                  # Muestra la graticula.
cv2.imshow('IMAGEN PROCESADA', imagen_fusionada)    # Muestra la imagen.
cv2.waitKey(0)                                      # Espera que se pulse cualquier tecla.
cv2.destroyAllWindows()                             # Cierra la ventana.
