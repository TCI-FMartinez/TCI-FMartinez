# -*- coding: utf-8 -*-
# =============================================================================
# Simulador de corte láser fibra (balance energético + Vmax por bisección)
# Autor: F. Martínez (ajustes y robustecimiento por ChatGPT)
# Fecha: 2025-10-02
# Versión: 2.0
#
# Este script:
#   1) Carga la óptica del cabezal desde 'cabezal_optica.json' usando spot_size.Cabezal.
#   2) Carga parámetros de proceso desde 'parametros_corte.json'.
#   3) Calcula el KERF en función del desenfoque Δf (no usa factor fijo).
#   4) Ejecuta un balance energético "avanzado" que incluye:
#        - Potencia absorbida láser
#        - Demanda térmica de fusión + calentamiento (y vaporización parcial)
#        - Término exotérmico por oxidación en O2 (si aplica)
#        - Pérdidas convectivas por chorro (h_jet escalado con presión)
#        - Otros términos (constante k_otros)
#   5) Resuelve siempre Vmax (residuo≈0) por bisección, independiente de la V que metas.
#
# Requisitos de archivos (proporcionados por el usuario/proyecto):
#   - parametros_corte.json : condiciones de proceso (potencia, espesor, gas, etc.)  [USO]  :contentReference[oaicite:3]{index=3}
#   - cabezal_optica.json  : datos ópticos del cabezal (BPP, λ, f_col, f_focus, ...) [USO]  :contentReference[oaicite:4]{index=4}
#   - spot_size.py         : clase Cabezal con los cálculos ópticos                   [USO]  :contentReference[oaicite:5]{index=5}
# =============================================================================

import json
from dataclasses import dataclass, replace
from typing import Dict, Any, Optional

# Carga de la clase Cabezal (óptica) desde el módulo del proyecto
from spot_size import Cabezal  # :contentReference[oaicite:6]{index=6}


# =============================================================================
# 1) CONSTANTES Y PROPIEDADES DE MATERIALES
# =============================================================================

# Nota: valores típicos (puedes sustituir por tu tabla validada de fábrica)
MATERIALES = {
    # cp [J/gK], densidad [g/cm3], deltaT [K], L_fusión [J/g]
    "acero":    dict(cp=0.50, rho_g_cm3=7.85, dT=1500.0, L=270.0),
    "inox":     dict(cp=0.50, rho_g_cm3=7.90, dT=1500.0, L=260.0),
    "aluminio": dict(cp=0.90, rho_g_cm3=2.70, dT=650.0,  L=400.0),
}

# Parámetros globales/heurísticos para balance
DEFAULTS = {
    "deltaT_conv_K": 1200.0,       # salto térmico típico para convección del chorro
    "alpha_presion": 0.50,         # exponente de escalado de h_jet con presión (sub-sónico)
    "P_ref_bar": 1.0,              # presión de referencia para h_jet
    "H_ox_J_gFe": 1700.0,          # entalpía exotérmica efectiva por g de Fe oxidado (ajustable)
    "frac_vap": 0.05,              # fracción de masa que vaporizamos (si no se especifica)
    "k_otros_W": 500.0,            # pérdidas/márgenes varios (si no se especifica)
    "phi_jet_base": 0.30,          # fracción mojada del perímetro por el chorro (si no se especifica)
}


# =============================================================================
# 2) LECTURA DE JSON DE PROCESO
# =============================================================================

