# https://docs.python.org/es/3/library/string.html
# https://docs.python.org/es/3/library/re.html

### COMPILACION

# C:\Users\user023\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\pyinstaller --distpath DISTRO --collect-data palettable --onefile -n LPARM_to_CSV LPARAMTOCSV.py

### MEJORAS ######
# El uso del dict inicial con el rango de n param
# La elección del parametro para concatenar el nombfre del fichero
# Poner una primera columna de titulos en el CSV y que no se tenga en cuenta al generar los ficheros.
#
##################

### lparam to CSV ###

import csv
import sys
import re
from os import listdir, getcwd, path, mkdir
from shutil import rmtree
from re import match, search, findall
from datetime import datetime


ahora = datetime.now()
ahora_hora = f"{ahora.hour}:{ahora.minute}:{ahora.second}"
ahora_fecha = f"{ahora.day}-{ahora.month}-{ahora.year}"
timestamp = str(f"{ahora_fecha} {ahora_hora}")

cod = 0
ver = "1.4"
author:str.encode = "F. Martínez"
prog_c = "LCSV"
cwd_path = getcwd()

### CABECERA #####################################
cabecera = f"´LPARAM to CVS'  versión: {ver}  autor: {author}"
print(cabecera)


### LOGGING #######################################
file_l = f"log_{ahora_fecha}.log"

def LogThis(mess_code: str,is_input: str, mess_str: str, value: str):
    ## Directorio OUTPUT

    new_line = f"{timestamp} {is_input} [{mess_code}] = {mess_str} {value}\n"
    #print (new_line)

    if path.exists(f"OUTPUT\\{file_l}"):
        exist_log = True

    else:
        exist_log = False
        #print("<--no existe el fichero log")
        if not path.exists(f"{cwd_path}\\OUTPUT"):
            mkdir(f"{cwd_path}\\OUTPUT")

    with open(f"OUTPUT\\{file_l}", 'a', newline="") as archivo_log:
        archivo_log.write(new_line)  

    return exist_log
################################################



##################  FUNCIONES

LogThis(cabecera, "", "", "")
LogThis(("="*70), "", "", "")

## Función de mirar el directorio y listar archivos.
def SearchFiles (my_path):

    ficheros = listdir(my_path)
    #print(len(ficheros), ficheros, "TODOS")

    ficheros = listdir(my_path)
    #print(len(ficheros), ficheros, "TODOS")
    #for i in ficheros:
    #    if not path.isfile(i):
    #        print(i, "no es un fichero")

    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if not path.isfile(archivo)]
    #print("a eliminar", indices_a_eliminar)
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)
    
    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.py')]
    #print("a eliminar", indices_a_eliminar)
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)
    
    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.ini') 
                          or archivo.endswith('.txt')
                           or archivo.endswith('.spec')
                            or archivo.endswith('.exe')
                             or archivo.endswith('.csv')
                              or archivo.endswith('.zip')]
    
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)

    n_ficheros = len(ficheros)
    #print(n_ficheros, ficheros, " sin") 

    if n_ficheros < 1:              # por si no hay ficheros.
        print("No hay ficheros")
        
        sys.exit()
    return n_ficheros, ficheros

## Función para crear un diccionario de parametros inicial.
def NewDict(n):  
    np = 0                      # inicializa un contador para iterar.
    tabla_dict = dict()         # crea el dict en blanco.
    _param_valure = list()
    
    while np < n :
        np += 1
        np_str = f"{str(np).zfill(3)}"              # esto convierte el int en un string de 3 caractéres.
        pr_str = f"N{np_str}R"
        #_param_valure.append(f"N{np_str}R")
        #_param_valure.insert((np-1), f"N{np_str}R")
        _param_valure = [pr_str]                    # Añade un campo a la lista.
        tabla_dict[np_str] = _param_valure         # Añade clave y valor de lista en blanco. #### nO VA!!!
    
    return tabla_dict
    
#print(tabla_dict)

## Función de lectura de fichero de la lista encontrada.
def OpenFile (file_name):
    try:
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


