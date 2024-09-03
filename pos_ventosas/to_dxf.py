###### SOLO PARA GENERAR CIRCULOS DE VENTOSAS EN FORMATO DXF ######

def generar_dxf(pads:list, filename="output.dxf", offset_XY:float=(0, 0)):
    """SOLO PARA GENERAR CIRCULOS DE VENTOSAS EN FORMATO DXF
    """
    with open(filename, 'w') as f:
        f.write("0\nSECTION\n2\nHEADER\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nTABLES\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nBLOCKS\n0\nENDSEC\n")
        f.write("0\nSECTION\n2\nENTITIES\n")

        # Añadir los círculos al archivo DXF
        for p in pads:
            if p.is_active:
                x = p.new_pos[0] + offset_XY[0]
                y = p.new_pos[1] + offset_XY[1]
                radius = p.diameter / 2
                f.write("0\nCIRCLE\n")
                f.write("8\n0\n")  # Layer
                f.write(f"10\n{x}\n")  # X-coordinate
                f.write(f"20\n{y}\n")  # Y-coordinate
                f.write("30\n0.0\n")  # Z-coordinate
                f.write(f"40\n{radius}\n")  # Radius
        
        # Añadir el texto al archivo DXF
        #moveX = 414  # Ejemplo de desplazamiento en X
        #moveY = 225  # Ejemplo de desplazamiento en Y
        #texto1 = f"Desplazamiento X: {moveX} Y: {moveY}"
        #f.write("0\nTEXT\n")
        #f.write("8\n0\n")  # Layer
        #f.write("10\n10\n")  # X-coordinate del texto
        #f.write("20\n10\n")  # Y-coordinate del texto
        #f.write("30\n0.0\n")  # Z-coordinate
        #f.write("40\n5\n")  # Altura del texto
        #f.write(f"1\n{texto1}\n")  # Contenido del texto
        
        f.write("0\nENDSEC\n")
        f.write("0\nSECTION\n2\nOBJECTS\n0\nENDSEC\n")
        f.write("0\nEOF\n")

