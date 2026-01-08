#### EDITOR DE PARÁMETROS ####
<<<<<<< HEAD


from os import getcwd, sep, path, mkdir

from modulos.find_files import find_param_dirs, find_params_files
from modulos.logthis import LogThis
=======
### COMPILACION

# pyinstaller --distpath DISTRO --collect-data palettable --onefile -n PARAMtoEXCEL main.py

from os import getcwd, sep, path, mkdir
from time import sleep
from re import search

from modulos.find_files import find_param_dirs, find_params_files, find_glob
from modulos.logthis import LogThis
from modulos.mk_excel import mk_excel
from modulos.add_excel import add_excel
>>>>>>> 1c10dfd723b18e7ebab8c2ec29ad78c9ad3f9b50
from modulos.param_methadata import param_methadata

####################################################
#------------------ Cabecera ----------------------#
<<<<<<< HEAD
cod = 0
ver = "0.1"
author:str.encode = "F. Martínez"
prog_code = "Param-EXCEL"

cabecera = f"TIDY model to CVS'  versión: {ver}  autor: {author}"
print(cabecera)

####################################################
#------------------ Inicializa --------------------#

p_methadata, values_units = param_methadata()
metha_propeties = p_methadata["properties"]

proces_path = "para_procesar"
output_path = "OUTPUT"
cwd_path = getcwd()                     # Ruta del script principal

=======
cod = "0001"
ver = "1.3"
author:str.encode = "F. Martínez"
prog_code = "Param-EXCEL"

cabecera = f"Param to EXCEL'  versión: {ver}  autor: {author}"
print(cabecera)
LogThis(cod, "INFO:", cabecera)
####################################################
#------------------ Inicializa --------------------#

result, ns_dict, values_units = param_methadata()
metha_propeties = ns_dict["properties"]

param_xlsx = "parametros.xlsx"
proces_path = "para_procesar"
output_folder = "out_temp"
output_xlsx = path.join(output_folder, param_xlsx)
cwd_path = getcwd()                     # Ruta del script principal

use_user_folder = False

####################################################
#--------------------- MAIN -----------------------#

####################################################
# Función encontra parámetros de interes
def find_param_line(tabla, origen):
    """Procesa líneas con formato NxxxRValor"""    
    numeros_de_linea = ns_dict.keys()
    #print("value units:", values_units.keys())
    new_tabla = {"N000": origen}
    if len(tabla) > 0:                            
        for e in tabla:
            value = e[0][5:]
            key = e[0][:4]
            if key == "properties":
                continue
            # Conversión de tipos basada en metadata
            try:
                data_type = ns_dict[key][2]
                if data_type in ["dist", "feedrate", "power", "focal"]:
                    new_tabla[key] = float(value)
                elif data_type == "duty":
                    new_tabla[key] = int(float(value))  # 50.0 -> 50
                else:
                    new_tabla[key] = str(value)
            except Exception as e:
                LogThis("CONVERSION", f"No se pudo convertir {key}={value}: {str(e)}", f"<- se mantiene {value}")
                new_tabla[key] = value  # Mantener valor original

    return new_tabla

def OpenFile (file_name):
    try:
        contenido_lst = list()
        with open(file_name, "r") as text_r_file:       # lectura de archivo LPARAM.
            contenido_lst = list()
            _contenido = text_r_file.readlines()
            for i in _contenido:
                salto = search(r"[\n]$", i)
                a,b = salto.span()
                i = i[:a]
                #print(f".{i}.")
                contenido_lst.append(f"{i}")  
    except Exception as my_excep:
        print("Se ha producido un error de excepción al abrir", f"'{file_name}'")
        print(my_excep)
        LogThis(f"OpenFile", "-->", f"Se ha producido un error de excepción\n{my_excep}", f"'{file_name}'" )

    # Crear una lista de listas con los datos en la columna
    datos_columna = [[dato] for dato in contenido_lst]
    #datos_columna2 = datos_columna
    #tabla = list(zip*[datos_columna, datos_columna2])
    #print(len(datos_columna))
    return datos_columna


####################################################


if not path.exists(output_folder):
    mkdir(output_folder)

if result:
    mk_excel(ns_dict, output_xlsx)
else:
    LogThis(cod, ">>", f"Error al obtener methadata", result)
    print(result, "Error crítico - Saliendo")
    exit(1)



### Busqueda de directorios y archivos  #######################

print("="*150)
# Buscamos directorios de parámetros.
factory_folders, user_folders = find_param_dirs(proces_path)

global_table = []

def process_folder(folder, is_user=False):
    """Procesa una carpeta de parámetros"""
    processed = []
    if folder[0] and (not is_user or use_user_folder):
        print(f"\nProcesando: {folder[1]}")
        print("    folders:", folder[2])
        for subdir in folder[2]:
            # Por cada directorio material en parametros
            full_path = path.join(proces_path, folder[1], subdir)

            for file in find_params_files(full_path):
                #Por cada espesor en el directorio de material
                file_path = path.join(full_path, file)
                lines = OpenFile(file_path)
                params = find_param_line(lines, folder[1])
                
                if params:
                    # Completar campos faltantes
                    for key in ns_dict:
                        if key == "properties":
                            continue
                        if key not in params and key != "properties":
                            params[key] = ""  # Placeholder para celdas vacías
                    
                    processed.append(params)
                    print(f"    >>> {file}: {len(params)} parámetros")
    
    return processed

# Procesar todas las carpetas
for folder_param in factory_folders:
    global_table.extend(process_folder(folder=folder_param))
    if global_table:
        print("        >> nombre del excel:", folder_param[1])
        nombre_archivo=path.join(proces_path, folder_param[1], "parametros.xlsx")
        mk_excel(ns_dict, nombre_archivo)
        success = add_excel(
            global_table,
            nombre_archivo=nombre_archivo,
            expected_columns=[col for col in ns_dict if col != "properties"],  # <-- Filtro
            #units=values_units
        )
        if success:
            print(f"\nDatos exportados: {len(global_table)} registros")
            
        else:
            print("\n Error al escribir en Excel")

if use_user_folder:
    print("El sistema no está preparado para parametros de usuario.")
    exit(1)
    for folder_uparam in user_folders:
        global_table.extend(process_folder(folder_uparam, is_user=True))


# Al final, global_table contendrá una lista con todas las tablas generadas


>>>>>>> 1c10dfd723b18e7ebab8c2ec29ad78c9ad3f9b50