print("-"*70)
#print(SearchFiles(cwd_path)[1].index((SearchFiles(cwd_path)[1][0])))   # debuelve la posición del archivo en la lista.

### Creación del la tabla inicial con n param segun primer archivo.
n_min_params = 1                                            # número mínimo de parametros en el dict.
tabla_dict = NewDict(n_min_params)                          # Se llama a la generación de una nueva tabla inicial
_file = SearchFiles(cwd_path)[1][0]             # Ejecuta función para extrraer ficheros. Quitar el ultimo [0] para el for.

#print(_file)
#_file_n = "x"                           # si no hay for.
columna = OpenFile(_file)                                   # Abre el fichero y debuelve la columna.
last_par = int((columna[-1])[0][1:4])                       # Devuelve el número del último parámetro.
#print("<--- Último parametro:", last_par)          # para logging


# Función para crear un diccionario de parámetros inicial.
def NewDict(n):  
    tabla_dict = dict()
    for np in range(1, n + 1):
        np_str = f"{str(np).zfill(3)}"
        tabla_dict[np_str] = []
    return tabla_dict

LogThis(f"{prog_c}-{str(cod+2).zfill(4)}", "-->", "Número de parámetros:", last_par )
tabla_dict = NewDict(last_par)                              # Anade a la tabla los n keys del primer fichero.
#print(tabla_dict)

# ... (El código anterior se mantiene igual) según ChatGPT 3.5


# Bucle relleno de tabla con todos los ficheros.

# Función rellenar tabla
def FillTable(tabla, columna):
    for i in columna:
        par_n = search(r"[N]+[0-9]{3,}", i[0])
        if par_n:
            key_v = par_n.group()
            key_v = int(key_v[1:])
            if key_v in tabla:
                tabla[key_v].append(i[0])
            else:
                tabla[key_v] = [i[0]]
        else:
            for key, value in tabla.items():
                if key != 0:
                    value.append("")  # Rellenar filas sin parámetro con espacios en blanco
    return tabla

# Función para preguntar entre dos opciones.
def Opcion1 (primera_opc, segunda_opc):
    opcional_1 = input(f"\n{primera_opc}\n{segunda_opc}\nElija una opción :")
    opcional_1 = opcional_1.upper()
    return opcional_1


