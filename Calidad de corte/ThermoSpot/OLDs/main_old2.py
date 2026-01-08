# Este script calcula el corte láser láser
# Autor: F. Martínez
# Fecha: 2024-06-20
# Versión: 1.2  (absorptividad desde Cabezal con Fresnel + loader n,k; fixes de prints)

#####################################################################################
from spot_size import Cabezal
import json
from dataclasses import dataclass
import cmath
from math import sin, cos, radians, log10, exp, pi
import os

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
# (modelo original; se mantiene tal cual para compatibilidad)
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

# --- I/O de parámetros de corte desde JSON ---
def cargar_parametros_corte_json(ruta_json="parametros_corte.json"):
    """
    Lee los parámetros de corte desde un archivo JSON y los devuelve como diccionario.
    """
    with open(ruta_json, 'r', encoding='utf-8') as f:
        parametros = json.load(f)
    return parametros

#####################################################################################
# ------------------------ PIPELINE AVANZADO (O2/N2) -------------------------------
# Objetivo: añadir términos de oxidación (solo O2) y enfriamiento del chorro
#           sin tocar Excel ni romper el API existente. Se usan las mismas
#           unidades que el modelo simple (mm, g, s, W) y se documenta cada paso.

@dataclass
class GasAssist:
    nombre: str                  # "O2" o "N2"
    T_gas_K: float               # ~300 K
    h_jet_W_m2K: float           # coef. convectivo del chorro en el kerf
    delta_h_reac_J_per_kgFe: float = 0.0  # <0 químico; aquí se usará la magnitud aportada
    frac_ox: float = 0.0         # fracción de la masa retirada que se oxida (0..1)

@dataclass
class CorteSetup:
    material: str                # clave en MATERIALES: "acero", "inox", etc.
    espesor_mm: float            # [mm]
    kerf_mm: float               # [mm]
    velocidad_mm_s: float        # [mm/s]
    P_laser_W: float             # [W]
    absorptividad: float         # 0..1 (puede venir del cabezal/superficie)
    f_vap: float = 0.0           # fracción de masa que vaporiza (0..1)
    k_otros_W: float = 0.0       # pérdidas lumped (conducción/radiación) opcional
    gas: GasAssist | None = None

# --- util avanzado: caudal másico (g/s) ---
def caudal_masico_g_s(setup: CorteSetup, densidad_g_cm3: float) -> float:
    # Volumen por segundo en mm³/s: w * t * v
    vdot_mm3_s = setup.kerf_mm * setup.espesor_mm * setup.velocidad_mm_s
    densidad_g_mm3 = densidad_g_cm3 / 1000.0  # g/mm³
    return densidad_g_mm3 * vdot_mm3_s        # g/s

# --- util avanzado: área "mojada" por segundo (m²/s) para convección del chorro ---
def area_kerf_por_seg_m2_s(setup: CorteSetup) -> float:
    # Aproximación: dos paredes (2*espesor) + fondo (kerf) ⇒ perímetro [mm]
    perimetro_mm = 2.0 * setup.espesor_mm + setup.kerf_mm
    # Área lateral barrida por segundo ≈ perímetro * velocidad  [mm²/s]
    A_mm2_s = perimetro_mm * setup.velocidad_mm_s
    # Conversión: mm² → m²  (1 mm = 1e-3 m ⇒ (1e-3)² = 1e-6)
    return A_mm2_s * 1e-6  # m²/s

# --- términos energéticos avanzados ---
def potencia_absorbida_W(setup: CorteSetup) -> float:
    return setup.P_laser_W * max(0.0, min(1.0, setup.absorptividad))

def calor_oxidacion_W(setup: CorteSetup, mdot_g_s: float) -> float:
    gas = setup.gas
    if gas is None or gas.nombre.upper() != "O2":
        return 0.0
    # Masa oxidada (kg/s): fracción de la masa retirada * mdot_total
    mdot_kg_s = (mdot_g_s / 1000.0) * max(0.0, min(1.0, gas.frac_ox))
    # delta_h_reac < 0 en convención química; aquí usamos su magnitud como aporte positivo.
    return mdot_kg_s * abs(gas.delta_h_reac_J_per_kgFe)

