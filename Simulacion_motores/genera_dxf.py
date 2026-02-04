import ezdxf
from ezdxf.math import Vec2

doc = ezdxf.new()
msp = doc.modelspace()

# Línea simple
msp.add_line((0, 0), (100, 100))

# Círculo (ya usa coordenadas polares implícitas)
msp.add_circle(center=(150, 150), radius=30)

# Polilínea abierta
msp.add_lwpolyline([(200, 200), (300, 200), (300, 300)])

# Arco con definición polar explícita
center = Vec2(600, 600)
radius = 40
start_angle = 0   # Grados (0° = eje X positivo)
end_angle = 270   # Grados (270° = eje Y negativo)

# Crear puntos inicial/final usando coordenadas polares
start_point = center + Vec2.from_deg_angle(start_angle) * radius
end_point = center + Vec2.from_deg_angle(end_angle) * radius

# Añadir arco al DXF
msp.add_arc(
    center=center, 
    radius=radius,
    start_angle=start_angle,
    end_angle=end_angle
)


doc.saveas("cutting_sample.dxf")