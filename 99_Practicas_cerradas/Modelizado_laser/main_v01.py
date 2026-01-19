import numpy as np
from scipy.optimize import minimize

# Parámetros del material (ej: Acero inoxidable)
material = {
    "Material": "Acero inoxidable",
    "densidad": 8000,       # kg/m³
    "C_p": 500,             # J/kg·K
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

def kerf_width(P0, v, w, Pg, material, gas_type='O2'):
    """
    Calcula el Kerf width según el tipo de gas.
    Adaptación de la ecuación (10) del artículo.
    """
    A = 0.5 if gas_type == 'O2' else 0.8  # Ajuste de absorción
    C = 3.5e5 if gas_type == 'O2' else 1.2e5  # Coef. enfriamiento
    
    # Término de reacción exotérmica (solo O2)
    q_L = 0.3 * P0 if gas_type == 'O2' else 0  # Ejemplo simplificado
    
    term1 = (2.51 * A * np.sqrt(material["lambda_laser"] / w) * (P0 + q_L) * np.sqrt(v))
    term2 = material["k"] * (material["T_m"] - 300) * (1 + C * material["densidad_gas"] * Pg * w**1.5)
    return term1 / term2


def objetivo(x, gas_type):
    P0, v, Pg = x
    w_k = kerf_width(P0, v, w_beam, Pg, material, gas_type)
    
    # Energía requerida (O2 incluye q_L)
    energia_requerida = material["densidad"] * v * w_k * espesor * (
        material["C_p"] * (material["T_m"] - 300) + material["L_m"]
    )
    energia_total = P0 + (0.3 * P0 if gas_type == 'O2' else 0)
    eta_I = energia_requerida / energia_total
    
    # Función objetivo: Minimizar w_k y maximizar eta_I
    return w_k + (1 / eta_I)

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


resultado = minimize(
    lambda x: objetivo(x, gas_type='O2'),
    x0=[1500, 10, 800],  # Valores iniciales (O2: menor presión)
    bounds=[(500, 8000), (500, 50000), (500, 2000 if gas_type == 'O2' else 15000)],   # (Pmin, Pmax) W, (Vmin, Vmax) mm/s, (press_min, pres_max) kPa 
    method='SLSQP')



# Conversión y visualización de resultados
if resultado.success:
    P0, v, Pg, gas = convertir_unidades(resultado, gas_type=gas_type)
    print(f"\nMaterial:{mat_name} esp:{espesor*1000} mm gas:{gas_type} ")
    print(f"\nPARÁMETROS OPTIMIZADOS:")
    print(f"- Potencia láser: {P0} W")
    print(f"- Velocidad de corte: {v} mm/min")
    print(f"- Presión de gas: {Pg} bar")
    print(f"- Valor objetivo: {resultado.fun:.2f}")
else:
    print("Error en la optimización:", resultado.message)
