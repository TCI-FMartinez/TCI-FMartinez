import numpy as np
from tmd.simulation.sdof import natural_frequency_hz, damping_ratio, sdof_frf_displacement_over_force


def test_sdof_natural_frequency():
    m = 2.0
    k = (2.0 * np.pi * 10.0) ** 2 * m  # fija fn=10 Hz
    fn = natural_frequency_hz(m, k)
    assert abs(fn - 10.0) < 1e-6


def test_sdof_frf_peak_near_fn():
    m = 2.0
    k = (2.0 * np.pi * 10.0) ** 2 * m
    c = 0.02 * (2.0 * m * (2.0 * np.pi * 10.0))  # zeta aprox 0.02
    f = np.linspace(1.0, 50.0, 5000)
    H = sdof_frf_displacement_over_force(f, m, k, c)
    f_peak = float(f[np.argmax(np.abs(H))])
    assert abs(f_peak - 10.0) < 0.2  # tolerancia por discretización


def test_damping_ratio():
    m = 2.0
    k = (2.0 * np.pi * 10.0) ** 2 * m
    z = 0.03
    c = z * (2.0 * m * (2.0 * np.pi * 10.0))
    assert abs(damping_ratio(m, k, c) - z) < 1e-6
