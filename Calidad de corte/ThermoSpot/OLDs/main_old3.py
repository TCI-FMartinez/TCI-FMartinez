# -*- coding: utf-8 -*-
# Script de cálculo de corte láser (modelo simple + avanzado con gas)
# Autor: F. Martínez (adaptado)
# Fecha: 2025-10-01
# Versión: 2.0  (kerf por desenfoque + JSON + [MODO AVANZADO] restaurado)

from spot_size import Cabezal
import json
from dataclasses import dataclass
import cmath
import os
from math import sqrt, sin, cos, radians, log10, exp, pi

#####################################################################################
# --- presets de material (valores típicos; ajusta a tu tabla) ---

MATERIALES = {
    "acero":    dict(calor_especifico_J_gK=0.50, densidad_g_cm3=7.85, deltaT_K=1500.0, calor_latente_J_g=270.0),
    "inox":     dict(calor_especifico_J_gK=0.50, densidad_g_cm3=7.90, deltaT_K=1500.0, calor_latente_J_g=260.0),
    "aluminio": dict(calor_especifico_J_gK=0.90, densidad_g_cm3=2.70, deltaT_K=650.0,  calor_latente_J_g=400.0),
}

def props_material(nombre: str, **overrides) -> dict:
    base = MATERIALES.get(str(nombre).strip().lower())
    if base is None:
        raise ValueError(f"Material desconocido: {nombre!r}. Opciones: {', '.join(MATERIALES.keys())}")
    out = base.copy()
    out.update(overrides or {})
    return out

#####################################################################################
# --- Balance térmico simple --------------------------------------------------------
def calculo_balance_termico(
    potencia_laser_w: float,
    espesor_mm: float,
    diametro_spot_um: float,
    velocidad_mm_s: float,
    calor_especifico_J_gK: float,
    densidad_g_cm3: float,
    deltaT_K: float,
    calor_latente_J_g: float,
    factor_ancho_kerf: float = 1.0,
):
    """
    Modelo 0D: P_laser * A = m_dot * (Cp*ΔT + Lm)

    - Ancho efectivo de corte w = (diametro_spot_um/1000) * factor_ancho_kerf
    - m_dot = ρ * w * espesor * velocidad
    """
    if potencia_laser_w <= 0 or espesor_mm <= 0 or diametro_spot_um <= 0 or velocidad_mm_s <= 0:
        raise ValueError("Parámetros geométricos o de potencia inválidos en modo simple.")
    # 1) Ancho efectivo (mm)
    w_mm = (float(diametro_spot_um) / 1000.0) * float(factor_ancho_kerf)

    # 2) Caudal volumétrico (mm^3/s)
    vdot_mm3_s = w_mm * float(espesor_mm) * float(velocidad_mm_s)

    # 3) Densidad (g/mm^3)
    densidad_g_mm3 = float(densidad_g_cm3) / 1000.0

    # 4) Caudal másico (g/s)
    mdot_g_s = densidad_g_mm3 * vdot_mm3_s

    # 5) Energía específica (J/g)
    energia_J_g = float(calor_especifico_J_gK) * float(deltaT_K) + float(calor_latente_J_g)

    # 6) Potencia requerida (W)
    potencia_requerida_w = mdot_g_s * energia_J_g

    # 7) Absorción necesaria A (idealmente ≤ 1)
    A_necesaria = potencia_requerida_w / float(potencia_laser_w)

    resultados = {
        "w_mm": w_mm,
        "vdot_mm3_s": vdot_mm3_s,
        "mdot_g_s": mdot_g_s,
        "energia_J_g": energia_J_g,
        "potencia_requerida_w": potencia_requerida_w,
        "potencia_laser_w": float(potencia_laser_w),
        "A_necesaria": A_necesaria,
    }
    return A_necesaria, resultados

