import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from os import path, mkdir

from modulos.param_n_list import list_n_param

# --- Definición de la lista de columnas ---
ns_dict = list_n_param(dict=True)
# Extraer los nombres de las columnas (solo la primera parte de cada tupla)
ns_list = [nombre for nombre, _ in ns_dict.values()]  

#print(ns_list)  # Verificar los nombres de las columnas

# --- Definir qué columnas se esperan numéricas (ajusta según tu CSV) ---
numeric_columns = [
    ns_dict["N004"][0],  # Espesor (por ejemplo, se espera que sea numérico)
    ns_dict["N005"][0],  # Laser power
    ns_dict["N006"][0],  # Longitud focal
    ns_dict["N012"][0],  # Diámetro boquilla
    ns_dict["N086"][0],  # Feedrate E01
    ns_dict["N087"][0],  # Cutting peak power E01
    ns_dict["N088"][0],  # Cutting frequency E01
    ns_dict["N089"][0],  # Cutting duty E01
    ns_dict["N090"][0],  # Assist gas pressure E01
    ns_dict["N098"][0],  # Feedrate E02
    ns_dict["N099"][0],  # Cutting peak power E02
    ns_dict["N100"][0],  # Cutting frequency E02
    ns_dict["N101"][0],  # Cutting duty E02
    ns_dict["N102"][0],  # Assist gas pressure E02
    ns_dict["N355"][0],  # Focal calidad1
    ns_dict["N356"][0],  # Zoom calidad1
    ns_dict["N357"][0]   # Focal calidad2
]
# --- Ruta del CSV y directorio de salida para los gráficos ---
csv_file = path.join("OUTPUT", "resultado_global.csv")   # Ruta al CSV generado previamente
output_folder = "OUTPUT_STAT"
output_plot = "OUTPUT_PLOTS"

if not path.exists(csv_file):
    print("No se ha encontrado el archivo:", csv_file)
    #exit(0)

if not path.exists(output_folder):
    mkdir(output_folder)

if not path.exists(output_plot):
    mkdir(output_plot)

# --- Lectura del CSV ---
# Asumimos que el CSV está delimitado por ";" y que no tiene encabezado.
df = pd.read_csv(csv_file, delimiter=";", header=None, names=ns_list,
                 encoding="utf-8", engine="python", on_bad_lines='skip')

if len(df.columns) < len(ns_list):
    missing_cols = len(ns_list) - len(df.columns)
    for i in range(missing_cols):
        df[df.columns.max() + 1 if df.columns.size > 0 else 0] = np.nan

# Asignamos los nombres de columna usando ns_list. Si el CSV tiene menos columnas,
# Asignamos los nombres de columna usando ns_list
if len(df.columns) >= len(ns_list):
    df.columns = ns_list
else:
    df.columns = ns_list[:len(df.columns)]

print("Resumen del DataFrame:")
print(df.head())

# --- Conversión de columnas numéricas ---
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# --- Resumen estadístico ---


print("\nResumen estadístico de las columnas numéricas:")
resumen = df[numeric_columns].describe().round(2)
print(resumen)
# Guardar el resumen estadístico en un CSV
resumen_csv_path = path.join(output_folder, "resumen_estadistico.csv")
resumen.to_csv(resumen_csv_path, sep=";")
print(f"Resumen estadístico guardado en: {resumen_csv_path}")

# --- Matriz de correlaciones ---
corr_matrix = df[numeric_columns].corr()
print("\nMatriz de correlaciones:")
print(corr_matrix)

# --- Graficar la matriz de correlaciones ---
plt.figure(figsize=(12, 10))
sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Matriz de correlaciones")
heatmap_path = path.join(output_plot, "correlacion.png")
plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
plt.close()
print(f"Heatmap de correlaciones guardado en: {heatmap_path}")
