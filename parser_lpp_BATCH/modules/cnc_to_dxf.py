from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

CMD_RE = re.compile(r"G(\d{1,3})")
PARAM_RE = re.compile(r"([XYZIJKR])\s*([+-]?\d+(?:\.\d+)?)", re.IGNORECASE)
EPS = 1e-6


@dataclass
class Entity:
    type: str
    start: tuple[float, float] | None = None
    end: tuple[float, float] | None = None
    center: tuple[float, float] | None = None
    radius: float | None = None
    clockwise: bool | None = None


@dataclass
class Contour:
    name: str
    entities: list[Entity] = field(default_factory=list)
    start_point: tuple[float, float] | None = None
    end_point: tuple[float, float] | None = None

    @property
    def is_closed(self) -> bool:
        if self.start_point is None or self.end_point is None:
            return False
        return distance(self.start_point, self.end_point) <= 1e-3


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def angle_deg(center: tuple[float, float], point: tuple[float, float]) -> float:
    angle = math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))
    if angle < 0:
        angle += 360.0
    return angle


def clean_line(line: str) -> str:
    line = line.split(";", 1)[0]
    return line.strip().upper()


def extract_params(line: str) -> dict[str, float]:
    return {match.group(1).upper(): float(match.group(2)) for match in PARAM_RE.finditer(line)}


def iter_cnc_lines(cnc_path: str | Path) -> Iterable[str]:
    with open(cnc_path, "r", encoding="latin-1", newline=None) as f:
        for raw_line in f:
            line = clean_line(raw_line)
            if line:
                yield line


def _entity_end(entity: Entity) -> tuple[float, float] | None:
    return entity.end


def simplify_contour_geometry(contour: Contour, tol: float = 1e-3) -> Contour:
    if not contour.entities:
        return contour

    anchor = contour.entities[-1].end
    if anchor is None:
        return contour

    cut_index = None
    for idx, entity in enumerate(contour.entities[:-1]):
        end = _entity_end(entity)
        if end and distance(end, anchor) <= tol:
            cut_index = idx
            break

    if cut_index is None:
        return contour

    new_entities = contour.entities[cut_index + 1:]
    if not new_entities:
        return contour

    return Contour(
        name=contour.name,
        entities=new_entities,
        start_point=new_entities[0].start,
        end_point=new_entities[-1].end,
    )

def parse_cnc_contours(cnc_path: str | Path) -> list[Contour]:
    contours: list[Contour] = []
    current_contour: Contour | None = None
    current_pos: tuple[float, float] | None = None
    modal_motion: str | None = None
    contour_index = 0

    for line in iter_cnc_lines(cnc_path):
        params = extract_params(line)

        if "G65" in line and "P9102" in line:
            contour_index += 1
            current_contour = Contour(name=f"contour_{contour_index:02d}")
            continue

        if "G65" in line and "P9104" in line:
            if current_contour and current_contour.entities:
                current_contour.end_point = current_pos
                contours.append(current_contour)
            current_contour = None
            continue

        cmd_match = CMD_RE.search(line)
        if cmd_match:
            modal_motion = f"G{cmd_match.group(1)}"

        if modal_motion not in {"G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"}:
            continue

        new_x = params.get("X", current_pos[0] if current_pos else None)
        new_y = params.get("Y", current_pos[1] if current_pos else None)

        if modal_motion in {"G0", "G00"}:
            if new_x is not None and new_y is not None:
                current_pos = (new_x, new_y)
            continue

        if current_contour is None:
            if new_x is not None and new_y is not None:
                current_pos = (new_x, new_y)
            continue

        if current_pos is None:
            raise ValueError(f"Movimiento {modal_motion} sin posicion inicial previa: {line}")
        if new_x is None or new_y is None:
            raise ValueError(f"Movimiento {modal_motion} sin X/Y resoluble: {line}")

        start = current_pos
        end = (new_x, new_y)

        if current_contour.start_point is None:
            current_contour.start_point = start

        if modal_motion in {"G1", "G01"}:
            current_contour.entities.append(Entity(type="LINE", start=start, end=end))
            current_pos = end
            continue

        if modal_motion in {"G2", "G02", "G3", "G03"}:
            if "I" not in params or "J" not in params:
                raise ValueError(f"Arco sin I/J: {line}")

            center = (start[0] + params["I"], start[1] + params["J"])
            radius = distance(start, center)
            clockwise = modal_motion in {"G2", "G02"}
            current_contour.entities.append(
                Entity(
                    type="ARC",
                    start=start,
                    end=end,
                    center=center,
                    radius=radius,
                    clockwise=clockwise,
                )
            )
            current_pos = end
            continue

    if current_contour and current_contour.entities:
        current_contour.end_point = current_pos
        contours.append(current_contour)

    return contours


