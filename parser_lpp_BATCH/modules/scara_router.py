from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return None


def _to_bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in {"YES", "TRUE", "1", "SI", "SÍ"}:
        return True
    if text in {"NO", "FALSE", "0"}:
        return False
    return None


def piece_passes_scara_filters(piece_meta: dict[str, Any], filters: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    """
    Evalua si una pieza cumple los filtros de SCARA.

    piece_meta esperado:
        {
            "bbox_x": float,
            "bbox_y": float,
            "weight_kg": float | None,
            "ferromagnetic": bool | None,
            "material": str,
            "material_family": str,
        }

    filters soportados:
        {
            "max_bbox_x": 400.0,
            "max_bbox_y": 300.0,
            "max_weight_kg": 2.0,
            "ferromagnetic": True | False | None,
            "material_family_any": ["STEEL", "STAINLESS"],
            "material_contains_any": ["INOX", "S235"],
        }
    """
    filters = filters or {}
    reasons: list[str] = []

    bbox_x = _to_float(piece_meta.get("bbox_x"))
    bbox_y = _to_float(piece_meta.get("bbox_y"))
    weight_kg = _to_float(piece_meta.get("weight_kg"))
    ferromagnetic = _to_bool_or_none(piece_meta.get("ferromagnetic"))
    material = str(piece_meta.get("material") or "").upper().strip()
    material_family = str(piece_meta.get("material_family") or "").upper().strip()

    max_bbox_x = _to_float(filters.get("max_bbox_x"))
    max_bbox_y = _to_float(filters.get("max_bbox_y"))
    max_weight_kg = _to_float(filters.get("max_weight_kg"))
    wanted_ferromagnetic = filters.get("ferromagnetic")
    if wanted_ferromagnetic is not None:
        wanted_ferromagnetic = _to_bool_or_none(wanted_ferromagnetic)

    material_family_any = [str(x).upper().strip() for x in (filters.get("material_family_any") or []) if str(x).strip()]
    material_contains_any = [str(x).upper().strip() for x in (filters.get("material_contains_any") or []) if str(x).strip()]

    if max_bbox_x is not None:
        if bbox_x is None:
            reasons.append("bbox_x desconocido")
        elif bbox_x > max_bbox_x:
            reasons.append(f"bbox_x={bbox_x:.3f} > {max_bbox_x:.3f}")

    if max_bbox_y is not None:
        if bbox_y is None:
            reasons.append("bbox_y desconocido")
        elif bbox_y > max_bbox_y:
            reasons.append(f"bbox_y={bbox_y:.3f} > {max_bbox_y:.3f}")

    if max_weight_kg is not None:
        if weight_kg is None:
            reasons.append("peso desconocido")
        elif weight_kg > max_weight_kg:
            reasons.append(f"weight_kg={weight_kg:.6f} > {max_weight_kg:.6f}")

    if wanted_ferromagnetic is not None:
        if ferromagnetic is None:
            reasons.append("ferromagnetismo desconocido")
        elif ferromagnetic is not wanted_ferromagnetic:
            reasons.append(
                f"ferromagnetic={ferromagnetic} != {wanted_ferromagnetic}"
            )

    if material_family_any and material_family not in material_family_any:
        reasons.append(f"material_family={material_family or 'UNKNOWN'} no permitido")

    if material_contains_any and not any(token in material for token in material_contains_any):
        reasons.append(f"material={material or 'UNKNOWN'} no contiene ninguno de {material_contains_any}")

    return len(reasons) == 0, reasons



def route_piece_outputs(
    piece_path: str | Path,
    piece_meta: dict[str, Any],
    filters: dict[str, Any] | None = None,
    *,
    default_cnc_dir: str | Path = "OUT_cnc",
    default_dxf_dir: str | Path = "OUT_dxf",
    default_png_dir: str | Path = "OUT_png",
    scara_root: str | Path = "SCARA",
    move_cnc: bool = True,
) -> dict[str, Any]:
    """
    Si la pieza cumple filtros, redirige sus salidas a:
        SCARA/OUT_cnc
        SCARA/OUT_dxf
        SCARA/OUT_png

    Si no cumple, mantiene:
        OUTPUT
        OUT_dxf
        OUT_png

    Devuelve un dict con rutas finales y el resultado del filtrado.
    """
    piece_path = Path(piece_path)

    default_cnc_dir = Path(default_cnc_dir)
    default_dxf_dir = Path(default_dxf_dir)
    default_png_dir = Path(default_png_dir)
    scara_root = Path(scara_root)

    passed, reasons = piece_passes_scara_filters(piece_meta, filters)

    if passed:
        cnc_dir = scara_root / "OUT_cnc"
        dxf_dir = scara_root / "OUT_dxf"
        png_dir = scara_root / "OUT_png"
    else:
        cnc_dir = default_cnc_dir
        dxf_dir = default_dxf_dir
        png_dir = default_png_dir

    cnc_dir.mkdir(parents=True, exist_ok=True)
    dxf_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    final_piece_path = cnc_dir / piece_path.name
    final_dxf_path = dxf_dir / f"{piece_path.stem}.dxf"
    final_png_path = png_dir / f"{piece_path.stem}_contours.png"

    if move_cnc:
        try:
            if piece_path.resolve() != final_piece_path.resolve():
                if final_piece_path.exists():
                    final_piece_path.unlink()
                shutil.move(str(piece_path), str(final_piece_path))
        except FileNotFoundError:
            pass
    else:
        final_piece_path = piece_path

    return {
        "passed": passed,
        "reasons": reasons,
        "piece_path": str(final_piece_path),
        "dxf_path": str(final_dxf_path),
        "png_path": str(final_png_path),
        "cnc_dir": str(cnc_dir),
        "dxf_dir": str(dxf_dir),
        "png_dir": str(png_dir),
    }


# Ejemplo de configuracion listo para copiar.
SCARA_FILTERS_EXAMPLE = {
    "max_bbox_x": 500.0,
    "max_bbox_y": 500.0,
    "max_weight_kg": 6.0,
    # "ferromagnetic": True,
    # "material_family_any": ["STEEL", "STAINLESS"],
    # "material_contains_any": ["INOX", "S235"],
}
