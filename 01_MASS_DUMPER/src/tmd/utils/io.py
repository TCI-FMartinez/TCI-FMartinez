from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TimeSeries:
    t: np.ndarray          # seconds, shape (N,)
    x: np.ndarray          # signal, shape (N,)
    fs: float              # sampling frequency (Hz)
    name: str = "signal"
    unit: str = ""


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_csv_timeseries(
    filepath: str | Path,
    time_col: str = "t",
    value_col: str = "x",
    name: str = "signal",
    unit: str = "",
) -> TimeSeries:
    df = pd.read_csv(filepath)
    t = df[time_col].to_numpy(dtype=float)
    x = df[value_col].to_numpy(dtype=float)

    if t.size < 2:
        raise ValueError("CSV con menos de 2 muestras. No puedo calcular fs.")

    dt = float(np.median(np.diff(t)))
    if dt <= 0:
        raise ValueError("Columna de tiempo inválida (dt <= 0).")

    fs = 1.0 / dt
    return TimeSeries(t=t, x=x, fs=fs, name=name, unit=unit)


def save_npz(filepath: str | Path, **arrays: np.ndarray) -> None:
    filepath = Path(filepath)
    ensure_dir(filepath.parent)
    np.savez(filepath, **arrays)


def try_load_tdms(filepath: str | Path, group: str, channel: str) -> Optional[np.ndarray]:
    """
    Lectura TDMS opcional. Requiere: pip install .[tdms]
    Devuelve None si no está instalado nptdms.
    """
    try:
        from nptdms import TdmsFile  # type: ignore
    except Exception:
        return None

    tdms = TdmsFile.read(str(filepath))
    ch = tdms[group][channel]
    return ch[:]
