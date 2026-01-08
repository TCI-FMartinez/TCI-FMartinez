
from os import path, mkdir, sep, getcwd
from datetime import datetime

def LogThis(mess_code:str="00",is_input:str="", mess_str:str="", value:str=""):
    ahora = datetime.now()
    cwd_path = getcwd() 
    
    ## Directorio LOG
    ahora_hora = f"{ahora.hour}:{ahora.minute}:{ahora.second}"
    ahora_fecha = f"{ahora.day}-{ahora.month}-{ahora.year}"
    timestamp = str(f"{ahora_fecha} {ahora_hora}")
    new_line = f"{timestamp} {is_input} [{mess_code}] = {mess_str} {value}\n"
    #print (new_line)
<<<<<<< HEAD
    file_l = f"log_{ahora_fecha}.log"
=======
    file_l = f"{ahora.year}-{ahora.month}-{ahora.day}.log"
>>>>>>> 1c10dfd723b18e7ebab8c2ec29ad78c9ad3f9b50

    if path.exists(f"LOG{sep}{file_l}"):
        exist_log = True

    else:
        exist_log = False
        #print("<--no existe el fichero log")
        if not path.exists(f"{cwd_path}{sep}LOG"):
            mkdir(f"{cwd_path}{sep}LOG")

    with open(f"LOG{sep}{file_l}", 'a', newline="") as archivo_log:
        archivo_log.write(new_line)  

    return exist_log