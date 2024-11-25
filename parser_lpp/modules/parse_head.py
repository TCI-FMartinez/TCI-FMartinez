
import re

def parse_gcode_head(file_content):
    head_dict = {
        "MACHINE" :  "h",
        "MATERIAL" : "h",
        "THICKNESS" : 0,
        "LENS" : "",
        "GAS" : "",
        "POWER" : "",
        "PARAM" : "",
        "REPETITIONS" : "",
        "SIMULATION TIME" : "",
        "FORMAT" : (0, 0),
        "JOB NUMBER" : "",
        "PROGRAM NUMBER" : "",
        "TYPE" : "",
        "NUMBER OF SHEETS " : "",
        "CUTTING HEADS" : "",
        "#516" : "",
        "#517" : ""
    }

    head_vars = list(head_dict.keys())

    patterns = [
        r"\( MACHINE :\s*(.*?)\s*\)",
        r"\( MATERIAL :\s*(.*?)\s*\)",
        r"\( THICKNESS :\s*(.*?)\s*\)",
        r"\( LENS :\s*(.*?)\s*\)",
        r"\( GAS :\s*(.*?)\s*\)",
        r"\( POWER :\s*(.*?)\s*\)",
        r"\( PARAM :\s*(.*?)\s*\)",
        r"\( REPETITIONS :\s*(.*?)\s*\)",
        r"\( SIMULATION TIME :\s*(.*?)\s*\)",
        r"\( FORMAT :\s*(.*?)\s*\)",
        r"\( JOB NUMBER :\s*(.*?)\s*\)",
        r"\( PROGRAM NUMBER :\s*(.*?)\s*\)",
        r"\( TYPE :\s*(.*?)\s*\)",
        r"\( NUMBER OF SHEETS :\s*(.*?)\s*\)",
        r"\(\s*CUTTING HEADS :\s*(.*?)\s*\)",
        r"#516\s*=\s*(\d+)\s*;",
        r"#517\s*=\s*(\d+)\s*;"
    ]

    patt_is_head = r"\(|#"    # Para encontrar que empieza por ( o por #

    i:int = 0
    n = len(patterns)

    # Parsear el archivo línea por línea
    for line in file_content:
        line = line.strip()
        # Solo si empieza por (
        match_line = re.search(patt_is_head, line)
        if match_line:
            while i < n:
                match = re.search(patterns[i], line)
                if match:
                    #print(f"Found: {match.group()}")
                    #print(f"{match[0]}")
                    #print(head_vars[i], "=", match.group(1))
                    head_dict[f"{head_vars[i]}"] = match.group(1)
                i += 1    
        i = 0
    
    # Descomponemos el str del formato en una tupla
    formato = head_dict["FORMAT"]
    #print(formato)

    format_match = re.search(r"(\d+)[xX](\d+)", formato)

    if format_match:
        f_x = int(format_match.group(1))
        f_y = int(format_match.group(2))
        #print("X =", f_x)
        #print("Y =", f_y)
    else:
        print("No se encontraró formaro válido.")
        f_x, f_y = 0, 0
    
    head_dict["FORMAT"] = (f_x, f_y)       # Sobreescribimos el valor de formato por la tupla.
    return head_dict
