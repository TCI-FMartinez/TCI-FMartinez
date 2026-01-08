#####
# Ejemplo de uso de la librería isofits para cálculos de tolerancias y ajustes
# https://github.com/parkergreene/isofits/blob/main/README.md
# COMPILAR
# pyinstaller --distpath DISTRO --collect-data palettable --onefile -n Ajuste_tolerancia main.py

from isofits import isotol, isofit, isoreport

print("=================================================")
print("Cálculo de tolerancias y ajustes según ISO 286-2")
print("Autor: Francisco Martínez Puchades      Oct2025\n")


# 1. Definir los parámetros del ajuste
DIAMETRO_NOMINAL = 50.0  # mm
AJUSTE_AGUJERO = 'H7'
AJUSTE_EJE = 'f6'

DIAMETRO_NOMINAL = float(input("Ingrese el diámetro nominal en mm (ejemplo 50.0): "))
AJUSTE_AGUJERO = str.upper(input("Ingrese el ajuste para el agujero (ejemplo H7): "))
AJUSTE_EJE = str.lower(input("Ingrese el ajuste para el eje (ejemplo f6): "))

if not AJUSTE_AGUJERO.isupper():
    raise ValueError("El ajuste del agujero debe estar en MAYÚSCULAS")
if not AJUSTE_EJE.islower():
    raise ValueError("El ajuste del eje debe estar en minúsculas")

try:
    # Cálculo tolerancias agujero
    upper_tolerance = isotol('hole', DIAMETRO_NOMINAL, AJUSTE_AGUJERO, 'upper')
    lower_tolerance = isotol('hole', DIAMETRO_NOMINAL, AJUSTE_AGUJERO, 'lower')
    print(f"\nAjuste para agujero Ø{DIAMETRO_NOMINAL}mm {AJUSTE_AGUJERO}:")
    print(f"  Tolerancia superior: {upper_tolerance} micras")
    print(f"  Tolerancia inferior: {lower_tolerance} micras")

    # Cálculo tolerancias eje
    shaft_upper = isotol('shaft', DIAMETRO_NOMINAL, AJUSTE_EJE, 'upper')
    shaft_lower = isotol('shaft', DIAMETRO_NOMINAL, AJUSTE_EJE, 'lower')
    print(f"\nAjuste para eje Ø{DIAMETRO_NOMINAL}mm {AJUSTE_EJE}:")
    print(f"  Tolerancia superior: {shaft_upper} micras")
    print(f"  Tolerancia inferior: {shaft_lower} micras")

    mmc, lmc = isofit(DIAMETRO_NOMINAL, AJUSTE_AGUJERO, AJUSTE_EJE) #returns mmc and lmc of hole/shaft fit
    print(f"\nLímites de ajuste para Ø10mm H7/h6:")
    print(f"  Apriete max: {mmc} micras")
    print(f"  Juego máx: {lmc} micras")

    # Reporte completo
    #print("\nReporte completo de tolerancias:")
    #isoreport(DIAMETRO_NOMINAL, AJUSTE_AGUJERO, AJUSTE_EJE)

except Exception as e:
    print(f"Error al calcular tolerancias: {str(e)}")

