import ezdxf
from ezdxf.math import Vec2
import numpy as np
import matplotlib.pyplot as plt

class SimuladorCorte:
    def __init__(self, params):
        self.mass = params["mass_kg"]
        self.reducer_ratio = params["reducer_ratio"]
        self.pinion_diameter = params["pinion_diameter_m"]
        self.motor_torque_nominal = params["motor_torque_nominal_nm"]
        self.motor_torque_peak = params["motor_torque_peak_nm"]
        self.sim_acceleration = params["sim_acceleration_mps2"]
        self.max_jerk = params["max_jerk_mps3"]
        self.cutting_speed = params["cutting_speed_mps"]
        self.rapid_speed = params["rapid_speed_mps"]

    def calcular_movimientos(self, movimientos):
        tiempos = []
        velocidades = []
        aceleraciones = []
        torques = []

        t_actual = 0
        v_actual = 0

        for tipo, distancia in movimientos:
            velocidad_objetivo = self.cutting_speed if tipo == "corte" else self.rapid_speed

            # Fase de aceleración
            t_acel = velocidad_objetivo / self.sim_acceleration
            d_acel = 0.5 * self.sim_acceleration * t_acel ** 2
            if d_acel > distancia / 2:
                t_acel = np.sqrt(2 * distancia / self.sim_acceleration)
                t_total = 2 * t_acel
            else:
                d_constante = distancia - 2 * d_acel
                t_constante = d_constante / velocidad_objetivo
                t_total = 2 * t_acel + t_constante

            t_segmento = np.linspace(0, t_total, 100)
            v_segmento = np.piecewise(t_segmento,
                                      [t_segmento < t_acel,
                                       (t_segmento >= t_acel) & (t_segmento < t_total - t_acel),
                                       t_segmento >= t_total - t_acel],
                                      [lambda t: self.sim_acceleration * t,
                                       velocidad_objetivo,
                                       lambda t: velocidad_objetivo - self.sim_acceleration * (t - (t_total - t_acel))])

            a_segmento = np.gradient(v_segmento, t_segmento)
            torque_segmento = self.mass * a_segmento * (self.pinion_diameter / 2)

            tiempos.extend((t_actual + t) for t in t_segmento.tolist())
            velocidades.extend(v_segmento.tolist())
            aceleraciones.extend(a_segmento.tolist())
            torques.extend(torque_segmento.tolist())

            t_actual += t_total

        return tiempos, velocidades, aceleraciones, torques

    def graficar_movimientos(self, tiempos, velocidades, aceleraciones, torques):
        fig, axs = plt.subplots(3, 1, figsize=(10, 8))

        axs[0].plot(tiempos, velocidades, color="blue")
        axs[0].set_title("Perfil de Velocidad vs Tiempo")
        axs[0].set_ylabel("Velocidad (m/s)")

        axs[1].plot(tiempos, aceleraciones, color="orange")
        axs[1].set_title("Perfil de Aceleración vs Tiempo")
        axs[1].set_ylabel("Aceleración (m/s²)")

        axs[2].plot(tiempos, torques, color="red", label="Torque")
        axs[2].axhline(self.motor_torque_nominal, linestyle="--", color="black", label="Nominal")
        axs[2].axhline(self.motor_torque_peak, linestyle="--", color="red", label="Pico")
        axs[2].set_title("Torque Requerido vs Tiempo")
        axs[2].set_ylabel("Torque (Nm)")
        axs[2].set_xlabel("Tiempo (s)")
        axs[2].legend()

        plt.tight_layout()
        plt.show()

# Leer elementos del DXF y definir movimientos
movimientos = [("vacio", 100), ("corte", 50), ("vacio", 80), ("corte", 40)]

# Definir parámetros
params = {
    "mass_kg": 550,
    "reducer_ratio": 5,
    "pinion_diameter_m": 0.06,
    "motor_torque_nominal_nm": 40,
    "motor_torque_peak_nm": 115,
    "sim_acceleration_mps2": 0.35,
    "max_jerk_mps3": 3.0,
    "cutting_speed_mps": 0.015,
    "rapid_speed_mps": 1.9
}

# Ejecutar simulación
simulador = SimuladorCorte(params)
tiempos, velocidades, aceleraciones, torques = simulador.calcular_movimientos(movimientos)
simulador.graficar_movimientos(tiempos, velocidades, aceleraciones, torques)
