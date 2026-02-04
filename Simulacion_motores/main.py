import json
import ezdxf
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from ezdxf.math import Vec2 
from scipy.spatial import KDTree

class GantrySimulator:
    def __init__(self, json_path, dxf_path):
        with open(json_path, 'r') as f:
            self.params = json.load(f)
        
        self.doc = ezdxf.readfile(dxf_path)
        self.msp = self.doc.modelspace()
        self.pinion_radius = self.params['pinion_diameter_m'] / 2

    def load_movements(self):
        cutting_entities = [e for e in self.msp if e.dxftype() in ['LINE', 'CIRCLE', 'LWPOLYLINE', 'ARC']]
        sorted_entities = self._sort_entities_by_distance(cutting_entities)
        
        movements = []
        previous_end = None
        
        for entity in sorted_entities:
            start, end = self._get_entity_points(entity)
            if previous_end is not None:
                movements.append(('RAPID', previous_end, start))
            movements.append(('CUT', start, end))
            previous_end = end
        
        return movements

    def _sort_entities_by_distance(self, entities):
        if not entities:
            return []

        # Crear un árbol k-d con los puntos iniciales
        points = [self._get_entity_points(e)[0] for e in entities]
        kd_tree = KDTree(points)

        sorted_entities = [entities[0]]
        remaining_indices = list(range(1, len(entities)))

        while remaining_indices:
            last_point = self._get_entity_points(sorted_entities[-1])[1]
            _, nearest_idx = kd_tree.query(last_point, k=1, distance_upper_bound=np.inf)
            if nearest_idx in remaining_indices:
                sorted_entities.append(entities[nearest_idx])
                remaining_indices.remove(nearest_idx)
            else:
                break  # No hay más vecinos cercanos
        # meto esto para no ordenar
        sorted_entities = entities
        return sorted_entities

    def _get_entity_points(self, entity):
        if entity.dxftype() == 'LINE':
            start = np.array([entity.dxf.start.x, entity.dxf.start.y])
            end = np.array([entity.dxf.end.x, entity.dxf.end.y])
        elif entity.dxftype() == 'CIRCLE':
            center = Vec2(entity.dxf.center.x, entity.dxf.center.y)
            start = center + Vec2(entity.dxf.radius, 0)
            end = start.copy()
        elif entity.dxftype() == 'LWPOLYLINE':
            points = entity.get_points()
            start = np.array([points[0][0], points[0][1]])
            end = np.array([points[-1][0], points[-1][1]]) if not entity.closed else start
        elif entity.dxftype() == 'ARC':
            center = Vec2(entity.dxf.center.x, entity.dxf.center.y)
            radius = entity.dxf.radius
            start_point = center + Vec2.from_deg_angle(entity.dxf.start_angle) * radius
            end_point = center + Vec2.from_deg_angle(entity.dxf.end_angle) * radius
            start = np.array([start_point.x, start_point.y])
            end = np.array([end_point.x, end_point.y])
        else:
            raise ValueError(f"Entidad no soportada: {entity.dxftype()}")
        
        # Convertir metros a milímetros
        #start *= 1000  
        #end *= 1000
        
        return start, end

    def sigmoid_velocity_profile(self, distance, move_type):
        """Perfil de velocidad suavizado (curva S) para minimizar jerk."""
        # Parámetros de movimiento
        if move_type == 'CUT':
            v_max = self.params['cutting_speed_mps']
        else:
            v_max = self.params['rapid_speed_mps']

        a_max = self.params['sim_acceleration_mps2']
        j_max = self.params['max_jerk_mps3']

        # Tiempos característicos
        t_accel = v_max / a_max  # Tiempo para alcanzar aceleración máxima
        t_jerk = a_max / j_max   # Tiempo de transición de jerk

        # Cálculo de tiempo total (integral de la curva de aceleración)
        t_total = 2 * (t_accel + t_jerk)

        # Generar curva de velocidad
        time = np.linspace(0, t_total, 500)
        speed = v_max * (0.5 + 0.5 * np.tanh( (time - t_total/2) / (t_total/8) ))

        # Ajustar distancia recorrida
        current_distance = np.trapz(speed, time)
        scaling_factor = distance / current_distance
        speed *= scaling_factor

        return time, speed

    def trapezoidal_profile(self, distance, move_type):
        # Parámetros de velocidad según tipo de movimiento
        if move_type == 'CUT':
            max_speed = self.params['cutting_speed_mps']
        else:
            max_speed = self.params['rapid_speed_mps']

        acceleration = self.params['sim_acceleration_mps2']

        # Tiempo para alcanzar velocidad máxima
        t_accel = max_speed / acceleration
        dist_accel = 0.5 * acceleration * t_accel**2

        # Determinar perfil (triangular o trapezoidal)
        if 2 * dist_accel > distance:
            # Perfil triangular (no alcanza velocidad máxima)
            t_accel = np.sqrt(distance / acceleration)
            t_total = 2 * t_accel
            num_points = 200
            time = np.linspace(1e-9, t_total, num_points)  # Evitar t=0
            speed = np.concatenate([
                acceleration * time[:num_points//2], 
                acceleration * t_accel - acceleration * (time[num_points//2:] - t_accel)
            ])
        else:
            # Perfil trapezoidal
            t_const = (distance - 2 * dist_accel) / max_speed
            t_total = 2 * t_accel + t_const
            num_points = 200
            time = np.linspace(1e-9, t_total, num_points)
            speed = np.piecewise(time,
                [time < t_accel, (time >= t_accel) & (time < t_accel + t_const), time >= t_accel + t_const],
                [lambda t: acceleration * t, max_speed, lambda t: max_speed - acceleration * (t - (t_accel + t_const))]
            )

        return time, speed

    def calculate_required_torque(self, acceleration):
        force = self.params['mass_kg'] * acceleration + self.params['mass_kg'] * 9.81 * 0.15
        # Como es un gantry, reparto entre dos al 70%
        force = force * 0.7
        torque_linear = force * self.pinion_radius
        torque_motor = torque_linear / (self.params['reducer_ratio'] * 0.95)
        torque_inertia = (self.params['motor_inertia_kgm2'] + self.params['reducer_inertia_kgm2']) * acceleration / self.pinion_radius
        total_torque = torque_motor + torque_inertia    # Creo que es irrelevante.
        
        if total_torque > self.params['max_reducer_radial_torque_nm']:
            raise RuntimeError(f"¡Error! Torque {total_torque:.2f} Nm excede el límite del reductor.")
        
        return total_torque

    def simulate_axis(self, axis_movements):
        time_total, speed_total, accel_total, torque_total = [], [], [], []
        cumulative_time = 0
        
        for move_type, start, end in axis_movements:
            distance = np.linalg.norm(end - start)
            # time, speed = self.trapezoidal_profile(distance, move_type)      # TRAPEZOIDAL
            time, speed = self.sigmoid_velocity_profile(distance, move_type)   # BELL-SHAPE
            # Manejar NaN/Inf en velocidad
            #speed = np.nan_to_num(speed, nan=0.0, posinf=0.0, neginf=0.0)
            speed = np.nan_to_num(speed, nan=0.0, posinf=0.0)
            #acceleration = np.gradient(speed, time)
            # Calcular diferencias de tiempo y evitar división por cero
            dt = np.diff(time)
            dt = np.where(dt == 0, 1e-9, dt)  # Reemplaza ceros por 1e-9 (1 ns)
            #acceleration = np.gradient(speed, edge_order=2) / np.append(dt, dt[-1])
            acceleration = np.gradient(speed, time, edge_order=2)

            torque = [self.calculate_required_torque(a) for a in acceleration]
            
            time_total.extend(time + cumulative_time)
            speed_total.extend(speed)
            accel_total.extend(acceleration)
            torque_total.extend(torque)
            cumulative_time = time_total[-1]

        total_time = time_total[-1]  # Tiempo total de simulación
        print(f"Tiempo total de simulación: {total_time:.2f} segundos")

        return (np.array(time_total), 
                np.array(speed_total), 
                np.array(accel_total), 
                np.array(torque_total))

    def print_summary_stats(self, time, speed, acceleration, torque):
        """Imprime estadísticas clave de la simulación."""
        print("\n=== RESUMEN DE SIMULACIÓN ===")
        print(f"Torque máximo: {np.max(torque):.2f} Nm")
        print(f"Velocidad máxima: {np.max(speed):.2f} m/s")
        print(f"Distancia total: {self._calculate_total_distance():.2f} m")
        print(f"Tiempo total: {time[-1]:.2f} s\n")

    def _calculate_total_distance(self):
        """Calcula la distancia total recorrida en todos los movimientos."""
        total = 0.0
        for entity in self.msp:
            if entity.dxftype() in ['LINE', 'LWPOLYLINE', 'ARC', 'CIRCLE']:
                start, end = self._get_entity_points(entity)
                total += np.linalg.norm(end - start)
        return total
    

    def plot_results(self, time, speed, acceleration, torque):
        fig, axs = plt.subplots(3, 1, figsize=(12, 8))
         # Añadir texto con los valores clave
        stats_text = (
            f"Torque máx: {np.max(torque):.2f} Nm\n"
            f"Velocidad máx: {np.max(speed):.2f} m/s\n"
            f"Aceleración máx: {np.max(acceleration):.2f} m/s²"
        )

        # Modificar las gráficas para incluir los datos
        
        for ax in axs[:1]:
            ax.text(0.98, 0.85, stats_text, 
                    transform=ax.transAxes, ha='right', va='top',
                    bbox=dict(facecolor='white', alpha=0.7))

        # Gráfica de Velocidad
        axs[0].plot(time, speed, label='Velocidad', color='blue')
        axs[0].set_ylabel('Velocidad (m/s)', fontsize=10)
        axs[0].set_title('Perfil de Velocidad vs Tiempo', fontsize=12)
        axs[0].grid(True)

        # Gráfica de Aceleración
        axs[1].plot(time, acceleration, label='Aceleración', color='orange')
        axs[1].set_ylabel('Aceleración (m/s²)', fontsize=10)
        axs[1].set_title('Perfil de Aceleración vs Tiempo', fontsize=12)
        axs[1].grid(True)

        # Gráfica de Torque
        axs[2].plot(time, torque, label='Torque', color='red')
        axs[2].axhline(self.params['motor_torque_nominal_nm'], color='k', linestyle='--', label='Nominal')
        axs[2].axhline(self.params['motor_torque_peak_nm'], color='r', linestyle='--', label='Pico')
        axs[2].set_xlabel('Tiempo (s)', fontsize=10)
        axs[2].set_ylabel('Torque (Nm)', fontsize=10)
        axs[2].set_title('Torque Requerido vs Tiempo', fontsize=12)
        axs[2].legend(loc='upper right')
        axs[2].grid(True)

        plt.tight_layout()
        plt.show()

    def _draw_entity(self, entity):
        """Dibuja la geometría original del DXF."""
        if entity.dxftype() == 'LINE':
            plt.plot([entity.dxf.start.x, entity.dxf.end.x],
                     [entity.dxf.start.y, entity.dxf.end.y], 
                     'blue', alpha=0.9)
        elif entity.dxftype() == 'CIRCLE':
            circle = plt.Circle(
                (entity.dxf.center.x, entity.dxf.center.y),
                entity.dxf.radius,
                fill=False, color='blue', alpha=0.9
            )
            plt.gca().add_patch(circle)

    def _draw_move(self, move):
        """Dibuja un movimiento específico."""
        move_type, start, end = move
        color = 'black' if move_type == 'CUT' else 'red'
        plt.plot([start[0], end[0]], [start[1], end[1]], 
                 color=color, linewidth=2.5, marker='o', markersize=6)

    def plot_movements(self, movements):
        """Dibuja movimientos de corte (negro) y vacío (rojo) en una gráfica estática."""
        plt.figure(figsize=(10, 8))

        # Dibujar geometría original del DXF
        for entity in self.msp:
            self._draw_entity(entity)

        # Dibujar trayectorias de movimiento
        for move in movements:
            self._draw_move(move)

        # Extraer todos los puntos y dibujar segmentos
        for move in movements:
            move_type, start, end = move
            color = 'black' if move_type == 'CUT' else 'red'
            plt.plot([start[0], end[0]], [start[1], end[1]], 
                     color=color, linewidth=1.5, marker='o', markersize=4)

        # Configurar la gráfica
        all_x = [coord for move in movements for point in [move[1], move[2]] for coord in [point[0]]]
        all_y = [coord for move in movements for point in [move[1], move[2]] for coord in [point[1]]]

        plt.xlim(min(all_x)-10, max(all_x)+10)
        plt.ylim(min(all_y)-10, max(all_y)+10)
        plt.xlabel('Posición X (mm)')
        plt.ylabel('Posición Y (mm)')
        plt.title('Trayectorias de Corte y Movimientos en Vacío')
        plt.grid(True, linestyle='--', alpha=0.7)

        # Crear leyenda personalizada
        legend_elements = [
            plt.Line2D([0], [0], color='black', lw=2, label='Corte'),
            plt.Line2D([0], [0], color='red', lw=2, label='Vacío')
        ]
        plt.legend(handles=legend_elements)

        plt.gca().set_aspect('equal', adjustable='box')
        plt.show()



if __name__ == "__main__":
    simulator = GantrySimulator('machine_params.json', 'cutting_sample.dxf')
    movements = simulator.load_movements()
    
    if not movements:
        print("¡No se encontraron movimientos en el DXF!")
        exit()
    
    # Simular ejes X e Y (versión corregida)
    time_x, speed_x, accel_x, torque_x = simulator.simulate_axis(
        [(m[0], np.array([m[1][0], 0]), np.array([m[2][0], 0])) for m in movements]
    )
    time_y, speed_y, accel_y, torque_y = simulator.simulate_axis(
        [(m[0], np.array([0, m[1][1]]), np.array([0, m[2][1]])) for m in movements]
    )
       
    # Calcular tiempo total y animar
    time_total = max(time_x[-2], time_y[-2])
    simulator.plot_results(time_x, speed_y, accel_y, torque_y)
    simulator.plot_movements(movements)
