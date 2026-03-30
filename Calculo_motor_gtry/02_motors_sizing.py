import math
from datetime import datetime
from pathlib import Path

# --- Parámetros de entrada (ejemplo) ---
# Masa y fuerzas
masa_mesa = 598                 # Masa total de la mesa [kg]
k = 1.2                         # Factor de seguridad para masa móvil (ajustar según experiencia o criterio)
gantry_ratio = 0.7              # 70% Masa de partes móviles (Gantry)
masa_movil = masa_mesa * gantry_ratio    # Masa de partes móviles [kg]
mu = 0.015                      # Coeficiente de fricción
Fg = 0                          # Fuerza de fijación (gibs) [N]
Fc = 0                          # Fuerza de corte [N] (si aplica)

# Piñón y cremallera
d_pinon = 0.0605                # Diámetro del piñón [m]
Z1_Z2 = 5                       # Relación de reducción (motor:piñón)
eta = 0.97                      # Eficiencia del sistema

# Motor y operación
ta = 0.085                      # Tiempo de aceleración [s]
V_rapid = 114                   # Velocidad lineal rápida [m/min]
JM_motor = 0.00932                # Inercia del rotor [kg·m²]
J_reductor = 0.00932            # Inercia del reductor [kg·m²]
ks = 80                         # Ganancia del lazo [s⁻¹]

# --- Cálculos ---
# 1) Distancia por revolución del motor (I)
circunferencia_pinon = math.pi * d_pinon      # [m/rev piñón]
I = circunferencia_pinon * (1 / Z1_Z2)        # [m/rev motor]

# 2) Fuerza total (F) [N]
W = masa_movil * 9.81
F_friccion = mu * (W + Fg)
F_total = F_friccion + Fc

# 3) Torque de carga (Tm) [N·m]
Tm = (F_total * I) / (2 * math.pi * eta)

# 4) Torque de fricción (Tf) [N·m]
Tf = 0.8  # ajustar si tienes dato real

# 5) Velocidad del motor (Vm) [min⁻¹]
Vm = (V_rapid) / I

# 6) Inercias
masa_pinon = 5.0
J_pinon = 0.5 * masa_pinon * (d_pinon / 2) ** 2   # inercia física del piñón (lado salida)

# Corrección: reflejar inercia del piñón al eje motor si hay reducción (motor:piñón = Z1_Z2)
# J_ref = J_load / (ratio^2)
J_pinon_ref = J_pinon / (Z1_Z2 ** 2)

J_carga = masa_movil * (I / (2 * math.pi)) ** 2    # ya está reflejada al motor por usar I (m/rev motor)

JM_total = JM_motor + J_reductor + J_pinon_ref
JL = J_carga

# 7) Torque de aceleración (Ta)
omega = (Vm * 2 * math.pi) / 60
term_exp = 1 - math.exp(-ks * ta)
Ta = (JM_total + (JL / eta)) * (omega / ta) * term_exp

# 8) Torque total
T_total = Tm + Ta + Tf

# 9) Aceleración
aceleracion_g = ((V_rapid / 60) / ta) / 9.8  # V_rapid está en m/min, así que dividimos por 60 para obtener m/s
interpolada_G = aceleracion_g * math.sqrt(2)

# --- Impresión ---
print("\n------ Parámetros de Entrada -------")
print("\n--- AM8072-0RH0-0000 + MGO170-05 ---")
print(f"  Masa total: {masa_mesa} kg | Masa móvil 1 motor: {masa_movil:.1f} kg ({gantry_ratio*100:.0f}%)")
print(f"  Coeficiente de fricción (μ): {mu}")
print(f"  Fuerza de fijación (Fg): {Fg} N")
print(f"  Fuerza de corte (Fc): {Fc} N")
print(f"  Diámetro del piñón: {d_pinon} m")
print(f"  Relación de reducción (motor:piñón): {Z1_Z2}")
print(f"  Eficiencia del sistema (η): {eta}")
print(f"  Tiempo de aceleración (ta): {ta} s")
print(f"  Velocidad rápida (V_rapid): {V_rapid} m/min")
print(f"  Inercia del motor (JM_motor): {JM_motor} kg·m²")
print(f"  Inercia del reductor (J_reductor): {J_reductor} kg·m²")
print(f"  Inercia piñón (J_pinon): {J_pinon:.6f} kg·m² | reflejada (J_pinon_ref): {J_pinon_ref:.6f} kg·m²")

print("\n--- Cálculos Finales ---")
print(f"  1. Distancia por revolución (I): {I:.6f} m/rev")
print(f"  2. Fuerza total (F_total): {F_total:.3f} N")
print(f"  3. Torque de carga (Tm): {Tm:.6f} N·m")
print(f"  4. Velocidad motor (Vm): {Vm:.2f} min⁻¹")
print(f"  5. Inercia total (JM_total): {JM_total:.6f} kg·m²")
print(f"  6. Inercia de carga (JL): {JL:.6f} kg·m²")
print(f"  7. Torque de aceleración (Ta): {Ta:.6f} N·m")
print(f"  8. Torque fricción (Tf): {Tf:.6f} N·m")
print(f"  9. Torque total (T_total): {T_total:.6f} N·m")
print(f" 10. Aceleración: {aceleracion_g:.3f} G | {interpolada_G:.3f} G (interpolada)")
print(f" 11. Relación de inercia (JL/JM_total): {JL/JM_total:.3f} veces")

# --- Export TXT en la misma ruta que el script ---
def guardar_resultados_txt():
    salida = Path(__file__).resolve().parent / "resultados_motor.txt"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas = [
        "RESULTADOS DIMENSIONAMIENTO MOTOR",
        f"Generado: {ts}",
        "",
        "PARAMETROS DE ENTRADA",
        f"masa_mesa_kg={masa_mesa}",
        f"masa_movil_kg={masa_movil}",
        f"mu={mu}",
        f"Fg_N={Fg}",
        f"Fc_N={Fc}",
        f"d_pinon_m={d_pinon}",
        f"Z1_Z2={Z1_Z2}",
        f"eta={eta}",
        f"ta_s={ta}",
        f"V_rapid_m_s={V_rapid}",
        f"JM_motor_kgm2={JM_motor}",
        f"J_reductor_kgm2={J_reductor}",
        f"masa_pinon_kg={masa_pinon}",
        f"J_pinon_kgm2={J_pinon}",
        f"J_pinon_ref_kgm2={J_pinon_ref}",
        "",
        "RESULTADOS",
        f"I_m_rev={I}",
        f"F_total_N={F_total}",
        f"Tm_Nm={Tm}",
        f"Vm_rpm={Vm}",
        f"omega_rad_s={omega}",
        f"JM_total_kgm2={JM_total}",
        f"JL_kgm2={JL}",
        f"Ta_Nm={Ta}",
        f"Tf_Nm={Tf}",
        f"T_total_Nm={T_total}",
        f"aceleracion_G={aceleracion_g}",
        f"aceleracion_G_interpolada={interpolada_G}",
        f"ratio_JL_JM={JL/JM_total}",
    ]

    salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\n[OK] Generado: {salida}")

guardar_resultados_txt()