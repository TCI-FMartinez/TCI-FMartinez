#### EDITOR DE PARÁMETROS ####


from os import getcwd, sep, path, mkdir

from modulos.find_files import find_param_dirs, find_params_files
from modulos.logthis import LogThis
from modulos.param_methadata import param_methadata

####################################################
#------------------ Cabecera ----------------------#
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

