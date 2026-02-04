
import ezdxf
from ezdxf.math import Vec2

# Crear documento DXF
doc = ezdxf.new()
msp = doc.modelspace()

# 1. Cuadrado principal de 200x200mm
main_square = msp.add_lwpolyline(
    points=[(0, 0), (200, 0), (200, 200), (0, 200), (0, 0)],
    close=True
)

## 2. Matriz de 5x5 círculos de 10mm de diámetro
#circle_diameter = 10
#circle_radius = circle_diameter/2
#spacing = 40  # Espaciado entre centros de círculos
#
#for x in range(5):
#    for y in range(5):
#        center_x = 20 + x * spacing
#        center_y = 20 + y * spacing
#        msp.add_circle(
#            center=(center_x, center_y),
#            radius=circle_radius
#        )

# 3. Tres cuadrados pequeños de 10mm
small_square_size = 10
small_square_positions = [
    (10, 10),        # Esquina inferior izquierda
    (180, 10),       # Esquina inferior derecha
    (180, 180)       # Esquina superior derecha
]

#for pos in small_square_positions:
#    start = Vec2(pos[0], pos[1])
#    msp.add_lwpolyline(
#        points=[
#            start,
#            start + (small_square_size, 0),
#            start + (small_square_size, small_square_size),
#            start + (0, small_square_size),
#            start
#        ],
#        close=True
#    )

## 4. Cuadrado de 40mm centrado
#big_square_size = 40
#big_square_center = Vec2(100, 100)
#msp.add_lwpolyline(
#    points=[
#        big_square_center + (-20, -20),
#        big_square_center + (20, -20),
#        big_square_center + (20, 20),
#        big_square_center + (-20, 20),
#        big_square_center + (-20, -20)
#    ],
#    close=True
#)

# 5. Círculo de 40mm de diámetro
big_circle_center = Vec2(150, 150)
msp.add_circle(
    center=big_circle_center,
    radius=20
)

# Guardar archivo
doc.saveas("cutting_sample.dxf")