def generate_files_from_csv(csv_file_path, output_folder, params_indices):
    if not path.exists(output_folder):
        mkdir(output_folder)

    # Leer el archivo CSV
    with open(csv_file_path, "r", newline="", encoding="utf-8") as archivo_csv:
        lector_csv = csv.reader(archivo_csv, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        data = [row for row in lector_csv]

    # Obtener la cantidad de columnas
    num_columns = len(data[0])


    # Crear un diccionario para almacenar los datos de cada columna
    column_data = {i: [] for i in range(1, num_columns + 1)}

    # Llenar el diccionario con los datos de cada columna
    for row in data:
        for col_idx, value in enumerate(row):
            column_data[col_idx + 1].append(value)

    # Crear los archivos con los datos de cada columna
    # Creamos lista con los param ini str a buscar.
    params_ind_str = list()
    for i in params_indices:
        i3 = f"N{str(i).zfill(3)}"
        #print("i3=", i3)
        params_ind_str.append(i3)

    regex_p = re.compile(r"\b(%s)+" % "|".join(re.escape(ini) for ini in params_ind_str))
    #print("regex=", regex_p.pattern)
    

    for col_idx, values in column_data.items():
        name_conc = list()
        name_conc_reord = list()
        # Creamos un nombre para cada columna.
        for i in values:
            # Buscar los parámetros para concatenar el nombre.
            for m in regex_p.finditer(i):
                #print("-->>>",m[0],"->", i[5:])
                i_str = str(i[5:])
                #print("i_str=",type(i_str), i_str)
                name_conc.append(i_str)
        # Reordenamos los parámetros para concatenar.
        name_conc_reord = name_conc[0], name_conc[2], name_conc[4], f"DIN{name_conc[1]}", name_conc[3]
        file_name = "_".join(name_conc_reord)
        #print("file_name=", file_name)

        # Concatenar los cinco primeros parámetros para obtener el nombre del archivo
        #file_name = "_".join(values[:5])
        #file_name = "_".join(value[5:] for value in values[:5]) # Oviando los 5 primeros caracteres.
        #file_name = "_".join(value[5:] for value in (values[i - 1] for i in params_indices)) # Pero eliigiendo qué index.
        file_path = path.join(output_folder, f"{file_name}.lparm")
        print(file_path)
        
        with open(file_path, "w", encoding="utf-8") as file:
            for value in values:
                file.write(f"{value}\n")
            LogThis(f"{prog_c}-{str(cod+9).zfill(4)}", "-->", "Archivo de parámetros creado:\n     ", file_path )

    print(f"Se han generado {col_idx} ficheros en el directorio \\OUTPUT\\")
    LogThis(f"{prog_c}-{str(cod+3).zfill(4)}", "-->", "Ficheros .lparm generados:", col_idx )


################## INSTRUCCIONES

_files = SearchFiles(cwd_path)[1]
_file_n = len(_files)
tabla_llena = dict()

## Directorio OUTPUT
if not path.exists(f"{cwd_path}\\OUTPUT"):
    mkdir(f"{cwd_path}\\OUTPUT")
    LogThis(f"{prog_c}-{str(cod+4).zfill(4)}", "-->", "Se ha creado el directorio:", "\\OUTPUT" )

# Para logging.
print("<---","Archivos encontrados:", _file_n, )
LogThis(f"{prog_c}-{str(cod+5).zfill(4)}", "<---", f"{_file_n} archivos encontrados.", "" )
for i in _files:
    print("   -->",i)
    LogThis(f"{prog_c}-{str(cod+6).zfill(4)}", "   -->", f"{i}", "" )

for i in _files:
    columna = OpenFile(i)
    tabla_llena = FillTable(tabla_llena, columna)

### Seleccionar acción.

print("-"*70)

primera_opc = "Para generar el fichero '\\OUTPUT\\resultado.csv' introducir 'C'."
segunda_opc = "Para generar LPARAM a partir del CSV introducir 'F'."
eleccion = ""

while eleccion != "C" and eleccion != "F":
    eleccion = Opcion1(primera_opc, segunda_opc)

eleccion = str(eleccion)

# Escritura del fichero CSV
if eleccion == "C":
    print("\n")
    print("-"*70)
    print("\nGenerando fichero 'resultado.csv'...\n")
    LogThis(f"{prog_c}-{str(cod+7).zfill(4)}", "", "Opción de generación CSV elegida:", f"'{eleccion}'" )
    with open(f"{cwd_path}\\OUTPUT\\resultado.csv", "w", newline='') as archivo_csv:
        escritor_csv = csv.writer(archivo_csv, delimiter=";", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        for key, value in sorted(tabla_llena.items(), key=lambda x: int(x[0])):
            escritor_csv.writerow(value)

        print("\nSe ha creado el nuevo archivo CSV 'resultado.csv'.")
        LogThis(f"{prog_c}-{str(cod+8).zfill(4)}", "-->", "Se ha creado el nuevo archivo CSV 'resultado.csv'.", "" )

# Creación de fichero LPARAM
if eleccion == "F":
    print("\n")
    print("-"*70)
    print("\nGenerando ficheros '*.lparm'...\n")
    csv_file_path = f"{cwd_path}\\OUTPUT\\resultado.csv"
    output_folder = f"{cwd_path}\\OUTPUT\\"
    params_indices = [1,  3, 4, 26, 37]  # Aquí especificamos los índices de los parámetros que queremos usar
    generate_files_from_csv(csv_file_path, output_folder, params_indices)




################ FINAL
print("-"*70)
salir = ""
while salir != "Y" and salir != "y":
    salir = input("¿Salir de la aplicación?\nIntroduzca Y/N:")

LogThis(f"{prog_c}-{str(cod+900).zfill(4)}", "", "Salir del programa:", f"'{salir}'" )
sys.exit()
