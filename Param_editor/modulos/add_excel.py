"""Módulo legado.

add_excel se mantiene solo por compatibilidad. La aplicación actual escribe el
Excel de forma atómica desde modulos.param_core y no acumula global_table.
"""
from pathlib import Path
from openpyxl import Workbook, load_workbook


def add_excel(lines, nombre_archivo="parametros.xlsx", expected_columns=None):
    columns = list(expected_columns or [])
    path = Path(nombre_archivo)
    if path.exists():
        wb = load_workbook(path)
        ws = wb["Hoja1"] if "Hoja1" in wb.sheetnames else wb.active
        if not columns:
            columns = [str(c.value) for c in ws[1] if c.value is not None]
    else:
        if not columns:
            return False
        wb = Workbook()
        ws = wb.active
        ws.title = "Hoja1"
        ws.append(columns)

    for line in lines:
        ws.append([line.get(col, "") for col in columns])
    wb.save(path)
    return True