def velocidad_max_mm_s(
    potencia_laser_w: float,
    absorcion_disponible: float,
    espesor_mm: float,
    kerf_mm: float,
    calor_especifico_J_gK: float,
    densidad_g_cm3: float,
    deltaT_K: float,
    calor_latente_J_g: float,
) -> float:
    """
    Inversión del balance para obtener la velocidad máxima con A fija.
    v_max = (P_laser * A) / [ρ * kerf * espesor * (Cp*ΔT + Lm)]
    """
    if not (0 < absorcion_disponible <= 1.0):
        raise ValueError("absorcion_disponible debe estar en (0,1].")
    numerador = float(potencia_laser_w) * float(absorcion_disponible)
    energia_especifica = float(calor_especifico_J_gK) * float(deltaT_K) + float(calor_latente_J_g)
    mdot_por_v = (float(densidad_g_cm3) / 1000.0) * float(kerf_mm) * float(espesor_mm)  # g/mm · mm => g/s por (mm/s)
    denom = mdot_por_v * energia_especifica  # W por (mm/s)
    if denom <= 0:
        raise ValueError("Denominador no válido al calcular v_max.")
    return numerador / denom

#####################################################################################
# --- Kerf por desenfoque -----------------------------------------------------------
def kerf_um_por_defocus(cabezal: Cabezal, posicion_focal_mm: float) -> float:
    """
    Calcula el kerf [µm] como el diámetro del spot en la superficie en función del desenfoque.
    
    Convención del signo:
      +posicion_focal_mm  -> foco por encima de la superficie (en el gas)
       0                   -> foco en la superficie
      -posicion_focal_mm  -> foco dentro del material

    Fórmulas:
      w0 = d_foco/2
      θ = (BPP / 1000) / w0      [rad]   (BPP en mm·mrad, w0 en mm)
      zR ≈ w0 / θ                [mm]
      w(z) = w0 * sqrt(1 + (z/zR)^2)
      d(z) = 2 * w(z)
      kerf = d(z) donde z = -posicion_focal_mm (desde foco hasta superficie)
    """
    p = cabezal.parametros
    d_foco_um = p.get("diametro_spot_foco")
    BPP_mm_mrad = p.get("BPP_fibra")

    if not d_foco_um or not BPP_mm_mrad or d_foco_um <= 0 or BPP_mm_mrad <= 0:
        raise ValueError("Faltan 'diametro_spot_foco' o 'BPP_fibra' en el cabezal. Revisa cabezal_optica.json.")

    w0_mm = (d_foco_um * 1e-3) / 2.0                # µm -> mm y /2
    theta_rad = (BPP_mm_mrad / 1000.0) / w0_mm      # rad
    if theta_rad <= 0:
        raise ValueError("Divergencia θ no válida (≤ 0).")

    zR_mm = w0_mm / theta_rad
    z_mm = -float(posicion_focal_mm)                # distancia desde foco a la superficie

    w_surface_mm = w0_mm * sqrt(1.0 + (z_mm / zR_mm) ** 2)
    d_surface_mm = 2.0 * w_surface_mm

    kerf_um = d_surface_mm * 1000.0                 # mm -> µm
    return max(1e-6, kerf_um)

#####################################################################################
# --- [MODO AVANZADO] con gas de asistencia ----------------------------------------
@dataclass
class GasAssist:
    nombre: str                  # "O2" o "N2"
    T_gas_K: float               # ~300 K
    h_jet_W_m2K: float           # coef. convectivo del chorro en el kerf
    delta_h_reac_J_per_kgFe: float = 0.0  # magnitud del calor de reacción (solo O2)
    frac_ox: float = 0.0         # fracción de masa oxidada (0..1)

@dataclass
class CorteSetup:
    material: str                # "acero", "inox", "aluminio"
    espesor_mm: float            # [mm]
    kerf_mm: float               # [mm]
    velocidad_mm_s: float        # [mm/s]
    P_laser_W: float             # [W]
    absorptividad: float         # 0..1
    f_vap: float = 0.0           # fracción de masa que vaporiza (0..1)
    k_otros_W: float = 0.0       # pérdidas lumped (conducción/radiación) opcional
    gas: GasAssist | None = None

