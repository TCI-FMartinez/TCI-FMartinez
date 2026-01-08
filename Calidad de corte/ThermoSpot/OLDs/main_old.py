# Este script calcula el corte láser láser
# Autor: F. Martínez
# Fecha: 2024-06-20
# Versión: 1.0

#####################################################################################
from spot_size import Cabezal
import json

#####################################################################################
# --- presets de material (valores típicos; ajusta a tu tabla) ---

MATERIALES = {
    "acero":   dict(calor_especifico_J_gK=0.5, densidad_g_cm3=7.85, deltaT_K=1500.0, calor_latente_J_g=270.0),
    "inox":    dict(calor_especifico_J_gK=0.50, densidad_g_cm3=7.9,  deltaT_K=1500.0, calor_latente_J_g=260.0),
    "aluminio":dict(calor_especifico_J_gK=0.90, densidad_g_cm3=2.70, deltaT_K=650.0,  calor_latente_J_g=400.0),
}

#####################################################################################

# --- util: propiedades de material con overrides ---
def props_material(nombre: str, **overrides):
    base = MATERIALES.get(nombre.lower())
    if not base:
        raise ValueError(f"Material desconocido: {nombre}")
    base = base.copy()
    base.update(overrides)
    return base

# ------------------------ Cálculo de balance térmico simple ------------------------
def calculo_balance_termico(
    potencia_laser_w,
    espesor_mm,
    diametro_spot_um,
    velocidad_mm_s,
    calor_especifico_J_gK=0.5,   # acero ~0.45–0.50 J/g·K
    densidad_g_cm3=7.85,         # acero ~7.85 g/cm³
    deltaT_K=1500.0,             # salto térmico hasta fusión (K)
    calor_latente_J_g=270.0,     # J/g (orden de magnitud para acero)
    factor_ancho_kerf=1.0        # >1 si el kerf real > spot (p.ej. 1.2)
):
    """
    Estima la absorción necesaria (A, 0–1) para sostener el corte.

    Modelo:
      - Volumen retirado por segundo: Vdot = w * t * v  [mm³/s]
      - Masa por segundo: mdot = rho_mm3 * Vdot        [g/s]
      - Potencia térmica requerida:
            P_req = mdot * (Cp*ΔT + Lm)                [W]
      - Balance: P_laser * A = P_req  =>  A = P_req / P_laser

    Parámetros
    ----------
    potencia_laser_w : float
        Potencia óptica disponible del láser (W).
    espesor_mm : float
        Espesor del material (mm).
    diametro_spot_um : float
        Diámetro del spot en el plano de corte (µm). Aproxima el ancho de entalla.
    velocidad_mm_s : float
        Velocidad de avance (mm/s).
    calor_especifico_J_gK : float, opcional
        Calor específico (J/g·K).
    densidad_g_cm3 : float, opcional
        Densidad del material (g/cm³).
    deltaT_K : float, opcional
        Incremento de temperatura hasta fusión (K).
    calor_latente_J_g : float, opcional
        Calor latente de fusión (J/g).
    factor_ancho_kerf : float, opcional
        Factor para contemplar que el kerf real suele ser > spot (1.0 si no se sabe).

    Returns
    -------
    A_necesaria : float
        Absorción necesaria (0–1 idealmente; >1 implica potencia insuficiente).
    resultados : dict
        Intermedios útiles para diagnóstico (potencias y caudales).

    Notas
    -----
    - Conversión densidad: g/cm³ → g/mm³ dividiendo por 1000.
    - Si A > 1.0: el corte, con esos parámetros, no se sostiene sin aumentar potencia,
      reducir velocidad, reducir espesor o aumentar absorción.
    """
    # Validaciones básicas
    if potencia_laser_w <= 0:
        raise ValueError("potencia_laser_w debe ser > 0 W")
    if espesor_mm <= 0:
        raise ValueError("espesor_mm debe ser > 0 mm")
    if diametro_spot_um <= 0:
        raise ValueError("diametro_spot_um debe ser > 0 µm")
    if velocidad_mm_s <= 0:
        raise ValueError("velocidad_mm_s debe ser > 0 mm/s")
    if densidad_g_cm3 <= 0:
        raise ValueError("densidad_g_cm3 debe ser > 0")
    if calor_especifico_J_gK <= 0 or deltaT_K <= 0 or calor_latente_J_g < 0:
        raise ValueError("Parámetros térmicos no válidos")

    # 1) Ancho efectivo de corte (mm)
    w_mm = (diametro_spot_um / 1000.0) * float(factor_ancho_kerf)

    # 2) Caudal volumétrico (mm³/s)
    vdot_mm3_s = w_mm * espesor_mm * velocidad_mm_s

    # 3) Densidad en g/mm³
    densidad_g_mm3 = densidad_g_cm3 / 1000.0

    # 4) Caudal másico (g/s)
    mdot_g_s = densidad_g_mm3 * vdot_mm3_s

    # 5) Energía específica total (J/g)
    energia_J_g = calor_especifico_J_gK * deltaT_K + calor_latente_J_g

    # 6) Potencia requerida (W)
    potencia_requerida_w = mdot_g_s * energia_J_g

    # 7) Absorción necesaria
    A_necesaria = potencia_requerida_w / potencia_laser_w

    resultados = {
        "w_mm": w_mm,
        "vdot_mm3_s": vdot_mm3_s,
        "mdot_g_s": mdot_g_s,
        "energia_J_g": energia_J_g,
        "potencia_requerida_w": potencia_requerida_w,
        "potencia_laser_w": potencia_laser_w,
        "A_necesaria": A_necesaria
    }

    return A_necesaria, resultados

