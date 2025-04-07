import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import unidecode

from scipy.stats import linregress
from os import path
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit

from modulos.param_n_list import list_n_param


# Configurar estilo de gráficos

sns.set_palette("husl")
#sns.set_style("whitegrid")
#plt.style.use('seaborn')

def load_and_preprocess_data(file_path):

    ns_dict = list_n_param(dict=True)
    ns_list = [nombre for nombre, _ in ns_dict.values()]
    
    # Cargar datos con nombres de columnas
    df = pd.read_csv(
        file_path,
        delimiter=";",
        header=None,
        names=ns_list,
        encoding="utf-8",
        engine="python",
        on_bad_lines='skip'
    )
    
    # Mapeo de parámetros a códigos N
    param_to_ncode = {
        'material': 'N002',     # Abreviado (material)
        'thickness': 'N004',    # Espesor
        'laser_power': 'N005',  # Laser power
        'feedrate_e01': 'N086', # Feedrate E01
        'focal_calidad1': 'N355', # Focal calidad1
        'feedrate_e02': 'N098', # Feedrate E02
        'focal_calidad2': 'N357', # Focal calidad2
        'gas_pressure': 'N090', # Assist gas pressure E01
        'nozzle_diameter': 'N012' # Diámetro boquilla
    }
        
    # Crear diccionario de índices basado en ns_list
    ncode_indices = {n_code: idx for idx, n_code in enumerate(ns_list)}
    
    # Obtener índices de columnas para cada parámetro
    column_indices = {}
    for param, n_code in param_to_ncode.items():
        try:
            column_indices[param] = ncode_indices[n_code]
        except KeyError:
            raise ValueError(f"Código N no encontrado: {n_code}")
    
    material_map = {
        "aceroinoxidable": "acero_inox",
        "stainlesssteel": "acero_inox",
        "inox": "acero_inox",
        "aisi304": "acero_inox",
        "aisi316": "acero_inox",
        "a-316": "acero_inox",
        "a316": "acero_inox",
        "316": "acero_inox",
        "a304": "acero_inox",
        "304": "acero_inox",
        "a-304": "acero_inox",
        "al-5754": "aluminio",
        "alumimnium": "aluminio",
        "aluminio": "aluminio",
        "cu": "cobre",
        "almg5": "aluminio",
        "almg3": "aluminio",
        "of-cu": "cobre",
        "cooper": "cobre",
        "latón": "laton",
        "aceroalcarbono": "acero_carbono",
        "steel": "acero_carbono",
        "steelalcarbono": "acero_carbono",
        "s235jr": "acero_carbono",
        "s235j0": "acero_carbono",
        "s235jo": "acero_carbono",
        "355": "acero_carbono",
        "s355": "acero_carbono",
        "s235": "acero_carbono",
        "275": "acero_carbono",
        "255": "acero_carbono",
        "dd11": "acero_carbono",
        "hierro": "acero_carbono",
        "bright": "acero_carbono",
        "st37-zinc": "galvanizado",
        "galva": "galvanizado",
        "titanio": "titanio",
        "cuzn37": "laton",
        "brass": "bronce",
        "laton": "laton",
        "cuzn": "laton"
    }

    data = []
    for _, row in df.iterrows():
        try:
            # Extraer y normalizar material
            material_raw = str(row[column_indices['material']]).strip().lower()
            material = material_map.get(material_raw, "desconocido")
            
            # Construir entrada
            entry = {
                'material': material,
                'thickness': float(row[column_indices['thickness']]),
                'laser_power': int(row[column_indices['laser_power']]),
                'feedrate_e01': int(row[column_indices['feedrate_e01']]),
                'focal_calidad1': float(row[column_indices['focal_calidad1']]),
                'feedrate_e02': int(row[column_indices['feedrate_e02']]),
                'focal_calidad2': float(row[column_indices['focal_calidad2']]),
                'gas_pressure': float(row[column_indices['gas_pressure']]),
                'nozzle_diameter': float(row[column_indices['nozzle_diameter']])
            }
            data.append(entry)
        except (IndexError, ValueError, KeyError) as e:
            print(f"Error en fila {_}: {str(e)}")
            continue

    return pd.DataFrame(data), material_map

def analyze_materials(df):
    if df.empty:
        print("No hay datos disponibles para el análisis.")
        return pd.DataFrame()
    
    stats = df.groupby(['material', 'thickness']).agg({
        'laser_power': ['mean', 'median', 'std', 'count'],
        'feedrate_e01': ['mean', 'median', 'std'],
        'gas_pressure': ['mean', 'median']
    }).reset_index()
    
    stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in stats.columns]
    return stats


