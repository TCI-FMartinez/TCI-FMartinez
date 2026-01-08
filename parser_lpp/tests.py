draw_y_n = ""

print("Piezas encontradas y sus contornos:")
while draw_y_n != "n" and draw_y_n != "y":
    draw_y_n = input("Draw contourns? [y] or [n]: >_")
    draw_y_n = draw_y_n.lower()

print(f"Opción [{draw_y_n}]")