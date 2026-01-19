import numpy as np
from tmd.identification.frf import frf_h1


def test_frf_shapes():
    fs = 1000.0
    t = np.arange(0, 2.0, 1.0 / fs)
    x_in = np.sin(2 * np.pi * 20 * t)
    x_out = 0.5 * x_in

    f, H = frf_h1(x_in, x_out, fs=fs, nperseg=1024)
    assert f.ndim == 1
    assert H.ndim == 1
    assert f.shape == H.shape
    assert len(f) > 10
