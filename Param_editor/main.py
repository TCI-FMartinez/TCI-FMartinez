#### EDITOR DE PARÁMETROS - PARAM -> EXCEL ####
# Compilación Windows:
# pyinstaller PARAMtoEXCEL.spec

from pathlib import Path
import sys

from modulos.logthis import LogThis
from modulos.param_core import ParamEditorError, create_workbook_for_factory, find_factory_dirs, load_metadata
from modulos.param_methadata import metadata_path

COD = "0001"
VER = "2.0"
PROCESS_ROOT = Path("para_procesar")


def main() -> int:
    banner = f"Param to EXCEL - versión {VER} - F. Martínez"
    print(banner)
    LogThis(COD, "INFO:", banner)

    if not PROCESS_ROOT.exists():
        print(f"No existe la carpeta '{PROCESS_ROOT}'.")
        return 1

    metadata = load_metadata(metadata_path())
    if not metadata:
        print("No se ha podido cargar modulos/methadata.xlsx.")
        return 1

    factories = find_factory_dirs(PROCESS_ROOT)
    if not factories:
        print("No se han encontrado carpetas 'factory' dentro de para_procesar.")
        return 1

    total_files = 0
    ok = 0
    for factory in factories:
        try:
            output, count = create_workbook_for_factory(factory, PROCESS_ROOT, metadata)
            total_files += count
            ok += 1
            print(f"OK  {factory}: {count} parámetros -> {output}")
        except ParamEditorError as exc:
            LogThis(COD, "ERROR:", str(factory), str(exc))
            print(f"ERROR {factory}: {exc}")

    print(f"Finalizado: {ok}/{len(factories)} carpetas factory; {total_files} ficheros exportados a Excel.")
    return 0 if ok == len(factories) else 2


if __name__ == "__main__":
    sys.exit(main())
