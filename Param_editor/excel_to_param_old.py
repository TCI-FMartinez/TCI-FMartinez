import pandas as pd
from os import getcwd, sep, path, makedirs

from modulos.logthis import LogThis
from modulos.find_files import find_param_dirs, find_params_files, find_glob
from modulos.param_methadata import param_methadata

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
def process_folder(folder=""):
    # Directorio de salida
    output_dir = "parametros_exportados"
    makedirs(output_dir, exist_ok=True)
    #print("    >>>", folder[1])
    full_param_xlsx = path.join(proces_path, folder[1], param_xlsx)
    if not path.exists(path.join(proces_path, folder[1])):
        return False
    find = find_glob(path.join(proces_path, folder[1]))
    #print("    <<<FIND:",find)
    if find[0]:
        if param_xlsx in find[1]:
            print("Encontrado EXCEL")
            # Cargar datos principales y metadata
            df_parametros = pd.read_excel("parametros.xlsx", sheet_name="Hoja1")
            #df_metadata = pd.read_excel(path.join("modulos","methadata.xlsx"))  # Asume columnas: Clave, Estado
            df_metadata = []
            for i in ns_dict.items():
                if i == 'properties':
                    continue
                df_metadata.append((i[0], i[1][0]))

            # Crear diccionario de metadata (Ej: {"N001": "R", "N002": "S"...})
            metadata_dict = {}

            for m in df_metadata:
                metadata_dict[str(m[0])] = m[1]
            #metadata_dict = dict(zip(df_metadata[0], df_metadata[1]))
            print(df_parametros)

            _=input("PAUSA...")

            for _, row in df_parametros.iterrows():
                # Generar nombre de archivo (sin guiones bajos)
                nombre = row["Nombre"].replace(" ", "")
                espesor = f"{row['Espesor']:.2f}".replace(".", "")  # Ej: 1.00 -> 100
                tipo_gas = row["Tipo de gas"].replace(" ", "")
                filename = f"{nombre}{espesor}{tipo_gas}.txt"

                # Escribir archivo
                with open(path.join(output_dir, filename), "w", encoding="utf-8") as f:
                    for col in df_parametros.columns[1:]:  # Excluir N000
                        clave = col
                        estado = metadata_dict.get(clave, "S")  # Default "S" si no hay metadata
                        valor = str(row[col]) if pd.notna(row[col]) else ""
                        f.write(f"{clave}{estado}{valor}\n")

            print("Proceso completado. Archivos generados en:", output_dir)

    return True

####################################################
#--------------------- MAIN -----------------------#

### Busqueda de directorios y archivos  ############

print("="*150)
# Buscamos directorios de parámetros.
factory_folders, user_folders = find_param_dirs(proces_path)

# Procesar todas las carpetas
for folder_param in factory_folders:
    if folder_param[0]:
        result = process_folder(folder=folder_param)

