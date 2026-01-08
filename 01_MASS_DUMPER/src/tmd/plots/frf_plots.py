from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def plot_frf_mag(
    f: np.ndarray,
    H: np.ndarray,
    title: str = "FRF magnitude",
    outpath: str | None = None,
) -> None:
    mag = np.abs(H)

    plt.figure()
    plt.plot(f, mag)
    plt.xlabel("Hz")
    plt.ylabel("|H|")
    plt.title(title)
    plt.grid(True)

    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches="tight")
    else:
        plt.show()
