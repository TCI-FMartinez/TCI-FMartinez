import matplotlib.pyplot as plt
import numpy as np

def draw_grid(size=10, step=1, major_step=5, central_color='red'):
    fig, ax = plt.subplots(figsize=(12,12))
    ax.set_xlim(-size, size)
    ax.set_ylim(-size, size)
    ax.set_xticks(np.arange(-size, size+step, step))
    ax.set_yticks(np.arange(-size, size+step, step))
    
    # Dibujar las líneas de la cuadrícula con diferentes grosores
    for x in range(-size, size+1, step):
        lw = 1 if x % major_step != 0 else (3 if x % (2*major_step) == 0 else 2)
        color = 'blue' if x != 0 else central_color
        ax.axvline(x, color=color, linewidth=lw)
    
    for y in range(-size, size+1, step):
        lw = 1 if y % major_step != 0 else (3 if y % (2*major_step) == 0 else 2)
        color = 'blue' if y != 0 else central_color
        ax.axhline(y, color=color, linewidth=lw)
    
    plt.grid(False)  # Desactivar la cuadrícula predeterminada
    plt.show()

# Llamar a la función para generar la cuadrícula
draw_grid(size=50, step=1, major_step=5)