def cargar_parametros_corte_json(ruta: str) -> Dict[str, Any]:
    """
    Lee el archivo JSON de parámetros de proceso.
    Acepta claves en mm/min y tolera el typo 'velocidad_mm_mim' (histórico).
    Devuelve un dict sin modificar para trazabilidad.
    """
    with open(ruta, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data  # Se usa íntegro más adelante.  :contentReference[oaicite:7]{index=7}


# =============================================================================
# 3) UTILIDADES DE GAS / NORMALIZACIÓN
# =============================================================================

def normalizar_gas(nombre: Optional[str]) -> str:
    """
    Normaliza el nombre de gas a un conjunto fijo ('O2' o 'N2').
    Acepta variantes en español/inglés y mayúsculas/minúsculas.
    """
    n = (nombre or "").strip().lower()
    if n in ("o2", "oxigeno", "oxígeno"): return "O2"
    if n in ("n2", "nitrogeno", "nitrógeno"): return "N2"
    # Por defecto usamos O2 (común en acero medio-grueso)
    return "O2"


def hjet_escalado(h_ref_W_m2K: float, P_bar: float, alpha: float = DEFAULTS["alpha_presion"],
                  P_ref: float = DEFAULTS["P_ref_bar"]) -> float:
    """
    Escala el coeficiente convectivo del chorro (h_jet) con la presión de gas:
    h ~ h_ref * (P/P_ref)^alpha, con alpha≈0.5 para regímenes sub-sónicos habituales.
    """
    P_bar = max(0.05, float(P_bar))  # evita 0
    return float(h_ref_W_m2K) * (P_bar / P_ref) ** alpha


# =============================================================================
# 4) ÓPTICA → KERF POR DESENFOQUE Δf
# =============================================================================

def m2_from_bpp_lambda(BPP_mm_mrad: float, lambda_nm: float) -> float:
    """
    Estima M^2 a partir del BPP y la longitud de onda.
    Se usa la relación w0*θ = M^2 * λ / π  y BPP = w0*θ (en mm·mrad).
    Convertimos λ[nm] → mm y θ[mrad] → rad dentro de BPP.
    Resultado: M^2 ≈ (π * BPP_mm·mrad / 1000) / λ_mm
    """
    lambda_mm = float(lambda_nm) * 1e-6
    return (3.141592653589793 * (BPP_mm_mrad / 1000.0)) / lambda_mm


def kerf_um_por_desenfoque(cabezal: Cabezal, delta_f_mm: float) -> float:
    """
    Calcula el ancho de entalla (KERF) a partir del desenfoque Δf respecto de la superficie:
      - Usa el diámetro en foco d0 (del cabezal) como condición z=0.
      - Propaga el radio gaussiano con M^2:
            w(z) = w0 * sqrt(1 + (Δf / zR)^2),  zR = π w0^2 / (M^2 λ)
      - Devuelve 2*w(z) convertido a micras.

    Notas:
      - d0 del cabezal viene en µm (archivo óptico).  :contentReference[oaicite:8]{index=8}
      - BPP y λ se leen del cabezal (mm·mrad, nm).     :contentReference[oaicite:9]{index=9}
    """
    p = cabezal.parametros
    d0_um = float(p["diametro_spot_foco"])          # µm (en foco)
    w0_mm = (d0_um * 1e-3) / 2.0                    # radio en foco [mm]
    M2 = m2_from_bpp_lambda(float(p["BPP_fibra"]), float(p["longitud_onda"]))
    lambda_mm = float(p["longitud_onda"]) * 1e-6    # mm
    zR_mm = 3.141592653589793 * w0_mm**2 / (M2 * lambda_mm)
    w_mm = w0_mm * (1.0 + (delta_f_mm / zR_mm)**2) ** 0.5
    d_mm = 2.0 * w_mm
    return d_mm * 1000.0  # µm


# =============================================================================
# 5) DATACLASS DEL SETUP DE PROCESO
# =============================================================================

@dataclass
class GasAssist:
    """
    Gas de asistencia “efectivo” para el balance.
    - nombre: 'O2' o 'N2'
    - h_jet_W_m2K: coef. convectivo de referencia (se escalará con presión real)
    - H_ox_J_gFe: entalpía exotérmica efectiva por gramo de Fe oxidado (solo O2)
    - phi_jet: fracción mojada del perímetro por el chorro (adimensional 0-1)
    """
    nombre: str
    h_jet_W_m2K: float
    H_ox_J_gFe: float
    phi_jet: float


@dataclass
class CorteSetup:
    """
    Paquete con todas las variables de proceso relevantes al balance.
    """
    material: str
    espesor_mm: float
    kerf_mm: float
    velocidad_mm_s: float
    P_laser_W: float
    absorptividad: float
    frac_vap: float
    k_otros_W: float
    gas: GasAssist
    deltaT_conv_K: float


# =============================================================================
# 6) BALANCE ENERGÉTICO
# =============================================================================

def demanda_termica_W(material: str, espesor_mm: float, kerf_mm: float, velocidad_mm_s: float,
                      frac_vap: float) -> Dict[str, float]:
    """
    Calcula la potencia térmica requerida para generar el canal (entalla) a la velocidad dada:
      - Volumen retirado por segundo: vdot = kerf * espesor * velocidad  [mm^3/s]
      - Masa por segundo: mdot = vdot * ρ  [g/s], con ρ[g/mm^3] = ρ[g/cm^3] / 1000
      - Energía específica: e = cp*ΔT + L + frac_vap * L_vap   [J/g]
        (Aquí aproximamos L_vap ≈ 0; si lo conoces, añádelo.)
      - Demanda térmica: Q_req = mdot * e  [W]

    Devuelve dict con intermedios para trazabilidad.
    """
    props = MATERIALES[material]
    rho_g_mm3 = props["rho_g_cm3"] / 1000.0
    vdot_mm3_s = kerf_mm * espesor_mm * velocidad_mm_s
    mdot_g_s = vdot_mm3_s * rho_g_mm3
    energia_J_g = props["cp"] * props["dT"] + props["L"] + frac_vap * 0.0  # L_vap≈0 aquí
    Q_req_W = mdot_g_s * energia_J_g
    return dict(vdot_mm3_s=vdot_mm3_s, mdot_g_s=mdot_g_s, energia_J_g=energia_J_g, demanda_W=Q_req_W)


def potencia_absorbida_W(P_laser_W: float, absorptividad: float) -> float:
    """
    Potencia absorbida efectiva por el baño de fusión.
    """
    return float(P_laser_W) * float(max(0.0, min(absorptividad, 1.0)))


def potencia_exotermica_oxidacion_W(gas: GasAssist, mdot_g_s: float) -> float:
    """
    Potencia exotérmica por oxidación (solo si el gas es O2).
      Q_ox = mdot * H_ox
    En N2 la reacción exotérmica es despreciable: Q_ox = 0.
    """
    if gas.nombre != "O2":
        return 0.0
    return mdot_g_s * float(gas.H_ox_J_gFe)


def perimetro_entalla_mm(kerf_mm: float, espesor_mm: float) -> float:
    """
    Perímetro del canal de corte como rectángulo aproximado:
      P ≈ 2*(kerf + espesor)
    """
    return 2.0 * (kerf_mm + espesor_mm)


def perdidas_convectivas_jet_W(gas: GasAssist, P_bar: float, perimetro_mm: float,
                               velocidad_mm_s: float, deltaT_K: float, h_ref_W_m2K: float) -> float:
    """
    Pérdidas convectivas modeladas como:
      Q_jet = h(P) * A_mojada * ΔT
    donde A_mojada por segundo ≈ (perímetro * velocidad) [mm^2/s] * φ_jet.
    Convertimos mm^2 → m^2.
    """
    hP = hjet_escalado(h_ref_W_m2K, P_bar)
    A_mm2_s = perimetro_mm * velocidad_mm_s * float(max(0.0, min(gas.phi_jet, 1.0)))
    A_m2_s = A_mm2_s * 1e-6
    Q_jet_W = hP * A_m2_s * deltaT_K
    return Q_jet_W


def balance_energetico_avanzado(setup: CorteSetup, P_bar: float, h_ref_W_m2K: float) -> Dict[str, float]:
    """
    Balance completo:
      Residuo = P_abs + Q_ox - (Q_req + Q_jet + k_otros)
      Si Residuo ≥ 0 → margen térmico positivo (posible aumentar velocidad).
    Devuelve dict con todos los términos y el residuo.
    """
    # Demanda térmica principal
    d = demanda_termica_W(setup.material, setup.espesor_mm, setup.kerf_mm,
                          setup.velocidad_mm_s, setup.frac_vap)
    P_abs_W = potencia_absorbida_W(setup.P_laser_W, setup.absorptividad)
    Q_ox_W = potencia_exotermica_oxidacion_W(setup.gas, d["mdot_g_s"])
    P_perim_mm = perimetro_entalla_mm(setup.kerf_mm, setup.espesor_mm)
    Q_jet_W = perdidas_convectivas_jet_W(setup.gas, P_bar, P_perim_mm,
                                         setup.velocidad_mm_s, setup.deltaT_conv_K, h_ref_W_m2K)
    Q_otros_W = setup.k_otros_W

    residuo_W = P_abs_W + Q_ox_W - (d["demanda_W"] + Q_jet_W + Q_otros_W)

    # Salida ordenada
    out = dict(
        mdot_g_s=d["mdot_g_s"],
        A_m2_s=(P_perim_mm * setup.velocidad_mm_s * setup.gas.phi_jet) * 1e-6,
        P_abs_W=P_abs_W,
        Q_ox_W=Q_ox_W,
        Q_jet_W=Q_jet_W,
        Q_otros_W=Q_otros_W,
        demanda_W=d["demanda_W"],
        residuo_W=residuo_W,
    )
    return out


# =============================================================================
# 7) SOLVER ROBUSTO PARA Vmax (bisección con acotado automático)
# =============================================================================

def residuo_a_velocidad(setup: CorteSetup, v_mm_s: float, P_bar: float, h_ref_W_m2K: float) -> float:
    """
    Helper: evalúa el residuo del balance para una velocidad propuesta.
    No modifica el setup original; usa una copia con la nueva velocidad.
    """
    s = replace(setup, velocidad_mm_s=float(v_mm_s))
    return balance_energetico_avanzado(s, P_bar=P_bar, h_ref_W_m2K=h_ref_W_m2K)["residuo_W"]


def vmax_por_biseccion(setup: CorteSetup, P_bar: float, h_ref_W_m2K: float,
                       iters: int = 40, v_cap_mm_s: float = 20000.0) -> float:
    """
    Busca la velocidad máxima tal que residuo≈0 con método de bisección.
      - Asegura que el límite NO depende de la velocidad que metas en el JSON.
      - Amplía automáticamente el rango [v_lo, v_hi] hasta encontrar cambio de signo.
      - Si no cruza (siempre sobra potencia), devuelve el máximo probado.

    Devuelve v_max en mm/s (puedes convertir a mm/min multiplicando por 60).
    """
    # Punto inicial seguro
    v_lo = 0.05
    r_lo = residuo_a_velocidad(setup, v_lo, P_bar, h_ref_W_m2K)
    tries = 0
    # Si ya nos quedamos cortos (residuo<0), bajamos más v_lo
    while r_lo < 0.0 and tries < 12:
        v_lo *= 0.5
        r_lo = residuo_a_velocidad(setup, v_lo, P_bar, h_ref_W_m2K)
        tries += 1

    # Partimos v_hi cerca de la V actual, pero lo iremos ampliando si hace falta
    v_hi = max(1.0, setup.velocidad_mm_s)
    r_hi = residuo_a_velocidad(setup, v_hi, P_bar, h_ref_W_m2K)
    while r_hi >= 0.0 and v_hi < v_cap_mm_s:
        v_hi *= 1.5
        r_hi = residuo_a_velocidad(setup, v_hi, P_bar, h_ref_W_m2K)

    # Si nunca cruzó (r_hi>=0 hasta el tope), reporta el máximo probado
    if r_hi >= 0.0:
        return v_hi

    # Bisección clásica
    for _ in range(iters):
        v_mid = 0.5 * (v_lo + v_hi)
        r_mid = residuo_a_velocidad(setup, v_mid, P_bar, h_ref_W_m2K)
        if r_mid >= 0.0:
            v_lo = v_mid
        else:
            v_hi = v_mid

    return v_lo


# =============================================================================
# 8) PROGRAMA PRINCIPAL
# =============================================================================

def main():
    """
    Orquesta la simulación:
      - Carga óptica y proceso.
      - Calcula kerf por Δf (no por factor fijo).
      - Prepara el setup del balance (unidades coherentes).
      - Evalúa el balance en la velocidad pedida.
      - Calcula SIEMPRE la Vmax por bisección y la muestra.
    """
    # ---- ÓPTICA del cabezal -------------------------------------------------
    cabezal = Cabezal()                                               # :contentReference[oaicite:10]{index=10}
    cabezal.cargar_optica_desde_json("cabezal_optica.json")           # :contentReference[oaicite:11]{index=11}
    d0_um = float(cabezal.parametros["diametro_spot_foco"])

    # ---- Proceso (JSON) -----------------------------------------------------
    cfg = cargar_parametros_corte_json("parametros_corte.json")       # :contentReference[oaicite:12]{index=12}
    material = str(cfg.get("material", "acero")).lower()
    espesor_mm = float(cfg.get("espesor_mm", 10.0))
    P_laser_W = float(cfg.get("potencia_laser_w", 8000.0))

    # Velocidad: aceptar mm/min (y typo histórico 'velocidad_mm_mim'), convertir a mm/s
    v_mm_min = float(cfg.get("velocidad_mm_min", cfg.get("velocidad_mm_mim", 1200.0)))
    v_mm_s = v_mm_min / 60.0

    # Δf: + arriba de superficie / - dentro del material
    delta_f_mm = float(cfg.get("posicion_focal_mm", 0.0))

    # Gas/Presión
    gas_in = normalizar_gas(cfg.get("gas", cfg.get("tipo_gas", "O2")))
    P_bar = float(cfg.get("presion_gas_bar", 1.0))

    # Parámetros adicionales
    phi_jet = float(cfg.get("phi_jet_base", DEFAULTS["phi_jet_base"]))
    frac_vap = float(cfg.get("f_vap", DEFAULTS["frac_vap"]))
    k_otros_W = float(cfg.get("k_otros_W", DEFAULTS["k_otros_W"]))
    deltaT_conv_K = float(cfg.get("deltaT_conv_K", DEFAULTS["deltaT_conv_K"]))

    # Absorptividad: usar fija si está en JSON; si no, asumir 0.9 por defecto
    A_eff = float(cfg.get("absorptividad_fija", 0.90))

    # Coeficiente convectivo de referencia (depende de boquilla/booster; si no hay, usar base)
    # Puedes calibrarlo con tu banco de datos; aquí un valor de referencia razonable.
    h_ref_W_m2K = float(cfg.get("h_jet_ref_W_m2K", 18000.0))

    # ---- Kerf por desenfoque ------------------------------------------------
    kerf_um = kerf_um_por_desenfoque(cabezal, delta_f_mm)
    kerf_mm = kerf_um / 1000.0

    # ---- Gas efectivo -------------------------------------------------------
    gas = GasAssist(
        nombre=gas_in,
        h_jet_W_m2K=h_ref_W_m2K,
        H_ox_J_gFe=float(cfg.get("H_ox_J_gFe", DEFAULTS["H_ox_J_gFe"])),
        phi_jet=phi_jet
    )

    # ---- Setup del balance --------------------------------------------------
    setup = CorteSetup(
        material=material,
        espesor_mm=espesor_mm,
        kerf_mm=kerf_mm,
        velocidad_mm_s=v_mm_s,
        P_laser_W=P_laser_W,
        absorptividad=A_eff,
        frac_vap=frac_vap,
        k_otros_W=k_otros_W,
        gas=gas,
        deltaT_conv_K=deltaT_conv_K,
    )

    # ---- Evaluación del balance en la velocidad pedida ----------------------
    res = balance_energetico_avanzado(setup, P_bar=P_bar, h_ref_W_m2K=h_ref_W_m2K)

    # ---- Solver de Vmax independiente de tu velocidad de entrada ------------
    vmax_mm_s = vmax_por_biseccion(setup, P_bar=P_bar, h_ref_W_m2K=h_ref_W_m2K)

    # ---- Salida clara (formato cercano a tus ejemplos) ----------------------
    v_mm_min_out = setup.velocidad_mm_s * 60.0
    vmax_mm_min_out = vmax_mm_s * 60.0

    print("=== RESUMEN ===")
    print(f"Material: {material} | Espesor: {espesor_mm:.2f} mm")
    print(f"Potencia láser: {P_laser_W:.0f} W | Velocidad: {setup.velocidad_mm_s:.2f} mm/s ({v_mm_min_out:.0f} mm/min)")
    print(f"Foco en superficie? Δf = {delta_f_mm:+.3f} mm ( + arriba / - dentro )")
    print(f"Spot en foco (µm): {d0_um:.1f} | Gas: {gas.nombre} @ {P_bar:.2f} bar")
    print(f"Kerf (µm) por desenfoque: {kerf_um:.1f}  => {kerf_mm:.3f} mm")

    # MODO SIMPLE (solo para referencia rápida de márgenes)
    if not gas.nombre == "O2":
        d_simple = demanda_termica_W(material, espesor_mm, kerf_mm, setup.velocidad_mm_s, setup.frac_vap)
        A_nec = d_simple["demanda_W"] / max(P_laser_W, 1e-9)
        print("\n[MODO SIMPLE] Absorción necesaria A: {:.3f}  (idealmente ≤ 1.0)".format(A_nec))
        print("Detalles intermedios:")
        print(f"  w_mm: {kerf_mm:.4f}")
        print(f"  vdot_mm3_s: {d_simple['vdot_mm3_s']:.4f}")
        print(f"  mdot_g_s: {d_simple['mdot_g_s']:.4f}")
        print(f"  energia_J_g: {d_simple['energia_J_g']:.4f}")
        print(f"  potencia_requerida_w: {d_simple['demanda_W']:.4f}")
        print(f"  potencia_laser_w: {P_laser_W:.1f}")
        print(f"  A_necesaria: {A_nec:.4f}")
        print("→ A ≤ 1.0: {}.".format("hay margen térmico en modo simple" if A_nec <= 1.0 else "no hay margen en modo simple"))

    # MODO AVANZADO
    print("\n[MODO AVANZADO] Balance con gas de asistencia:")
    print(f"  Absorptividad (fija o estimada): {A_eff:.3f}")
    print(f"  h_jet escalado: {hjet_escalado(h_ref_W_m2K, P_bar):.0f} W/m^2K  (P={P_bar:.2f} bar, α={DEFAULTS['alpha_presion']:.2f}, Pref={DEFAULTS['P_ref_bar']:.1f} bar)")
    print(f"  mdot_g_s: {res['mdot_g_s']:.2f}")
    print(f"  A_m2_s: {res['A_m2_s']:.6f}")
    print(f"  P_abs_W: {res['P_abs_W']:.2f}")
    print(f"  Q_ox_W: {res['Q_ox_W']:.2f}")
    print(f"  Q_jet_W: {res['Q_jet_W']:.2f}")
    print(f"  Q_otros_W: {res['Q_otros_W']:.2f}")
    print(f"  demanda_W: {res['demanda_W']:.2f}")
    print(f"  residuo_W: {res['residuo_W']:.2f}")
    #print(f"[φ_jet aplicado] fracción mojada del perímetro: {gas.phi_jet:.2f}")
    print(f"→ Velocidad actual: {v_mm_min_out:.0f} mm/min;   Velocidad máxima (residuo≈0): {vmax_mm_min_out:.0f} mm/min")


# =============================================================================
# 9) ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()
