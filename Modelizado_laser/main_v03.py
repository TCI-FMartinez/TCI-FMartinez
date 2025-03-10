import numpy as np
from scipy.optimize import minimize

# Parámetros del material (ej: Acero inoxidable)
material = {
    "Material": "Acero inoxidable",
    "densidad": 7880,       # kg/m³
    "C_p": 460,             # J/kg·K
    "T_m": 1700,            # K
    "L_m": 2.6e5,           # J/kg
    "k": 20,                # W/m·K (conductividad térmica)
    "lambda_laser": 1.07e-6 # m (fibra)
}

# Configuración óptica
M2 = 1.1                    # Calidad del haz
d_fibra = 100e-6            # 100 µm
f = 150e-3                  # 150 mm
# Calcular el diámetro del haz en el foco (en metros)
w_beam = (M2 * material["lambda_laser"] * f) / (np.pi * d_fibra)
w_beam_mm = w_beam * 1000   # Convertir a milímetros

def calcular_beam_waist(M2, f, d_fibra, lambda_laser):
    """Calcula el diámetro del haz en la superficie (m)."""
    return (M2 * lambda_laser * f) / (np.pi * d_fibra)

def kerf_width(P0, v, w_beam_mm, Pg, material, gas_type):
    """
    Calcula el ancho del kerf (w_k) en milímetros (mm).

    Se ha introducido un factor de calibración (K_factor) para ajustar el modelo
    a resultados experimentales en fibre laser cutting.
    
    Parámetros:
      - P0: Potencia láser (W)
      - v: Velocidad de corte (mm/s)
      - w_beam_mm: Diámetro del haz en la superficie (mm)
      - Pg: Presión del gas (kPa)
      - material: Diccionario con propiedades del material
      - gas_type: 'O2' o 'N2'
    """
    # Conversión de unidades:
    w_beam = w_beam_mm / 1000       # mm → m
    if w_beam <= 0:
        return np.inf
    v_mps = v / 1000                # mm/s → m/s
    Pg_Pa = Pg * 1000               # kPa → Pa
    lambda_laser = material["lambda_laser"]
    k = material["k"]
    T_m = material["T_m"]
    
    # Coeficientes empíricos
    A = 0.5 if gas_type == 'O2' else 0.8
    C = 3.5e5 if gas_type == 'O2' else 1.2e5

    term1 = 2.51 * A * np.sqrt(lambda_laser / w_beam) * P0 * np.sqrt(v_mps)
    term2 = k * (T_m - 300) * (1 + C * Pg_Pa * w_beam**1.5)
    
    print(f"🔍 term1={term1:.3f}, term2={term2:.3e}, w_beam={w_beam:.6e}, P0={P0}, v_mps={v_mps}, Pg_Pa={Pg_Pa}")
    
    if term2 == 0:
        return np.inf
    
    # Factor de calibración empírico (ajustado a datos experimentales)
    K_factor = 7260  
    w_k_m = term1 / term2  # Kerf sin calibrar en metros
    return w_k_m * K_factor * 1000  # Resultado en milímetros

def objetivo(x, gas_type, material, w_beam_mm, w_k_max, v_max, espesor, alpha=0.3, beta=0.7):
    """
    Función objetivo para la optimización:
      - Minimiza el kerf y maximiza la velocidad de corte.
      - alpha y beta ponderan la importancia relativa (alpha + beta = 1).
      
    Parámetros:
      - x: Vector de variables [P0, v, Pg] en [W, mm/s, kPa]
      - espesor: Espesor del material (m)
    """
    P0, v, Pg = x
    w_k_min = 0.05  # Kerf mínimo aceptable (mm)
    
    try:
        w_k = kerf_width(P0, v, w_beam_mm, Pg, material, gas_type)
    except Exception as e:
        print(f"⚠️ Error en kerf_width: {e}")
        return np.inf

    print(f"🔍 Evaluando: P0={P0}, v={v}, Pg={Pg}, w_k={w_k:.6f}")
    
    # Verificar que el kerf esté dentro del rango operativo y la velocidad en rango
    if w_k < w_k_min or w_k > w_k_max or v < 1 or v > v_max:
        print(f"❌ Restricción violada: w_k={w_k:.6f}, v={v}")
        return np.inf

    # Cálculo de la eficiencia (energía requerida/energía total)
    v_mps = v / 1000
    w_k_m = w_k / 1000
    energia_requerida = material["densidad"] * v_mps * w_k_m * espesor * (
        material["C_p"] * (material["T_m"] - 300) + material["L_m"]
    )
    energia_total = P0 + (0.3 * P0 if gas_type == 'O2' else 0)
    eta_I = energia_requerida / energia_total
    if eta_I <= 0:
        print(f"❌ Valor de eficiencia inválido: eta_I={eta_I}")
        return np.inf
    
    # Normalización de los parámetros: se escalan en función de los rangos operativos
    w_k_norm = (w_k - w_k_min) / (w_k_max - w_k_min)
    v_norm = (v - 1) / (v_max - 1)
    
    return -(alpha * (1 - w_k_norm) + beta * v_norm) + (1 / eta_I)

def convertir_unidades(resultado, gas_type, decimales=2):
    """
    Convierte las unidades de los parámetros optimizados:
      - Velocidad: de mm/s a mm/min
      - Presión: de kPa a bar
    """
    P0_opt = round(resultado.x[0], decimales)
    v_opt = round(resultado.x[1] * 60, decimales)  # mm/s → mm/min
    Pg_opt = round(resultado.x[2] / 100, decimales)  # kPa → bar
    gas_str = "O₂" if gas_type == 'O2' else "N₂"
    return (P0_opt, v_opt, Pg_opt, gas_str)

# Parámetros de optimización y operación
espesor = 2e-3  # Espesor en metros (2 mm)
gas_type = 'N2'
material["densidad_gas"] = 1.25  # kg/m³ para N2 (a 20°C)
mat_name = material["Material"]

# Rango operativo para kerf (según datos experimentales)
w_k_max = 0.4    # Kerf máximo aceptable (mm)
v_max = 1200     # Velocidad máxima en mm/s

# Valor inicial (x0 = [P0, v, Pg]) en [W, mm/s, kPa]
x0 = [3000, 500, 200]

# Límites (bounds) para cada variable
bounds = [
    (500, 4000),    # Potencia láser P0 en W
    (100, v_max),   # Velocidad v en mm/s
    (50, 3000)      # Presión Pg en kPa (para N₂, hasta 3000 kPa)
]

resultado = minimize(
    lambda x: objetivo(x, gas_type, material, w_beam_mm, w_k_max, v_max, espesor, alpha=0.3, beta=0.7),
    x0=x0,
    bounds=bounds,
    method='SLSQP'
)
print(f"🔍 Valores iniciales: {x0}")
print(f"🔍 Límites: {bounds}")

if resultado.success:
    kerf = kerf_width(resultado.x[0], resultado.x[1], w_beam_mm, resultado.x[2], material, gas_type)
    P0, v, Pg, gas = convertir_unidades(resultado, gas_type)
    print(f"\nMaterial: {mat_name}, espesor: {espesor*1000} mm, gas: {gas}")
    print("\nPARÁMETROS OPTIMIZADOS:")
    print(f"- Potencia láser: {int(P0)} W")
    print(f"- Velocidad de corte: {int(v)} mm/min")
    print(f"- Presión de gas: {Pg} bar")
    print(f"- Kerf: {kerf:.6f} mm")
    print(f"- Valor objetivo: {resultado.fun:.2f} (si es menor, más óptimo)")
else:
    print("Error en la optimización:", resultado.message)
