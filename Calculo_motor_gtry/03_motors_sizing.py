########################################################################################################################
# Mi método (A)
# USO LA FORMULA DE ACELERACIÓN PARAEL CÁLCULO DE LA FUERZA TANGENCIAL EN EL PIÑÓN 
#   '(((masa_total x Gantry) x 9,81 x roz) + ((masa_total x Gantry) x k = Fuerza tangencial corregida [N/m]
# Luego verificare usando el Toque Fanuc (B) para verificar el resultado.
#   Ta_fanuc = (JM + JL/eta) * (omega/ta) * (1 - exp(-ksta))
#   Vr = Vm * (1 - (1/(taks)) * (1 - exp(-ks*ta)))
########################################################################################################################
# V03 - Enfoque por fuerza de aceleración (masa_total * Gy por motor) + verificación con fórmula Fanuc ("Torque_fanuc")
#
# Acordado:
#   masa equivalente por motor = masa_total * Gy
#   k es global (se aplica al total de fuerzas/par variable)
#
# Método A (fuerzas -> par):
#   m_eff = masa_total * Gy
#   F_fric = mu*(m_eff*g + Fg)
#   F_acc  = m_eff*acc
#   F_total = (F_fric + F_acc + Fc) * k
#   T_motor_force = (F_total * (d_pinon/2)) / (eta * Z1_Z2) + Tf
#
# Método B (Fanuc - según imagen):
#   Ta_fanuc = (JM + JL/eta) * (omega/ta) * (1 - exp(-ks*ta))
#   Vr = Vm * (1 - (1/(ta*ks)) * (1 - exp(-ks*ta)))
#   T_total_fanuc = (Ta_fanuc + Tm) * k + Tf
#
# Unidades:
#   V_rapid: m/min
#   ta: s
#   acc: m/s^2
########################################################################################################################
# ------ FUNCIONES -------

import math
from datetime import datetime
from pathlib import Path

def torque_por_fuerzas(
    masa_total_kg: float,
    Gy: float,
    mu: float,
    acc_m_s2: float,
    d_pinon_m: float,
    Z1_Z2: float,
    eta: float,
    k: float,
    Fg_N: float,
    Fc_N: float,
    Tf_Nm: float,
) -> dict:
    g = 9.81
    m_eff = masa_total_kg * Gy

    F_fric = mu * (m_eff * g + Fg_N)
    F_acc = m_eff * acc_m_s2
    F_total = (F_fric + F_acc + Fc_N) * k

    r_pinon = d_pinon_m / 2.0
    T_pinion = F_total * r_pinon
    T_motor = T_pinion / (eta * Z1_Z2)
    T_motor_total = T_motor + Tf_Nm

    return {
        "m_eff_kg": m_eff,
        "F_fric_N": F_fric,
        "F_acc_N": F_acc,
        "F_total_N": F_total,
        "T_pinion_Nm": T_pinion,
        "T_motor_Nm": T_motor,
        "T_motor_total_Nm": T_motor_total,
    }


def torque_fanuc(
    masa_total_kg: float,
    Gy: float,
    mu: float,
    d_pinon_m: float,
    Z1_Z2: float,
    eta: float,
    V_rapid_m_min: float,
    ta_s: float,
    ks_s_1: float,
    JM_motor_kgm2: float,
    J_reductor_kgm2: float,
    masa_pinon_kg: float,
    k: float,
    Fg_N: float,
    Fc_N: float,
    Tf_Nm: float,
) -> dict:
    g = 9.81
    m_eff = masa_total_kg * Gy * k  # Aquí aplico el k global a la masa equivalente (en vez de a cada fuerza por separado)

    # Cinemática (Vm en rpm)
    I = (math.pi * d_pinon_m) / Z1_Z2
    Vm = V_rapid_m_min / I
    omega = (Vm * 2.0 * math.pi) / 60.0

    # Inercia del piñón (lado salida) reflejada al motor
    J_pinon = 0.5 * masa_pinon_kg * (d_pinon_m / 2.0) ** 2 if masa_pinon_kg > 0 else 0.0
    J_pinon_ref = J_pinon / (Z1_Z2 ** 2) if masa_pinon_kg > 0 else 0.0

    # Inercias Fanuc
    JL = m_eff * (I / (2.0 * math.pi)) ** 2
    JM = JM_motor_kgm2 + J_reductor_kgm2 + J_pinon_ref

    # Torque de aceleración (Fanuc)
    term_exp = 1.0 - math.exp(-ks_s_1 * ta_s)
    Ta = (JM + (JL / eta)) * (omega / ta_s) * term_exp

    # Vr (Fanuc)
    Vr = Vm * (1.0 - (1.0 / (ta_s * ks_s_1)) * (1.0 - math.exp(-ks_s_1 * ta_s)))

    # Torque de carga (fricción + corte)
    F_fric = mu * (m_eff * g + Fg_N)
    F_carga = F_fric + Fc_N
    Tm = (F_carga * I) / (2.0 * math.pi * eta)

    # Total Fanuc (k global aplicado a variables; Tf sumado fijo en motor)
    k_f = 1  # k global <-- aquí me cargo el k porque lo pongo en la masa equivalente por motor (m_eff)
    T_total = (Tm + Ta) * k_f + Tf_Nm

    return {
        "m_eff_kg": m_eff,
        "I_m_rev": I,
        "Vm_rpm": Vm,
        "omega_rad_s": omega,
        "J_pinon_kgm2": J_pinon,
        "J_pinon_ref_kgm2": J_pinon_ref,
        "JL_kgm2": JL,
        "JM_kgm2": JM,
        "Ta_fanuc_Nm": Ta,
        "Vr_rpm": Vr,
        "F_fric_N": F_fric,
        "Tm_Nm": Tm,
        "T_total_fanuc_Nm": T_total,
    }


