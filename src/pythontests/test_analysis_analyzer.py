"""Unit tests for MCPL_Analyzer_1D/2D construction and unit-converter logic.

No MCPL file is read anywhere: auto_range_file defaults to '' and the
constructors only set up binning and converters (ctor ~0.1 ms). The unit
converters, recoverer and axis labels are pinned against the UNITEnum
factor tables also covered by test_analysis_units.py.
"""
import numpy as np
import pytest

from Cinema.analysis import (
    MCPL_Analyzer_1D,
    MCPL_Analyzer_2D,
    MomentumTransferQParameters,
    ParticleParameter,
    ScatteringAngleParameters,
)


# ------------------------------------------------------------- 1D: parameter
def test_string_para_converts_to_enum():
    analyser = MCPL_Analyzer_1D(para='time')
    assert analyser.para is ParticleParameter.TIME


def test_invalid_para_type_raises():
    with pytest.raises(ValueError, match='Invalid parameter type'):
        MCPL_Analyzer_1D(para=3.14)


def test_direct_param_with_incident_params_raises():
    # a direct MCPL parameter must not come with incident parameters
    with pytest.raises(ValueError, match='does not require'):
        MCPL_Analyzer_1D(
            para='time',
            incident_params=ScatteringAngleParameters(incident_wavelength_A=4.0))


def test_calculated_param_without_incident_raises():
    with pytest.raises(ValueError, match='requires incident parameters'):
        MCPL_Analyzer_1D(para='momentum_transfer_q')


def test_wavelength_and_velocity_construct_without_incident():
    # documented special case: both depend only on the outgoing energy
    analyser_wl = MCPL_Analyzer_1D(para='wavelength')
    analyser_v = MCPL_Analyzer_1D(para='velocity')
    assert analyser_wl.para is ParticleParameter.WAVELENGTH
    assert analyser_v.para is ParticleParameter.VELOCITY
    assert analyser_wl.incident_params is None
    assert analyser_v.incident_params is None


def test_wrong_incident_class_names_required_class():
    # Q needs MomentumTransferQParameters; a ScatteringAngleParameters
    # instance must be rejected by name
    with pytest.raises(ValueError, match='MomentumTransferQParameters'):
        MCPL_Analyzer_1D(
            para='momentum_transfer_q',
            incident_params=ScatteringAngleParameters(incident_wavelength_A=4.0))


# ---------------------------------------------------------- 1D: unit logic
def test_time_ms_to_us_converter():
    analyser = MCPL_Analyzer_1D(para='time', unit='us')
    # default storage unit for time is ms; 2 ms == 2000 us
    assert analyser.demanded_unit is not analyser.default_unit
    assert analyser.unit_converter(2.0) == pytest.approx(2000.0)


def test_recoverer_inverts_converter():
    analyser = MCPL_Analyzer_1D(para='time', unit='us')
    recover = analyser._get_unit_recoverer()
    value = 123.4
    assert recover(analyser.unit_converter(value)) == pytest.approx(value)
    values = np.linspace(0.0, 10.0, 8)
    assert np.allclose(recover(analyser.unit_converter(values)), values)


def test_label_axis_composes_label_and_unit_symbol():
    analyser = MCPL_Analyzer_1D(para='time')  # no unit demanded -> default ms
    assert analyser.demanded_unit is analyser.default_unit
    assert analyser.label_axis == \
        ParticleParameter.TIME.get_label() + f", {analyser.demanded_unit.symbol}"
    assert analyser.label_axis.startswith('Time of Flight')
    assert r'$\mathrm{ms}$' in analyser.label_axis


# ------------------------------------------------------------------ 2D
def test_2d_label_axes_compose_independently():
    analyser = MCPL_Analyzer_2D(x_para='time', y_para='ekin',
                                x_unit='us', y_unit='meV')
    assert analyser.label_axis_x == \
        ParticleParameter.TIME.get_label() + f", {analyser.x_demanded_unit.symbol}"
    assert analyser.label_axis_y == \
        ParticleParameter.KINETIC_ENERGY.get_label() + f", {analyser.y_demanded_unit.symbol}"
    assert r'$\mu\mathrm{s}$' in analyser.label_axis_x
    assert r'$\mathrm{meV}$' in analyser.label_axis_y


def test_2d_converters_use_independent_units():
    analyser = MCPL_Analyzer_2D(x_para='time', y_para='ekin',
                                x_unit='us', y_unit='meV')
    # x: 2 ms -> 2000 us ; y: 2 MeV -> 2e9 meV
    assert analyser.x_unit_converter(2.0) == pytest.approx(2000.0)
    assert analyser.y_unit_converter(2.0) == pytest.approx(2.0e9)


def test_2d_validation_error_names_the_axis():
    with pytest.raises(ValueError, match='x-axis'):
        MCPL_Analyzer_2D(x_para='momentum_transfer_q')
