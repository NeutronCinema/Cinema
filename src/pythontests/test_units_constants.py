"""Constant ladders and physical identities in Cinema.Interface.units.

Extends test_units.py (which covers the time/energy ladders) with the
length/area ladder and the cross-constant identities. Base unit is
angstrom (aa == 1), so c is expressed in Aa/s and masses in eV/(Aa/s)^2.
All cases are attribute reads - sub-0.1 ms bodies.
"""
import numpy as np
import pytest

from Cinema.Interface import units as u


def test_length_ladder():
    assert u.aa == pytest.approx(1.0)
    assert u.mm == pytest.approx(1e7 * u.aa)
    assert u.cm == pytest.approx(1e8 * u.aa)
    assert u.m == pytest.approx(1e10 * u.aa)
    # fm is defined via cm: 1e-13 cm = 1e-5 angstrom
    assert u.fm == pytest.approx(1e-5 * u.aa)
    # Bohr radius in angstrom (CODATA-vintage value frozen in the module)
    assert u.au == pytest.approx(0.529177249)


def test_barn_in_cm2():
    # 1 barn = 1e-24 cm^2 = 1e-8 angstrom^2
    assert u.barn == pytest.approx(1e-24 * u.cm**2)
    assert u.barn == pytest.approx(1e-8)


def test_speed_of_light_and_hbar():
    # SI definition of the metre: c == 299792458 m/s exactly
    assert u.c == 299792458 * u.m / u.s
    assert u.c == pytest.approx(2.99792458e18)  # in Aa/s
    # hbar is exactly planck / (2*pi) in this module
    assert u.hbar == pytest.approx(u.planck / (2 * np.pi), rel=1e-15)
    assert u.planck == pytest.approx(4.13566769692386e-15)  # eV*s, CODATA 2018


def test_ev2kk_is_two_m_over_hbar2():
    # eV2kk converts eV -> A^-2 via E = hbar^2 k^2 / 2 m; the module defines
    # it from the 2.07212465 meV*A^2 constant while neutron_mass_evc2/hbar
    # come from CODATA 2018 entries, so agree to ~1e-7
    assert u.eV2kk == pytest.approx(2 * u.neutron_mass_evc2 / u.hbar**2, rel=1e-5)
    assert u.eV2kk == pytest.approx(1 / 2.072124652399821e-3)


def test_boltzmann_and_angular_frequency_pairs():
    # kb (with eV/K units folded in) and boltzmann (eV/K) are two vintages
    assert u.kb == pytest.approx(u.boltzmann, rel=1e-5)
    assert u.radpsec2eV == u.hbar
    assert u.eV2radpsec == 1.0 / u.radpsec2eV


def test_mass_constants_definitional():
    # atomic_mass is defined from the neutron mass and its atomic mass unit
    assert u.atomic_mass == u.neutron_mass_evc2 / u.neutron_atomic_mass
    # ekin2v is the sqrt(2/m) prefactor giving velocity in Aa/s
    assert u.ekin2v == np.sqrt(2.0 / u.neutron_mass_evc2)
    # cross-check the two neutron-mass vintages: a mass in eV/(Aa/s)^2 equals
    # m[kg] * 1e-20 / 1.602176634e-19 (1 Aa/s = 1e-10 m/s), i.e. m[kg]/16.02
    assert u.neutron_mass_evc2 == \
        pytest.approx(u.neutron_mass * 1e-3 / 16.02176634, rel=1e-8)
    # the classic thermal anchor: ekin2v*sqrt(25.3 meV) = 2200 m/s
    v_ms = u.ekin2v * np.sqrt(25.3e-3) * 1e-10  # Aa/s -> m/s
    assert v_ms == pytest.approx(2200.0, rel=1e-4)


def test_umass_matches_dalton():
    # umass is 931.494095 MeV/c^2 expressed in eV/(Aa/s)^2, so multiplying by
    # c^2 restores the eV/c^2 value, which must match dalton2eVc2
    assert u.umass * u.c**2 == pytest.approx(u.dalton2eVc2, rel=1e-8)


def test_angle_and_meV_frequency_ladders():
    assert u.deg2rad == np.pi / 180.0
    assert u.radpsec2meV == u.radpsec2eV * 1e3
    assert u.radpfs2meV == u.radpsec2meV * 1e15
