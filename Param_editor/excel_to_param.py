#pyinstaller --distpath DISTRO2 --collect-data palettable --onefile -n EXCELtoPARAM excel_to_param.py

import pandas as pd
from os import getcwd, sep, path, makedirs

from modulos.logthis import LogThis
from modulos.find_files import find_param_dirs, find_params_files, find_glob
from modulos.param_methadata import param_methadata

####################################################
#------------------ Cabecera ----------------------#
cod = "0002"
ver = "1.3"
author:str.encode = "F. Martínez"
prog_code = "EXCEL-param"

cabecera = f"EXCEL to param'  versión: {ver}  autor: {author}"
print(cabecera)
LogThis(cod, "INFO:", cabecera)

####################################################
#------------------ Inicializa --------------------#

result, ns_dict, values_units = param_methadata()
metha_propeties = ns_dict["properties"]

param_xlsx = "parametros.xlsx"
proces_path = "para_procesar"
output_folder = "OUTPUT"
output_xlsx = path.join(output_folder, param_xlsx)
cwd_path = getcwd()                     # Ruta del script principal

use_user_folder = False


####################################################
#------------------- FUNCIONES --------------------#

def normalice_materials(original: str) -> str:
    """
    Normaliza nombres de materiales según un diccionario de equivalencias.
    
    Args:
        original (str): Nombre del material a normalizar.
        
    Returns:
        str: Nombre estandarizado en mayúsculas o el original en mayúsculas si no hay coincidencia.
    """
    # Limpieza y estandarización de la entrada
    original = original.lower()
    
    # Diccionario de equivalencias (claves en minúsculas)
    material_map = {
        "steel": "MILD STEEL",
        "steel al carbono": "MILD STEEL",
        "esteel al carbono-mix": "MILD STEEL",
        "steel al carbono mix": "MILD STEEL",
        "acero al carbono": "MILD STEEL",
        "acero": "MILD STEEL",
        "hierro": "MILD STEEL",
        "galva": "GALVA",
        "galvanizado": "GALVA",
        "galvanized": "GALVA",
        "inox": "STAINLESS STEEL",
        "stainless": "STAINLESS STEEL",
        "aluminio": "ALUMINIUM",
        "aluminum": "ALUMINIUM"
    }
    
    # Buscar coincidencia o retornar el original en mayúsculas
    
    return material_map.get(original, original.upper())

def process_folder(folder=""):
    output_dir = "parametros_exportados"
    makedirs(output_dir, exist_ok=True)
    
    folder_path = path.join(proces_path, folder[1])
    if not path.exists(folder_path):
        print(f"Error: Carpeta {folder_path} no existe.")
        return False
    
    # Buscar archivo parametros.xlsx dentro de la carpeta
    find = find_glob(folder_path)
    if not find[0] or param_xlsx not in find[1]:
        print(f"    No se encontró {param_xlsx} en {folder_path}")
        return False
    
    print(f"Procesando: {folder_path}")
    full_param_xlsx = path.join(folder_path, param_xlsx)
    
    try:
        # Cargar datos del Excel
        df_parametros = pd.read_excel(full_param_xlsx, sheet_name="Hoja1")
    except Exception as e:
        print(f"Error al leer {full_param_xlsx}: {e}")
        return False
    
    # Construir metadata_dict desde ns_dict
    metadata_dict = {
        key: values[0] for key, values in ns_dict.items() 
        if key != "properties" and isinstance(values, tuple) and len(values) > 0
    }
    
    # Validar columnas obligatorias
    required_columns = [
        "N000",  # Ruta
        "N001",  # Nombre
        "N002",  # Abreviado
        "N003",  # DIN
        "N004",  # Espesor
        "N005",  # Potencia fuente láser
        "N006",  # Longitud focal
        "N026",  # Texto1
        "N037"   #Tipo de gas
    ]

    
    missing_columns = [col for col in required_columns if col not in df_parametros.columns]
    if missing_columns:
        print(f"Columnas faltantes: {missing_columns}")
        return False
    
    # Procesar TODAS las columnas del Excel
    all_columns = [col for col in df_parametros.columns if col != "N000"]  # Excluir columna de ruta
    
    for _, row in df_parametros.iterrows():
        if row["N000"] == "Ruta":
            continue
        # Generar nombre del archivo
        _ruta = str(row["N000"]) if pd.notna(row["N000"]) else ""
        _nombre = str(row["N001"]) if pd.notna(row["N001"]) else "SinNombre"
        _espesor = f"{row['N004']}".replace(".", ",") if pd.notna(row['N004']) else "00"
        _potencia = f"{row['N005']}".replace(".", "") if pd.notna(row['N005']) else "0000"
        _texto1 = f"{row['N026']}".replace(".", "") if pd.notna(row['N026']) else ""
        if len(_texto1) > 0: _texto1 = f"-{_texto1}"
        _tipo_de_gas = str(row["N037"]).strip() if pd.notna(row["N037"]) else "SinGAS"
        
        _nombre = normalice_materials(_nombre)

        filename = f"{_nombre}-{_tipo_de_gas}-{_espesor}-{_potencia}W{_texto1}.lparam"
        filename_folder = path.join(_ruta,f"{_nombre}_{_tipo_de_gas}")
        if not path.exists(path.join(output_dir, filename_folder)):
            makedirs(path.join(output_dir, filename_folder), exist_ok=True)

        with open(path.join(output_dir, filename_folder, filename), "w", encoding="utf-8") as f:
            for col in all_columns:  # Iterar sobre todas las columnas
                clave = col
                estado = metadata_dict.get(clave, "S")  # Default "S"
                valor = str(row[col]).strip() if pd.notna(row[col]) else ""
                f.write(f"{clave}{estado}{valor}\n")

    print(f"Archivos generados en: {output_dir}")
    return True

####################################################
#--------------------- MAIN -----------------------#

print("=" * 100)
factory_folders, user_folders = find_param_dirs(proces_path)

# Procesar carpetas de fábrica
for folder_param in factory_folders:
    if folder_param[0]:
        process_folder(folder=folder_param)