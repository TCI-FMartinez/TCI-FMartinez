import json
import cv2
import numpy as np
from os import sep

formato = (800, 600)
filename = "tool01_salida_contornos"

my_list = []
_puntos = []
_ventosas = []
_circulos = []


def Lienzo(x_px=800, y_px=600, grey_n=255):
    """Creación de una imagen con una matríz
       de 'x' filas por 'y' columnas con 3 canales (b,g,r).
    Esta matriz se multiplica por 255 para hacerla blanca."""
    if x_px == 0: x_px = 800
    if y_px == 0: y_px = 600
    imagen = grey_n*np.ones((y_px, x_px,3),dtype=np.uint8)
    return imagen

with open(f"HERRAMIENTA01{sep}tool01_entrada_ventosas.json") as v:
    herramienta_ = json.load(v)


ventosas = herramienta_["ventosas"]
contorno = herramienta_["contorno"]

print(">>>>>>>>>>>> contorno =:", type(contorno), contorno)

ventosas_dict = dict(ventosas[0])
contorno_dict = dict(contorno)

for i in ventosas:        
    x = float(i["position"][0]+formato[0]/2)
    y = float(i["position"][1]+formato[1]/2)
    x_ = i["position"][0]
    y_ = i["position"][1]
    position = {"position": [x_, y_]}
    diameter = {"diameter": [i["diameter"]]}
    type_ = {"type": [i["type"]]}
    _ventosas.append([position, diameter, type_])
    _circulos.append(((x, y), float(i["diameter"])))

#####################################################################
print("#"*50)
print("contorno =",type(contorno), contorno)
print("_ventosas =",type(_ventosas))
for i in _ventosas:
    print(i)

#####################################################################

my_list.append(_ventosas)
my_list.append(contorno)

with open(f"HERRAMIENTA01{sep}{filename}.json", "w") as f:

    json.dump(my_list, f, indent=4)
    f.close()

#####################################################################
imagen = Lienzo(x_px=formato[0], y_px=formato[1])

for p in contorno:
    x = p[0]+formato[0]/2
    y = p[1]+formato[1]/2
    p_c = (int(x), int(y))
    _puntos.append(p_c)

for c in _circulos:
    print(">>>>>>>>>>>>>>> circulo=", c[0], c[1])
    cv2.circle(imagen, (int(c[0][0]),int(c[0][1])), int(c[1]/2), (0,0,0), 2)

puntos_array = np.array(_puntos)


#cv2.drawContours(imagen, [contorno["contour"]], -1, (0, 0, 0), 2)
cv2.drawContours(imagen, [puntos_array], -1, (0, 0, 0), 2)
cv2.imshow("HERRAMIENTA", imagen)
cv2.waitKey(5000)
cv2.imwrite(f"HERRAMIENTA01{sep}{filename}.png", imagen)