def _dxf_header() -> list[str]:
    return [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1009",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]


def _dxf_footer() -> list[str]:
    return ["0", "ENDSEC", "0", "EOF"]


def _fmt(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _entity_to_dxf(entity: Entity, layer: str = "0") -> list[str]:
    if entity.type == "LINE":
        sx, sy = entity.start
        ex, ey = entity.end
        return [
            "0", "LINE",
            "8", layer,
            "10", _fmt(sx),
            "20", _fmt(sy),
            "30", "0",
            "11", _fmt(ex),
            "21", _fmt(ey),
            "31", "0",
        ]

    if entity.type == "ARC":
        assert entity.start and entity.end and entity.center and entity.radius is not None
        cx, cy = entity.center
        start_angle = angle_deg(entity.center, entity.start)
        end_angle = angle_deg(entity.center, entity.end)

        if entity.clockwise:
            start_angle, end_angle = end_angle, start_angle

        if distance(entity.start, entity.end) <= 1e-4:
            return [
                "0", "CIRCLE",
                "8", layer,
                "10", _fmt(cx),
                "20", _fmt(cy),
                "30", "0",
                "40", _fmt(entity.radius),
            ]

        return [
            "0", "ARC",
            "8", layer,
            "10", _fmt(cx),
            "20", _fmt(cy),
            "30", "0",
            "40", _fmt(entity.radius),
            "50", _fmt(start_angle),
            "51", _fmt(end_angle),
        ]

    raise ValueError(f"Tipo de entidad no soportado: {entity.type}")


def write_contours_dxf(
    contours: list[Contour],
    dxf_path: str | Path,
    separate_layers: bool = True,
    layer_prefix: str = "CONTORNO_",
) -> Path:
    dxf_path = Path(dxf_path)
    lines = _dxf_header()

    for idx, contour in enumerate(contours, start=1):
        layer = f"{layer_prefix}{idx:02d}" if separate_layers else "0"
        for entity in contour.entities:
            lines.extend(_entity_to_dxf(entity, layer=layer))

    lines.extend(_dxf_footer())
    dxf_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return dxf_path

##### MAIN FUNCTION TO CALL FROM OUTSIDE #####
def cnc_to_single_dxf(
    cnc_path: str | Path,
    dxf_path: str | Path | None = None,
    geometry_only: bool = True,
    separate_layers: bool = False,
) -> Path:
    """Convierte un archivo CNC a un único archivo DXF con todos los contornos.
    Cada contorno se puede colocar en una capa separada o todos en la misma capa.
    Args:
        cnc_path: Ruta al archivo CNC de entrada.
        dxf_path: Ruta al archivo DXF de salida. Si es None, se crea en el mismo directorio que el CNC con el mismo nombre pero extensión .dxf.
        geometry_only: Si es False, desactiva la simplificación de la geometría de los contornos para eliminar segmentos redundantes.
        separate_layers: Si es True, cada contorno se coloca en una capa separada. Si es False, todos los contornos se colocan en la capa "0".
    """
    cnc_path = Path(cnc_path)
    if dxf_path is None:
        out_dir = cnc_path.parent / "OUT_dxf"
        out_dir.mkdir(parents=True, exist_ok=True)
        dxf_path = out_dir / f"{cnc_path.stem}_all_contours.dxf"

    contours = parse_cnc_contours(cnc_path)
    if geometry_only:
        contours = [simplify_contour_geometry(c) for c in contours]
    if not contours:
        raise ValueError(f"No se han detectado contornos en: {cnc_path}")

    return write_contours_dxf(contours, dxf_path, separate_layers=separate_layers)


if __name__ == "__main__":
    import sys
    cnc_file = Path(sys.argv[1])
    out = cnc_to_single_dxf(cnc_file)
    print(out)
