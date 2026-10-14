"""Unit tests for Cinema.analysis UNITEnum factor tables and ParticleParameter.

The conversion factors are pinned against physical anchors (SI prefixes and
geometric identities), not just against themselves, so a constant inversion
regression (like the 2026-10 eV/meV flip in the related convertor family)
cannot pass. All bodies are pure numpy arithmetic in the microsecond-to-
low-millisecond range; the shared libprompt_core load happens at collection.
"""
import numpy as np
import pytest

from Cinema.analysis import (
    AngleUnit,
    EnergyUnit,
    LengthUnit,
    MomentumTransferUnit,
    ParticleParameter,
    ScatteringAngleParameters,
    TimeUnit,
    VelocityUnit,
    WavelengthUnit,
    MomentumTransferQParameters,
)


# ------------------------------------------------------------------ TimeUnit
def test_time_unit_conversions():
    # factor tables are relative to ms; s must be 1000x larger
    assert TimeUnit.SECOND.convert_to(1.0, TimeUnit.MILLISECOND) == pytest.approx(1000.0)
    assert TimeUnit.MILLISECOND.convert_to(2.0, TimeUnit.MICROSECOND) == pytest.approx(2000.0)


def test_time_unit_from_str_invalid_raises():
    with pytest.raises(ValueError, match='Invalid unit.*availables'):
        TimeUnit.from_str('banana')


# ---------------------------------------------------------------- EnergyUnit
def test_energy_unit_conversions():
    # 1 MeV is exactly 1e6 eV
    assert EnergyUnit.MEGAEV.convert_to(1.0, EnergyUnit.EV) == pytest.approx(1e6)
    # 25.3 meV must be 0.0253 eV (regression anchor for the inverted
    # eV/meV constant family fixed 2026-10)
    assert EnergyUnit.MILLIEV.convert_to(25.3, EnergyUnit.EV) == pytest.approx(0.0253)


def test_energy_unit_array_conversion():
    values = np.full(1000, 25.3)
    out = EnergyUnit.MILLIEV.convert_to(values, EnergyUnit.EV)
    assert out.shape == (1000,)
    assert np.allclose(out, 0.0253)


# ---------------------------------------------------------------- LengthUnit
def test_length_unit_ladder():
    # 2 m == 200 cm == 2000 mm
    two_m = 2.0
    assert LengthUnit.METER.convert_to(two_m, LengthUnit.CENTIMETER) == pytest.approx(200.0)
    assert LengthUnit.METER.convert_to(two_m, LengthUnit.MILLIMETER) == pytest.approx(2000.0)
    assert LengthUnit.MILLIMETER.convert_to(2000.0, LengthUnit.CENTIMETER) == pytest.approx(200.0)


# ----------------------------------------------------------------- AngleUnit
def test_angle_unit_cosine_to_degrees():
    # arccos(0.5) is exactly 60 degrees
    assert AngleUnit.COSINE.convert_to(0.5, AngleUnit.DEGREES) == pytest.approx(60.0)


def test_angle_unit_degrees_to_radians():
    assert AngleUnit.DEGREES.convert_to(180.0, AngleUnit.RADIANS) == pytest.approx(np.pi)


def test_angle_unit_radians_to_cosine():
    assert AngleUnit.RADIANS.convert_to(np.pi, AngleUnit.COSINE) == pytest.approx(-1.0)


def test_angle_unit_same_unit_identity():
    value = 0.37
    assert AngleUnit.COSINE.convert_to(value, AngleUnit.COSINE) == pytest.approx(value)
    arr = np.linspace(-0.9, 0.9, 7)
    assert np.allclose(AngleUnit.DEGREES.convert_to(arr, AngleUnit.DEGREES), arr)


# ------------------------------------------------------- MomentumTransferUnit
def test_momentum_transfer_unit_angstrom_inverse():
    # 1 AA^-1 == 10 nm^-1
    assert MomentumTransferUnit.ANGSTROM_INVERSE.convert_to(
        1.0, MomentumTransferUnit.NANOMETER_INVERSE) == pytest.approx(10.0)


# ------------------------------------------------------------- WavelengthUnit
def test_wavelength_unit_angstrom_to_nm():
    assert WavelengthUnit.ANGSTROM.convert_to(1.0, WavelengthUnit.NANOMETER) == \
        pytest.approx(0.1)


