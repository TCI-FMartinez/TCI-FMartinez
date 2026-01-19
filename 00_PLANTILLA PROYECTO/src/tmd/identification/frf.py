from __future__ import annotations

import numpy as np
from scipy import signal


def frf_h1(
    x_in: np.ndarray,
    x_out: np.ndarray,
    fs: float,
    nperseg: int = 4096,
    noverlap: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Estimador H1: H = G_yx / G_xx (robusto si hay ruido en salida).
    x_in: excitación (fuerza/impacto/referencia)
    x_out: respuesta (aceleración/desplazamiento)
    Devuelve: f (Hz), H (complejo)
    """
    if noverlap is None:
        noverlap = nperseg // 2

    f, Pxy = signal.csd(x_out, x_in, fs=fs, nperseg=nperseg, noverlap=noverlap)
    _, Pxx = signal.welch(x_in, fs=fs, nperseg=nperseg, noverlap=noverlap)
    H = Pxy / Pxx
    return f, H


def peak_frequency(f: np.ndarray, H: np.ndarray, f_min: float = 0.0, f_max: float | None = None) -> float:
    mag = np.abs(H)
    mask = f >= f_min
    if f_max is not None:
        mask &= f <= f_max
    if not np.any(mask):
        raise ValueError("Rango de búsqueda vacío para el pico.")
    idx = np.argmax(mag[mask])
    return float(f[mask][idx])


def damping_half_power(f: np.ndarray, H: np.ndarray, fn: float) -> float:
    """
    Estimación rápida por método de -3 dB (half-power).
    Para sistemas tipo SDOF cerca del pico.
    Devuelve zeta aproximado.
    """
    mag = np.abs(H)
    i0 = int(np.argmin(np.abs(f - fn)))
    peak = mag[i0]
    if peak <= 0:
        raise ValueError("Magnitud de pico inválida.")

    target = peak / np.sqrt(2.0)

    left = mag[: i0 + 1]
    right = mag[i0:]

    if left.size < 2 or right.size < 2:
        raise ValueError("No hay puntos suficientes alrededor del pico.")

    il = np.where(left <= target)[0]
    ir = np.where(right <= target)[0]

    if il.size == 0 or ir.size == 0:
        raise ValueError("No encuentro cruces half-power. Falta resolución o hay ruido.")

    f1 = float(f[il[-1]])
    f2 = float(f[i0 + ir[0]])

    if f2 <= f1 or fn <= 0:
        raise ValueError("Frecuencias half-power inválidas.")

    zeta = (f2 - f1) / (2.0 * fn)
    return float(zeta)
