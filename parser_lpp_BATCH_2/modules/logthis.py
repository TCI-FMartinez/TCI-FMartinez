
from os import path, mkdir, sep, getcwd
from datetime import datetime

def LogThis(mess_code: str,is_input: str, mess_str: str, value: str):
    """Función para escribir en el log de la aplicación. Crea un nuevo archivo de log cada día, con el formato 'YYYY-MM-DD.log'. Cada entrada de log incluye una marca de tiempo, el código del mensaje, si es una entrada o salida, y el mensaje en sí.
    Args:
        mess_code (str): Código del mensaje, para identificar el tipo de evento o acción.
        is_input (str): Indica si el mensaje es una entrada ('IN'), una salida ('OUT') o error ('ERR').
        mess_str (str): El mensaje descriptivo que se desea registrar.
        value (str): El valor asociado al mensaje, que puede ser cualquier información relevante. O el número de error.
    Returns:
        bool: True si el archivo de log ya existía, False en caso contrario.
    """
    
    ahora = datetime.now()
    cwd_path = getcwd() 
    
    ## variables para el log
    ahora_hora = f"{ahora.hour}:{ahora.minute}:{ahora.second}"
    ahora_fecha = f"{ahora.day}-{ahora.month}-{ahora.year}"
    ahora_filename = f"{ahora.year}-{ahora.month}-{ahora.day}_Sorting-study.log"
    timestamp = str(f"{ahora_fecha} {ahora_hora}")
    new_line = f"{timestamp} {is_input} [{mess_code}] = {mess_str} {value}\n"
    log_route = "LOG"
    #print (new_line)
    
    if path.exists(f"{log_route}{sep}{ahora_filename}"):
        exist_log = True

    else:
        exist_log = False
        #print("<--no existe el fichero log")
        if not path.exists(f"{cwd_path}{sep}LOG"):
            mkdir(f"{cwd_path}{sep}LOG")

    with open(f"{log_route}{sep}{ahora_filename}", 'a', newline="") as archivo_log:
        archivo_log.write(new_line)  

    return exist_log