def list_n_param(dict=False):
    ns_list = [
        "N000",  # Ruta del parámetro
        "N001",  # Nombre, str     
        "N002",  # Abreviado, str       
        "N003",  # DIN, str     
        "N004",  # Espesor, str (se espera numérico, pero viene como str)
        "N005",  # Laser power, str 
        "N006",  # Longitud focal, str
        "N007",  # Posición focal (1) E01, mm (por retrocompatibilidad, no usar)
        "N008",  # Posición focal (2) E02, E04, mm (por retrocompatibilidad, no usar)
        "N011",  # Tipo boquilla, str
        "N012",  # Diámetro boquilla, mm 
        "N026",  # Texto 1, str
        "N037",  # Tipo de GAS principal, str
        "N086",  # Feedrate E01, mm/min    
        "N087",  # Cutting peak power E01, W     
        "N088",  # Cutting frequency E01, Hz
        "N089",  # Cutting duty E01, %
        "N090",  # Assist gas pressure E01, bar
        "N091",  # Assist gas select E01, int/str
        "N098",  # Feedrate E02, mm/min    
        "N099",  # Cutting peak power E02, W     
        "N100",  # Cutting frequency E02, Hz
        "N101",  # Cutting duty E02, %
        "N102",  # Assist gas pressure E02, bar
        "N355",  # Focal calidad1, mm
        "N356",  # Zoom calidad1, mm
        "N357",  # Focal calidad2, mm
        "N358"   # Zoom calidad2, mm
    ]
    ns_dict = {
        "N000": ("Ruta del parámetro", ""),
        "N001": ("Nombre", "str"),
        "N002": ("Abreviado", "str"),
        "N003": ("DIN", "str"),
        "N004": ("Espesor", "mm"),
        "N005": ("Laser power", "str"),
        "N006": ("Longitud focal", "str"),
        "N007": ("Posición focal E01", "mm"),  # Retrocompatibilidad
        "N008": ("Posición focal E02/E04", "mm"),  # Retrocompatibilidad
        "N011": ("Tipo boquilla", "str"),
        "N012": ("Diámetro boquilla", "mm"),
        "N026": ("Texto 1", "str"),
        "N037": ("Tipo de GAS principal", "str"),
        "N086": ("Feedrate E01", "mm/min"),
        "N087": ("Cutting peak power E01", "W"),
        "N088": ("Cutting frequency E01", "Hz"),
        "N089": ("Cutting duty E01", "%"),
        "N090": ("Assist gas pressure E01", "bar"),
        "N091": ("Assist gas select E01", "int/str"),
        "N098": ("Feedrate E02", "mm/min"),
        "N099": ("Cutting peak power E02", "W"),
        "N100": ("Cutting frequency E02", "Hz"),
        "N101": ("Cutting duty E02", "%"),
        "N102": ("Assist gas pressure E02", "bar"),
        "N355": ("Focal calidad1", "mm"),
        "N356": ("Zoom calidad1", "mm"),
        "N357": ("Focal calidad2", "mm"),
        "N358": ("Zoom calidad2", "mm"), 
    }
    if dict:
        return ns_dict
    else:
        return ns_list