from __future__ import annotations

import numpy as np


def sdof_frf_displacement_over_force(
    f: np.ndarray,
    m: float,
    k: float,
    c: float,
) -> np.ndarray:
    """
    FRF X/F de un SDOF: 1 / (k - m*w^2 + j*c*w)
    f: Hz
    """
    w = 2.0 * np.pi * f
    jw = 1j * w
    denom = k - m * (w**2) + c * jw
    return 1.0 / denom


def natural_frequency_hz(m: float, k: float) -> float:
    if m <= 0 or k <= 0:
        raise ValueError("m y k deben ser positivos.")
    wn = np.sqrt(k / m)  # rad/s
    return float(wn / (2.0 * np.pi))


def damping_ratio(m: float, k: float, c: float) -> float:
    fn = natural_frequency_hz(m, k)
    wn = 2.0 * np.pi * fn
    cc = 2.0 * m * wn
    if cc <= 0:
        raise ValueError("c crítico inválido.")
    return float(c / cc)
