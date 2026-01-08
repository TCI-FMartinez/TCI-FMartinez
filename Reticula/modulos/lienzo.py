### GENERAR LIEZO ###

#import cv2
import numpy as np

def Lienzo(x_px=800, y_px=600, grey_n=255):
    # creación de una imagen con una matríz de x filas
    #   por y columnas y 3 canales.
    # Esta matriz se multiplica por 255 para hacerla blanca.
    imagen = grey_n*np.ones((y_px, x_px,3),dtype=np.uint8)
    return imagen

if __name__ == "__main__":
    import cv2
    imagen = Lienzo(600, 400, 255)

    cv2.imshow('lienzo',imagen)     # Muestra la imagen.
    cv2.waitKey(0)                  # Espera que se pulse cualquier tecla.
    cv2.destroyAllWindows()         # Cierra la ventana.