# Calibración rápida por espesor y gas (valores de partida)
CALIB_GAS = {
    "acero": {
        3:  {"O2": dict(h_jet=1.8e4, frac_ox=0.35, dh=3.2e6), "N2": dict(h_jet=1.5e4, frac_ox=0.0, dh=0.0)},
        6:  {"O2": dict(h_jet=2.0e4, frac_ox=0.40, dh=3.5e6), "N2": dict(h_jet=1.6e4, frac_ox=0.0, dh=0.0)},
        10: {"O2": dict(h_jet=2.2e4, frac_ox=0.45, dh=3.7e6), "N2": dict(h_jet=1.8e4, frac_ox=0.0, dh=0.0)},
    }
}

def _nearest_key(keys, value):
    return min(keys, key=lambda k: abs(k - value))

def gas_calibrado(material: str, espesor_mm: float, nombre_gas: str, T_gas_K: float = 400.0) -> GasAssist:
    mat_tbl = CALIB_GAS.get(material, {})
    if not mat_tbl:
        return GasAssist(nombre=nombre_gas, T_gas_K=T_gas_K, h_jet_W_m2K=1.8e4, delta_h_reac_J_per_kgFe=(3.5e6 if nombre_gas.upper()=="O2" else 0.0), frac_ox=(0.4 if nombre_gas.upper()=="O2" else 0.0))
    k = _nearest_key(list(mat_tbl.keys()), espesor_mm)
    row = mat_tbl[k].get(nombre_gas.upper())
    if not row:
        return GasAssist(nombre=nombre_gas, T_gas_K=T_gas_K, h_jet_W_m2K=1.8e4)
    return GasAssist(
        nombre=nombre_gas,
        T_gas_K=T_gas_K,
        h_jet_W_m2K=row["h_jet"],
        delta_h_reac_J_per_kgFe=row["dh"],
        frac_ox=row["frac_ox"],
    )

# Absorptividad desde óptica del cabezal (Fresnel + correcciones); con fallback log(I)
ABS_CONST = {
    "acero":    dict(A0=0.30, k=0.03, Iref_W_m2=1.0e8, A_min=0.10, A_max=0.60),
    "inox":     dict(A0=0.32, k=0.03, Iref_W_m2=1.0e8, A_min=0.12, A_max=0.62),
    "aluminio": dict(A0=0.12, k=0.02, Iref_W_m2=2.0e8, A_min=0.05, A_max=0.40),
}

OPTICAL_NK = {
    "acero":    dict(lambda_nm=1070.0, n=2.9,  k=3.3),
    "inox":     dict(lambda_nm=1070.0, n=2.2,  k=3.4),
    "aluminio": dict(lambda_nm=1070.0, n=1.5,  k=11.0),
}

