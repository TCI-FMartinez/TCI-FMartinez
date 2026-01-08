# Este script caracteriza el spot láser
# Autor: F. Martínez
# Fecha: 2024-06-20
# Versión: 1.1

import json

class Cabezal:
    def __init__(self):
        self.version = "1.1"
        self.parametros = {
            # ENTRADAS (con unidades explícitas)
            "diametro_fibra": 100.0,                 # µm (core ~ multimodo)
            "distancia_focal_colimacion": 100.0,     # mm (f_col)
            "distancia_focal_enfoque": 100.0,        # mm (f_focus)
            "BPP_fibra": 3.5,                        # mm·mrad (w0·θ en mm y mrad)
            "longitud_onda": 1070.0,                 # nm (solo informativa aquí)
            "NA_fibra": None,                        # (rad) si la conoces; si None la estimo con BPP y Df
            "angulo_incidente_deg": 0.0,
            "estado_superficie": "laminada",

            # DERIVADOS / CALCULADOS
            "NA_mrad": None,                         # mrad (para mostrar)
            "diametro_haz_colimado": None,           # mm tras colimador (D_col)
            "diametro_spot_foco": None,              # µm en el foco (2·w0)
            "diametro_spot_nearfield": None,         # µm (2·w0 estimado en la fibra)
            "BPP_calculado": None,                   # mm·mrad (consistencia geométrica Df y NA)
        }

        # Cálculo inicial con defaults
        self._recalcular_todo()

    # ------------------------ CONVERSIÓN DE UNIDADES ------------------------
    @staticmethod
    def _um_to_mm(x_um): return x_um / 1000.0
    @staticmethod
    def _mm_to_um(x_mm): return x_mm * 1000.0
    @staticmethod
    def _rad_to_mrad(x_rad): return x_rad * 1000.0
    @staticmethod
    def _mrad_to_rad(x_mrad): return x_mrad / 1000.0

    # ------------------------ CARGA JSON ------------------------
    def cargar_optica_desde_json(self, ruta_json="cabezal_optica.json"):
        """
        Lee características ópticas del cabezal desde JSON.
        Claves aceptadas: diametro_fibra [µm], distancia_focal_colimacion [mm],
        distancia_focal_enfoque [mm], BPP_fibra [mm·mrad], longitud_onda [nm], NA_fibra [rad].
        """
        with open(ruta_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        try:
            self.parametros["diametro_fibra"] = datos.get("diametro_fibra", self.parametros["diametro_fibra"])
            self.parametros["distancia_focal_colimacion"] = datos.get("distancia_focal_colimacion", self.parametros["distancia_focal_colimacion"])
            self.parametros["distancia_focal_enfoque"] = datos.get("distancia_focal_enfoque", self.parametros["distancia_focal_enfoque"])
            self.parametros["BPP_fibra"] = datos.get("BPP_fibra", self.parametros["BPP_fibra"])
            self.parametros["longitud_onda"] = datos.get("longitud_onda", self.parametros["longitud_onda"])
            self.parametros["angulo_incidente_deg"] = float(datos["angulo_incidente_deg"])
            self.parametros["estado_superficie"] = str(datos["estado_superficie"])
            if "NA_fibra" in datos:
                self.parametros["NA_fibra"] = datos["NA_fibra"]
            else:
                self.parametros["NA_fibra"] = None  # forzar reestimación si no viene
        except KeyError as e:
            raise KeyError(f"Falta clave en JSON: {e}")
        except Exception as e:
            raise ValueError(f"Error al leer JSON: {e}")

        # Recalcular todo tras la carga
        self._recalcular_todo()

    # ------------------------ CÁLCULOS PRINCIPALES ------------------------
    def _estimar_NA_si_falta(self):
        """
        Si no hay NA_fibra explícita:
        Estima NA (rad) a partir de BPP y diámetro de fibra asumiendo BPP = w0·θ con w0 ≈ Df/2.
        θ(rad) ≈ (BPP_mm·rad) / (w0_mm)  => usando BPP en mm·mrad: θ(rad) = (BPP_mm·mrad/1000) / (Df_mm/2)
        """
        p = self.parametros
        if p["NA_fibra"] is not None:
            return  # ya está definida

        Df_mm = self._um_to_mm(p["diametro_fibra"])
        BPP_mmmrad = p["BPP_fibra"]

        if Df_mm <= 0 or BPP_mmmrad is None:
            p["NA_fibra"] = None
            return

        w0_mm = Df_mm / 2.0
        theta_rad = (BPP_mmmrad / 1000.0) / w0_mm  # rad
        p["NA_fibra"] = round(theta_rad, 4)  # en aire, NA ≈ θ (rad) para ángulos pequeños

    def _calcular_haz_colimado(self):
        """
        Diámetro del haz colimado tras el colimador:
        D_col [mm] ≈ 2 * f_col [mm] * NA_rad
        """
        p = self.parametros
        f_col = p["distancia_focal_colimacion"]
        NA_rad = p["NA_fibra"]

        if f_col is None or NA_rad in (None, 0):
            p["diametro_haz_colimado"] = None
            return

        p["diametro_haz_colimado"] = round(2.0 * f_col * NA_rad, 3) # mm

    def _calcular_diametro_spot_enfocado(self):
        """
        Diámetro en el foco (2·w0) usando:
        d_foco [µm] = (4 * BPP_mm·mrad * f_focus[mm]) / D_col[mm]
        """
        p = self.parametros
        BPP = p["BPP_fibra"]                # mm·mrad
        f_focus = p["distancia_focal_enfoque"]
        D_col = p["diametro_haz_colimado"]

        if None in (BPP, f_focus, D_col) or D_col == 0:
            p["diametro_spot_foco"] = None
            return

        d_um = (4.0 * BPP * f_focus) / D_col  # µm (ver deducción en explicación)
        p["diametro_spot_foco"] = round(d_um, 3)

    def _calcular_spot_nearfield(self):
        """
        Diámetro near-field (2·w0) derivado de BPP y NA:
        d0 [µm] = 2 * (BPP_mm·mrad / NA_mrad) * 1000
        """
        p = self.parametros
        BPP = p["BPP_fibra"]              # mm·mrad
        NA_rad = p["NA_fibra"]

        if BPP is None or NA_rad in (None, 0):
            p["diametro_spot_nearfield"] = None
            return

        NA_mrad = self._rad_to_mrad(NA_rad)
        d0_um = 2.0 * (BPP / NA_mrad) * 1000.0
        p["diametro_spot_nearfield"] = round(d0_um, 3)

    def _calcular_BPP_consistencia(self):
        """
        BPP estimado por geometría simple de fibra:
        BPP_est [mm·mrad] ≈ (Df_mm/2) * NA_mrad
        """
        p = self.parametros
        Df_mm = self._um_to_mm(p["diametro_fibra"])
        NA_rad = p["NA_fibra"]
        if Df_mm <= 0 or NA_rad in (None, 0):
            p["BPP_calculado"] = None
            return
        NA_mrad = self._rad_to_mrad(NA_rad)
        p["BPP_calculado"] = round((Df_mm / 2.0) * NA_mrad, 3)

    def _recalcular_todo(self):
        """Secuencia de recálculo con unidades consistentes."""
        p = self.parametros

        # 1) NA (rad) -> si no viene dada, estimo con BPP y Df
        self._estimar_NA_si_falta()

        # 2) NA en mrad para mostrar
        p["NA_mrad"] = None if p["NA_fibra"] is None else self._rad_to_mrad(p["NA_fibra"])

        # 3) Haz colimado
        self._calcular_haz_colimado()

        # 4) Spot en foco
        self._calcular_diametro_spot_enfocado()

        # 5) Near-field (por claridad y comprobación)
        self._calcular_spot_nearfield()

        # 6) BPP “calculado” por geometría de fibra (consistencia)
        self._calcular_BPP_consistencia()

    # ------------------------ Utils de usuario ------------------------
    def resumen(self):
        """Pequeño helper para imprimir parámetros clave con unidades claras."""
        p = self.parametros
        print("=== Cabezal Óptico ===")
        print(f"Fibra: D={p['diametro_fibra']:.1f} µm, BPP={p['BPP_fibra']:.3f} mm·mrad, λ={p['longitud_onda']:.0f} nm")
        if p['NA_fibra'] is not None:
            print(f"NA ≈ {p['NA_fibra']:.4f} rad  ({p['NA_mrad']:.1f} mrad)")
        else:
            print("NA: no disponible")

        print(f"f_col = {p['distancia_focal_colimacion']:.2f} mm → D_col ≈ {p['diametro_haz_colimado'] if p['diametro_haz_colimado'] is not None else 'nd'} mm")
        print(f"f_focus = {p['distancia_focal_enfoque']:.2f} mm → d_foco ≈ {p['diametro_spot_foco'] if p['diametro_spot_foco'] is not None else 'nd'} µm")
        print(f"d_near-field ≈ {p['diametro_spot_nearfield'] if p['diametro_spot_nearfield'] is not None else 'nd'} µm")
        if p["BPP_calculado"] is not None:
            print(f"BPP_calc (Df & NA) ≈ {p['BPP_calculado']:.3f} mm·mrad   (útil para comprobar consistencia)")


######################################################################################
# ------------------------ EJEMPLO DE USO ------------------------
if __name__ == "__main__":

    # Crear una instancia de Cabezal con la fibra
    cabezal = Cabezal()

    # Cargar parámetros ópticos desde un fichero JSON (IMPRESCINDIBLE)
    cabezal.cargar_optica_desde_json("cabezal_optica.json")
    
    # Mostrar un resumen claro
    print("\nResumen óptico del cabezal:")
    cabezal.resumen()