def plot_trends(df, material):
    material_df = df[df['material'] == material].sort_values('thickness')
    
    if len(material_df) < 3:
        return  # No suficiente data
    
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'Tendencias para {material.capitalize()}', fontsize=16)
    
    # Laser Power vs Thickness
    sns.scatterplot(data=material_df, x='thickness', y='laser_power', ax=axs[0, 0])
    try:
        slope, intercept, r_value, *_ = linregress(material_df['thickness'], material_df['laser_power'])
        axs[0, 0].plot(material_df['thickness'], intercept + slope*material_df['thickness'], 'r--')
        axs[0, 0].set_title(f'Potencia vs Espesor (R²={r_value**2:.2f})')
    except:
        axs[0, 0].set_title('Potencia vs Espesor')
    
    # Feedrate vs Thickness
    sns.scatterplot(data=material_df, x='thickness', y='feedrate_e01', ax=axs[0, 1])
    try:
        slope, intercept, r_value, *_ = linregress(material_df['thickness'], material_df['feedrate_e01'])
        axs[0, 1].plot(material_df['thickness'], intercept + slope*material_df['thickness'], 'r--', min=0)
        axs[0, 1].set_title(f'Avance vs Espesor (R²={r_value**2:.2f})')
    except:
        axs[0, 1].set_title('Avance vs Espesor')
    
    # 3D Surface Plot
    from mpl_toolkits.mplot3d import Axes3D
    ax = fig.add_subplot(223, projection='3d')
    ax.scatter(material_df['thickness'], material_df['laser_power'], material_df['feedrate_e01'])
    ax.set_xlabel('Espesor (mm)')
    ax.set_ylabel('Potencia (W)')
    ax.set_zlabel('Avance (mm/min)')
    ax.set_title('Relación 3D: Espesor-Potencia-Avance')
    
    # Distribución de presiones
    sns.boxplot(data=material_df, x='thickness', y='gas_pressure', ax=axs[1, 1])
    axs[1, 1].set_title('Distribución de Presión de Gas por Espesor')
    
    plt.tight_layout()
    plt.show()

def advanced_analysis(df):
    """Análisis avanzado usando solo SciPy"""
    materials = df['material'].unique()
    
    for material in materials:
        material_data = df[df['material'] == material]
        if len(material_data) < 3:
            continue
            
        thickness = material_data['thickness'].values
        feedrate = material_data['feedrate_e01'].values
        
        # Correlación
        pearson_r, pearson_p = stats.pearsonr(thickness, feedrate)
        print(f"\n{material.capitalize()} - Correlación espesor-avance:")
        print(f"Coeficiente Pearson: {pearson_r:.2f}, p-valor: {pearson_p:.4f}")
        
        # Regresión lineal
        slope, intercept, r_value, p_value, std_err = stats.linregress(thickness, feedrate)
        print(f"Regresión lineal: y = {slope:.2f}x + {intercept:.2f}")
        print(f"R²: {r_value**2:.2f}, Error std: {std_err:.2f}")

