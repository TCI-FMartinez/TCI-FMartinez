### LOGGING ###

# https://docs.python.org/es/3/library/filesys.html
# https://recursospython.com/guias-y-manuales/os-shutil-archivos-carpetas/

#from timestamp import timestamp, ahora_fecha
from modulos.timestamp import timestamp, ahora_fecha
from os import mkdir, close
import os.path as path



file_l = f"log_{ahora_fecha}.log"
path_l = "LOG\\"

print(f"{path_l}{file_l}")

def log_this(mess_code: str,is_input: str, mess_str: str, value: str):

    new_line = f"{timestamp} {is_input} [{mess_code}] = {mess_str} {value}\n"
    #print (new_line)

    if not path.exists(path_l):    
        mkdir(path_l)

    if path.exists(f"{path_l}{file_l}"):
        #print("="*50)
        exist_log = True
        #print(f"<--Encontrado {file_l}")

    else:
        #print(f"-->ruta type:{type(path_l)} rutatype:{type(file_l)}")
        #open(f"{path_l}{file_l}", 'w')
        #close(f"{path_l}{file_l}")
        exist_log = False
        #print("<--no existe el fichero log")

    with open(f"{path_l}{file_l}", 'a', newline="") as archivo_log:
        archivo_log.write(new_line)  



    return exist_log

#x = log_this("error 404", "-->", "mensage", "8765" )



