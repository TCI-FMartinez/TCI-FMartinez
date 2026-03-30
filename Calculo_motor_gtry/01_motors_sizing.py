import math

# --- Parámetros de entrada (ejemplo) ---
# Masa y fuerzas
masa_mesa = 550      # Masa total de la mesa [kg]
masa_movil = masa_mesa * 0.6    # 60% Masa de partes móviles [kg]
mu = 0.015            # Coeficiente de fricción
Fg = 0             # Fuerza de fijación (gibs) [N]
Fc = 0            # Fuerza de corte [N] (si aplica)

# Piñón y cremallera
d_pinon = 0.0605        # Diámetro del piñón [m]
Z1_Z2 = 5            # Relación de reducción (Z1:Z2 = motor:piñón)
eta = 0.97           # Eficiencia del sistema (piñón + reductor)

# Motor y operación
ta = 0.085             # Tiempo de aceleración [s]    <<------------------------
V_rapid = 2.33        # Velocidad lineal rápida [m/s]
JM_motor = 0.0099     # Inercia del rotor [kg·m²]
J_reductor = 0.00015  # Inercia del reductor [kg·m²]
ks = 80              # Ganancia del lazo [s⁻¹]

# --- Cálculos clave según el PDF ---
# 1. Distancia por revolución del motor (I)
circunferencia_pinon = math.pi * d_pinon  # [m/rev del piñón]
I = circunferencia_pinon * (1 / Z1_Z2)    # [m/rev del motor]

# 2. Fuerza total (F) [N]
W = masa_movil * 9.81                     # Peso [N]
F_friccion = mu * (W + Fg)                # Fuerza de fricción
F_total = F_friccion + Fc                 # Fuerza total a vencer

# 3. Torque de carga (Tm) [N·m] (Eq. 2.2.2.1 del PDF)
Tm = (F_total * I) / (2 * math.pi * eta)  # Tm sin Tf

# 4. Torque de fricción en rodamientos (Tf) [N·m] (dato o estimado)
Tf = 0.8  # Ejemplo: Valor típico para rodamientos (ajustar según especificaciones)

# 5. Velocidad del motor (Vm) [min⁻¹] (Eq. 2.2.2.2 del PDF)
Vm = (V_rapid * 60) / I  # Convertir m/s → m/min → min⁻¹

# 6. Inercias (Eq. 2.2.2.3 del PDF)
# Inercia del piñón (cilindro)
masa_pinon = 5.0  # [kg] (ajustar)
J_pinon = 0.5 * masa_pinon * (d_pinon/2)**2  # [kg·m²]
# Inercia de la carga reflejada al motor
J_carga = masa_movil * (I / (2 * math.pi))**2  # [kg·m²]
# Inercia total del sistema
JM_total = JM_motor + J_reductor + J_pinon  # Inercia en el motor
JL = J_carga  # JL ya está reflejada al motor por "I"

# 7. Torque de aceleración (Ta) [N·m] (Eq. 2.2.2.4 del PDF)
omega = (Vm * 2 * math.pi) / 60  # Velocidad angular [rad/s]
term_exp = 1 - math.exp(-ks * ta)
Ta = (JM_total + JL / eta) * omega / ta * term_exp

# 8. Torque total (T) [N·m]
T_total = Tm + Ta + Tf  # Suma según el PDF (Tm + Ta + Tf)

# 9. Aceleración (α) [Gs]
aceleracion_g = (V_rapid / ta) / 9.8  # Aceleración en G
interpolada_G = aceleracion_g * math.sqrt(2)

# --- RESUMEN DE DATOS ---
print("\n--- Parámetros de Entrada ---")
print(f"  Masa móvil: {masa_mesa} kg | {masa_movil:.1f} kg (gantry 60%)")
print(f"  Coeficiente de fricción (μ): {mu}")
print(f"  Fuerza de fijación (Fg): {Fg} N")
print(f"  Fuerza de corte (Fc): {Fc} N")
print(f"  Diámetro del piñón: {d_pinon} m")
print(f"  Relación de reducción (Z1:Z2): {Z1_Z2}")
print(f"  Eficiencia del sistema (η): {eta}")
print(f"  Tiempo de aceleración (ta): {ta} s  <<-------------")
print(f"  Velocidad rápida (V_rapid): {V_rapid} m/s")
print(f"  Inercia del motor (JM_motor): {JM_motor} kg·m²")
print(f"  Inercia del reductor (J_reductor): {J_reductor} kg·m²")

# --- Resultados ---
print("\n--- Cálculos Finales según PDF Fanuc---")
print(f"  1. Distancia por revolución (I): {I:.4f} m/rev")
print(f"  2. Fuerza total (F): {F_total:.2f} N")
print(f"  3. Torque de carga (Tm): {Tm:.2f} N·m")
print(f"  4. Velocidad motor (Vm): {Vm:.0f} min⁻¹")
print(f"  5. Inercia total (JM_total): {JM_total:.4f} kg·m²")
print(f"  6. Inercia de carga (JL): {JL:.4f} kg·m²")
print(f"  7. Torque de aceleración (Ta): {Ta:.2f} N·m")
print(f"  8. Torque total (T_total): {T_total:.2f} N·m")
print(f"  9. Aceleración: {aceleracion_g:.1f} G | {interpolada_G:.1f} G (interpolada) <<--")
print(f"  10. Relación de inercia (JL/JM_total): {JL/JM_total:.1f} veces")