def polynomial_regression_scipy(df, material, degree=2):
    """Regresión polinomial con SciPy y visualización de la ecuación ajustada en la esquina inferior izquierda."""
    material_df = df[df['material'] == material].sort_values('thickness')
    
    if len(material_df) < 5:
        print(f"No hay suficientes datos para {material}")
        return
    
    x = material_df['thickness'].values
    y = material_df['feedrate_e01'].values
    
    # Función polinomial general
    def poly_func(x, *coeffs):
        return sum(c * (x**i) for i, c in enumerate(coeffs))
    
    try:
        material_clean = material.replace(" ", "_")
        # Ajuste polinomial
        coeffs, _ = curve_fit(poly_func, x, y, p0=[1]*(degree+1))
        
        # Generar valores para el ajuste
        x_fit = np.linspace(min(x), max(x), 100)
        y_fit = poly_func(x_fit, *coeffs)
        
        # Calcular R² usando linregress (para los datos reales)
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        # Construir la ecuación ajustada, por ejemplo:
        # "y = 2.00 -0.50x^1 +0.10x^2" y R²
        eq_terms = []
        for i, c in enumerate(coeffs):
            if i == 0:
                eq_terms.append(f"{c:.2f}")
            else:
                eq_terms.append(f"{c:+.2f}x^{i}")
        eq_text = "y = " + " ".join(eq_terms) + f"\nR² = {r_value**2:.2f}"
        
        # Crear el gráfico
        plt.figure(figsize=(10, 6))
        plt.scatter(x, y, label='Datos reales')
        plt.plot(x_fit, y_fit, 'r-', label=f'Ajuste polinomial (grado {degree})')
        plt.title(f'{material.capitalize()} - Regresión Polinomial')
        plt.xlabel('Espesor (mm)')
        plt.ylabel('Avance (mm/min)')
        plt.legend(loc='upper right')
        
        # Añadir la ecuación ajustada en la esquina inferior izquierda
        plt.text(0.03, 0.03, eq_text, transform=plt.gca().transAxes,
                 fontsize=10, verticalalignment='bottom',
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
        plt.savefig(path.join("OUTPUT_PLOTS", f"Regresión_{material_clean}"))
        plt.show()
        
    except Exception as e:
        print(f"Error en regresión para {material}: {str(e)}")



def feature_importance_without_rf(df):
    """
    Calcula la importancia de variables (coeficientes estandarizados)
    mediante una regresión lineal múltiple usando NumPy y SciPy,
    descartando variables constantes (con std=0).
    
    Se usan las siguientes columnas:
      - Features: 'thickness', 'laser_power', 'gas_pressure', 'nozzle_diameter'
      - Target: 'feedrate_e01'
    """
    # Definir variables predictoras y la variable objetivo
    features = ['thickness', 'laser_power', 'gas_pressure', 'nozzle_diameter']
    target = 'feedrate_e01'
    
    # Eliminar filas con NaN en las columnas relevantes
    df_clean = df.dropna(subset=features + [target])
    
    if df_clean.shape[0] < 10:
        print("No hay suficientes datos limpios para calcular la importancia de variables.")
        return
    
    # Obtener los valores en formato NumPy
    X = df_clean[features].values  # matriz de features
    y = df_clean[target].values    # vector de la variable objetivo
    
    # Calcular la media y la desviación estándar de cada feature
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    
    # Detectar features con desviación estándar cero
    nonzero_std_mask = X_std != 0
    if not np.all(nonzero_std_mask):
        features_to_drop = [f for f, flag in zip(features, nonzero_std_mask) if not flag]
        print("Advertencia: Las siguientes variables tienen varianza cero y se descartarán:", features_to_drop)
        # Seleccionar solo las columnas con desviación estándar no cero
        X = X[:, nonzero_std_mask]
        X_mean = X_mean[nonzero_std_mask]
        X_std = X_std[nonzero_std_mask]
        # Actualizar la lista de features
        features = [f for f, flag in zip(features, nonzero_std_mask) if flag]
    
    # Estandarizar X y y
    X_stdized = (X - X_mean) / X_std
    y_mean = y.mean()
    y_std = y.std()
    y_stdized = (y - y_mean) / y_std
    
    # Agregar columna de unos (intercepto) a la matriz de diseño
    ones = np.ones((X_stdized.shape[0], 1))
    X_design = np.hstack([ones, X_stdized])
    
    # Resolver la regresión lineal con mínimos cuadrados
    coeffs, residuals, rank, s = np.linalg.lstsq(X_design, y_stdized, rcond=None)
    # coeffs[0] corresponde al intercepto; los coeficientes estandarizados son el resto
    standardized_betas = coeffs[1:]
    
    # Asignar la importancia a cada feature
    importance = {feat: beta for feat, beta in zip(features, standardized_betas)}
    
    print("Importancia de variables (coeficientes estandarizados):")
    for feat, imp in importance.items():
        print(f"{feat}: {imp:.3f}")
    
    return importance


def main():
    grado = 3   # Polinomio de regresión

    # Cargar y preprocesar datos
    df, material_map = load_and_preprocess_data(path.join('OUTPUT', 'resultado_global.csv'))
    if df.empty:
        print("\nSin datos que procesar!")
        return
    

    #VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
    # Análisis de materiales desconocidos

    desconocidos = df[df['material'] == 'desconocido']
    if not desconocidos.empty:
        print("\nMateriales desconocidos detectados:")
        print(desconocidos[['material_original', 'thickness']].groupby('material_original').count())
    exit(0)
    #AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    # Análisis estadístico
    stats = analyze_materials(df)
    print("Estadísticas principales:")
    print(stats.head(10))
    
    # Generar gráficos por material
    #for material in df['material'].unique():
    #    print(f"\nAnalizando: {material.upper()}")
    #    plot_trends(df, material)
    #    
    #    # Mostrar correlaciones
    #    material_df = df[df['material'] == material]
    #    corr_matrix = material_df[['thickness', 'laser_power', 'feedrate_e01']].corr()
    #    plt.figure(figsize=(8, 6))
    #    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm')
    #    plt.title(f'Matriz de Correlación - {material.capitalize()}')
    #    plt.show()

    # Análisis avanzado con SciPy
    advanced_analysis(df)
    
    # Regresión polinomial para cada material
    print("\n\nANÁLISIS DE REGRESIÓN POLINOMIAL:")
    for material in df['material'].unique():
        polynomial_regression_scipy(df, material, degree=grado)
    
    # Importancia de variables basada en correlación
    feature_importance_without_rf(df)
    
    # Análisis comparativo final
    plt.figure(figsize=(14, 8))
    
    # Gráfico comparativo de velocidades
    plt.subplot(2, 1, 1)
    sns.boxplot(data=df, x='material', y='feedrate_e01', showfliers=False)
    plt.title('Distribución de Velocidades de Corte por Material')
    plt.xlabel('Material')
    plt.ylabel('Avance (mm/min)')
    plt.xticks(rotation=45)
    
    # Gráfico comparativo de potencias
    plt.subplot(2, 1, 2)
    sns.lineplot(data=df, x='thickness', y='laser_power', 
                 hue='material', estimator='median', err_style='band')
    plt.title('Relación Espesor-Potencia por Material')
    plt.xlabel('Espesor (mm)')
    plt.ylabel('Potencia Láser (W)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(path.join('OUTPUT_PLOTS','analisis_corte_laser.png'))
    plt.show()

    # Exportación de resultados
    stats.to_csv(path.join('OUTPUT_STAT','analisis_corte_laser.csv'), index=False)
    print("\nResultados exportados a 'analisis_corte_laser.csv'")

if __name__ == "__main__":
    main()