# --------------------------------------------------------------- VelocityUnit
def test_velocity_unit_m_per_s_to_mm_per_s():
    # thermal neutron 2200 m/s == 2.2e6 mm/s
    assert VelocityUnit.METER_PER_SECOND.convert_to(
        2200.0, VelocityUnit.MILLIMETER_PER_SECOND) == pytest.approx(2.2e6)


# ---------------------------------------------------------------- defaults
def test_get_default_all_families():
    assert TimeUnit.get_default() is TimeUnit.MILLISECOND
    assert EnergyUnit.get_default() is EnergyUnit.MEGAEV
    assert LengthUnit.get_default() is LengthUnit.CENTIMETER
    assert AngleUnit.get_default() is AngleUnit.COSINE
    assert MomentumTransferUnit.get_default() is MomentumTransferUnit.ANGSTROM_INVERSE
    assert WavelengthUnit.get_default() is WavelengthUnit.ANGSTROM
    assert VelocityUnit.get_default() is VelocityUnit.MILLIMETER_PER_SECOND


# ------------------------------------------------------------------ symbols
def test_symbols_are_latex_strings():
    expectations = {
        TimeUnit.MILLISECOND: r'$\mathrm{ms}$',
        TimeUnit.MICROSECOND: r'$\mu\mathrm{s}$',
        EnergyUnit.EV: r'$\mathrm{eV}$',
        LengthUnit.CENTIMETER: r'$\mathrm{cm}$',
        AngleUnit.COSINE: r'$\cos$',
        MomentumTransferUnit.ANGSTROM_INVERSE: r'$\mathrm{\AA}^{-1}$',
        WavelengthUnit.ANGSTROM: r'$\mathrm{\AA}$',
        VelocityUnit.MILLIMETER_PER_SECOND: r'$\mathrm{mm/s}$',
    }
    for unit, symbol in expectations.items():
        assert unit.symbol == symbol


# -------------------------------------------------------- ParticleParameter
def test_particle_parameter_unit_mapping():
    assert ParticleParameter.TIME.unit is TimeUnit
    assert ParticleParameter.KINETIC_ENERGY.unit is EnergyUnit
    assert ParticleParameter.MOMENTUM_TRANSFER_Q.unit is MomentumTransferUnit
    assert ParticleParameter.WAVELENGTH.unit is WavelengthUnit
    assert ParticleParameter.VELOCITY.unit is VelocityUnit


def test_particle_parameter_labels():
    assert ParticleParameter.TIME.get_label() == 'Time of Flight'
    assert ParticleParameter.KINETIC_ENERGY.get_label() == 'Kinetic Energy'
    assert ParticleParameter.MOMENTUM_TRANSFER_Q.get_label() == 'Momentum Transfer Q'


def test_particle_parameter_is_calculated():
    calculated = [
        ParticleParameter.MOMENTUM_TRANSFER_Q,
        ParticleParameter.ENERGY_TRANSFER_OMEGA,
        ParticleParameter.SCATTERING_ANGLE,
        ParticleParameter.WAVELENGTH,
        ParticleParameter.VELOCITY,
    ]
    for param in calculated:
        assert param.is_calculated() is True
    # direct MCPL parameters are not calculated
    for param in (ParticleParameter.TIME, ParticleParameter.KINETIC_ENERGY,
                  ParticleParameter.X_POSITION, ParticleParameter.PDG_CODE):
        assert param.is_calculated() is False


def test_particle_parameter_required_incident_class():
    assert ParticleParameter.MOMENTUM_TRANSFER_Q.get_required_incident_class() is \
        MomentumTransferQParameters
    assert ParticleParameter.SCATTERING_ANGLE.get_required_incident_class() is \
        ScatteringAngleParameters
    # wavelength/velocity are calculated but need no incident parameters
    assert ParticleParameter.WAVELENGTH.get_required_incident_class() is None
    assert ParticleParameter.VELOCITY.get_required_incident_class() is None
    # direct parameters have no required incident class at all
    with pytest.raises(ValueError, match='not a calculated parameter'):
        ParticleParameter.TIME.get_required_incident_class()
