# Este script caracteriza el spot láser
# Autor: F. Martínez
# Fecha: 2024-06-20


import numpy as np
import matplotlib.pyplot as plt
import math
import json

#########################################
# CABEZAL
#########################################
class Cabezal:
    def __init__(self): 
        self.version = "1.0"
        self.parametros = {
            "diametro_fibra": 100,  # micrómetros
            "distancia_focal_colimacion": 100.0,  # mm
            "distancia_focal_enfoque": 100.0,  # mm
            "BPP_fibra": 3.5,  # mm*mrad
            "longitud_onda": 1070,  # nm
            "NA": 0,  # Apertura numérica
            "diametro_spot": 0,  # micrómetros
            "spot_divergente": 0,  # micrómetros
            "BPP_calculado": 0  # mm*mrad
        }
        # Calcular la apertura numérica al crear la instancia
        self.parametros["NA"] = self.calcular_apertura_numerica()
        # Calcular el diámetro del spot al crear la instancia
        self.parametros["diametro_spot"] = self.calcular_diametro_spot()
        # Calcular el spot divergente al crear la instancia
        self.parametros["spot_divergente"] = self.calcular_spot_divergente()
        # VERIFICA el BPP al crear la instancia
        self.parametros["BPP_calculado"] = self.calcular_BPP()

    def cargar_optica_desde_json(self, ruta_json="cabezal_optica.json"):
        """
        Lee las características ópticas del cabezal desde un fichero JSON.
        Espera las claves: diametro_fibra, distancia_focal_colimacion, distancia_focal_enfoque, BPP_fibra
        """
        with open(ruta_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        self.parametros["diametro_fibra"] = datos.get("diametro_fibra", self.parametros["diametro_fibra"])
        self.parametros["distancia_focal_colimacion"] = datos.get("distancia_focal_colimacion", None)
        self.parametros["distancia_focal_enfoque"] = datos.get("distancia_focal_enfoque", None)
        self.parametros["BPP_fibra"] = datos.get("BPP_fibra", None)
        self.parametros["longitud_onda"] = datos.get("longitud_onda", None)

    def calcular_apertura_numerica(self):
        """
        Calcula la apertura numérica (NA) en milirradianes (mrad) usando el diámetro de la fibra y la distancia focal de colimación.
        NA (mrad) = (diámetro_fibra / distancia_focal_colimacion)
        Retorna el valor calculado.
        """
        diametro = self.parametros["diametro_fibra"]  # micrómetros
        distancia_focal = self.parametros["distancia_focal_colimacion"]  # mm
        # Convertimos diámetro a mm para que las unidades sean consistentes
        diametro_mm = diametro / 1000.0
        if distancia_focal == 0:
            self.parametros["NA"] = None
            return None
        NA_mrad = (diametro_mm / distancia_focal) * 1000  # resultado en mrad
        #print(f"{diametro_mm} mm / {distancia_focal} mm  (NA) calculada: {NA_mrad:.2f} mrad")
        self.parametros["NA"] = NA_mrad
        return NA_mrad
    
    def calcular_diametro_spot(self):
        """
        Calcula el diámetro del spot en el plano de enfoque usando la fórmula:
        diámetro_spot (micrómetros) = (BPP_fibra * distancia_focal_enfoque)
        Retorna el valor calculado en micrómetros.
        """
        BPP = self.parametros["BPP_fibra"]  # mm*mrad
        distancia_focal = self.parametros["distancia_focal_enfoque"]  # mm
        if BPP is None or distancia_focal is None:
            return None
        diametro_spot = BPP * distancia_focal  # resultado en mm*mrad
        return round(diametro_spot, 3)  # Si quieres en micrómetros: diametro_spot * 1000

    def calcular_spot_divergente(self):
        """
        Calcula el diámetro del spot divergente (en micrómetros) usando el BPP y la apertura numérica (NA).
        Fórmula:
            spot_divergente (µm) = (BPP_fibra / NA) * 1000
        Donde:
            BPP_fibra está en mm·mrad
            NA está en mrad
        Retorna el valor calculado.
        """
        BPP = self.parametros["BPP_fibra"]  # mm*mrad
        NA = self.parametros["NA"]           # mrad
        if BPP is None or NA in (None, 0):
            return None
        spot_divergente = (BPP / NA) * 1000  # resultado en micrómetros
        return round(spot_divergente, 3)

    def calcular_BPP(self):
        """
        Calcula el BPP (Beam Parameter Product) usando la fórmula:
        BPP = (Df / 2) * (θ / 2)
        Donde:
            Df: diámetro de la fibra (micrómetros)
            θ: ángulo de divergencia (mrad)
        El resultado se da en mm·mrad.
        """
        Df = self.parametros["diametro_fibra"]  # micrómetros
        Lf = self.parametros["distancia_focal_enfoque"]  # mm
        Lc = self.parametros["distancia_focal_colimacion"]  # mm
        theta = self.parametros["NA"]           # mrad
        if Df is None or theta is None:
            return None
        Df_mm = Df / 1000  # Convertir a mm
        BPP = (Df_mm / 2) * (theta / 2)  # mm * mrad
        print(f"{Df_mm} mm / 2 * {theta} mrad / 2  (BPP) calculado: {BPP:.2f} mm·mrad")
        ##### Verificación del Spot Divergente #####
        if Lc != 0:
            SPOT_div = 0.5 * ((Df_mm * Lf * theta) / Lc)
            print(f"Verificación BPP -> Spot: {SPOT_div:.2f} micrómetros")
        return BPP


#####################################################################################
if __name__ == "__main__":

    # Crear una instancia de Cabezal con la fibra
    cabezal = Cabezal()

    # Cargar parámetros ópticos desde un fichero JSON
    cabezal.cargar_optica_desde_json("cabezal_optica.json")

    # Mostrar los parámetros cargados
    print("Parámetros del cabezal óptico:")
    for clave, valor in cabezal.parametros.items():
        print(f"  {clave}: {valor}")