def enfriamiento_chorro_W(setup: CorteSetup, A_m2_s: float) -> float:
    gas = setup.gas
    if gas is None:
        return 0.0
    # Q = h * A * (T_melt - T_gas). Tomamos T_melt ~ 1800 K para acero.
    T_melt_K = 1800.0
    deltaT = max(0.0, T_melt_K - gas.T_gas_K)
    return gas.h_jet_W_m2K * A_m2_s * deltaT

def demanda_frente_W(mdot_g_s: float, cp_J_gK: float, dT_K: float, Lf_J_g: float, f_vap: float, Lv_J_g=6000.0) -> float:
    # Nota: mantenemos magnitudes por g para coherencia con el modelo simple.
    energia_J_g = cp_J_gK * dT_K + Lf_J_g + f_vap * Lv_J_g
    return mdot_g_s * energia_J_g

# --- MINI-CALIBRADOR (tablas internas por espesor y gas) ---
# Objetivo: proporcionar valores iniciales de h_jet, frac_ox y delta_h_reac por espesor
# sin tocar el Excel. Se usa interpolación por vecindad más cercana.
CALIB_GAS = {
    "acero": {
        3:  {"O2": dict(h_jet=1.8e4, frac_ox=0.35, dh=3.2e6), "N2": dict(h_jet=1.5e4, frac_ox=0.0, dh=0.0)},
        6:  {"O2": dict(h_jet=2.0e4, frac_ox=0.40, dh=3.5e6), "N2": dict(h_jet=1.6e4, frac_ox=0.0, dh=0.0)},
        10: {"O2": dict(h_jet=2.2e4, frac_ox=0.45, dh=3.7e6), "N2": dict(h_jet=1.8e4, frac_ox=0.0, dh=0.0)},
    }
}

def _nearest_key(keys, value):
    return min(keys, key=lambda k: abs(k - value))

def gas_calibrado(material: str, espesor_mm: float, nombre_gas: str, T_gas_K: float = 300.0) -> GasAssist:
    mat_tbl = CALIB_GAS.get(material, {})
    if not mat_tbl:
        # fallback genérico
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

# --- ABSORPTIVIDAD DESDE CABEZAL ---
# Estima absorptividad efectiva combinando Fresnel para metales (n,k complejos),
# ángulo/polarización y correcciones de rugosidad/óxido. Mantiene clamp con ABS_CONST.
# Si fallan datos ópticos, hace fallback al modelo log(I) anterior.

# Límites/prior de absorptividad por material (para clamp y fallback)
ABS_CONST = {
    "acero":    dict(A0=0.30, k=0.03, Iref_W_m2=1.0e8, A_min=0.10, A_max=0.60),
    "inox":     dict(A0=0.32, k=0.03, Iref_W_m2=1.0e8, A_min=0.12, A_max=0.62),
    "aluminio": dict(A0=0.12, k=0.02, Iref_W_m2=2.0e8, A_min=0.05, A_max=0.40),
}

# Constantes ópticas aproximadas a 1.06–1.07 µm (valores típicos; ajustar si mides)
OPTICAL_NK = {
    "acero":    dict(lambda_nm=1070.0, n=2.9,  k=3.3),
    "inox":     dict(lambda_nm=1070.0, n=2.2,  k=3.4),
    "aluminio": dict(lambda_nm=1070.0, n=1.5,  k=11.0),
}

def cargar_optical_nk_json(ruta_json: str = "optical_constants.json"):
    """Carga opcional de n,k desde JSON externo (no toca Excel). Devuelve True si cargó."""
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

SURFACE_SIGMA_UM = {  # rugosidad RMS (µm) típica para corrección de Beckmann-like
    "pulida":   0.05,
    "lijada":   0.15,
    "laminada": 0.30,
    "oxidada":  0.50,
}

OXIDE_REDUCTION = {   # reducción relativa de R por óxido/escala (heurístico)
    "ninguna": 0.00,
    "ligera":  0.08,
    "media":   0.15,
    "fuerte":  0.25,
}

