
import sys
import os
from os import listdir, getcwd, path, mkdir
from shutil import rmtree
from re import match, search, findall

cwd_path = getcwd()

def SearchFiles (my_path):

    # Elimina el directorio de salida si existe.
    if path.exists(f"{my_path}\\OUTPUT"):
        rmtree(f"{my_path}\\OUTPUT")

    ficheros = listdir(my_path)
    #print(len(ficheros), ficheros, "TODOS")
    for i in ficheros:
        if not os.path.isfile(i):
            print(i, "no es un fichero")

    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if not os.path.isfile(archivo)]
    #print("a eliminar", indices_a_eliminar)
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)
    
    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.py')]
    #print("a eliminar", indices_a_eliminar)
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)

    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.csv')]
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)

    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.exe')]
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)

    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.spec')]
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)



    n_ficheros = len(ficheros)
    #print(n_ficheros, ficheros, " sin") 

    if n_ficheros < 1:              # por si no hay ficheros.
        print("No hay ficheros")
        sys.exit()
    return n_ficheros, ficheros



print(SearchFiles(cwd_path)[1])