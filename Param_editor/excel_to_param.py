#### EDITOR DE PARÁMETROS - EXCEL -> PARAM ####
# Compilación Windows:
# pyinstaller EXCELtoPARAM.spec

from pathlib import Path
import sys

from modulos.logthis import LogThis
from modulos.param_core import (
    ParamEditorError,
    build_export_plan,
    discover_workbooks,
    load_metadata,
    validate_collisions,
    write_export_plan,
)
from modulos.param_methadata import metadata_path

COD = "0002"
VER = "2.0"
PROCESS_ROOT = Path("para_procesar")
OUTPUT_ROOT = Path("parametros_exportados")


def main() -> int:
    banner = f"EXCEL to param - versión {VER} - F. Martínez"
    print(banner)
    LogThis(COD, "INFO:", banner)

    metadata = load_metadata(metadata_path())
    if not metadata:
        print("No se ha podido cargar modulos/methadata.xlsx.")
        return 1

    workbooks = discover_workbooks(PROCESS_ROOT)
    if not workbooks:
        print("No se han encontrado parametros.xlsx dentro de carpetas factory.")
        return 1

    plan = []
    try:
        for workbook in workbooks:
            items = build_export_plan(workbook, PROCESS_ROOT, OUTPUT_ROOT, metadata)
            plan.extend(items)
            changed = sum(1 for item in items if item.changed_columns)
            print(f"VALIDADO {workbook}: {len(items)} recetas, {changed} modificadas")

        # Se valida toda la operación antes de escribir el primer fichero.
        validate_collisions(plan)
        manifest = write_export_plan(plan, OUTPUT_ROOT)
    except ParamEditorError as exc:
        LogThis(COD, "ERROR:", "Exportación abortada", str(exc))
        print("EXPORTACIÓN ABORTADA")
        print(exc)
        return 2

    print(f"Generados {len(plan)} ficheros .lparam en '{OUTPUT_ROOT}'.")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
