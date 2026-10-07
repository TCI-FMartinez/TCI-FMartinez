from __future__ import annotations

import sys
from pathlib import Path

from .param_core import load_metadata


def metadata_path() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "modulos" / "methadata.xlsx"
    return Path(__file__).with_name("methadata.xlsx")


def param_methadata(metric=True):
    metadata = load_metadata(metadata_path())
    ns_dict = {
        "properties": ("R=escritura/S=Solo lectura", "Titulo de columna", "Valor", "Tipo de dato", "Valor max", "Valor min."),
    }
    for key, info in metadata.items():
        ns_dict[key] = (
            info.get("status") or "R",
            info.get("title") or "",
            "",
            info.get("data_type") or "",
            info.get("max") if info.get("max") is not None else "",
            info.get("min") if info.get("min") is not None else "",
        )

    metric_values = {
        "text": "string", "dist": "mm", "feedrate": "mm/min", "power": "W",
        "frequency": "Hz", "duty": "%", "press": "bar", "focal": "mm", "zoom": "multipl.",
    }
    imperial_values = {**metric_values, "dist": "inch", "feedrate": "inch/min", "press": "psi"}
    return bool(metadata), ns_dict, metric_values if metric else imperial_values


if __name__ == "__main__":
    result, data, units = param_methadata()
    print("metadata:", result, "parametros:", len(data) - 1, "unidades:", units)
