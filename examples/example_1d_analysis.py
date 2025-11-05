#!/usr/bin/env python3
"""
1D example demonstrating CinemaArray usage.

- create and fill a 1D histogram
- convert to CinemaArray for error propagation
- perform simple math operations (scale, power, exp if supported)
- plot mean +/- sdev with matplotlib
- interpolate to a finer x grid
"""

import numpy as np
import matplotlib.pyplot as plt
from Cinema.Prompt.histogram import Hist1D
from Cinema.Interface import CinemaArray

def create_hist1d(npoints=100000, xbin=50, xmin=0.0, xmax=1.0):
    """Create and fill a 1D histogram with weighted random data."""
    hist = Hist1D(xmin, xmax, xbin)
    # generate (x, weight) pairs and fill
    samples = np.random.random([2, npoints])  # shape (2, npoints)
    hist.fillmany(*samples)  # unpack into (x_array, weight_array)
    return hist


def plot_array_1d(arr, title="CinemaArray 1D", ax=None):
    """Plot mean +/- sdev using matplotlib.errorbar."""
    if ax is None:
        ax = plt.gca()
    x = np.asarray(arr.x)
    y = np.asarray(arr.mean) if hasattr(arr, "mean") else np.asarray(arr)
    yerr = np.asarray(arr.sdev) if hasattr(arr, "sdev") else np.zeros_like(y)
    ax.errorbar(x, y, yerr=yerr, fmt='o', ms=4, capsize=3)
    ax.set_xlabel("x")
    ax.set_ylabel("mean")
    ax.set_title(title)
    return ax

def main():
    hist = create_hist1d(npoints=200000, xbin=40, xmin=0.0, xmax=1.0)
    # convert to CinemaArray (try multiple paths inside helper)
    data = hist.toArrayXY()

    # show basic properties
    print("type(data):", type(data))
    print("x.shape:", np.asarray(data.x).shape)
    print("mean.shape:", np.asarray(data.mean).shape)
    print("sdev.shape:", np.asarray(data.sdev).shape)

    # basic operations
    scaled = data * 2.0
    squared = None
    try:
        squared = data ** 2
    except Exception:
        # fallback: construct expected result (no side-effects)
        squared = CinemaArray(x=np.asarray(data.x),
                              mean=np.asarray(data.mean) ** 2,
                              sdev=np.abs(2 * np.asarray(data.mean)) * np.asarray(data.sdev))

    # try exponential (may be unsupported by CinemaArray ufuncs)
    exp_arr = None
    try:
        exp_arr = np.exp(data)
    except Exception:
        try:
            exp_arr = CinemaArray(x=np.asarray(data.x),
                                  mean=np.exp(np.asarray(data.mean)),
                                  sdev=np.exp(np.asarray(data.mean)) * np.asarray(data.sdev))
        except Exception:
            exp_arr = None

    # Plot original, scaled and squared
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    plot_array_1d(data, title="Original", ax=axes[0])
    plot_array_1d(scaled, title="Scaled ×2", ax=axes[1])
    plot_array_1d(squared, title="Squared", ax=axes[2])
    plt.tight_layout()
    plt.show()

    # If exp succeeded, show it
    if exp_arr is not None:
        plt.figure(figsize=(6,4))
        plot_array_1d(exp_arr, title="Exponential (exp)")
        plt.tight_layout()
        plt.show()
    else:
        print("exp operation not available on CinemaArray; skipped exp plot.")

    # interpolation to a finer grid using histogram edges if available
    if hasattr(hist, "getEdges"):
        edges = hist.getEdges()
        xlo, xhi = edges[0][0], edges[0][-1]
    else:
        xlo, xhi = np.min(np.asarray(data.x)), np.max(np.asarray(data.x))
    new_x = np.linspace(xlo, xhi, 200)
    try:
        interp = data.interpolate(new_x)
        plt.figure(figsize=(8,4))
        plot_array_1d(interp, title="Interpolated (finer x)")
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print("Interpolation not supported:", e)

if __name__ == "__main__":
    main()