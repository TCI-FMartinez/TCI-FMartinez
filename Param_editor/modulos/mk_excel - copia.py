#### CREACION DEL EXCEL VACÍO ####
import pandas as pd

def mk_excel(ns_dict, nombre_archivo = "parametros.xlsx"):
    """Crea un excel vacío con las columnas de methadata"""
    if len(ns_dict) < 2:
        return False
    
    # Generar lista de columnas usando el primer elemento de cada tupla.
    # Se omite la clave "properties" ya que es una referencia general.
    columnas = []
    for key in ns_dict:
        if key == "properties":
            continue
        # Si el título de la columna está vacío, se puede usar la clave
        titulo = ns_dict[key][0] if ns_dict[key][0] else key
        columnas.append(titulo)

    # Crear un DataFrame vacío con las columnas definidas
    df = pd.DataFrame(columns=columnas)
    
    # Guardar el DataFrame en un archivo Excel
    #df.to_excel(nombre_archivo, header=True, index=False)

    # Utilizar ExcelWriter con el motor xlsxwriter
    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Hoja1', index=False)

        # Acceder al libro y a la hoja
        workbook  = writer.book
        worksheet = writer.sheets['Hoja1']

        # Crear un formato personalizado (ej. fuente en negrita, color de fondo gris y texto en negro)
        formato_fila = workbook.add_format({
            'bold': True,
            'font_color': 'black',
            'bg_color': "grey"
        })

        # Aplicar el formato a la primera fila (la cabecera)
        # El índice de la fila en Excel es 0 (por ejemplo, la fila 0 es la cabecera creada por to_excel)
        worksheet.set_row(0, None, formato_fila)

    #print(f"Archivo Excel '{nombre_archivo}' creado con las columnas definidas.")

    return True

if __name__ == "__main__":
    from param_methadata import param_methadata
    p_methadata, values_units = param_methadata()

    archivo = "parametros.xlsx"

    if mk_excel(p_methadata, ):
        print(f"Archivo Excel '{archivo}' creado con las columnas definidas.")
