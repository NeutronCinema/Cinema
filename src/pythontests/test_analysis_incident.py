"""Unit tests for IncidentParameters subclasses and their calc() math.

All references are analytic or computed inline from the independent
Cinema.convertor functions, so the tests pin real physics rather than the
implementation. Concrete subclasses are used throughout because
IncidentParameters itself is abstract.

Note: from_string() is exercised on ScatteringAngleParameters, the subclass
whose __init__ accepts direction/sample kwargs; EnergyTransferOmegaParameters
restricts its __init__ to the two energy arguments and would reject the
direction keys.
"""
import numpy as np
import pytest

from Cinema import convertor
from Cinema.analysis import (
    EnergyTransferOmegaParameters,
    MomentumTransferQParameters,
    ScatteringAngleParameters,
)

# thermal anchor: 4 A <-> 81.81/wl^2 = 5.113 meV = 0.005113 eV
_WL = 4.0
_EIN_EV = convertor.wl2ekin(_WL)


# ------------------------------------------------------------- construction
def test_both_energy_and_wavelength_raise():
    with pytest.raises(ValueError, match='Cannot specify both'):
        EnergyTransferOmegaParameters(
            incident_energy_eV=0.005, incident_wavelength_A=4.0)


def test_neither_energy_nor_wavelength_raises():
    with pytest.raises(ValueError, match='Must specify either'):
        EnergyTransferOmegaParameters()


def test_negative_energy_raises():
    with pytest.raises(ValueError, match='must be positive'):
        EnergyTransferOmegaParameters(incident_energy_eV=-0.005)


def test_wavelength_energy_anchor():
    params = EnergyTransferOmegaParameters(incident_wavelength_A=_WL)
    assert params.incident_energy_eV == pytest.approx(81.81 / _WL**2 / 1000.0, rel=1e-3)
    assert params.incident_energy_eV == pytest.approx(0.005113, rel=1e-3)
    # the wavelength round-trips exactly
    assert params.incident_wavelength_A == pytest.approx(_WL)


def test_direction_and_sample_stored_as_float_tuples():
    params = ScatteringAngleParameters(
        incident_wavelength_A=_WL,
        incident_direction=(0, 0, 1),
        sample_position=(1, 2, 3),
    )
    assert params.incident_direction == (0.0, 0.0, 1.0)
    assert params.sample_position == (1.0, 2.0, 3.0)
    assert all(isinstance(x, float) for x in params.incident_direction)
    assert all(isinstance(x, float) for x in params.sample_position)
    assert len(params.incident_direction) == 3
    assert len(params.sample_position) == 3


def test_from_string_parses_full_config():
    params = ScatteringAngleParameters.from_string(
        'incident_energy_eV=0.005;incident_direction=(0,0,1);sample_position=(0,0,0)')
    assert params.incident_energy_eV == pytest.approx(0.005)
    assert params.incident_direction == (0.0, 0.0, 1.0)
    assert params.sample_position == (0.0, 0.0, 0.0)


# ------------------------------------------------- MomentumTransferQ calc
def test_q_backscatter_elastic_is_two_k():
    params = MomentumTransferQParameters(
        incident_wavelength_A=_WL, incident_direction=(0.0, 0.0, 1.0))
    particle_data = {
        'position': np.zeros((1, 3)),
        'direction': np.array([[0.0, 0.0, -1.0]]),  # exact backscattering
        'ekin': np.array([_EIN_EV * 1e-6]),         # elastic, MeV
    }
    q = params.calc(particle_data)
    # elastic backscattering: Q = 2k = 4*pi/lambda = pi for lambda=4 A
    assert q[0] == pytest.approx(4.0 * np.pi / _WL)
    assert q[0] == pytest.approx(3.14159, rel=1e-5)
    # same answer through the independent convertor reference
    assert q[0] == pytest.approx(convertor.angleCosine2Q(-1.0, _EIN_EV, _EIN_EV))


def test_q_forward_scattering_is_zero():
    params = MomentumTransferQParameters(
        incident_wavelength_A=_WL, incident_direction=(0.0, 0.0, 1.0))
    q = params.calc({
        'position': np.zeros((1, 3)),
        'direction': np.array([[0.0, 0.0, 1.0]]),  # unscattered
        'ekin': np.array([_EIN_EV * 1e-6]),
    })
    assert q[0] == pytest.approx(0.0, abs=1e-12)


def test_q_random_directions_match_inline_reference():
    rng = np.random.default_rng(2026)
    n = 32
    directions = rng.normal(size=(n, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    eout_eV = _EIN_EV * rng.uniform(0.2, 1.0, size=n)
    params = MomentumTransferQParameters(
        incident_wavelength_A=_WL, incident_direction=(0.0, 0.0, 1.0))
    q = params.calc({
        'position': np.zeros((n, 3)),
        'direction': directions,
        'ekin': eout_eV * 1e-6,
    })
    # reference computed inline from the convertor, not from the class
    angle_cos = directions @ np.array(params.incident_direction)
    reference = convertor.angleCosine2Q(angle_cos, _EIN_EV, eout_eV)
    assert np.allclose(q, reference)


# ----------------------------------------------- EnergyTransferOmega calc
def test_omega_is_incident_minus_outgoing_energy():
    params = EnergyTransferOmegaParameters(incident_wavelength_A=_WL)
    ekin_out_mev = 0.5e-6  # 0.5 eV
    omega = params.calc({'ekin': np.array([ekin_out_mev])})
    assert omega[0] == pytest.approx(_EIN_EV - convertor.MeV2eV(ekin_out_mev))
    assert omega[0] == pytest.approx(_EIN_EV - 0.5)


# ----------------------------------------------- ScatteringAngle calc
def test_scattering_angle_45deg_gives_sqrt_half():
    params = ScatteringAngleParameters(
        incident_wavelength_A=_WL, incident_direction=(1.0, 0.0, 0.0))
    cos = params.calc({'direction': np.array([[np.sqrt(0.5), np.sqrt(0.5), 0.0]])})
    assert cos[0] == pytest.approx(np.sqrt(0.5))


def test_scattering_angle_aligned_gives_one():
    params = ScatteringAngleParameters(
        incident_wavelength_A=_WL, incident_direction=(0.0, 0.0, 1.0))
    cos = params.calc({'direction': np.array([[0.0, 0.0, 1.0]])})
    assert cos[0] == pytest.approx(1.0)


def test_scattering_angle_output_is_clipped_cosine():
    params = ScatteringAngleParameters(
        incident_wavelength_A=_WL, incident_direction=(0.0, 0.0, 1.0))
    # non-normalized directions push the dot product beyond [-1, 1]; the
    # axis-1 dot must be clipped, never wrapped or left unbounded
    cos = params.calc({'direction': np.array([
        [0.0, 0.0, 2.0],     # dot =  2 -> clipped to  1
        [0.0, 0.0, -2.0],    # dot = -2 -> clipped to -1
        [1.0, 0.0, 0.0],     # orthogonal
        [0.0, np.sqrt(0.5), np.sqrt(0.5)],  # 45 degrees in the y-z plane
    ])})
    assert np.allclose(cos, [1.0, -1.0, 0.0, np.sqrt(0.5)])
