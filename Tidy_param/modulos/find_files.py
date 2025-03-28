#### Encontrar ficheros de parametros #####
import glob
from os import listdir, path, sep

def find_glob(ruta=""):
    """
    Obtén la lista de directorios en un directorio.
    
    """
    #ruta_compl = f"para_procesar{sep}{ruta}"
    ruta_compl = ruta
    #print(f"\nBuascando en {ruta_compl}...")
    # Comprobar si existe la ruta completa
    #print(">>>>>>>>>>>>>>>>>",ruta_compl,"\n", listdir(ruta_compl))
    if not path.exists(ruta_compl):
        print(f" >> No encontrada la ruta: {ruta_compl}")
        return False, [], []
    
    # Obtener todos los elementos (ficheros y directorios) de la ruta
    elementos = listdir(ruta_compl)
    
    # Inicializamos las listas
    lista_archivos = []
    lista_directorios = []
    
    # Recorremos cada elemento comprobando si es fichero o directorio
    for elem in elementos:
        full_path = path.join(ruta_compl, elem)
        if path.isfile(full_path):
            lista_archivos.append(elem)
        elif path.isdir(full_path):
            lista_directorios.append(elem)
    
    #print(f"\nLista de ficheros:\n{lista_archivos}")
    #print(f"\nLista de directorios:\n{lista_directorios}")
    
    return True, lista_archivos, lista_directorios

def find_params_files(proces_path=""):
    "Obtiene los nombres de los ficheros en las carpetas de parámetros."
    ficheros = list()

    ficheros = listdir(proces_path)
    #print(len(ficheros), ficheros, "TODOS")
    #print("        >>>> FICHEROS:", ficheros)
    for i in ficheros:
        if not path.isfile(i):
            continue
    # Eliminamos todo lo que no sean archivos de la lista. También quita archivos sin extensión.
    #indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if not path.isfile(archivo)]
    #for indice in sorted(indices_a_eliminar, reverse=True):
    #    fichero_del = ficheros.pop(indice)

    # Eliminamos de la lista los ficheros con estas extensiones
    indices_a_eliminar = [i for i, archivo in enumerate(ficheros) if archivo.endswith('.ini') 
                          or archivo.endswith('.txt')
                           or archivo.endswith('.spec')
                            or archivo.endswith('.exe')
                             or archivo.endswith('.csv')
                              or archivo.endswith('.xls')
                               or archivo.endswith('.xlsx')
                                or archivo.endswith('.zip')]
        
    for indice in sorted(indices_a_eliminar, reverse=True):
        fichero_del = ficheros.pop(indice)

    return ficheros

def find_param_dirs(proces_path=""):
    """Obtiene listado de directorios que contenga 'factory' y 'user'"""

    exist, archivos, directorios = find_glob(proces_path)
    factory_path = ""
    user_path = ""
    hay_parametros_u = False
    hay_parametros_f = False
    factory_exist = False
    factory_directorios_M = list()
    user_directorios_M = list()
    factory_directorios = list()
    user_directorios = list()

    if exist:
        for d in directorios:
            # Verificar si hay subdirectorios en el nivel de `proces_path/d`
            n_exist, _archivos, _directorios = find_glob(f"{proces_path}{sep}{d}")

            # Buscar 'factory' dentro del primer nivel de `d`
            if "factory" in _directorios:
                factory_exist, factory_archivos, factory_directorios = find_glob(f"{proces_path}{sep}{d}{sep}factory")
                if factory_exist and len(factory_directorios) > 0: 
                    #print("\nDIRECTORIOS DE FACTORY:\n", factory_directorios)
                    factory_path = f"{d}{sep}factory"
                    hay_parametros_f = True
                    param = [hay_parametros_f, factory_path, factory_directorios]
                    factory_directorios_M.append(param)

            # Buscar 'user' dentro del mismo nivel de `d`, pero solo si ya encontramos `factory`
            if "user" in _directorios and factory_exist:
                user_exist, user_archivos, user_directorios = find_glob(f"{proces_path}{sep}{d}{sep}user")
                if user_exist and len(user_directorios) > 0:
                    #print("\nDIRECTORIOS DE USER:\n", user_directorios)
                    user_path = f"{d}{sep}user"
                    hay_parametros_u = True
                    param_u = [hay_parametros_u, user_path, user_directorios]
                    user_directorios_M.append(param_u)

            # Si no encontramos `factory` en `d`, buscar en sus subdirectorios `sd`
            if not factory_exist and _directorios:
                for sd in _directorios:
                    sd_exist, sd_archivos, sd_directorios = find_glob(f"{proces_path}{sep}{d}{sep}{sd}")

                    if "factory" in sd_directorios:
                        factory_exist, factory_archivos, factory_directorios = find_glob(f"{proces_path}{sep}{d}{sep}{sd}{sep}factory")
                        if factory_exist and len(factory_directorios) > 0: 
                            #print("\nDIRECTORIOS DE FACTORY:\n", factory_directorios)
                            factory_path = f"{d}{sep}{sd}{sep}factory"
                            hay_parametros_f = True
                            param = [hay_parametros_f, factory_path, factory_directorios]
                            factory_directorios_M.append(param)

                    if "user" in sd_directorios and factory_exist:
                        user_exist, user_archivos, user_directorios = find_glob(f"{proces_path}{sep}{d}{sep}{sd}{sep}user")
                        if user_exist and len(user_directorios) > 0:
                            #print("\nDIRECTORIOS DE USER:\n", user_directorios)
                            user_path = f"{d}{sep}{sd}{sep}user"
                            hay_parametros_u = True
                            param_u = [hay_parametros_u, user_path, user_directorios]
                            factory_directorios_M.append(param_u)

        return factory_directorios_M, user_directorios_M
    else:
        return [], []



########################################################################################################
if __name__ == "__main__":
    proces_path = ""

    exist, archivos, directorios = find_glob()
    print(exist, archivos, directorios)

    factory_folders, user_folders = find_param_dirs(proces_path)

    for d in factory_folders:
        print(d)