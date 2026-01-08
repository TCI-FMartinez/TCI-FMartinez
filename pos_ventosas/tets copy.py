import json
import cv2
import numpy as np

formato = (800, 600)

my_list = []
_puntos = []


contorno = {
    "contour": [(-13, 97), (13, 97), (160, 21), (160, -21), (13, -97), (-13, -97), (-160, -21), (-160, 21)]
}

my_list.append(contorno)

def Lienzo(x_px=800, y_px=600, grey_n=255):
    """Creación de una imagen con una matríz
       de x filas por y columnas y 3 canales (b,g,r).
    Esta matriz se multiplica por 255 para hacerla blanca."""
    imagen = grey_n*np.ones((y_px, x_px,3),dtype=np.uint8)
    return imagen


with open("my_file.json", "w") as f:

    json.dump(contorno, f, indent=4)


with open("my_file.json") as f:

    my_other_list = json.load(f)


contorno_ = list(my_other_list.values())
print("contorno_ =",type(contorno_), contorno_[0])

for p in contorno_[0]:
    x = p[0]+formato[0]/2
    y = p[1]+formato[1]/2
    p_c = (int(x), int(y))
    _puntos.append(p_c)

puntos_array = np.array(_puntos)

######################################################

imagen = Lienzo(x_px=formato[0], y_px=formato[1])
#cv2.drawContours(imagen, [contorno["contour"]], -1, (0, 0, 0), 2)
cv2.drawContours(imagen, [puntos_array], -1, (0, 0, 0), 2)
cv2.imshow("HERRAMIENTA", imagen)
cv2.waitKey(5000)
