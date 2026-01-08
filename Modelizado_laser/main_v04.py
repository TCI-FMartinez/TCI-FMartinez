import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # para gráficos 3D

# =============================================================================
# DEFINICIÓN DEL MODELO
# =============================================================================
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
w_beam = (M2 * material["lambda_laser"] * f) / (np.pi * d_fibra)  # en m
w_beam_mm = w_beam * 1000   # en mm

def kerf_width(P0, v, w_beam_mm, Pg, material, gas_type):
    """
    Calcula el ancho del kerf (w_k) en milímetros (mm) utilizando una
    ecuación empírica. Se incorpora un factor de calibración (K_factor)
    para ajustar el modelo a resultados experimentales.
    """
    # Conversión de unidades
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
    
    # Factor de calibración empírico para ajustar a valores típicos (p.ej. 0.2–0.4 mm)
    K_factor = 7260  
    w_k_m = term1 / term2  # Kerf sin calibrar en metros
    return w_k_m * K_factor * 1000  # Resultado en mm

def objetivo(x, gas_type, material, w_beam_mm, w_k_max, v_max, espesor, alpha=0.2, db_lvl=0):
    """
    Función objetivo que intenta minimizar el kerf y maximizar la velocidad.
    Los parámetros se ponderan según alpha y (1 - alpha).
    
    Parámetros:
      - x: [P0, v, Pg] en [W, mm/s, kPa]
      - espesor: espesor del material (m)
      - db_lvl: nivel de depuración (0 = sin prints, >0 activa mensajes)
    """
    P0, v, Pg = x
    # Kerf mínimo aceptable (en mm)
    w_k_min = 0.1
    
    try:
        w_k = kerf_width(P0, v, w_beam_mm, Pg, material, gas_type)
    except Exception as e:
        if db_lvl > 0:
            print(f"⚠️ Error en kerf_width: {e}")
        return np.inf

    if db_lvl > 0:
        print(f"🔍 Evaluando: P0={P0}, v={v}, Pg={Pg}, w_k={w_k:.6f}")
    
    # Validar restricciones: el kerf debe estar entre w_k_min y w_k_max, la velocidad en rango
    if w_k < w_k_min or w_k > w_k_max or v < 1 or v > v_max:
        if db_lvl > 0:
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
        if db_lvl > 0:
            print(f"❌ Eficiencia inválida: eta_I={eta_I}")
        return np.inf

    # Normalización: se mapean el kerf y la velocidad a un rango [0,1]
    w_k_norm = (w_k - w_k_min) / (w_k_max - w_k_min)
    v_norm = (v - 1) / (v_max - 1)

    # Se penaliza con 1/eta_I (a mayor eficiencia, menor penalización)
    return -(alpha * (1 - w_k_norm) + (1 - alpha) * v_norm) + (1 / eta_I)

def convertir_unidades(resultado, gas_type, decimales=2):
    """Convierte unidades de velocidad (mm/s a mm/min) y presión (kPa a bar)."""
    P0_opt = round(resultado.x[0], decimales)
    v_opt = round(resultado.x[1] * 60, decimales)  # mm/s → mm/min
    Pg_opt = round(resultado.x[2] / 100, decimales)  # kPa → bar
    gas_str = "O₂" if gas_type == 'O2' else "N₂"
    return (P0_opt, v_opt, Pg_opt, gas_str)

# =============================================================================
# CONFIGURACIÓN Y PARÁMETROS DE OPTIMIZACIÓN
# =============================================================================
#espesor = 2e-3  # 2 mm en metros
espesor = 8e-3  # 8 mm en metros
gas_type = 'N2'
material["densidad_gas"] = 1.25  # para N₂ a 20°C
mat_name = material["Material"]

# Rangos operativos (según datos experimentales)
w_k_max = 0.4    # Kerf máximo aceptable (mm)
v_max = 1200     # Velocidad máxima (mm/s)

# Valor inicial (x0 = [P0, v, Pg])
#x0 = [3000, 500, 200]
x0 = [6000, 430, 1800]

