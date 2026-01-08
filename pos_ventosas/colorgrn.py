#

# https://gradients.app/es/newcolorpalette/f18ed9-ff939e-ffb270-d7d66e-8ef1a6/

import random

def hsl_to_rgb(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    r, g, b = 0, 0, 0

    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    elif 300 <= h < 360:
        r, g, b = c, 0, x

    r = (r + m) * 255
    g = (g + m) * 255
    b = (b + m) * 255

    return int(r), int(g), int(b)

def rgb_to_hex(r, g, b):
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

def generar_paleta_proxima_hex(tono_inicial, num_colores, proximidad=3, aleatorio=False):
    """
    Genera una paleta de colores basados en un tono inicial en la rueda de color HSL.

    :param tono_inicial: El primer color en grados (Hue), entre 0 y 360.
    :param num_colores: Número de colores a generar.
    :param proximidad: Separación entre colores en grados (entre 0 y 360).
    :param aleatorio: Si True, los colores se organizarán de forma aleatoria.
    """
    colores_hex = []
    for i in range(num_colores):
        hue = (tono_inicial + i * proximidad) % 360  # Colores próximos
        r, g, b = hsl_to_rgb(hue, 1, 0.5)  # Saturación 1 y Luminosidad 0.5
        color_hex = rgb_to_hex(r, g, b)
        colores_hex.append(color_hex)

    # Si se elige aleatorio, reorganizar la lista
    if aleatorio:
        random.shuffle(colores_hex)

    return colores_hex

# Ejemplo de uso:
tono_inicial = 159  # Color inicial en HSL (verde)
num_colores = 50     # Número de colores a generar
proximidad = 3     # Separación entre colores en grados
aleatorio = True    # Organizar la lista de colores de forma aleatoria

paleta = generar_paleta_proxima_hex(tono_inicial, num_colores, proximidad, aleatorio)

print(paleta)
