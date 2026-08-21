#!/usr/bin/env python3

from Cinema import CinemaArray
import numpy as np


# Error propagation helper formulas (implemented as functions)
def err_add_sub(sa, sb):
    # For z = a ± b : σ_z = sqrt(σ_a^2 + σ_b^2)
    return np.sqrt(sa ** 2 + sb ** 2)


def err_mul(a, sa, b, sb):
    # For z = a * b : σ_z = sqrt( (b*σ_a)^2 + (a*σ_b)^2 )
    return np.sqrt((b * sa) ** 2 + (a * sb) ** 2)


def err_div(a, sa, b, sb):
    # For z = a / b : σ_z = sqrt( (σ_a / b)^2 + (a * σ_b / b^2)^2 )
    return np.sqrt((sa / b) ** 2 + ((a * sb) / (b ** 2)) ** 2)


def err_scalar_mul(sa, s):
    # For z = s * a : σ_z = |s| * σ_a
    return np.abs(s) * sa


def err_scalar_div(sa, s):
    # For z = a / s : σ_z = σ_a / |s|
    return sa / np.abs(s)


def err_power(a, sa, n):
    # For z = a^n : dz/da = n * a^(n-1) -> σ_z = |n * a^(n-1)| * σ_a
    return np.abs(n * (a ** (n - 1))) * sa


def err_exp(a, sa):
    # For z = exp(a) : dz/da = exp(a) -> σ_z = exp(a) * σ_a
    return np.exp(a) * sa


def test_add():
    a = CinemaArray.from_counts([100,1000,10000])
    b = CinemaArray.from_sdev([100,1000,10000], [10, np.sqrt(1000), 100])

    np.testing.assert_array_equal((a+b).mean, a.mean+b.mean)
    np.testing.assert_array_equal((a+b).sdev, err_add_sub(a.sdev, b.sdev))


def test_cinemaarray():
    test_add()