# Límites para cada variable
bounds = [
    (3000, 6000),    # P0 (W)
    (10, v_max),   # v (mm/s)
    (50, 2500)      # Pg (kPa)
]

# =============================================================================
# PREPARANDO LAS ITERACIONES CON DIVERSOS MÉTODOS
# =============================================================================
# Se definen los métodos a probar; se omiten los bounds para Nelder-Mead y Powell
methods = {
    'BFGS': {'method': 'BFGS', 'bounds': bounds},
    'L-BFGS-B': {'method': 'L-BFGS-B', 'bounds': bounds},
    'SLSQP': {'method': 'SLSQP', 'bounds': bounds},
    'Nelder-Mead': {'method': 'Nelder-Mead', 'bounds': None},
    'Powell': {'method': 'Powell', 'bounds': None}
}

# Diccionario para almacenar la trayectoria de iteraciones para cada método
iterations = {}

# Función fábrica para generar callbacks que almacenen los puntos iterados
def make_callback(method_name):
    def callback(x):
        iterations[method_name].append(np.copy(x))
    return callback

# Diccionario para almacenar los resultados finales
results = {}

# Nivel de depuración para el objetivo (0: sin prints, 1: con prints)
debug_lvl = 0

# Ejecutar la optimización para cada método
for name, opts in methods.items():
    print(f"\n=== Método: {name} ===")
    iterations[name] = []  # inicializar lista de iteraciones
    
    # Si el método admite bounds, se pasan; de lo contrario se omiten
    extra_args = {}
    if opts['bounds'] is not None:
        extra_args['bounds'] = opts['bounds']
    
    res = minimize(
        lambda x: objetivo(x, gas_type, material, w_beam_mm, w_k_max, v_max, espesor, alpha=0.2, db_lvl=debug_lvl),
        x0=x0,
        method=opts['method'],
        callback=make_callback(name),
        **extra_args
    )
    results[name] = res
    print(f"Resultado final: x = {res.x}\nValor objetivo: {res.fun:.4f}")

# =============================================================================
# GRAFICANDO LA NUBE DE PUNTOS DE LAS ITERACIONES
# =============================================================================
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Colores para cada método
colors = {
    'BFGS': 'r',
    'L-BFGS-B': 'g',
    'SLSQP': 'b',
    'Nelder-Mead': 'c',
    'Powell': 'm'
}

for name, points in iterations.items():
    points = np.array(points)
    if points.size == 0:
        continue
    # Graficar la trayectoria iterativa: eje X=P0, Y=v y Z=Pg
    ax.scatter(points[:, 0], points[:, 1], points[:, 2],
               c=colors[name], label=name, alpha=0.7, marker='o')
    # También se puede conectar los puntos para ver la trayectoria
    ax.plot(points[:, 0], points[:, 1], points[:, 2], c=colors[name], alpha=0.5)

ax.set_xlabel("Potencia (W)")
ax.set_ylabel("Velocidad (mm/s)")
ax.set_zlabel("Presión (kPa)")
ax.set_title("Trayectoria de iteraciones de la optimización")
ax.legend()
plt.show()

# =============================================================================
# Mostrar resultados finales convertidos
# =============================================================================
for name, res in results.items():
    if res.success:
        kerf = kerf_width(res.x[0], res.x[1], w_beam_mm, res.x[2], material, gas_type)
        P0_opt, v_opt, Pg_opt, gas = convertir_unidades(res, gas_type)
        print(f"\n[{name}]")
        print(f"Material: {mat_name}, espesor: {espesor*1000} mm, gas: {gas}")
        print("PARÁMETROS OPTIMIZADOS:")
        print(f"- Potencia láser: {int(P0_opt)} W")
        print(f"- Velocidad de corte: {int(v_opt)} mm/min")
        print(f"- Presión de gas: {Pg_opt} bar")
        print(f"- Valor objetivo: {res.fun:.4f}")
        print(f"- Kerf: {kerf:.6f} mm")
    else:
        print(f"\n[{name}] Error: {res.message}")