def cargar_optical_nk_json(ruta_json: str = "optical_constants.json"):
    try:
        if not os.path.exists(ruta_json):
            return False
        with open(ruta_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mat, row in data.items():
            if isinstance(row, dict) and all(k in row for k in ("lambda_nm", "n", "k")):
                OPTICAL_NK[mat] = dict(lambda_nm=float(row["lambda_nm"]), n=float(row["n"]), k=float(row["k"]))
        return True
    except Exception:
        return False

SURFACE_SIGMA_UM = {  # rugosidad RMS (µm) típica
    "pulida":   0.05,
    "lijada":   0.15,
    "laminada": 0.30,
    "oxidada":  0.50,
}

OXIDE_REDUCTION = {   # reducción relativa de R por óxido
    "ninguna": 0.00,
    "ligera":  0.08,
    "media":   0.15,
    "fuerte":  0.25,
}

def _fresnel_R_metal(n: float, k: float, theta_deg: float, pol: str = "unpol") -> float:
    n1 = 1.0
    n2 = complex(n, -k)
    theta = radians(theta_deg)
    sin_t = n1 * sin(theta) / n2
    cos_t = cmath.sqrt(1 - sin_t**2)
    cos_i = cos(theta)

    rs = (n1*cos_i - n2*cos_t) / (n1*cos_i + n2*cos_t)
    rp = (n2*cos_i - n1*cos_t) / (n2*cos_i + n1*cos_t)

    Rs = abs(rs)**2
    Rp = abs(rp)**2

    if pol == 's':
        return float(Rs)
    if pol == 'p':
        return float(Rp)
    return float(0.5*(Rs+Rp))

def _roughness_correction(R: float, lambda_nm: float, theta_deg: float, sigma_um: float) -> float:
    cos_i = cos(radians(theta_deg))
    lambda_um = lambda_nm * 1e-3
    atten = exp(- (4*pi*sigma_um*cos_i / lambda_um)**2 )
    return R * atten

def estimar_absorptividad_desde_cabezal(cabezal: "Cabezal", P_W: float, material: str,
                                        lambda_nm: float = 1070.0,
                                        theta_deg: float | None = None,
                                        polarizacion: str = "unpol",
                                        estado_superficie: str | None = None,
                                        oxido: str = "ligera") -> float:
    pars = ABS_CONST.get(material, ABS_CONST["acero"])
    nk = OPTICAL_NK.get(material)

    d_um = cabezal.parametros.get("diametro_spot_foco")
    theta_from_head = cabezal.parametros.get("angulo_incidente_deg")
    if theta_deg is None:
        theta_deg = float(theta_from_head) if theta_from_head is not None else 0.0

    try:
        if nk and d_um and d_um > 0:
            R = _fresnel_R_metal(nk['n'], nk['k'], theta_deg, pol=polarizacion)
            surf = (estado_superficie or cabezal.parametros.get("estado_superficie") or "laminada").lower()
            sigma_um = SURFACE_SIGMA_UM.get(surf, 0.30)
            R_corr = _roughness_correction(R, lambda_nm, theta_deg, sigma_um)
            ox = (oxido or "ligera").lower()
            red = OXIDE_REDUCTION.get(ox, 0.0)
            R_corr = max(0.0, R_corr * (1.0 - red))
            A = 1.0 - R_corr
        else:
            raise RuntimeError("Falta n,k o d_um para Fresnel")
    except Exception:
        if not d_um or d_um <= 0:
            return max(pars["A_min"], min(pars["A_max"], pars["A0"]))
        d_m = d_um * 1e-6
        area_m2 = pi * (d_m/2.0)**2
        I = max(1.0, P_W / area_m2)
        A = pars["A0"] + pars["k"] * log10(I / pars["Iref_W_m2"])

    return max(pars["A_min"], min(pars["A_max"], float(A)))

# Utilidades avanzadas
def caudal_masico_g_s(setup: CorteSetup, densidad_g_cm3: float) -> float:
    vdot_mm3_s = setup.kerf_mm * setup.espesor_mm * setup.velocidad_mm_s
    densidad_g_mm3 = densidad_g_cm3 / 1000.0
    return densidad_g_mm3 * vdot_mm3_s

def area_kerf_por_seg_m2_s(setup: CorteSetup) -> float:
    perimetro_mm = 2.0 * setup.espesor_mm + setup.kerf_mm
    A_mm2_s = perimetro_mm * setup.velocidad_mm_s
    return A_mm2_s * 1e-6

def potencia_absorbida_W(setup: CorteSetup) -> float:
    return setup.P_laser_W * max(0.0, min(1.0, setup.absorptividad))

def calor_oxidacion_W(setup: CorteSetup, mdot_g_s: float) -> float:
    gas = setup.gas
    if gas is None or gas.nombre.upper() != "O2":
        return 0.0
    mdot_kg_s = (mdot_g_s / 1000.0) * max(0.0, min(1.0, gas.frac_ox))
    return mdot_kg_s * abs(gas.delta_h_reac_J_per_kgFe)

def enfriamiento_chorro_W(setup: CorteSetup, A_m2_s: float) -> float:
    gas = setup.gas
    if gas is None:
        return 0.0
    T_melt_K = 1800.0
    deltaT = max(0.0, T_melt_K - gas.T_gas_K)
    return gas.h_jet_W_m2K * A_m2_s * deltaT

# --- corrección: factor de mojado del chorro -------------------------------
def factor_mojado_jet(nozzle_d_mm: float | None, standoff_mm: float | None,
                      presion_bar: float, base: float = 0.30) -> float:
    """
    Estima la fracción de perímetro realmente 'mojado' por el chorro en el kerf.
    - base: valor típico 0.30 (30%) si no hay datos geométricos.
    - Aumenta con boquillas grandes y standoff pequeño. Suavemente con presión.
    Devuelve un valor clampado en [0.10, 0.70].
    """
    phi = float(base)
    if nozzle_d_mm and standoff_mm and nozzle_d_mm > 0:
        cobertura = nozzle_d_mm / (nozzle_d_mm + 2.0*max(0.1, standoff_mm))
        pres_gain = (max(0.3, min(2.0, presion_bar)) / 1.0) ** 0.2
        phi = base * (0.8 + 0.8 * cobertura) * pres_gain
    return max(0.10, min(0.70, phi))

def area_convectiva_efectiva_m2_s(setup: CorteSetup, presion_bar: float,
                                  nozzle_d_mm: float | None, standoff_mm: float | None) -> tuple[float,float]:
    """
    Devuelve (A_eff, phi) = área convectiva efectiva [m²/s], fracción mojada.
    """
    A_geo = area_kerf_por_seg_m2_s(setup)
    phi = factor_mojado_jet(nozzle_d_mm, standoff_mm, presion_bar, base=0.30)
    return A_geo * phi, phi






def demanda_frente_W(mdot_g_s: float, cp_J_gK: float, dT_K: float, Lf_J_g: float, f_vap: float, Lv_J_g=6000.0) -> float:
    energia_J_g = cp_J_gK * dT_K + Lf_J_g + f_vap * Lv_J_g
    return mdot_g_s * energia_J_g

def h_jet_escalado_por_presion(h_base_W_m2K: float,
                               presion_bar: float,
                               P_ref_bar: float = 1.0,
                               alpha: float = 0.4,
                               clamp_min: float = 0.2,
                               clamp_max: float = 5.0) -> float:
    """
    Escala h_jet con la presión: h = h_base * (P/P_ref)^alpha
    - presion_bar: presión de asistencia (bar, gauge)
    - alpha: exponente (0.3–0.5 típico para chorros; 0.4 por defecto)
    - clamp_min/max: límites de seguridad para evitar valores extremos
    """
    P = max(0.05, float(presion_bar))  # evita 0
    escala = (P / max(0.05, float(P_ref_bar))) ** float(alpha)
    escala = max(float(clamp_min), min(float(clamp_max), escala))
    return float(h_base_W_m2K) * escala

def balance_energetico_avanzado(setup: CorteSetup) -> dict:
    mat = MATERIALES[setup.material]
    cp = mat["calor_especifico_J_gK"]
    rho = mat["densidad_g_cm3"]
    dT = mat["deltaT_K"]
    Lf = mat["calor_latente_J_g"]

    mdot_g_s = caudal_masico_g_s(setup, rho)
    A_m2_s = area_kerf_por_seg_m2_s(setup)

    P_abs = potencia_absorbida_W(setup)
    Q_ox  = calor_oxidacion_W(setup, mdot_g_s)
    Q_jet = enfriamiento_chorro_W(setup, A_m2_s)
    Q_otros = max(0.0, setup.k_otros_W)

    demanda = demanda_frente_W(mdot_g_s, cp, dT, Lf, setup.f_vap)

    residuo = P_abs + Q_ox - Q_jet - Q_otros - demanda

    return {
        "mdot_g_s": mdot_g_s,
        "A_m2_s": A_m2_s,
        "P_abs_W": P_abs,
        "Q_ox_W": Q_ox,
        "Q_jet_W": Q_jet,
        "Q_otros_W": Q_otros,
        "demanda_W": demanda,
        "residuo_W": residuo,
    }

def velocidad_max_para_balance_avanzado(setup: CorteSetup, residuo_obj_W: float = 0.0, iters: int = 30, v_min_mm_s: float = 0.1, v_max_mm_s: float = 0.0) -> float:
    if v_max_mm_s <= 0.0:
        v_max_mm_s = max(500.0, setup.velocidad_mm_s * 3)
    setup_local = CorteSetup(**{k: v for k, v in setup.__dict__.items()})
    lo, hi = v_min_mm_s, v_max_mm_s
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        setup_local.velocidad_mm_s = mid
        residuo = balance_energetico_avanzado(setup_local)["residuo_W"]
        if residuo >= residuo_obj_W:
            lo = mid
        else:
            hi = mid
    return lo

#####################################################################################
# --- utilidades de E/S -------------------------------------------------------------

def velocidad_max_residuo_cero(setup: CorteSetup, direction: str = "up",
                               residuo_obj_W: float = 0.0, iters: int = 40,
                               growth: float = 1.6, vmin_mm_s: float = 0.05,
                               vmax_cap_mm_s: float = 3000.0) -> float:
    """
    Busca la velocidad límite tal que el residuo energético ≈ 0.
    - direction="up": aumenta velocidad desde el valor actual (caso de potencia sobrante).
    - direction="down": reduce velocidad (caso de déficit).
    Retorna la mejor cota alcanzada (si no se cruza el signo, devuelve el extremo alcan-zado).
    """
    setup_local = CorteSetup(**{k: v for k, v in setup.__dict__.items()})

    def residuo(v_mm_s: float) -> float:
        setup_local.velocidad_mm_s = max(vmin_mm_s, float(v_mm_s))
        return balance_energetico_avanzado(setup_local)["residuo_W"]

    v0 = max(vmin_mm_s, setup.velocidad_mm_s)
    r0 = residuo(v0)

    if direction.lower().startswith("up"):
        lo, r_lo = v0, r0
        hi, r_hi = v0, r0
        # Expandir hacia arriba hasta cruzar a residuo < 0 o alcanzar el tope
        while hi < vmax_cap_mm_s and r_hi >= residuo_obj_W:
            hi = min(vmax_cap_mm_s, hi * growth)
            r_hi = residuo(hi)
        # Si no se cruzó, devolver el tope alcanzado
        if r_hi >= residuo_obj_W:
            return hi
        # Bisección entre lo (≥0) y hi (<0)
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            r_mid = residuo(mid)
            if r_mid >= residuo_obj_W:
                lo = mid
            else:
                hi = mid
        return lo

    else:  # direction == "down"
        hi, r_hi = v0, r0
        lo, r_lo = v0 / growth, residuo(v0 / growth)
        # Reducir hasta cruzar a residuo ≥ 0 o llegar a vmin
        while lo > vmin_mm_s and r_lo < residuo_obj_W:
            lo = max(vmin_mm_s, lo / growth)
            r_lo = residuo(lo)
        # Si no se cruzó, devolver la cota alcanzada
        if r_lo < residuo_obj_W:
            return lo
        # Bisección entre lo (≥0) y hi (<0)
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            r_mid = residuo(mid)
            if r_mid >= residuo_obj_W:
                lo = mid
            else:
                hi = mid
        return lo

def cargar_parametros_corte_json(ruta_json: str = "parametros_corte.json") -> dict:
    with open(ruta_json, "r", encoding="utf-8") as f:
        return json.load(f)


#####################################################################################
#
# -------------------------------- MAIN ---------------------------------------------
#
#####################################################################################

if __name__ == "__main__":
    # 1) Óptica del cabezal
    cabezal = Cabezal()
    cabezal.cargar_optica_desde_json("cabezal_optica.json")

    # 1b) Carga opcional de constantes ópticas (n,k)
    if cargar_optical_nk_json():
        print("Constantes ópticas (n,k) cargadas desde optical_constants.json")

    # 2) Parámetros de corte (desde JSON)
    cfg = cargar_parametros_corte_json("parametros_corte.json")
    potencia_laser = float(cfg.get("potencia_laser_w", 8000.0))
    gas_nombre = str(cfg.get("gas", "O2")).upper()
    presion_gas = float(cfg.get("presion_gas_bar", 1.0))
    espesor = float(cfg.get("espesor_mm", 10.0))
    v_mm_min = float(cfg.get("velocidad_mm_mim", cfg.get("velocidad_mm_min", 5000.0)))
    velocidad = v_mm_min / 60.0  # mm/s
    posicion_focal_mm = float(cfg.get("posicion_focal_mm", 0.0))
    nombre_material = str(cfg.get("material", "acero")).lower()

    # 3) Propiedades del material
    mat = props_material(nombre_material)

    # 4) Kerf por desenfoque (sin factor fijo)
    kerf_um = kerf_um_por_defocus(cabezal, posicion_focal_mm)
    kerf_mm = kerf_um / 1000.0

    print("=== RESUMEN ===")
    print(f"Material: {nombre_material} | Espesor: {espesor:.2f} mm")
    print(f"Potencia láser: {potencia_laser:.0f} W | Velocidad: {velocidad:.2f} mm/s ({v_mm_min:.0f} mm/min)")
    print(f"Foco en superficie? Δf = {posicion_focal_mm:+.3f} mm ( + arriba / - dentro )")
    print(f"Spot en foco (µm): {cabezal.parametros.get('diametro_spot_foco', 'nd')} | Presión de {gas_nombre}: {presion_gas:.1f} bar ")
    print(f"Kerf (µm) por desenfoque: {kerf_um:.1f}  => {kerf_mm:.3f} mm\n")

    # ---------------- MODO SIMPLE ----------------
    A_simple, resultados = calculo_balance_termico(
        potencia_laser_w=potencia_laser,
        espesor_mm=espesor,
        diametro_spot_um=kerf_um,
        velocidad_mm_s=velocidad,
        calor_especifico_J_gK=mat["calor_especifico_J_gK"],
        densidad_g_cm3=mat["densidad_g_cm3"],
        deltaT_K=mat["deltaT_K"],
        calor_latente_J_g=mat["calor_latente_J_g"],
        factor_ancho_kerf=1.0,
    )

    print("[MODO SIMPLE] Absorción necesaria A:", f"{A_simple:.3f}  (idealmente ≤ 1.0)")
    print("Detalles intermedios:")
    for k, v in resultados.items():
        print(f"  {k}: {v:.4f}")

    if A_simple > 1.0:
        print("Energéticamente no cierra con estos parámetros (modo simple).")
        A_obj = 0.95  # absorción típica realista
        v_max = velocidad_max_mm_s(
            potencia_laser, A_obj, espesor, kerf_mm,
            mat["calor_especifico_J_gK"], mat["densidad_g_cm3"], mat["deltaT_K"], mat["calor_latente_J_g"]
        )
        print(f"→ Reduce velocidad a ≤ {v_max*60:.0f} mm/min o aumenta potencia.")
    else:
        print("A ≤ 1.0: hay margen térmico en modo simple.\n")

    # ---------------- MODO AVANZADO (con gas de asistencia) ----------------
    print("[MODO AVANZADO] Balance con gas de asistencia:")
    # a) Absorptividad
    absorptividad_override = cfg.get("absorptividad_fija")
    if absorptividad_override is not None:
        absorptividad_estimada = max(0.0, min(1.0, float(absorptividad_override)))
    else:
        absorptividad_estimada = estimar_absorptividad_desde_cabezal(
            cabezal, potencia_laser, material=nombre_material,
            theta_deg=cfg.get("theta_incidente_deg"),
            polarizacion=str(cfg.get("polarizacion", "unpol")).lower(),
            estado_superficie=cfg.get("estado_superficie"),
            oxido=str(cfg.get("oxido", "ligera")).lower()
        )
    print(f"Absorptividad (estimada o fija): {absorptividad_estimada:.3f}")

   # b) Gas (siempre desde tabla y luego overrides opcionales)
    gas = gas_calibrado(nombre_material, espesor, gas_nombre, T_gas_K=float(cfg.get("T_gas_K", 300.0)))

    # Pisados opcionales (solo si están en el JSON; respetan mayúsculas/minúsculas de la clave)
    if "h_jet_W_m2K" in cfg:
        gas.h_jet_W_m2K = float(cfg["h_jet_W_m2K"])
    if "frac_ox" in cfg:
        gas.frac_ox = float(cfg["frac_ox"])
    if "delta_h_reac_J_per_kgFe" in cfg:
        gas.delta_h_reac_J_per_kgFe = float(cfg["delta_h_reac_J_per_kgFe"])
    if "T_gas_K" in cfg:  # redundante, ya aplicado en gas_calibrado; lo dejamos por claridad
        gas.T_gas_K = float(cfg["T_gas_K"])

    # Conectar el HELPER de presión (si procede)
    usar_presion_en_h = bool(cfg.get("usar_presion_en_h_jet", True))    # Poner a False y usara el k de flujo de gas y no la presión <<<<<<<<<<<<<<<<<<<<
    alpha_presion = float(cfg.get("alpha_presion_h_jet", 0.5))          
    P_ref_bar = float(cfg.get("P_ref_h_jet_bar", 1.0))

    if usar_presion_en_h:
        gas.h_jet_W_m2K = h_jet_escalado_por_presion(
            h_base_W_m2K=gas.h_jet_W_m2K,
            presion_bar=presion_gas,
            P_ref_bar=P_ref_bar,
            alpha=alpha_presion,
            clamp_min=0.2,
            clamp_max=5.0
        )
        print(f"\n[PRESIÓN] h_jet escalado: {gas.h_jet_W_m2K:.0f} W/m^2K  (P={presion_gas:.1f} bar, α={alpha_presion:.2f}, Pref={P_ref_bar:.1f} bar)")


    # c) Otros parámetros avanzados
    f_vap = float(cfg.get("f_vap", 0.05))
    k_otros = float(cfg.get("k_otros_W", 500.0))

    setup = CorteSetup(
        material=nombre_material,
        espesor_mm=espesor,
        kerf_mm=kerf_mm,
        velocidad_mm_s=velocidad,
        P_laser_W=potencia_laser,
        absorptividad=absorptividad_estimada,
        f_vap=f_vap,
        k_otros_W=k_otros,
        gas=gas
    )

# cálculo de área convectiva efectiva
    nozzle_d_mm = float(cfg.get("boquilla_d_mm", 1.2))
    standoff_mm = float(cfg.get("standoff_mm", 1.0))
    A_geo = area_kerf_por_seg_m2_s(setup)
    A_eff, phi = area_convectiva_efectiva_m2_s(setup, presion_gas, nozzle_d_mm, standoff_mm)

    res_adv = balance_energetico_avanzado(setup)
    # sustituimos el Q_jet con área efectiva
    res_adv["Q_jet_W"] = enfriamiento_chorro_W(setup, A_eff)
    res_adv["A_m2_s"] = A_eff
    res_adv["residuo_W"] = (res_adv["P_abs_W"] + res_adv["Q_ox_W"]
                            - res_adv["Q_jet_W"] - res_adv["Q_otros_W"]
                            - res_adv["demanda_W"])

    for k, v in res_adv.items():
        prec = 6 if k == "A_m2_s" else 2
        print(f"  {k}: {v:.{prec}f}")
    print(f"[φ_jet aplicado] fracción mojada del perímetro: {phi:.2f}")

    if res_adv["residuo_W"] < 0:
        v_max_adv = velocidad_max_para_balance_avanzado(setup)
        print(f"→ Residuo < 0. Velocidad máx (residuo≈0): {v_max_adv*60:.0f} mm/min.")
    else:
        v_max_up = velocidad_max_residuo_cero(setup, direction="up")
        print(f"→ Residuo ≥ 0. Puedes aumentar velocidad hasta ≈ {v_max_up*60:.0f} mm/min.")
