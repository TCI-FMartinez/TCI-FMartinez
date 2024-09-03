import cv2
import numpy as np
import json
from to_dxf import generar_dxf
from os import sep, path, makedirs

pads = list()
lienzo_xy = (1500, 1125)
FormatoSalida = (800, 600)

class Pad:
    def __init__ (self, id:int=0, posX:int=0, posY:int=0, _type:int=1, force:float=0.0,
                  is_active:bool=False, diameter:int=0, dependence:tuple=(1, 1)):
        self.id = id
        self.pos = (posX, posY)
        self._type = _type
        self.force = force
        self.is_active = is_active
        self.diameter = diameter
        self.dependence = dependence    # Una tupla con el operador para el eje X e Y. -1=invierte, 0=no mueve.

    def activate(self) -> bool:
        self.is_active = True
        return True
    
    def deactivate(self) -> bool:
        self.is_active = False
        return False
    
    def move(self, movXY:tuple) -> tuple:
        self.new_pos = ((self.pos[0] + (movXY[0] * self.dependence[0])),
                        (self.pos[1] + (movXY[1] * self.dependence[1])))
        return self.new_pos

def Lienzo(x_px=800, y_px=600, grey_n=255):
    """Creación de una imagen con una matríz
       de x filas por y columnas y 3 canales (b,g,r).
    Esta matriz se multiplica por 255 para hacerla blanca."""
    imagen = grey_n*np.ones((y_px, x_px,3),dtype=np.uint8)
    return imagen

def invertY(value):
    """Invierte el signo"""
    return -1*value

def coloize(active:bool=False, _type:int=1):
    if active and _type == 1:
        color = (100, 200, 100)
    elif active and _type == 2:
        color = (255, 100, 100)
    elif active and _type > 2:
        color = (0, 0, 255)
    else:
        color = (155, 155, 155)
    return color

def cargar_pads_desde_json(ruta_json):
    """Lee el archivo JSON y devuelve los datos como un diccionario."""
    with open(ruta_json, 'r') as archivo:
        data = json.load(archivo)
    pads = []
    for pad_data in data['pads']:
        pad = Pad(
            id=pad_data['id'],
            posX=pad_data['posX'],
            posY=pad_data['posY'],
            _type=pad_data['type'],
            force=pad_data['force'],
            is_active=pad_data['is_active'],
            diameter=pad_data['diameter'],
            dependence=tuple(pad_data['dependence'])
        )
        pads.append(pad)
    return pads

############################################################################
if __name__ == "__main__":
    print("PROCESANDO...")
    posiciones_x = list(set((0, 76, 150, 262, 326, 326, 450)))
    posiciones_y = list(set((0, 76, 150, 262)))

    pads = cargar_pads_desde_json("pads.json")

    # Activar pads
    #pads[7].activate()  # pad08
    #pads[8].activate()  # pad09
    #pads[11].activate() # pad12
    #pads[12].activate() # pad13

    for p in pads:  # Activa todas menos las ,6 primeras, 0 activa todas.
        if p.id > 0: p.activate()

    p_actives = list()

    for p in pads:              #  p_actives = [p.id for p in pads if p.is_active]
        if p.is_active:
            p_actives.append(p.id)
    n_actives = len(p_actives)

    # SALIDA
    print("GENERANDO...")
    n_h = 0
    tools = []
    pads_data = [] 

    for y in posiciones_y:
        for x in posiciones_x:
            imagen = Lienzo(lienzo_xy[0], lienzo_xy[1], 255)
            # DESPLAZAR PADS
            for p in pads:
                p.move((x, y))  
                #print(f"pad{p.id} movído a:", p.new_pos)
                # Generar lista de diccionarios para cada Pad
                pad_data = {
                    "id": p.id,
                    "diameter": p.diameter,
                    "position": [p.pos[0], p.pos[1]],
                    "force": p.force
                }
                pads_data.append(pad_data)
            id_h = {"tool":n_h}
            tools.append((id_h, pads_data))

            # DIBUJADO
            texto1= f"Herramienta:{n_h} X:{x} Y:{y}"
            imagen = cv2.putText(imagen, texto1,(10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 1, cv2.LINE_AA)
            centro = (0 + int(lienzo_xy[0]/2), 0 + int(lienzo_xy[1]/2))

            for p in pads:
                pos_p = (int(p.new_pos[0]+centro[0]), lienzo_xy[1] + invertY(int(p.new_pos[1]+centro[1])))
                txt_long = int(len(p.new_pos)*18)
                imagen = cv2.circle(imagen, pos_p, int(p.diameter/2), coloize(p.is_active, p._type), -1)
                imagen = cv2.circle(imagen, pos_p, int(p.diameter/2), (0,0,0), 2)    #borde exterior
                imagen = cv2.putText(imagen, f"{p.id}",(pos_p[0]-6, pos_p[1]+4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
                imagen = cv2.putText(imagen, f"{p.new_pos}",(pos_p[0]-txt_long, pos_p[1]+18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (40, 40, 40), 1, cv2.LINE_AA)
                #centro
                imagen = cv2.putText(imagen, "(0, 0)",(centro[0]-20, centro[1]+6), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (40, 40, 40), 1, cv2.LINE_AA)

            # GENRAR SALIDA
            if not path.exists("OUTPUT"):
                makedirs("OUTPUT")
            img_peq = cv2.resize(imagen, FormatoSalida)
            filename = f"{n_h}_Herramienta_{x}-{y}"

            #cv2.imshow("VENTOSAS", img_peq)
            #cv2.waitKey()
            cv2.imwrite(f"OUTPUT{sep}{filename}.png", img_peq)

            generar_dxf(pads, f"OUTPUT{sep}{filename}.dxf")
            n_h +=1

    # Convertir la lista de diccionarios a JSON
    json_data = json.dumps({"tools": tools}, indent=4)

    # Guardar en un archivo JSON
    with open(f"OUTPUT{sep}tools_data.json", "w") as f:
        f.write(json_data)

print("FINALIZADO")