def _fresnel_R_metal(n: float, k: float, theta_deg: float, pol: str = "unpol") -> float:
    """Reflectancia Fresnel para metal con índice complejo n-ik.
    pol: 's', 'p' o 'unpol' (media). θ en grados en el medio incidente (aire).
    """
    n1 = 1.0
    n2 = complex(n, -k)  # convención n - i k
    theta = radians(theta_deg)
    sin_t = n1 * sin(theta) / n2
    cos_t = cmath.sqrt(1 - sin_t**2)
    cos_i = cos(theta)

    # Coeficientes de reflexión compleos
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
    # Atenuación especular ~ exp(-(4πσ cosθ / λ)^2)
    # Aumenta absorción efectiva al reducir R especular.
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
    pars = ABS_CONST.get(material, ABS_CONST["acero"])  # para clamp y fallback
    nk = OPTICAL_NK.get(material)

    # Geometría/intensidad
    d_um = cabezal.parametros.get("diametro_spot_foco")
    theta_from_head = cabezal.parametros.get("angulo_incidente_deg")
    if theta_deg is None:
        theta_deg = float(theta_from_head) if theta_from_head is not None else 0.0

    # Si tenemos n,k, usamos Fresnel; si no, caemos a log(I)
    try:
        if nk and d_um and d_um > 0:
            R = _fresnel_R_metal(nk['n'], nk['k'], theta_deg, pol=polarizacion)
            # Corrección por rugosidad/estado superficial
            surf = (estado_superficie or cabezal.parametros.get("estado_superficie") or "laminada").lower()
            sigma_um = SURFACE_SIGMA_UM.get(surf, 0.30)
            R_corr = _roughness_correction(R, lambda_nm, theta_deg, sigma_um)
            # Corrección por óxido superficial
            ox = (oxido or "ligera").lower()
            red = OXIDE_REDUCTION.get(ox, 0.0)
            R_corr = max(0.0, R_corr * (1.0 - red))
            A = 1.0 - R_corr  # transmisión ≈ 0 en metales a 1 µm
        else:
            raise RuntimeError("Falta n,k o d_um para Fresnel")
    except Exception:
        # Fallback: modelo por intensidad (log) con clamp
        if not d_um or d_um <= 0:
            return max(pars["A_min"], min(pars["A_max"], pars["A0"]))
        d_m = d_um * 1e-6
        area_m2 = pi * (d_m/2.0)**2
        I = max(1.0, P_W / area_m2)
        A = pars["A0"] + pars["k"] * log10(I / pars["Iref_W_m2"])

    return max(pars["A_min"], min(pars["A_max"], float(A)))

# --- balance avanzado: devuelve desglose y residuo ---
def balance_energetico_avanzado(setup: CorteSetup) -> dict:
    mat = MATERIALES[setup.material]
    cp = mat["calor_especifico_J_gK"]      # J/g/K
    rho = mat["densidad_g_cm3"]            # g/cm³
    dT = mat["deltaT_K"]                    # K
    Lf = mat["calor_latente_J_g"]          # J/g

    mdot_g_s = caudal_masico_g_s(setup, rho)
    A_m2_s = area_kerf_por_seg_m2_s(setup)

    P_abs = potencia_absorbida_W(setup)
    Q_ox  = calor_oxidacion_W(setup, mdot_g_s)
    Q_jet = enfriamiento_chorro_W(setup, A_m2_s)
    Q_otros = max(0.0, setup.k_otros_W)

    demanda = demanda_frente_W(mdot_g_s, cp, dT, Lf, setup.f_vap)

    # Convención: residuo > 0 ⇒ margen térmico; residuo < 0 ⇒ falta energía.
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

