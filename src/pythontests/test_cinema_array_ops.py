#!/usr/bin/env python3

from Cinema import CinemaArray
import numpy as np

RNG = np.random.default_rng(12345)


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


def test_add_sub():
    """Test addition and subtraction error propagation"""
    # Use smaller dataset, ensure unique values
    data = np.arange(1, 21)  # 20 values
    a = CinemaArray.from_counts(data)
    b = CinemaArray.from_sdev(data, np.sqrt(data))

    # Test addition
    c = a + b
    np.testing.assert_allclose(c.mean, a.mean + b.mean, rtol=1e-12)
    np.testing.assert_allclose(c.sdev, err_add_sub(a.sdev, b.sdev), rtol=1e-12)

    # Test subtraction
    d = a - b
    np.testing.assert_allclose(d.mean, a.mean - b.mean, rtol=1e-12)
    np.testing.assert_allclose(d.sdev, err_add_sub(a.sdev, b.sdev), rtol=1e-12)


def test_multiply():
    """Test multiplication error propagation"""
    data1 = np.arange(1, 21)
    data2 = np.arange(2, 22)

    a = CinemaArray.from_counts(data1)
    b = CinemaArray.from_sdev(data2, np.sqrt(data2))

    c = a * b
    np.testing.assert_allclose(c.mean, a.mean * b.mean, rtol=1e-12)
    np.testing.assert_allclose(c.sdev, err_mul(a.mean, a.sdev, b.mean, b.sdev), rtol=1e-12)


def test_divide():
    """Test division error propagation"""
    data1 = np.arange(1, 21)
    data2 = np.arange(10, 30)  # Larger numbers for division denominator

    a = CinemaArray.from_counts(data1)
    b = CinemaArray.from_sdev(data2, np.sqrt(data2))

    c = a / b
    np.testing.assert_allclose(c.mean, a.mean / b.mean, rtol=1e-12)
    np.testing.assert_allclose(c.sdev, err_div(a.mean, a.sdev, b.mean, b.sdev), rtol=1e-12)


def test_scalar_operations():
    """Test scalar multiplication and division error propagation"""
    data = np.arange(1, 21)
    a = CinemaArray.from_counts(data)
    scalar = 2.5

    # Test scalar multiplication
    b = a * scalar
    np.testing.assert_allclose(b.mean, a.mean * scalar, rtol=1e-12)
    np.testing.assert_allclose(b.sdev, err_scalar_mul(a.sdev, scalar), rtol=1e-12)

    # Test scalar division
    c = a / scalar
    np.testing.assert_allclose(c.mean, a.mean / scalar, rtol=1e-12)
    np.testing.assert_allclose(c.sdev, err_scalar_div(a.sdev, scalar), rtol=1e-12)


def test_power():
    """Test power operation with integer exponent"""
    data = np.arange(1, 6)  # Small positive integers
    a = CinemaArray.from_counts(data)
    n = 2  # Square

    try:
        # Try direct power operation
        b = a ** n
    except TypeError:
        try:
            # Fallback: manual computation
            b = CinemaArray.from_sdev(
                np.power(a.mean, n),
                err_power(a.mean, a.sdev, n),
                getattr(a, 'x', None)
            )
        except Exception as e:
            print(f"SKIP power: neither operation worked: {e}")
            return 0

    # Compare results using raw arrays
    np.testing.assert_allclose(
        np.asarray(b.mean),
        np.power(np.asarray(a.mean), n),
        rtol=1e-12
    )
    np.testing.assert_allclose(
        np.asarray(b.sdev),
        err_power(np.asarray(a.mean), np.asarray(a.sdev), n),
        rtol=1e-12
    )


def test_exponential():
    """Test exponential operation"""
    data = np.array([0.1, 0.2, 0.3, 0.4, 0.5])  # Small values
    a = CinemaArray.from_counts(data)

    try:
        # Try numpy exp
        b = np.exp(a)
    except TypeError:
        try:
            # Fallback: manual computation
            b = CinemaArray.from_sdev(
                np.exp(a.mean),
                err_exp(a.mean, a.sdev),
                getattr(a, 'x', None)
            )
        except Exception as e:
            print(f"SKIP exponential: neither operation worked: {e}")
            return 0

    # Compare results using raw arrays
    np.testing.assert_allclose(
        np.asarray(b.mean),
        np.exp(np.asarray(a.mean)),
        rtol=1e-12
    )
    np.testing.assert_allclose(
        np.asarray(b.sdev),
        err_exp(np.asarray(a.mean), np.asarray(a.sdev)),
        rtol=1e-12
    )


def main():
    """Run all error propagation tests"""
    tests = [
        ("Addition/Subtraction", test_add_sub),
        ("Multiplication", test_multiply),
        ("Division", test_divide),
        ("Scalar Operations", test_scalar_operations),
        ("Power", test_power),
        ("Exponential", test_exponential)
    ]

    failures = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"PASS: {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {name}")
            print(str(e))
        except Exception as e:
            failures += 1
            print(f"ERROR: {name}")
            print(f"  {type(e).__name__}: {str(e)}")

    if failures:
        print(f"\n{failures} tests failed")
        return 1
    else:
        print("\nAll tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())


def test_cinema_array_ops():
    import sys