def guardar_resultados_txt(nombre: str, lineas: list[str]) -> Path:
    salida = Path(__file__).resolve().parent / nombre
    salida.write_text("\n".join(lineas), encoding="utf-8")
    return salida

########################################################################################################################
# ------ MAIN -------
if __name__ == "__main__":
    # Entradas
    ref_motor = "AM8072-0RH0-0000"
    ref_reductor = "MGO170-05"
    masa_total = 598.0
    Gy = 0.70
    mu = 0.015
    Fg = 0.0
    Fc = 0.0

    d_pinon = 0.0605
    Z1_Z2 = 5.0
    eta = 0.97

    acc = 35.0          # m/s^2
    ta = 0.085          # s
    ks = 80.0           # 1/s

    JM_motor = 0.00932
    J_reductor = 0.001554
    masa_pinon = 5.0

    V_rapid = 114.0     # m/min
    k = 1.2
    Tf = 0.8

    # Instancia del Cálculo método A
    res_force = torque_por_fuerzas(
        masa_total_kg=masa_total,
        Gy=Gy,
        mu=mu,
        acc_m_s2=acc,
        d_pinon_m=d_pinon,
        Z1_Z2=Z1_Z2,
        eta=eta,
        k=k,
        Fg_N=Fg,
        Fc_N=Fc,
        Tf_Nm=Tf,
    )

    # Instancia del Cálculo método B
    res_fanuc = torque_fanuc(
        masa_total_kg=masa_total,
        Gy=Gy,
        mu=mu,
        d_pinon_m=d_pinon,
        Z1_Z2=Z1_Z2,
        eta=eta,
        V_rapid_m_min=V_rapid,
        ta_s=ta,
        ks_s_1=ks,
        JM_motor_kgm2=JM_motor,
        J_reductor_kgm2=J_reductor,
        masa_pinon_kg=masa_pinon,
        k=k,
        Fg_N=Fg,
        Fc_N=Fc,
        Tf_Nm=Tf,
    )

    # Comparación
    T_force = res_force["T_motor_total_Nm"]
    T_fanuc = res_fanuc["T_total_fanuc_Nm"]
    ratio = (T_force / T_fanuc) if T_fanuc != 0 else float("inf")

    #------ IMPRESION POR TERMINAL -------
    print("\n--- V03 | Entradas ---")
    print(f"Masa total: {masa_total:.2f} kg")
    print(f"Factor gantry Gy (por motor): {Gy:.3f} -> Masa equivalente por motor: {res_force['m_eff_kg']:.2f} kg")
    print(f"Aceleración lineal: {acc:.2f} m/s² | {acc/9.81:.3f} G")
    print(f"ta: {ta:.3f} s | ks: {ks:.1f} 1/s | V_rapid: {V_rapid:.2f} m/min")
    print(f"mu: {mu} | Fg: {Fg} N | Fc: {Fc} N | k global: {k} | Tf: {Tf} N·m")

    print("\n--- Método A | Par por fuerzas ---")
    print(f"Fricción guías: {res_force['F_fric_N']:.2f} N")
    print(f"Fuerza de aceleración: {res_force['F_acc_N']:.2f} N")
    print(f"Fuerza total (con k): {res_force['F_total_N']:.2f} N")
    print(f"Par total en motor (incluye Tf): {res_force['T_motor_total_Nm']:.2f} N·m")

    print("\n--- Método B | Torque_fanuc ---")
    print(f"Vm: {res_fanuc['Vm_rpm']:.2f} rpm | Vr: {res_fanuc['Vr_rpm']:.2f} rpm | ω: {res_fanuc['omega_rad_s']:.2f} rad/s")
    print(f"JM: {res_fanuc['JM_kgm2']:.6f} kg·m² | JL: {res_fanuc['JL_kgm2']:.6f} kg·m²")
    print(f"Ta_fanuc: {res_fanuc['Ta_fanuc_Nm']:.2f} N·m | Tm: {res_fanuc['Tm_Nm']:.2f} N·m")
    print(f"Par total Fanuc (incluye k y Tf): {res_fanuc['T_total_fanuc_Nm']:.2f} N·m")

    print(f"\nRelación de inercia carga/total JL/JM [-]: {res_fanuc['JL_kgm2']/res_fanuc['JM_kgm2']:.2f}")

    print("\n--- Comparación ---")
    print(f"Par fuerzas / Par Fanuc: {ratio:.3f}")

    # ------ SALIDA A ARCHIVO.TXT -------
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lineas = [
        "RESULTADOS MOTOR V03 (comparación: método fuerzas vs método Fanuc)",
        f"Motor: {ref_motor} + Reductor: {ref_reductor}",
        "",
        f"Generado: {ts}",
        "",
        "ENTRADAS",
        f"    Masa total [kg]: {masa_total:.2f}",
        f"    Factor gantry Gy (masa equivalente por motor) [-]: {Gy*100:.0f}%",
        f"    Masa equivalente por motor [kg]: {res_force['m_eff_kg']:.2f}",
        f"    Coeficiente fricción (roz) [-]: {mu:.4f}",
        f"    Fuerza gibs / precarga [N]: {Fg:.1f}",
        f"    Fuerza de corte [N]: {Fc:.1f}",
        f"    Factor global de seguridad k [-]: {k:.2f}",
        f"    Par fricción fijo en motor Tf [N·m]: {Tf:.2f}",
        f"    Diámetro piñón [m]: {d_pinon:.4f}",
        f"    Reducción motor:piñón [-]: {Z1_Z2:.2f}",
        f"    Eficiencia η [-]: {eta:.3f}",
        f"    Aceleración lineal [m/s²]: {acc:.2f}",
        f"    Tiempo de aceleración ta [s]: {ta:.3f}",
        f"    Ganancia lazo posición ks [1/s]: {ks:.1f}",
        f"    Velocidad rápida [m/min]: {V_rapid:.2f}",
        f"    Inercia rotor motor [kg·m²]: {JM_motor:.6f}",
        f"    Inercia reductor [kg·m²]: {J_reductor:.6f}",
        f"    Masa piñón [kg]: {masa_pinon:.2f}",
        "",
        "RESULTADOS - MÉTODO A (por fuerzas)",
        f"    Fuerza fricción guías [N]: {res_force['F_fric_N']:.2f}",
        f"    Fuerza aceleración [N]: {res_force['F_acc_N']:.2f}",
        f"    Fuerza total aplicada (incluye k) [N]: {res_force['F_total_N']:.2f}",
        f"--> Par total en motor (incluye Tf) [N·m]: {res_force['T_motor_total_Nm']:.2f}",
        "",
        "RESULTADOS - MÉTODO B (Torque_fanuc)",
        f"    Avance lineal por vuelta motor I [m/rev]: {res_fanuc['I_m_rev']:.6f}",
        f"    Velocidad motor Vm [rpm]: {res_fanuc['Vm_rpm']:.2f}",
        f"    Velocidad Vr (inicio caída par) [rpm]: {res_fanuc['Vr_rpm']:.2f}",
        f"    Velocidad angular ω [rad/s]: {res_fanuc['omega_rad_s']:.2f}",
        f"    Inercia total en motor JM [kg·m²]: {res_fanuc['JM_kgm2']:.6f}",
        f"    Inercia carga reflejada JL [kg·m²]: {res_fanuc['JL_kgm2']:.6f}",
        f"    Relación de inercia carga/total JL/JM [-]: {res_fanuc['JL_kgm2']/res_fanuc['JM_kgm2']:.2f}",
        f"    Par de aceleración Ta_fanuc [N·m]: {res_fanuc['Ta_fanuc_Nm']:.2f}",
        f"    Par de carga Tm (fricción+corte) [N·m]: {res_fanuc['Tm_Nm']:.2f}",
        f"--> Par total Fanuc (incluye k y Tf) [N·m]: {res_fanuc['T_total_fanuc_Nm']:.2f}",
        "",
        "COMPARACIÓN",
        f"    Par método fuerzas / Par método Fanuc [-]: {ratio:.3f}",
    ]

    salida = guardar_resultados_txt("resultados_motor_v03.txt", lineas)
    print(f"\nTXT generado: {salida}")
