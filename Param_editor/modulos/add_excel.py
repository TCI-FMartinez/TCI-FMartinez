import pandas as pd
from os import path

def add_excel(lines, nombre_archivo="parametros.xlsx", expected_columns=None):
    """
    Añade filas al Excel.
    
    Si la fila que se añade no tiene algunos campos, se completan con cadena vacía.
    Si el archivo no existe, se crea un DataFrame vacío con las columnas de 'expected_columns'.
    
    Parámetros:
      lines: lista de diccionarios. Cada diccionario representa una fila a agregar.
      nombre_archivo: ruta/nombre del archivo Excel.
      expected_columns: lista con los nombres de las columnas esperadas.
    
    Retorna:
      True si se realizó la operación; False en caso de error.
    """
    
    # Si se proporcionan columnas esperadas, pero no existen aún, se crea el DataFrame con dichas columnas.
    if not path.exists(nombre_archivo):
        if expected_columns is None or len(expected_columns) == 0:
            print(f"El archivo {nombre_archivo} no existe y no se han proporcionado columnas esperadas.")
            return False
        print(f"El archivo {nombre_archivo} no existe. Se creará un nuevo archivo.")
        df = pd.DataFrame(columns=expected_columns)
    else:
        try:
            df = pd.read_excel(nombre_archivo)
            print("Archivo cargado exitosamente.")
        except Exception as e:
            print("Error al cargar el archivo:", e)
            return False
        
        # Si no se han proporcionado columnas esperadas, se toman las que ya tiene el Excel
        if expected_columns is None or len(expected_columns) == 0:
            expected_columns = df.columns.tolist()
    
    # Para cada nueva fila, se asegura que tenga todas las columnas esperadas; si falta alguna, se le asigna cadena vacía.
    for new_line in lines:
        # Se crea una fila completa: se mantienen los valores que existan, y se asigna "" a los campos que falten.
        complete_line = {col: new_line.get(col, "") for col in expected_columns}
        # Se añade la fila al DataFrame.
        df = df.append(complete_line, ignore_index=True)
    
    # Guardar el DataFrame actualizado en el archivo Excel aplicando formato.
    try:
        with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Hoja1', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Hoja1']
            
            # Formato para la cabecera: negrita con fondo azul claro.
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#DCE6F1',
                'border': 1
            })
            worksheet.set_row(0, None, header_format)
        print("Archivo Excel actualizado correctamente.")
    except Exception as e:
        print("Error al escribir el archivo:", e)
        return False

    return True

if __name__ == "__main__":
    # Se asume que 'param_methadata' es una función que retorna (p_methadata, values_units),
    # donde p_methadata es la lista de columnas esperadas.
    try:
        from param_methadata import param_methadata
    except ImportError:
        print("No se encontró el módulo 'param_methadata'. Verifica la ruta o el nombre.")
        exit(1)
        
    p_methadata, values_units = param_methadata()
    
    # Ejemplo de una nueva fila con algunos campos omitidos.
    nueva_fila = {
        "Ruta del parámetro": "ruta/nueva",
        "Nombre": "Ejemplo fila nueva",
        "Abreviado": "EX",
        "DIN": "5678",
        # Faltan campos como "Espesor", "Laser power", etc. que se completarán en blanco.
    }
    
    # La lista de líneas a agregar.
    lineas = [nueva_fila]
    
    archivo = "parametros.xlsx"
    
    if add_excel(lineas, nombre_archivo=archivo, expected_columns=p_methadata):
        print(f"Añadidas correctamente {len(lineas)} línea(s) al archivo: '{archivo}'")
    else:
        print("Ocurrió un error al añadir las líneas.")
