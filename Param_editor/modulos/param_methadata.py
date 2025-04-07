from os import path

def param_methadata(metric=True):
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
        "properties": ("R=escritura/S=solo lectura", "Titulo de columna", "Tipo de dato", "Valor max", "Valor min."),
        "N000": ("R", "Ruta del parámetro", "text", "", ""),
        "N001": ("R", "Nombre", "text", "", ""),
        "N002": ("R", "Abreviado", "text", "", ""),
        "N003": ("R", "DIN", "text", "", ""),
        "N004": ("R", "Espesor", "dist", "", ""),
        "N005": ("R", "Laser power", "power", "", ""),
        "N006": ("R", "Longitud focal", "focal", "", ""),
        "N007": ("R", "Posición focal E01", "focal", "", ""),  # Retrocompatibilidad
        "N008": ("R", "Posición focal E02/E04", "focal", "", ""),  # Retrocompatibilidad
        "N009": ("R", "", "", "", ""),
        "N010": ("R", "", "", "", ""),
        "N011": ("R", "Tipo boquilla", "text", "", ""),
        "N012": ("R", "Diámetro boquilla", "dist"),
        "N013": ("R", "", "", "", ""),
        "N014": ("R", "", "", "", ""),
        "N015": ("R", "", "", "", ""),
        "N016": ("R", "", "", "", ""),
        "N017": ("R", "", "", "", ""),
        "N018": ("R", "", "", "", ""),
        "N019": ("R", "", "", "", ""),
        "N020": ("R", "", "", "", ""),
        "N021": ("R", "", "", "", ""),
        "N022": ("R", "", "", "", ""),
        "N023": ("R", "", "", "", ""),
        "N024": ("R", "", "", "", ""),
        "N025": ("R", "", "", "", ""),
        "N026": ("R", "Texto 1", "text", "", ""),
        "N037": ("R", "Tipo de GAS principal", "text", "", ""),
        "N086": ("R", "Feedrate E01", "feedrate", "", ""),
        "N087": ("R", "Cutting peak power E01", "power", "", ""),
        "N088": ("R", "Cutting frequency E01", "frequency", "", ""),
        "N089": ("R", "Cutting duty E01", "dury", "", ""),
        "N090": ("R", "Assist gas pressure E01", "press", "", ""),
        "N091": ("R", "Assist gas select E01", "text", "", ""),
        "N098": ("R", "Feedrate E02", "feedrate", "", ""),
        "N099": ("R", "Cutting peak power E02", "power", "", ""),
        "N100": ("R", "Cutting frequency E02", "frequency", "", ""),
        "N101": ("R", "Cutting duty E02", "duty", "", ""),
        "N102": ("R", "Assist gas pressure E02", "press", "", ""),
        "N355": ("R", "Focal calidad1", "dist", "", ""),
        "N356": ("R", "Zoom calidad1", "dist", "", ""),
        "N357": ("R", "Focal calidad2", "dist", "", ""),
        "N358": ("R", "Zoom calidad2", "dist", "", ""), 
    }

    # Si se proporcionan columnas esperadas, pero no existen aún, se crea el DataFrame con dichas columnas.
    if not path.exists("methadata.xlsx"):
        ns_dict = def_ns_dict
        print("\n¡No encontrado el fichero methadata.xlsx!!")

    if metric:
        return ns_dict, metric_values
    else:
        return ns_dict, imperial_values