#!/usr/bin/env python3
"""
Convierte un DXF de herramienta en un JSON con el esquema de pads/contorno.

Reglas implementadas:
- CIRCLE -> un pad
- Diametro 36 mm -> type 1 (iman), force 10.0
- Diametro 50 mm -> type 2 (ventosa), force 2.5
- Diametro 80 mm -> type 2 (ventosa), force 7.0
- Zona central -> dependence [0, 0]
- Zonas laterales moviles en X -> dependence [1, 0]
- Los IDs se asignan ordenando por Y descendente y X ascendente
- El contorno se calcula a partir de la caja exterior del dibujo

Uso:
    python dxf_to_tool_json.py entrada.dxf salida.json

Opcional:
    python dxf_to_tool_json.py entrada.dxf salida.json --pretty
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import ezdxf


EPS = 1e-6


@dataclass(frozen=True)
class Rect:
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def contains_point(self, x: float, y: float, tol: float = 1e-6) -> bool:
        return (
            self.min_x - tol <= x <= self.max_x + tol
            and self.min_y - tol <= y <= self.max_y + tol
        )


def round_clean(value: float, digits: int = 6) -> float:
    value = round(float(value), digits)
    if abs(value) < 10 ** (-digits):
        return 0.0
    return value


def normalize_num(value: float) -> int | float:
    value = round_clean(value, 6)
    if abs(value - round(value)) < 1e-6:
        return int(round(value))
    return value


def bbox_from_points(points: Sequence[Tuple[float, float]]) -> Rect:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return Rect(min(xs), max(xs), min(ys), max(ys))


def get_all_rectangles(msp) -> List[Rect]:
    rects: List[Rect] = []
    for entity in msp.query("LWPOLYLINE"):
        points = [(float(p[0]), float(p[1])) for p in entity.get_points()]
        if len(points) >= 2:
            rects.append(bbox_from_points(points))
    return rects


def get_outer_contour(msp) -> list[list[int | float]]:
    points: list[tuple[float, float]] = []

    for entity in msp.query("LWPOLYLINE"):
        points.extend((float(p[0]), float(p[1])) for p in entity.get_points())

    for entity in msp.query("LINE"):
        points.append((float(entity.dxf.start.x), float(entity.dxf.start.y)))
        points.append((float(entity.dxf.end.x), float(entity.dxf.end.y)))

    if not points:
        raise ValueError("No se ha podido calcular el contorno: el DXF no tiene LINE ni LWPOLYLINE.")

    bbox = bbox_from_points(points)
    return [
        [normalize_num(bbox.min_x), normalize_num(bbox.max_y)],
        [normalize_num(bbox.max_x), normalize_num(bbox.max_y)],
        [normalize_num(bbox.max_x), normalize_num(bbox.min_y)],
        [normalize_num(bbox.min_x), normalize_num(bbox.min_y)],
    ]


def get_central_rect(rectangles: Sequence[Rect]) -> Rect:
    candidates = [r for r in rectangles if r.min_x <= 0 <= r.max_x]
    if not candidates:
        raise ValueError("No se ha encontrado una zona central que cruce X=0.")

    # Escoge la mas ancha que cruce el origen; en tus DXF es el bloque central.
    return max(candidates, key=lambda r: (r.width, r.height))


def classify_dependence(x: float, y: float, central_rect: Rect) -> list[int]:
    if central_rect.contains_point(x, y):
        return [0, 0]
    return [1, 0]


def classify_pad(diameter: float, tolerance: float = 1.0) -> tuple[int, float, int]:
    known = {
        36: (1, 10.0, 36),
        50: (2, 2.5, 50),
        80: (2, 7.0, 80),
    }

    closest = min(known.keys(), key=lambda d: abs(d - diameter))
    if abs(closest - diameter) > tolerance:
        raise ValueError(
            f"Diametro no soportado: {diameter:.3f} mm. "
            "Solo se contemplan 36, 50 y 80 mm."
        )
    return known[closest]


def sort_key(circle: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, diameter = circle
    return (-round_clean(y, 6), round_clean(x, 6), round_clean(diameter, 6))


def extract_circles(msp) -> list[tuple[float, float, float]]:
    circles: list[tuple[float, float, float]] = []
    for entity in msp.query("CIRCLE"):
        x = round_clean(float(entity.dxf.center.x), 6)
        y = round_clean(float(entity.dxf.center.y), 6)
        diameter = round_clean(float(entity.dxf.radius) * 2.0, 6)
        circles.append((x, y, diameter))
    if not circles:
        raise ValueError("El DXF no contiene entidades CIRCLE.")
    return sorted(circles, key=sort_key)


def build_pads(circles: Sequence[tuple[float, float, float]], central_rect: Rect) -> list[dict]:
    pads = []
    for idx, (x, y, diameter_raw) in enumerate(circles, start=1):
        pad_type, force, diameter = classify_pad(diameter_raw)
        pads.append(
            {
                "id": idx,
                "posX": normalize_num(x),
                "posY": normalize_num(y),
                "type": pad_type,
                "force": force,
                "is_active": False,
                "diameter": diameter,
                "dependence": classify_dependence(x, y, central_rect),
            }
        )
    return pads


def convert_dxf_to_json(input_path: Path) -> dict:
    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace()

    rectangles = get_all_rectangles(msp)
    if not rectangles:
        raise ValueError("No se han encontrado rectangulos LWPOLYLINE para detectar zonas.")

    central_rect = get_central_rect(rectangles)
    circles = extract_circles(msp)

    return {
        "pads": build_pads(circles, central_rect),
        "contorno": get_outer_contour(msp),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte un DXF de herramienta en un JSON de pads/contorno."
    )
    parser.add_argument("input_dxf", type=Path, help="Ruta del archivo DXF de entrada")
    parser.add_argument("output_json", type=Path, help="Ruta del archivo JSON de salida")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Escribe el JSON con indentacion legible",
    )
    args = parser.parse_args()

    if not args.input_dxf.exists():
        raise SystemExit(f"No existe el DXF de entrada: {args.input_dxf}")

    result = convert_dxf_to_json(args.input_dxf)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        if args.pretty:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")
        else:
            json.dump(result, f, ensure_ascii=False)

    print(f"JSON generado en: {args.output_json}")


if __name__ == "__main__":
    main()
