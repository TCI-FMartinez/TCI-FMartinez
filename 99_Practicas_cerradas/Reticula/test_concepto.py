import cv2
import numpy as np
import os

# --- PASO 1: Cargar las dos imágenes ---
# Asegúrate de que las imágenes tengan las mismas dimensiones (ancho y alto).
# El número de canales puede ser diferente, pero el enmascaramiento es más directo
# si ambas son BGR o si una es BGR y la otra Gris, y se convierte a BGR antes de operar.

ruta_imagen1 = 'imagen1.jpg'         # <--- Reemplaza con tu primera imagen (fondo)
ruta_imagen2 = 'graticula.png' # <--- Reemplaza con tu segunda imagen (primer plano con áreas negras transparentes)
ruta_salida = 'imagen_fusionada_mascara_negro.jpg'

try:
    imagen1 = cv2.imread(ruta_imagen1)
    # Leer imagen2 con posible canal alfa si es PNG, aunque el check de negro (0,0,0) es para BGR
    # Si imagen2 es BGR, cv2.imread la carga como BGR por defecto.
    # Si es PNG con alfa, imread(..., cv2.IMREAD_UNCHANGED) la carga como BGRA (4 canales).
    # Para este caso específico (ignorar negro BGR), cargaremos como BGR.
    imagen2 = cv2.imread(ruta_imagen2, cv2.IMREAD_COLOR) # Aseguramos cargarla en color (BGR)

    if imagen1 is None:
        raise FileNotFoundError(f"No se pudo cargar {ruta_imagen1}")
    if imagen2 is None:
         raise FileNotFoundError(f"No se pudo cargar {ruta_imagen2}")

    # Asegurarse de que imagen2 sea BGR (si era gris, convertirla)
    if len(imagen2.shape) == 2: # Es escala de grises
         imagen2 = cv2.cvtColor(imagen2, cv2.COLOR_GRAY2BGR)
    # Asegurarse de que imagen1 sea BGR (si era gris, convertirla) para que coincida
    if len(imagen1.shape) == 2: # Es escala de grises
         imagen1 = cv2.cvtColor(imagen1, cv2.COLOR_GRAY2BGR)


    # Asegúrate de que tengan las mismas dimensiones
    if imagen1.shape[:2] != imagen2.shape[:2]:
        print(f"Las imágenes no tienen las mismas dimensiones. Redimensionando {ruta_imagen2}.")
        # Redimensionar la segunda imagen para que coincida con la primera en alto y ancho
        imagen2 = cv2.resize(imagen2, (imagen1.shape[1], imagen1.shape[0]), interpolation=cv2.INTER_AREA)

except FileNotFoundError as e:
    print(f"Error al cargar una de las imágenes: {e}")
    exit()
except Exception as e:
    print(f"Ocurrió un error: {e}")
    exit()

# --- PASO 2: Crear la máscara basada en los píxeles negros de imagen2 ---
# Un píxel es negro si sus componentes B, G y R son 0.
# Queremos que la máscara sea 255 donde NO es negro, y 0 donde SÍ es negro.

# Sumar los canales B, G, R. Un píxel negro (0,0,0) sumará 0.
suma_canales = imagen2.sum(axis=2)

# Crear la máscara: 255 donde la suma > 0 (no es negro), 0 donde la suma == 0 (es negro)
# Convertir el resultado booleano a uint8 (True=1, False=0) y multiplicar por 255
mascara = (suma_canales > 0).astype(np.uint8) * 255

# Opcional: Si quieres ver la máscara
# cv2.imshow("Máscara (255=No Negro, 0=Negro)", mascara)

# --- PASO 3: Definir el factor alfa para la mezcla en las áreas NO negras ---
# Este alfa solo se aplicará donde imagen2 NO sea negra.
alpha = 0.7 # <--- Controla aquí el nivel de mezcla (entre 0.0 y 1.0) en las áreas no negras

# --- PASO 4: Realizar la fusión utilizando la máscara ---

# Convertir imágenes a float para cálculos de ponderación precisos
imagen1_float = imagen1.astype(np.float32)
imagen2_float = imagen2.astype(np.float32)
mascara_float = mascara.astype(np.float32) / 255.0 # Máscara con valores 0.0 o 1.0

# --- Calcular los pesos para cada imagen en base a la máscara y alpha ---

# Peso que se aplica a imagen1:
# Donde mascara_float es 0 (imagen2 negra), el peso para imagen1 es 1.0 (100%)
# Donde mascara_float es 1.0 (imagen2 NO negra), el peso para imagen1 es alpha
# La fórmula es: 1.0 * (1.0 - mascara_float) + alpha * mascara_float
peso_para_imagen1 = 1.0 - mascara_float + alpha * mascara_float # Esto sigue siendo (alto, ancho)

# Peso que se aplica a imagen2:
# Donde mascara_float es 0 (imagen2 negra), el peso para imagen2 es 0.0 (0%)
# Donde mascara_float es 1.0 (imagen2 NO negra), el peso para imagen2 es (1.0 - alpha)
# La fórmula es: 0.0 * (1.0 - mascara_float) + (1.0 - alpha) * mascara_float
peso_para_imagen2 = (1.0 - alpha) * mascara_float # Esto también es (alto, ancho)

# --- Expandir las dimensiones de los pesos para que coincidan con los canales de las imágenes ---
# Ahora convertimos los mapas de peso (alto, ancho) a (alto, ancho, 1)
# Esto permite que NumPy los "broadcast" correctamente a (alto, ancho, 3) durante la multiplicación

peso_para_imagen1_3chan = peso_para_imagen1[:, :, np.newaxis] # Forma (alto, ancho, 1)
peso_para_imagen2_3chan = peso_para_imagen2[:, :, np.newaxis] # Forma (alto, ancho, 1)


# --- Aplicar los pesos a las imágenes ---
# Ahora la multiplicación es compatible: (alto, ancho, 3) * (alto, ancho, 1) -> (alto, ancho, 3)
parte_imagen1 = imagen1_float * peso_para_imagen1_3chan
parte_imagen2 = imagen2_float * peso_para_imagen2_3chan

# Sumar las dos partes para obtener la imagen final
imagen_fusionada_float = parte_imagen1 + parte_imagen2

# Convertir el resultado de vuelta a uint8 y asegurar que los valores estén en el rango 0-255
imagen_fusionada = np.clip(imagen_fusionada_float, 0, 255).astype(np.uint8)


# --- PASO 5: Mostrar o guardar la imagen resultante ---
cv2.imshow('Imagen 1 (Fondo)', imagen1)
cv2.imshow('Imagen 2 (Primer plano)', imagen2)
cv2.imshow('Imagen Fusionada (Negro en imagen2 = Transparente)', imagen_fusionada)

# Guardar la imagen procesada
cv2.imwrite(ruta_salida, imagen_fusionada)
print(f"Imagen procesada guardada como {ruta_salida}")

print(f"Imágenes fusionadas con alfa = {alpha} (aplicado solo fuera de las áreas negras de imagen2). Presiona cualquier tecla para salir.")

cv2.waitKey(0)
cv2.destroyAllWindows()