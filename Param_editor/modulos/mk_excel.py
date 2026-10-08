"""Compatibilidad con la API antigua.

La generación segura de Excel está implementada en modulos.param_core.
"""
from pathlib import Path

from .param_core import create_workbook_for_factory, load_metadata
from .param_methadata import metadata_path


def mk_excel(ns_dict=None, archivo="parametros.xlsx"):
    # Se conserva la función para no romper imports antiguos, pero la aplicación
    # principal ya no crea plantillas vacías: crea libros ligados a sus fuentes.
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    wb.save(archivo)
    return True


def create_factory_excel(factory_dir, process_root="para_procesar", archivo=None):
    metadata = load_metadata(metadata_path())
    return create_workbook_for_factory(
        Path(factory_dir), Path(process_root), metadata,
        Path(archivo) if archivo else None,
    )
