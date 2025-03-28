### COMPILACION

# pyinstaller --distpath DISTRO --collect-data palettable --onefile -n TIDYPARAMTOCSV main.py

### MEJORAS ######
#
##################

### LIBRERIAS ##########################################################################
import csv
from os import getcwd, sep, path, mkdir
from re import match, search, findall


from modulos.find_files import find_param_dirs, find_params_files
from modulos.logthis import LogThis
from modulos.param_n_list import list_n_param

### CABECERA ######################################################################
cod = 0
ver = "0.1"
author:str.encode = "F. Martínez"
prog_c = "LCSV"
cwd_path = getcwd()                     # Ruta del script principal
proces_path = "para_procesar"

cabecera = f"TIDY model to CVS'  versión: {ver}  autor: {author}"
print(cabecera)
print(cwd_path)


### MAIN ##########################################################################

#### FUNCIONES ################################################

##############################################################

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
        LogThis(f"{prog_c}-{str(cod+1).zfill(4)}", "-->", f"Se ha producido un error de excepción\n{my_excep}", f"'{file_name}'" )

    # Crear una lista de listas con los datos en la columna
    datos_columna = [[dato] for dato in contenido_lst]
    #datos_columna2 = datos_columna
    #tabla = list(zip*[datos_columna, datos_columna2])
    #print(len(datos_columna))
    return datos_columna


##############################################################
# Función encontra parámetros de interes
def find_param_line(tabla, origen):
    ns_list = list_n_param()
    new_tabla = [origen]
    for ns in ns_list:
        for e in tabla:
            if e[0].startswith(ns):
                new_tabla.append(e[0][5:])

    return new_tabla

##############################################################
print("="*150)
# Buscamos directorios de parámetros.
factory_folders, user_folders = find_param_dirs(proces_path)


### Ficheros por carpeta de parámetros #######################
# Buscamos fichero por carpeta en los directorios encontrados.
global_table = []  # Aquí se acumularán todas las tablas generadas
for d in factory_folders:
    # d[0] indica si el directorio es válido (según la lógica de find_param_dirs)
    if d[0]:
        print(">>>>>>>>>>>>>>>>", d[1])
        # d[2] es la lista de subdirectorios (carpetas que contienen parámetros)
        for pf in d[2]:
            pf_complt = f"{proces_path}{sep}{d[1]}{sep}{pf}"
            ficheros = find_params_files(pf_complt)
            # Recorremos cada fichero encontrado en la carpeta de parámetros
            for f in ficheros:
                pf_complt_f = f"{pf_complt}{sep}{f}"
                # Abrimos el fichero y extraemos su contenido
                tabla = OpenFile(pf_complt_f)
                # Procesamos la tabla para obtener sólo las líneas de interés,
                # usando como 'origen' el nombre del directorio (d[1])
                tabla = find_param_line(tabla, origen=d[1])
                # Imprimimos la tabla para revisión (opcional)
                # print(tabla)
                # Añadimos la tabla generada a la tabla global
                global_table.append(tabla)

# Al final, global_table contendrá una lista con todas las tablas generadas
#print("\nTabla global con todo lo encontrado:")
#for row in global_table:
#    print(row)

# Nombre del archivo CSV de salida
csv_file = path.join(cwd_path, "OUTPUT", "resultado_global.csv")

# Asegurarse de que el directorio OUTPUT exista
if not path.exists(path.join(cwd_path, "OUTPUT")):
    from os import mkdir
    mkdir(path.join(cwd_path, "OUTPUT"))

# Escribir la tabla global en un archivo CSV con el formato deseado
with open(csv_file, "w", newline='', encoding="utf-8") as f:
    escritor_csv = csv.writer(f, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
    for fila in global_table:
        escritor_csv.writerow(fila)

print("Se ha generado el archivo CSV:", csv_file)


############################################################################################
# Supongamos que global_table es una lista de listas, donde cada fila tiene al menos 4 columnas.
# global_table = [ [...], [...], ... ]
# Los índices que nos interesan son:
#   índice 1: material (ns[1])
#   índice 3: espesor (ns[3])

# Creamos un diccionario para agrupar las filas según (material, espesor)
grupos = {}  # clave: (material, espesor), valor: lista de filas
for fila in global_table:
    # Asegurarse de que la fila tiene al menos 4 elementos
    if len(fila) >= 4:
        material = fila[2]  #fila[1]Nombre fila[]Nombre corto fila[3]DIN
        if material == "A304": material = "A-304"
        if material == "Al5754": material = "Al-5754"
        if material == "AlMg3": material = "Al-5754"
        if material == "AlMg5": material = "Al-5754"
        if material == "ST37ZINC": material = "ST37-ZINC"
        if material == "ZINC": material = "ST37-ZINC"
        if material == "Galva": material = "ST37-ZINC"
        if material == "275": material = "S275JR"
        if material == "235": material = "S235JR"
        if material == "S235": material = "S235JR"
        if material == "355": material = "S355JR"
        if material == "S355": material = "S355JR"
        if material == "S355J2": material = "S355JR"
        if material == "LA": material = "CuZn"
        try:
            # Convertir el valor a float y formatearlo a un decimal
            espesor_val = float(fila[4])
            espesor = f"{espesor_val:.1f}"
        except Exception as ex:
            # En caso de error (por ejemplo, no poder convertir a float), usar el valor original
            espesor = fila[4]

        clave = (material, espesor)
        if clave not in grupos:
            grupos[clave] = []
        grupos[clave].append(fila)

# Definimos la carpeta de salida (se usa la misma carpeta OUTPUT que en el otro CSV)
output_folder = path.join(cwd_path, "OUTPUT")
if not path.exists(output_folder):
    mkdir(output_folder)

# Generamos un CSV para cada grupo.
for clave, filas in grupos.items():
    material, espesor = clave
    # Opcional: limpia el nombre para la generación del archivo (por ejemplo, quitando espacios)
    material_clean = material.replace(" ", "_")
    espesor_clean = str(espesor).replace(" ", "_")
    nombre_archivo = f"{material_clean}_{espesor_clean}.csv"
    ruta_csv = path.join(output_folder, nombre_archivo)
    
    # Escribir el CSV usando el mismo estilo que antes
    with open(ruta_csv, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        for fila in filas:
            writer.writerow(fila)
    
    print(f"Archivo generado: {ruta_csv}")


