import json
from os import sep
import numpy as np

ruta_pos_json = f"HERRAMIENTA01{sep}posiciones.json"

def cargar_posiciones_desde_json(ruta_json="posiciones.json"):
    """Lee el fichero posiciones.json y devuelbe una lista con dos listas X Y"""
    posX = list()
    posY = list()
    with open(ruta_json, 'r') as archivo:
        data = json.load(archivo)
        for xpos in data["posX"]:
            posX.append(xpos)
        for ypos in data["posY"]:
            posY.append(ypos)
    return posX[0], posY[0]

posiciones = cargar_posiciones_desde_json(ruta_pos_json)

print(posiciones)