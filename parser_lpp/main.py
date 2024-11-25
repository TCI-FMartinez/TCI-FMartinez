
from os import sep, path, makedirs, _exit, listdir
from shutil import rmtree

from modules.draw_part import draw_contours
from modules.parse_head import parse_gcode_head
from modules.parse_parts import parse_gcode_parts

def read_piece_file(directorio):
    if not path.exists(directorio):
        print("No existe el directorio", directorio)
        return False

    else:
        # Lista todos los elementos en el directorio
        elementos = listdir(directorio)

        # Filtra solo los archivos (excluyendo carpetas)
        archivos = []
        for elemento in elementos:
            # Verifica si el elemento es un archivo
            if path.isfile(path.join(directorio, elemento)) and elemento.endswith('.cnc'):
                archivos.append(elemento)

        n_archivos = len(archivos)

        if n_archivos > 0:
            return archivos
        else:
            print("No hay archivos *.cnc")
            return False
            
###################################################################################
###################################################################################
##########      MAIN

filename = "SKRLJ-INOX-10.cnc"

draw_y_n:str = ""

#### Lectura del archivo

# Verificación de existencia del archivo
if not path.exists(filename):
    print(f"Archivo '{filename}' no encontrado.")
    _exit(0)
else:
    # Lectura del archivo
    with open(filename, "r") as text_r_file:
        gcode_content = text_r_file.read()

    # Dividir el contenido en líneas
    file_lines = gcode_content.splitlines()

# DIRECTORIO DE SALIDA
if not path.exists("OUTPUT"):
    makedirs("OUTPUT")
else:
    print("Borrando el directorio 'OUTPUT'...")
    rmtree("OUTPUT")
    makedirs("OUTPUT")


# Parsear el archivo G-code
pieces_info = parse_gcode_parts(file_lines)
file_head = parse_gcode_head(file_lines)


# Mostrar las valiables de la cabecera.
print("\nCABECERA DIC:")
for l in file_head.items():
    print(f"    {l[0]}: {l[1]}")


# Mostrar el formato:
formato = file_head["FORMAT"]
espesor = float(file_head["THICKNESS"])
print(f"Formato X={formato[0]} y={formato[1]} espesor={espesor}")


# Buscar archivos de piezas.
read_files = read_piece_file("OUTPUT")
if read_files:
    for f in read_files:
        print(f)
else:
    _exit(0)

# Mostrar las piezas encontradas y los contornos sin el numerador, espacios ni punto y coma
print("Piezas encontradas y sus contornos:")
while draw_y_n != "n" and draw_y_n != "y":
    draw_y_n = input("Draw contourns? [y] or [n]: >_")
    draw_y_n = draw_y_n.lower()

if draw_y_n == "y":
    draw_contours(read_files, out_WH= (800,800))  
