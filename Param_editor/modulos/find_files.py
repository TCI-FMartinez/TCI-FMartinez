#### Encontrar ficheros de parametros #####
import glob
from os import listdir, path, sep
if __name__ == "__main__":
    debu=True
else:
    debu=False

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
    if debu: print("\nELEMENTOS:", elementos)
    # Inicializamos las listas
    lista_archivos = []
    lista_directorios = []
    
    # Recorremos cada elemento comprobando si es fichero o directorio
    for elem in elementos:
        full_path = path.join(ruta_compl, elem)
        if path.isfile(full_path):
            lista_archivos.append(elem)
            if debu: print("\nlista_archivos:", lista_archivos)
        elif path.isdir(full_path):
            lista_directorios.append(elem)
            if debu: print("\nlista_directorios:", lista_directorios)
    
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
    """Obtiene listado de directorios que contengan 'factory' y 'user'"""
    
    exist, archivos, directorios = find_glob(proces_path)
    factory_directorios_M = []
    user_directorios_M = []
    
    if exist:
        if debu: print("\ndirectorios:", directorios)
        
        for d in directorios:
            # Reiniciar variables para cada directorio principal
            factory_exist = False
            hay_parametros_f = False
            hay_parametros_u = False
            factory_path = ""
            user_path = ""
            
            # Buscar en el primer nivel de `d`
            d_path = f"{proces_path}{sep}{d}"
            n_exist, _archivos, _directorios = find_glob(d_path)
            
            # Buscar 'factory' en el primer nivel
            if "factory" in _directorios:
                factory_path_full = f"{d_path}{sep}factory"
                _, _, factory_subdirs = find_glob(factory_path_full)
                if factory_subdirs:
                    factory_directorios_M.append((True, f"{d}{sep}factory", factory_subdirs))
                    factory_exist = True
            
            # Buscar 'user' solo si se encontró 'factory'
            if factory_exist and "user" in _directorios:
                user_path_full = f"{d_path}{sep}user"
                _, _, user_subdirs = find_glob(user_path_full)
                if user_subdirs:
                    user_directorios_M.append((True, f"{d}{sep}user", user_subdirs))
            
            # Si no se encontró 'factory' en el primer nivel, buscar en subdirectorios
            if not factory_exist:
                for sd in _directorios:
                    sd_path = f"{d_path}{sep}{sd}"
                    sd_exist, _, sd_dirs = find_glob(sd_path)
                    
                    if "factory" in sd_dirs:
                        factory_path_full = f"{sd_path}{sep}factory"
                        _, _, factory_subdirs = find_glob(factory_path_full)
                        if factory_subdirs:
                            factory_directorios_M.append((True, f"{d}{sep}{sd}{sep}factory", factory_subdirs))
                            factory_exist = True
                    
                    if factory_exist and "user" in sd_dirs:
                        user_path_full = f"{sd_path}{sep}user"
                        _, _, user_subdirs = find_glob(user_path_full)
                        if user_subdirs:
                            user_directorios_M.append((True, f"{d}{sep}{sd}{sep}user", user_subdirs))
        
        if debu: 
            print("\nDirectorios factory encontrados:", factory_directorios_M)
            print("\nDirectorios user encontrados:", user_directorios_M)
        
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