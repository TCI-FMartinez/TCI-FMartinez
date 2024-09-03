import json

def cargar_pads_desde_json(ruta_json):
    """Lee el archivo JSON y devuelve los datos como un diccionario."""
    with open(ruta_json, 'r') as archivo:
        data = json.load(archivo)
    return data['pads']

pads = cargar_pads_desde_json("pads.json")

for pad in pads:
    print(pad)