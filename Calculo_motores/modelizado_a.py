import matplotlib.pyplot as plt
import numpy as np

# Parámetros simulados
t = np.linspace(0, 10, 1000)  # Tiempo de 0 a 10 segundos
velocidad_corte = 0.8  # m/s
velocidad_vacio = 1.5  # m/s
aceleracion = 0.7  # m/s²

# Perfil trapezoidal (simplificado)
velocidad = np.piecewise(t,
    [t < 2, (t >= 2) & (t < 8), t >= 8],
    [lambda t: aceleracion * t, lambda t: velocidad_corte, lambda t: velocidad_corte - aceleracion * (t - 8)]
)

aceleracion_plot = np.piecewise(t,
    [t < 2, (t >= 2) & (t < 8), t >= 8],
    [aceleracion, 0, -aceleracion]
)

# Gráfica
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

ax1.plot(t, velocidad, label='Velocidad (m/s)', color='blue')
ax1.set_title('Perfil de Velocidad (Eje X/Y)')
ax1.set_ylabel('m/s')
ax1.grid(True)

ax2.plot(t, aceleracion_plot, label='Aceleración (m/s²)', color='red')
ax2.set_title('Perfil de Aceleración')
ax2.set_xlabel('Tiempo (s)')
ax2.set_ylabel('m/s²')
ax2.grid(True)

plt.tight_layout()
plt.show()