

import re

data = """
( MACHINE : Dynamicline )  ;
( MATERIAL : Inoxidable )  ;
( THICKNESS : 10 )  ;
( LENS : 150 )  ;
( GAS : 1 )  ;
( POWER : 6000 )  ;
( PARAM : Acero_Carbomo N2 )  ;
( REPETITIONS : 1 )  ;
( SIMULATION TIME : 02:20:22 )  ;
( FORMAT : 3000x1500 )  ;
( JOB NUMBER : SKRLJ )  ;
( PROGRAM NUMBER : 93741 )  ;
( TYPE : 0 )  ;
( NUMBER OF SHEETS : 1 )  ;
( CUTTING HEADS : 1 )  ;
#516= 1  ;
#517= 1  ;
"""

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

i:int = 0
n = len(patterns)
while i < n:
    print("\nParam:", i)
    match = re.search(patterns[i], data)
    if match:
        #print(f"Found: {match.group()}")
        print(f"{match[0]}")
    i += 1
