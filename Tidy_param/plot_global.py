import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from os import path, mkdir

from modulos.param_n_list import list_n_param

# -----------------------------
# Definición de la lista de columnas
# -----------------------------
ns_list_dict = list_n_param(dict=True)
ns_list = ns_list_dict.values()


# -----------------------------
# Parámetros de entrada y salida
# -----------------------------
csv_file = path.join("OUTPUT", "resultado_global.csv")   # Ruta al CSV generado previamente
output_folder = "OUTPUT_PLOTS"

if not path.exists(csv_file):
    print("No se ha encontrado el archivo:", csv_file)
    exit(0)

if not path.exists(output_folder):
    mkdir(output_folder)

# -----------------------------
# Lectura del CSV
# -----------------------------
# Suponemos que el CSV está delimitado por ";" y no tiene encabezado.
#df = pd.read_csv(csv_file, delimiter=";", header=None, encoding="utf-8")
# Lee el CSV indicando que no tiene encabezado y asignando la lista de nombres:
df = pd.read_csv(csv_file,
                 delimiter=";",
                 header=None,     # No usar la primera fila como header
                 names=ns_list,   # Forzamos que se usen estos nombres de columnas
                 engine="python") # A veces el motor 'python' es más flexible


# Asignamos los nombres de columna usando ns_list
if len(df.columns) >= len(ns_list):
    df.columns = ns_list
else:
    print("¡Advertencia! El número de columnas del CSV es menor al esperado.")
    df.columns = ns_list[:len(df.columns)]

print("Primeras filas del DataFrame:")
print(df.head())

# -----------------------------
# Conversión a numérico
# -----------------------------
# Definimos una lista de nombres de columnas que se esperan numéricas.
# Puedes ajustar esta lista según tu caso.
numeric_columns = [
    "N004",  # Espesor (aunque originalmente es str, se espera poder convertirlo)
    "N005",  # Laser power
    "N006",  # Longitud focal
    "N012",  # Diámetro boquilla
    "N086",  # Feedrate E01
    "N087",  # Cutting peak power E01
    "N088",  # Cutting frequency E01
    "N089",  # Cutting duty E01
    "N090",  # Assist gas pressure E01
    "N098",  # Feedrate E02
    "N099",  # Cutting peak power E02
    "N100",  # Cutting frequency E02
    "N101",  # Cutting duty E02
    "N102",  # Assist gas pressure E02
    "N355",  # Focal calidad1
    "N356",  # Zoom calidad1
    "N357",  # Focal calidad2
    "N358"   # Zoom calidad2
]

# Convertimos las columnas indicadas a valores numéricos (se asigna NaN si falla)
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# -----------------------------
# Graficación de outliers
# -----------------------------
# Configuramos Seaborn para mejorar la estética de los gráficos.
sns.set_style("whitegrid")

for col in numeric_columns:
    if col in df.columns:
        # Eliminar NaN y comprobar si la columna tiene al menos un dato válido
        datos_validos = df[col].dropna()
        if datos_validos.empty:
            print(f"La columna {col} está vacía o solo contiene NaN; se omite el boxplot.")
            continue
        
        plt.figure(figsize=(8, 6))
        sns.boxplot(y=datos_validos)
        plt.title(f"Boxplot de {col}")
        plt.ylabel("Valor")
        output_path = path.join(output_folder, f"boxplot_{col}.png")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Gráfico guardado: {output_path}")


print("Proceso completado. Revisa la carpeta de salida para ver los gráficos de outliers.")
