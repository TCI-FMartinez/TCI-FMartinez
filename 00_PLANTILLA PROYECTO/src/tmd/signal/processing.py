from __future__ import annotations

import numpy as np
from scipy import signal


def detrend(x: np.ndarray) -> np.ndarray:
    return signal.detrend(x, type="linear")


def bandpass(x: np.ndarray, fs: float, f_low: float, f_high: float, order: int = 4) -> np.ndarray:
    if not (0 < f_low < f_high < fs / 2):
        raise ValueError("Frecuencias de bandpass inválidas respecto a fs.")
    sos = signal.butter(order, [f_low, f_high], btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def welch_psd(x: np.ndarray, fs: float, nperseg: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    f, pxx = signal.welch(x, fs=fs, nperseg=nperseg)
    return f, pxx
