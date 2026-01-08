import pandas as pd
from os import path
#from openpyxl import load_workbook

def param_methadata(metric=True):
    xlsx_archivo = path.join("modulos", "methadata.xlsx")
    metric_values = {
        "text": "string",
        "dist": "mm",
        "feedrate": "mm/min",
        "power": "W",
        "frequency": "Hz",
        "duty": "%",
        "press": "bar",
        "focal": "mm",
        "zoom": "multipl."
    }
    imperial_values = {
        "text": "string",
        "dist": "inch",
        "feedrate": "inch/min",
        "power": "W",
        "frequency": "Hz",
        "duty": "%",
        "press": "psi",
        "focal": "mm",
        "zoom": "multipl."
    }
    # Si no existe el excel 'methadata.xlsx'
    def_ns_dict = {
        "properties": ("R=escritura/S=Solo lectura", "Titulo de columna","Valor", "Tipo de dato", "Valor max", "Valor min."),
        "N000": ("S", "Ruta del parámetro", "", "text", "", ""),
        "N001": ("S", "Nombre", "", "text", "", ""),
        "N002": ("S", "Abreviado", "", "text", "", ""),
        "N003": ("S", "DIN", "", "text", "", ""),
        "N004": ("S", "Espesor", "", "dist", "", ""),
        "N005": ("S", "Laser power", "", "power", "", ""),
        "N006": ("S", "Longitud focal", "", "focal", "", ""),
        "N007": ("R", "Posición focal E01", "", "focal", "", ""),  # Retrocompatibilidad
        "N008": ("R", "Posición focal E02/E04", "", "focal", "", ""),  # Retrocompatibilidad
        "N009": ("R", "", "", "", "", ""),
        "N010": ("R", "", "", "", "", ""),
        "N011": ("R", "Tipo boquilla", "", "text", "", ""),
        "N012": ("R", "Diámetro boquilla", "", "dist","",""),
        "N013": ("R", "", "", "", "", ""),
        "N014": ("R", "", "", "", "", ""),
        "N015": ("R", "", "", "", "", ""),
        "N016": ("R", "", "", "", "", ""),
        "N017": ("R", "", "", "", "", ""),
        "N018": ("R", "", "", "", "", ""),
        "N019": ("R", "", "", "", "", ""),
        "N020": ("R", "", "", "", "", ""),
        "N021": ("R", "", "", "", "", ""),
        "N022": ("R", "", "", "", "", ""),
        "N023": ("R", "", "", "", "", ""),
        "N024": ("R", "", "", "", "", ""),
        "N025": ("R", "", "", "", "", ""),
        "N026": ("R", "Texto 1", "", "text", "", ""),
        "N037": ("R", "Tipo de GAS principal", "", "text", "", ""),
        "N086": ("R", "Feedrate E01", "feedrate", "", ""),
        "N087": ("R", "Cutting peak power E01", "", "power", "", ""),
        "N088": ("R", "Cutting frequency E01", "", "frequency", "", ""),
        "N089": ("R", "Cutting duty E01", "", "duty", "", ""),
        "N090": ("R", "Assist gas pressure E01", "", "press", "", ""),
        "N091": ("R", "Assist gas select E01", "", "text", "", ""),
        "N098": ("R", "Feedrate E02", "", "feedrate", "", "", ""),
        "N099": ("R", "Cutting peak power E02", "", "power", "", ""),
        "N100": ("R", "Cutting frequency E02", "", "frequency", "", ""),
        "N101": ("R", "Cutting duty E02", "duty", "", "", ""),
        "N102": ("R", "Assist gas pressure E02", "", "press", "", ""),
        "N355": ("R", "Focal calidad1", "", "dist", "", ""),
        "N356": ("R", "Zoom calidad1", "", "dist", "", ""),
        "N357": ("R", "Focal calidad2", "", "dist", "", ""),
        "N358": ("R", "Zoom calidad2", "", "dist", "", ""), 
    }

    def xlsx_to_dict(archivo=xlsx_archivo):
        datos = {}
        ns_dict={"properties": ("R=escritura/S=Solo lectura", "Titulo de columna", "Valor", "Tipo de dato", "Valor max", "Valor min."),}
        spec_sheets = ['Methadata', 'Piercing', 'E-conditions', 'EDGE', 'Power Control', 'Pierce tech', 'FOCALS']
        expected_columns = ["properties", "R=escritura/S=solo lectura", 
                       "Titulo de columna","Valor", "Tipo de dato", "Valor max.", "Valor min."]
        
        if not path.exists(archivo):
            print(f"El archivo '{archivo}' no existe. Crea el Excel con la metadata primero.")
            return False, ns_dict
        #------------------------------------------
        # Abrir el libro con pandas
        try:
            # Lee todas las hojas del archivo Excel; sheet_name=None indica que se lean todas.
            sheets = pd.read_excel(archivo, sheet_name=None, engine='openpyxl')
        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            return False, ns_dict

        # Procesar cada hoja relevante (excluir hojas vacías como Hoja7)
        for sheet_name, df in sheets.items():
            if "empty" in sheet_name.lower() or sheet_name == "Hoja7" or sheet_name not in spec_sheets:
                print("    --> Error hoja:", sheet_name)
                continue
            for line in df.to_dict(orient='records'):
                ns_dict[line["properties"]] = (line["R=escritura/S=solo lectura"],
                                               line["Titulo de columna"],
                                               line["Valor"],
                                               line["Tipo de dato"],
                                               line["Valor max."],
                                               line["Valor min."])
                
            datos[sheet_name] = df.to_dict(orient='records')

        #------------------------------------------
        datos= {}   # Borramos los datos. ¿innecesario?
        return True, ns_dict

    # Si se proporcionan columnas esperadas, pero no existen aún, se crea el DataFrame con dichas columnas.

    if not path.exists(xlsx_archivo):
        result = False
        ns_dict = def_ns_dict
        print("\n¡No encontrado el fichero methadata.xlsx!!")
    else:
        print("Encontrado el fichero methadata.xlsx")
        result, ns_dict = xlsx_to_dict()
        

    if metric:
        return result, ns_dict, metric_values
    else:
        return result, ns_dict, imperial_values
    
if __name__ == "__main__":
    result, datos, _ = param_methadata()
    if result: print(datos)