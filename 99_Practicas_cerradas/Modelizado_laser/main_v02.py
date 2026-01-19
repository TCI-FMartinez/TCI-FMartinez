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
d_fibra = 100e-6             # 100 µm
f = 150e-3                  # 150 mm
w_beam = (M2 * material["lambda_laser"] * f) / (np.pi * d_fibra)

def calcular_beam_waist(M2, f, d_fibra, lambda_laser):
    return (M2 * lambda_laser * f) / (np.pi * d_fibra)

def kerf_width(P0, v, w_beam_mm, Pg_kPa, material, gas_type):
    """
    Calcula el ancho del kerf (w_k) en milímetros (mm).
    
    Parámetros:
    - P0 : Potencia láser (W)
    - v : Velocidad de corte (mm/s)
    - w_beam_mm : Diámetro del haz en la superficie (mm)
    - Pg_kPa : Presión del gas (kPa)
    - material : Diccionario con propiedades del material
    - gas_type : 'O2' o 'N2'
    """
    # Conversión a unidades SI para cálculo interno
    w_beam = w_beam_mm / 1000  # mm → metros (m)
    v_mps = v / 1000  # mm/s → m/s
    Pg = Pg_kPa * 1000  # kPa → Pa (N/m²)
    lambda_laser = material["lambda_laser"]  # en metros (m)
    k = material["k"]  # Conductividad térmica (W/m·K)
    T_m = material["T_m"]  # Temperatura de fusión (K)
    
    # Coeficientes ajustados para unidades SI
    A = 0.5 if gas_type == 'O2' else 0.8
    C = 3.5e5 if gas_type == 'O2' else 1.2e5  # (1/Pa·m^0.5)
    
    # Términos de la ecuación (unidades SI)
    term1 = (2.51 * A * np.sqrt(lambda_laser / w_beam) * P0 * np.sqrt(v_mps))
    term2 = k * (T_m - 300) * (1 + C * Pg * w_beam**1.5)
    
    w_k_m = term1 / term2  # Kerf en metros (m)
    return w_k_m * 1000  # Convertir a milímetros (mm)

def objetivo(x, gas_type, material, w_beam, w_k_max, v_max, espesor, alpha=0.5, beta=0.5):
    P0, v, Pg = x
    
    # Validar parámetros físicos antes de calcular
    if v <= 0 or P0 <= 0 or Pg <= 0:
        return np.inf
    
    try:
        w_k = kerf_width(P0, v, w_beam, Pg, material, gas_type)
        if w_k <= 0.1 or w_k > w_k_max or v > v_max:
            return np.inf
    except:
        return np.inf
    
    # Cálculo de eficiencia térmica
    energia_requerida = material["densidad"] * v * w_k * espesor * (
        material["C_p"] * (material["T_m"] - 300) + material["L_m"]
    )
    energia_total = P0 + (0.3 * P0 if gas_type == 'O2' else 0)
    eta_I = energia_requerida / energia_total
    
    # Normalización adaptativa
    w_k_norm = (w_k - 0.1) / (w_k_max - 0.1)  # Rango 0-1
    v_norm = (v - 10) / (v_max - 10)          # Rango 0-1
    
    # Función objetivo equilibrada
    return -(alpha * (1 - w_k_norm) + beta * v_norm) + (1 / eta_I)

#def objetivo_(x, gas_type, alpha=0.5, beta=0.5):
#    """
#    Función objetivo que permite ponderar entre:
#    - alpha: Minimizar kerf width (0 < alpha < 1)
#    - beta: Maximizar velocidad de corte (0 < beta < 1, alpha + beta = 1)
#    
#    alpha	beta	Comportamiento
#    0.9	0.1	Prioridad máxima a kerf pequeño (velocidad secundaria).
#    0.5	0.5	Equilibrio entre kerf y velocidad.
#    0.2	0.8	Prioridad a velocidad alta (kerf más ancho permitido).
#    """
#    P0, v, Pg = x
#    w_k = kerf_width(P0, v, w_beam, Pg, material, gas_type)
#    
#    # Energía requerida (O2 incluye q_L)
#    energia_requerida = material["densidad"] * v * w_k * espesor * (
#        material["C_p"] * (material["T_m"] - 300) + material["L_m"]
#    )
#    energia_total = P0 + (0.3 * P0 if gas_type == 'O2' else 0)
#    eta_I = energia_requerida / energia_total
#    
#    # Función objetivo: Minimizar w_k y maximizar eta_I
#    return w_k + (1 / eta_I)

# Función para conversión de unidades
def convertir_unidades(resultado, decimales=2):
    """
    Convierte las unidades de los parámetros optimizados:
    - Velocidad: de mm/s → mm/min
    - Presión: de kPa → bar
    """
    P0_opt = int(resultado.x[0])  # Potencia (W) - misma unidad
    v_opt = int(resultado.x[1] * 60)  # Convertir mm/s → mm/min
    Pg_opt = round(resultado.x[2] / 100, decimales)  # Convertir kPa → bar
    
    return P0_opt, v_opt, Pg_opt

# Función de conversión de unidades (actualizada)
def convertir_unidades(resultado, gas_type, decimales=2):
    P0_opt = round(resultado.x[0], decimales)
    v_opt = round(resultado.x[1] * 60, decimales)  # mm/s → mm/min
    Pg_opt = round(resultado.x[2] / 100, decimales)  # kPa → bar
    gas_str = "O₂" if gas_type == 'O2' else "N₂"
    return (P0_opt, v_opt, Pg_opt, gas_str)

# Parámetros de optimización (ejemplo para O2)
espesor = 2e-3  # 2 mm
gas_type = "N2"
material["densidad_gas"] = 1.43 if gas_type == 'O2' else 1.25  # kg/m³ (O2/N2 a 20°C)
mat_name = material["Material"]

# Parámetros de operación
w_k_max = 0.4  # mm (kerf máximo aceptable)
v_max = 50000     # mm/s (velocidad máxima)
gas_type = 'N2'

resultado = minimize(
    lambda x: objetivo(x, gas_type, material, w_beam, w_k_max, v_max, espesor, alpha=0.5, beta=0.5),
    x0=[1500, 10, 800],  # Valores iniciales (O2: menor presión)
    bounds=[(500, 8000), (500, v_max), (100, 500 if gas_type == 'O2' else 3000)],   # (Pmin, Pmax) W, (Vmin, Vmax) mm/s, (press_min, pres_max) kPa 
    method='SLSQP')

kerf = kerf_width(*resultado.x, w_beam, material, gas_type)


# Conversión y visualización de resultados
if resultado.success:
    P0, v, Pg, gas = convertir_unidades(resultado, gas_type=gas_type)
    print(f"\nMaterial:{mat_name} esp:{espesor*1000} mm gas:{gas_type} ")
    print(f"\nPARÁMETROS OPTIMIZADOS:")
    print(f"- Potencia láser: {P0} W")
    print(f"- Velocidad de corte: {v} mm/min")
    print(f"- Presión de gas: {Pg} bar")
    print(f"- Valor objetivo 0, resultado= {resultado.fun:.2f}")
    print(f"- Kerf: {kerf:.6f} mm")
else:
    print("Error en la optimización:", resultado.message)
