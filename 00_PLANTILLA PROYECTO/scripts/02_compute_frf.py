from __future__ import annotations

from pathlib import Path

from tmd.utils.io import load_csv_timeseries, save_npz
from tmd.signal.processing import detrend
from tmd.identification.frf import frf_h1, peak_frequency, damping_half_power
from tmd.plots.frf_plots import plot_frf_mag


def main() -> None:
    # Ajusta rutas a tu estructura real
    in_csv_exc = Path("data/raw/2026-01-08/ensayo01/excitation.csv")
    in_csv_resp = Path("data/raw/2026-01-08/ensayo01/response.csv")

    exc = load_csv_timeseries(in_csv_exc, time_col="t", value_col="x", name="exc")
    resp = load_csv_timeseries(in_csv_resp, time_col="t", value_col="x", name="resp")

    if abs(exc.fs - resp.fs) > 1e-6:
        raise ValueError("fs distinto entre excitación y respuesta. No son comparables.")

    x_in = detrend(exc.x)
    x_out = detrend(resp.x)

    f, H = frf_h1(x_in=x_in, x_out=x_out, fs=exc.fs, nperseg=4096)

    fn = peak_frequency(f, H, f_min=1.0)
    zeta = damping_half_power(f, H, fn)

    print(f"fn estimada = {fn:.3f} Hz")
    print(f"zeta estimada = {zeta:.4f}")

    save_npz("data/processed/2026-01-08/ensayo01/frf.npz", f=f, H=H)
    plot_frf_mag(f, H, title="FRF ensayo01", outpath="results/figures/2026-01-08_ensayo01_frf.png")


if __name__ == "__main__":
    main()