# --- util: kerf desde el spot del cabezal ---
def obtener_kerf_um_desde_cabezal(cabezal, factor_kerf: float = 1.2) -> float:
    """
    Devuelve el kerf [µm] como spot_en_foco * factor_kerf.
    El spot en foco (µm) lo proporciona la clase Cabezal tras cargar el JSON.
    """
    spot_um = cabezal.parametros.get("diametro_spot_foco")
    if spot_um is None:
        raise ValueError(
            "El spot en foco es None. Revisa 'cabezal_optica.json' (NA_fibra, BPP, f_col, f_focus) y vuelve a cargar."
        )
    return spot_um * float(factor_kerf)

# --- cálculo de velocidad máxima dada absorción disponible ---
def velocidad_max_mm_s(
    potencia_laser_w, absorcion_disponible,
    espesor_mm, ancho_mm,
    calor_especifico_J_gK, densidad_g_cm3, deltaT_K, calor_latente_J_g
):
    """
    Despeje de v en: P_laser*A = rho_mm3 * (w * t * v) * (Cp*ΔT + Lm)
    v = (P_laser * A) / [rho_mm3 * w * t * (Cp*ΔT + Lm)]
    """
    if not (0 < absorcion_disponible <= 1.0):
        raise ValueError("absorcion_disponible debe estar en (0,1].")
    densidad_g_mm3 = densidad_g_cm3 / 1000.0
    energia_J_g = calor_especifico_J_gK * deltaT_K + calor_latente_J_g
    denom = densidad_g_mm3 * ancho_mm * espesor_mm * energia_J_g
    if denom <= 0:
        raise ValueError("Parámetros geométricos/térmicos inválidos para velocidad.")
    return (potencia_laser_w * absorcion_disponible) / denom

def cargar_parametros_corte_json(ruta_json="parametros_corte.json"):
    """
    Lee los parámetros de corte desde un archivo JSON y los devuelve como diccionario.
    """
    with open(ruta_json, 'r', encoding='utf-8') as f:
        parametros = json.load(f)
    return parametros

#####################################################################################
#####################################################################################
# ------------------------ MAIN ------------------------

if __name__ == "__main__":
    cabezal = Cabezal()
    cabezal.cargar_optica_desde_json("cabezal_optica.json")

    mat = props_material("acero")  # "aluminio" o "inox" según toque

    # Parámetros de ejemplo
    potencia_laser = 8000.0       # W
    espesor = 10.0                # mm
    velocidad = 600.0            # mm/s

    # 1) Obtén el kerf = spot_en_foco * 1.2
    factor_kerf = 1.2

    kerf_um = obtener_kerf_um_desde_cabezal(cabezal, factor_kerf=factor_kerf)

    print(f"Spot en foco (µm): {cabezal.parametros['diametro_spot_foco']}")
    print(f"Kerf estimado (µm) = spot * {factor_kerf}: {kerf_um:.1f}")

    # 
    A, resultados = calculo_balance_termico(
        potencia_laser_w=potencia_laser,
        espesor_mm=espesor,
        diametro_spot_um=kerf_um,
        velocidad_mm_s=velocidad,
        calor_especifico_J_gK=mat["calor_especifico_J_gK"],
        densidad_g_cm3=mat["densidad_g_cm3"],
        deltaT_K=mat["deltaT_K"],
        calor_latente_J_g=mat["calor_latente_J_g"],
        factor_ancho_kerf=1.0
    )

    print(f"Absorción necesaria A: {A:.3f} (idealmente ≤ 1.0)")
    print("\nDetalles intermedios:")
    for k, v in resultados.items():
        print(f"  {k}: {v:.2f}")

    if A > 1.0:
        print("\nEnergéticamente no cierra con estos parámetros.")
        A_obj = 0.95  # absorción estimada realista
        kerf_mm = kerf_um / 1000.0
        v_max = velocidad_max_mm_s(
            potencia_laser, A_obj, espesor, kerf_mm,
            mat["calor_especifico_J_gK"], mat["densidad_g_cm3"], mat["deltaT_K"], mat["calor_latente_J_g"]
        )
        print(f"   Velocidad máx con A={A_obj*100:.0f}%: {v_max:.1f} mm/s")
        print("    --> Aumenta potencia o reduce la velocidad.")

    param_corte = cargar_parametros_corte_json("parametros_corte.json")
    print("\nParámetros de corte cargados desde JSON:")
    for k, v in param_corte.items():
        print(f"  {k}: {v}")