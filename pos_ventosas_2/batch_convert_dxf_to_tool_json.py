#!/usr/bin/env python3
"""
Convierte por lotes todos los DXF de una carpeta a JSON usando dxf_to_tool_json.py.

Uso:
    python batch_convert_dxf_to_tool_json.py ./dxf ./json --pretty

Opciones:
    --pattern "Herramienta*.dxf"   Filtra los archivos a convertir
    --recursive                    Busca DXF en subcarpetas
    --suffix "_generado"          Sufijo para el nombre del JSON
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_converter(script_path: Path):
    spec = importlib.util.spec_from_file_location("dxf_to_tool_json", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se ha podido cargar el conversor: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iter_dxf_files(input_dir: Path, pattern: str, recursive: bool):
    if recursive:
        yield from sorted(input_dir.rglob(pattern))
    else:
        yield from sorted(input_dir.glob(pattern))


def write_json(output_path: Path, data: dict, pretty: bool):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        else:
            json.dump(data, f, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte por lotes archivos DXF a JSON de herramienta."
    )
    parser.add_argument("input_dir", type=Path, help="Carpeta con archivos DXF")
    parser.add_argument("output_dir", type=Path, help="Carpeta de salida para los JSON")
    parser.add_argument(
        "--converter",
        type=Path,
        default=Path(__file__).with_name("dxf_to_tool_json.py"),
        help="Ruta al script dxf_to_tool_json.py",
    )
    parser.add_argument(
        "--pattern",
        default="*.dxf",
        help="Patron de archivos DXF a convertir",
    )
    parser.add_argument(
        "--suffix",
        default="_generado",
        help="Sufijo para el nombre del JSON de salida",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Busca DXF tambien en subcarpetas",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Escribe JSON con indentacion legible",
    )
    args = parser.parse_args()

    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise SystemExit(f"La carpeta de entrada no existe o no es valida: {args.input_dir}")

    if not args.converter.exists():
        raise SystemExit(f"No existe el conversor base: {args.converter}")

    converter = load_converter(args.converter)
    dxf_files = list(iter_dxf_files(args.input_dir, args.pattern, args.recursive))

    if not dxf_files:
        raise SystemExit(
            f"No se han encontrado archivos que coincidan con '{args.pattern}' en {args.input_dir}"
        )

    ok = 0
    failed = 0

    for dxf_path in dxf_files:
        output_name = f"{dxf_path.stem}{args.suffix}.json"
        output_path = args.output_dir / output_name
        try:
            result = converter.convert_dxf_to_json(dxf_path)
            write_json(output_path, result, args.pretty)
            ok += 1
            print(f"[OK] {dxf_path.name} -> {output_path}")
        except Exception as exc:
            failed += 1
            print(f"[ERROR] {dxf_path.name}: {exc}")

    print("-")
    print(f"Convertidos correctamente: {ok}")
    print(f"Con error: {failed}")

    if ok == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