# --- velocidad máxima que satisface residuo≈0 (búsqueda binaria) ---
def velocidad_max_para_balance_avanzado(setup: CorteSetup, residuo_obj_W: float = 0.0, iters: int = 30, v_min_mm_s: float = 0.1, v_max_mm_s: float = 0.0) -> float:
    if v_max_mm_s <= 0.0:
        v_max_mm_s = max(500.0, setup.velocidad_mm_s * 3)  # cota superior amplia [mm/s]
    # Copia ligera del setup para no mutar el original
    setup_local = CorteSetup(**{**setup.__dict__})
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
#####################################################################################
# ------------------------ MAIN ------------------------

if __name__ == "__main__":
    # 1) Carga de óptica del cabezal
    cabezal = Cabezal()
    cabezal.cargar_optica_desde_json("cabezal_optica.json")

    # 1b) Carga opcional de constantes ópticas (n,k)
    if cargar_optical_nk_json():
        print("Constantes ópticas (n,k) cargadas desde optical_constants.json")

    # 2) Material de trabajo
    mat = props_material("acero")  # "aluminio" o "inox" según toque

    # 3) Parámetros de ejemplo (ajusta a tu caso)
    potencia_laser = 8000.0        # W
    espesor = 10.0                 # mm
    velocidad = 600.0              # mm/s

    # 4) Kerf = spot_en_foco * factor
    factor_kerf = 1.2
    kerf_um = obtener_kerf_um_desde_cabezal(cabezal, factor_kerf=factor_kerf)
    kerf_mm = kerf_um / 1000.0

    print(f"Spot en foco (µm): {cabezal.parametros['diametro_spot_foco']}")
    print(f"Kerf estimado (µm) = spot * {factor_kerf}: {kerf_um:.1f}")

    # ---------------- MODO SIMPLE (compatibilidad) ----------------
    A_simple, resultados = calculo_balance_termico(
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

    print("\n[MODO SIMPLE] Absorción necesaria A:", f"{A_simple:.3f} (idealmente ≤ 1.0)")
    print("Detalles intermedios (simple):")
    for k, v in resultados.items():
        print(f"  {k}: {v:.2f}")

    if A_simple > 1.0:
        print("\n  Energéticamente no cierra con estos parámetros.")
        A_obj = 0.95  # absorción estimada realista
        v_max = velocidad_max_mm_s(
            potencia_laser, A_obj, espesor, kerf_mm,
            mat["calor_especifico_J_gK"], mat["densidad_g_cm3"], mat["deltaT_K"], mat["calor_latente_J_g"]
        )
        #print(f"   Velocidad máx con A={A_obj*100:.0f}%: {v_max:.1f} mm/s")
        print(f"    --> Aumenta potencia o reduce la velocidad a {v_max*60:.0f} mm/min o menos.")

    # ---------------- MODO AVANZADO (con gas de asistencia) ----------------
    print("\n[MODO AVANZADO] Balance con gas de asistencia:")
    
    # 4b) Absorptividad efectiva desde cabezal
    absorptividad_estimada = estimar_absorptividad_desde_cabezal(cabezal, potencia_laser, material="acero")
    print(f"Absorptividad estimada (desde cabezal): {absorptividad_estimada:.3f}")

    # 4c) Gas calibrado por espesor
    gas_O2 = gas_calibrado("acero", espesor, "O2")
    gas_N2 = gas_calibrado("acero", espesor, "N2")

    setup = CorteSetup(
        material="acero",
        espesor_mm=espesor,
        kerf_mm=kerf_mm,
        velocidad_mm_s=velocidad,
        P_laser_W=potencia_laser,
        absorptividad=absorptividad_estimada,
        f_vap=0.05,
        k_otros_W=500.0,
        gas=gas_O2  # cambia a gas_N2 para evaluar nitrógeno
    )

    res_adv = balance_energetico_avanzado(setup)
    
    for k, v in res_adv.items():
        print(f"  {k}: {v:.2f}")

    if res_adv["residuo_W"] < 0:
        v_max_adv = velocidad_max_para_balance_avanzado(setup)
        print(f"  → Residuo < 0. Velocidad máx (residuo≈0): {v_max_adv*60:.0f} mm/min.")
    else:
        print("  → Residuo ≥ 0. Existe margen térmico; puedes aumentar velocidad hasta residuo≈0.")

# Fin del script
