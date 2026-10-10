"""Closed-form analytic anchors for Cinema.convertor.

Each case pins the (C-backed) conversion functions against an independent
closed-form physics identity rather than against themselves:

- neutron kinematics use E = k^2 / eV2kk with eV2kk = 2*m_n/hbar^2
  (k in A^-1, E in eV), i.e. E = 2.07212465 meV * k^2;
- the momentum transfer of a scattering event with incident wave vector k0
  and outgoing wave vector k1 is Q = |k1 - k0|, so for elastic scattering
  Q = 2*k*sin(theta/2), and for a 4:1 energy jump the kinematic limits are
  k0+k1 (backward) and k1-k0 (forward);
- 25.3 meV is the classic thermal neutron: v = 2200 m/s.

Scalar calls are ctypes c_double round trips; array calls run through
np.vectorize. Grids are kept small so every body stays in the
sub-millisecond range.
"""
import numpy as np
import pytest

from Cinema import convertor
from Cinema.Interface import helper
from Cinema.Interface import units as u

# kinetic energy of a k = 1 A^-1 neutron
K1_ENERGY = 1.0 / u.eV2kk  # 2.072124652399821e-3 eV


def test_ekin2k_unit_wavenumber():
    # E = k^2 * 2.07212465 meV convention: k == 1 A^-1 exactly at this energy
    assert convertor.eKin2k(K1_ENERGY) == pytest.approx(1.0, rel=1e-12)
    # the value truncated at the 8th digit still lands on 1.0 to 1e-7
    assert convertor.eKin2k(2.0721246e-3) == pytest.approx(1.0, rel=1e-7)


def test_ekin2v_thermal_2200_ms():
    # v = sqrt(2E/m) = 2200.05 m/s = 2.20005e6 mm/s for a 25.3 meV neutron
    v = convertor.ekin2v(25.3e-3)
    assert v == pytest.approx(2.20005e6, rel=1e-4)
    # cross-check against the units.py velocity factor (which yields Aa/s;
    # 1 Aa/s = 1e-7 mm/s)
    assert v == pytest.approx(u.ekin2v * np.sqrt(25.3e-3) * 1e-7, rel=1e-5)


def test_ekin2wl_is_two_pi_over_k():
    # de Broglie: wl = 2*pi/k; the C implementation matches to ~4e-8 rel
    energies = np.linspace(0.5e-3, 25.3e-3, 25)
    expect = 2 * np.pi / convertor.eKin2k(energies)
    assert convertor.ekin2wl(energies) == pytest.approx(expect, rel=1e-6)


def test_wavelength_energy_roundtrip():
    wl = np.linspace(0.5, 5.0, 37)
    energy = convertor.wl2ekin(wl)
    # both directions of the roundtrip are exact to double precision
    assert convertor.ekin2wl(energy) == pytest.approx(wl)
    assert convertor.wl2ekin(convertor.ekin2wl(energy)) == pytest.approx(energy)


def test_velocity_energy_roundtrip():
    energies = np.logspace(-4, 0, 25)  # 0.1 meV .. 1 eV
    assert convertor.v2ekin(convertor.ekin2v(energies)) == pytest.approx(energies)


def test_angle_cosine_elastic_closed_form():
    # elastic: Q(cos t) = 2 k sin(t/2) over the full angular range
    t = np.linspace(0.0, 180.0, 37)
    energy = 0.0253
    k = convertor.eKin2k(energy)
    q = convertor.angleCosine2Q(np.cos(t * u.deg2rad), energy)
    assert q == pytest.approx(2 * k * np.sin(t / 2 * u.deg2rad), rel=1e-12)


def test_angle_cosine_backward_limit():
    # cos(theta) = -1 with a 4x energy gain: Q = k0 + k1, k1 = 2*k0
    for energy_in in (1e-4, 0.0253, 1.0):
        k0 = convertor.eKin2k(energy_in)
        q = convertor.angleCosine2Q(-1.0, energy_in, 4.0 * energy_in)
        assert q == pytest.approx(k0 + 2.0 * k0, rel=1e-12)


def test_angle_cosine_forward_limit():
    # cos(theta) = +1 with a 4x energy gain: Q = |k1 - k0| = k0
    for energy_in in (1e-4, 0.0253, 1.0):
        k0 = convertor.eKin2k(energy_in)
        q = convertor.angleCosine2Q(1.0, energy_in, 4.0 * energy_in)
        assert q == pytest.approx(2.0 * k0 - k0, rel=1e-12)


def test_convertor_and_helper_angle_agree():
    # the C scalar kernel and the python helper.angle2Q implement the same
    # closed form; compare over elastic and a 4:1 inelastic ratio
    for ratio in (1.0, 4.0):
        for t_deg in (5.0, 30.0, 90.0, 137.0, 179.0):
            assert convertor.angleCosine2Q(np.cos(t_deg * u.deg2rad),
                                           0.0253, ratio * 0.0253) == \
                pytest.approx(helper.angle2Q(t_deg, 0.0253, ratio * 0.0253),
                              rel=1e-12)


def test_angle_cosine_array_broadcast():
    # 1d cosine grid with a scalar energy keeps the input shape
    cos1d = np.array([0.1, 0.2, 0.3])
    assert np.shape(convertor.angleCosine2Q(cos1d, 0.0253)) == (3,)
    # a (4,1) cosine grid broadcasts against a (3,) energy grid to (4,3),
    # and the elastic closed form holds elementwise
    cos2d = np.linspace(-0.9, 0.9, 4)[:, None]
    energies = np.array([0.01, 0.03, 0.09])
    q = convertor.angleCosine2Q(cos2d, energies, energies)
    assert q.shape == (4, 3)
    kk = np.sqrt(energies * u.eV2kk)[None, :]
    expect = 2.0 * kk * np.sin(np.arccos(cos2d) / 2.0)
    assert q == pytest.approx(expect, rel=1e-12)


def test_energy_prefix_ladder_factors():
    # exact power-of-ten ladder
    assert convertor.keV2eV(1.0) == pytest.approx(1e3)
    assert convertor.eV2keV(1.0) == pytest.approx(1e-3)
    assert convertor.MeV2eV(1.0) == pytest.approx(1e6)
    assert convertor.eV2MeV(1.0) == pytest.approx(1e-6)


def test_prefix_roundtrips():
    energies = np.logspace(-3, 3, 19)
    assert convertor.meV2eV(convertor.eV2meV(energies)) == pytest.approx(energies)
    assert convertor.keV2eV(convertor.eV2keV(energies)) == pytest.approx(energies)


def test_angle_cosine_units_elastic_default():
    # enout=None must be identical to the explicit same-energy call
    assert convertor.angleCosine2Q_units(0.5, 25.3, enin_unit='meV') == \
        pytest.approx(convertor.angleCosine2Q(0.5, 25.3e-3), rel=1e-15)
    assert convertor.angleCosine2Q_units(0.5, 25.3, 'meV', 25.3, 'meV') == \
        pytest.approx(convertor.angleCosine2Q(0.5, 25.3e-3), rel=1e-15)


def test_units_wrappers_match_bare_calls():
    # ekin2wl_units converts its input to eV first
    assert convertor.ekin2wl_units(25.3, 'meV') == \
        pytest.approx(convertor.ekin2wl(25.3e-3), rel=1e-15)
    # wl2ekin_units converts its eV result back out to meV
    assert convertor.wl2ekin_units(1.8, 'meV') == \
        pytest.approx(convertor.wl2ekin(1.8) * 1e3, rel=1e-15)
