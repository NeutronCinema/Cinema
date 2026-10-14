"""Cross-checked unit-conversion coverage for Cinema.Interface.units,
Cinema.convertor and the analytic part of Cinema.Interface.helper.

Three independent angles of attack, all in the fast tier:

1. CODATA anchors - the constants inside the C kernels (h^2/2m_n in
   wl2ekin/ekin2wl, hbar^2/2m_n in eKin2k, m_n*c^-2 in ekin2v/v2ekin) are
   re-derived here from SI-2019 exact values (h, e) and the CODATA 2018
   neutron mass, so a mistyped constant fails even though every pair of
   module functions may round-trip cleanly against itself.
2. Pairwise round-trip matrix - every reversible edge the modules offer
   (ekin<->lambda, ekin<->velocity, ekin<->k, ekin<->angular frequency,
   Q<->elastic cosine, angle<->Q) is inverted on 20 log-spaced values with
   f(g(x)) == x to 1e-10. There is no direct time<>energy pair in these
   modules; the time-like axis they expose is angular frequency via hbar,
   covered as the ekin-omega edges.
3. Dense-grid closed forms - helper.py kinematics (angle2Q, angle2Alpha,
   q2Alpha, minMaxQ, Bragg d-spacing chain) against textbook formulas.

Tolerances are chosen from measured behaviour: same-constant round trips
close to ~1e-15, while cross-constant identities (e.g. ekin2wl vs 2*pi/k,
whose C constants stem from slightly different CODATA vintages, ~8.9e-8
relative) and CODATA cross-checks (CODATA 2014 vs 2018 m_n, ~1.6e-8) are
pinned 10x above their measured offsets instead of at roundoff.
"""
import numpy as np
import pytest

from Cinema import convertor
from Cinema.Interface import helper as hp
from Cinema.Interface import units as u

# --------------------------------------------------------------------------
# SI-2019 exact / CODATA 2018 inputs, deliberately independent of Cinema
# --------------------------------------------------------------------------
H_J_S = 6.62607015e-34          # Planck constant (exact, SI-2019)
M_N_KG = 1.67492749804e-27      # neutron mass (CODATA 2018)
E_CHARGE = 1.602176634e-19      # elementary charge (exact, SI-2019)

# h^2/(2 m_n) in meV*A^2: the "81.8042" constant of neutron scattering.
H2_2M_MEV_AA2 = H_J_S**2 / (2.0 * M_N_KG) / (1e-3 * E_CHARGE) * 1e20
# hbar^2/(2 m_n) in eV*A^2: E = hbar^2 k^2 / 2m means E[k = 1 A^-1] == this.
HBAR2_2M_EV_AA2 = H2_2M_MEV_AA2 * 1e-3 / (2.0 * np.pi)**2
# thermal-neutron family, all from the closed forms above
V_THERMAL_MS = np.sqrt(2.0 * 25.3e-3 * E_CHARGE / M_N_KG)   # 2200.05 m/s
WL_THERMAL_AA = np.sqrt(H2_2M_MEV_AA2 / 25.3)               # 1.79816 A
E_2200MS_EV = 0.5 * M_N_KG * 2200.0**2 / E_CHARGE           # 25.2989 meV


# --------------------------------------------------------------------------
# CODATA anchors for the hard-coded kernel constants
# --------------------------------------------------------------------------
def test_wl2ekin_codata_one_angstrom():
    # E[eV] = (h^2/2m_n)[eV A^2] / lambda[A]^2; the C kernel hardcodes
    # 0.081804209605330899 eV*A^2, which matches CODATA to 9e-9 relative.
    h2_2m_ev = H2_2M_MEV_AA2 * 1e-3
    assert convertor.wl2ekin(1.0) == pytest.approx(h2_2m_ev, rel=1e-7)
    # ekin2wl is its exact algebraic inverse: lambda = sqrt(h^2/2m / E)
    assert convertor.ekin2wl(1.0) == pytest.approx(np.sqrt(h2_2m_ev), rel=1e-7)


def test_wl2ekin_dense_grid_codata():
    wl = np.geomspace(0.3, 12.0, 40)
    assert convertor.wl2ekin(wl) == pytest.approx(
        H2_2M_MEV_AA2 * 1e-3 / wl**2, rel=1e-7)


def test_ekin2k_ksquared_constant_codata():
    # E = hbar^2 k^2 / 2m_n -> E[k = 1 A^-1] = hbar^2/2m_n = 2.0721 meV
    assert hp.k2eKin(1.0) == pytest.approx(HBAR2_2M_EV_AA2, rel=1e-6)
    assert 1.0 / u.eV2kk == pytest.approx(HBAR2_2M_EV_AA2, rel=1e-6)
    # closed form over a dense grid: k(E) = sqrt(E / (hbar^2/2m))
    e = np.geomspace(1e-5, 1.0, 40)
    assert convertor.eKin2k(e) == pytest.approx(
        np.sqrt(e / HBAR2_2M_EV_AA2), rel=5e-7)


def test_thermal_253mev_velocity_family():
    # v = sqrt(2 E / m_n) from CODATA: 25.3 meV <-> 2200.05 m/s
    assert convertor.ekin2v(25.3e-3) == pytest.approx(V_THERMAL_MS * 1e3, rel=1e-7)
    # the classic "2200 m/s" label holds to 5 digits (agreement is ~2e-6)
    assert convertor.ekin2v(25.3e-3) == pytest.approx(2.2e6, rel=1e-4)
    # inverse direction: a 2200 m/s neutron carries 25.2989 meV
    assert convertor.v2ekin(2200.0e3) == pytest.approx(E_2200MS_EV, rel=1e-7)


def test_thermal_253mev_wavelength_family():
    # lambda = sqrt((h^2/2m_n)/E): 25.3 meV <-> 1.7981568 A (7 digits)
    assert convertor.ekin2wl(25.3e-3) == pytest.approx(WL_THERMAL_AA, rel=1e-7)
    # the lambda -> E -> v chain lands on the same family: a 1.8 A neutron
    # moves at sqrt(2*E_CODATA(1.8 A)/m_n)
    e18 = H2_2M_MEV_AA2 * 1e-3 / 1.8**2
    assert convertor.ekin2v(convertor.wl2ekin(1.8)) == pytest.approx(
        np.sqrt(2.0 * e18 * E_CHARGE / M_N_KG) * 1e3, rel=1e-6)


def test_planck_hbar_and_angular_frequency_dense():
    # h in eV*s is pure arithmetic from the SI-2019 definitions
    h_ev_s = H_J_S / E_CHARGE
    # abs=0: these magnitudes (~4e-15) are below approx's default abs floor
    assert u.planck == pytest.approx(h_ev_s, rel=1e-15, abs=0.0)
    assert u.hbar == pytest.approx(h_ev_s / (2.0 * np.pi), rel=3e-15, abs=0.0)
    # helper.angularFre2eKin(omega) == hbar*omega on a dense grid
    omega = np.geomspace(1e12, 1e16, 40)
    expect = omega * h_ev_s / (2.0 * np.pi)
    assert hp.angularFre2eKin(omega) == pytest.approx(expect, rel=1e-14)
    assert hp.eKin2AngularFre(expect) == pytest.approx(omega, rel=1e-14)


def test_neutron_mass_consistent_across_layers():
    # units.py stores m_n*c^-2 in eV/(Aa/s)^2; the C speed kernels work in
    # mm/s, and 1 mm/s = 1e7 Aa/s lifts the numeric mass by 1e14
    v = 3.7e6  # mm/s
    assert convertor.v2ekin(v) == pytest.approx(
        0.5 * u.neutron_mass_evc2 * 1e14 * v * v, rel=1e-9)
    e = np.geomspace(1e-6, 1.0, 20)
    assert convertor.ekin2v(e) == pytest.approx(
        u.ekin2v * np.sqrt(e) * 1e-7, rel=1e-9)
    # CODATA view of the same constant: m_n c^-2 = m[kg]/e[eV] * 1e-6 in
    # eV/(mm/s)^2 because c = 2.998e11 mm/s (abs=0, see planck test)
    m_codata_mm = M_N_KG / E_CHARGE * 1e-6
    assert u.neutron_mass_evc2 * 1e14 == pytest.approx(
        m_codata_mm, rel=1e-7, abs=0.0)


def test_lambda_and_k_constants_tell_same_story():
    # ekin2wl uses h^2/2m while eKin2k uses hbar^2/2m; physics demands
    # lambda == 2*pi/k. The two C constants come from slightly different
    # CODATA vintages (8.9e-8 relative), so pin to 1e-6, not to roundoff.
    # This is the check that actually fails if EITHER constant is mistyped,
    # which a within-family round trip (ekin->wl->ekin) cannot catch.
    e = np.geomspace(1e-6, 1.0, 20)
    assert convertor.ekin2wl(e) == pytest.approx(
        2.0 * np.pi / convertor.eKin2k(e), rel=1e-6)


# --------------------------------------------------------------------------
# pairwise round-trip matrix: f(g(x)) == x to 1e-10 on 20 log-spaced values
# --------------------------------------------------------------------------
E20 = np.geomspace(1e-6, 1.0, 20)       # eV
WL20 = np.geomspace(0.2, 20.0, 20)      # A
V20 = np.geomspace(2e3, 2e8, 20)        # mm/s (20 m/s .. 200 km/s)
K20 = np.geomspace(0.02, 20.0, 20)      # A^-1
OM20 = np.geomspace(1e10, 1e16, 20)     # rad/s

ROUNDTRIP_EDGES = [
    pytest.param(convertor.ekin2wl, convertor.wl2ekin, E20, id="ekin-lambda"),
    pytest.param(convertor.wl2ekin, convertor.ekin2wl, WL20, id="lambda-ekin"),
    pytest.param(convertor.ekin2v, convertor.v2ekin, E20, id="ekin-velocity"),
    pytest.param(convertor.v2ekin, convertor.ekin2v, V20, id="velocity-ekin"),
    pytest.param(convertor.eKin2k, hp.k2eKin, E20, id="ekin-k"),
    pytest.param(hp.k2eKin, convertor.eKin2k, K20, id="k-ekin"),
    pytest.param(hp.eKin2AngularFre, hp.angularFre2eKin, E20, id="ekin-omega"),
    pytest.param(hp.angularFre2eKin, hp.eKin2AngularFre, OM20, id="omega-ekin"),
]


@pytest.mark.parametrize("fwd,inv,start", ROUNDTRIP_EDGES)
def test_roundtrip_matrix(fwd, inv, start):
    # both directions of the pair on the same 20 log-spaced values
    np.testing.assert_allclose(inv(fwd(start)), start, rtol=1e-10, atol=0.0)
    np.testing.assert_allclose(fwd(inv(start)), start, rtol=1e-10, atol=0.0)


def test_roundtrip_q_via_elastic_cosine():
    # inverse pair: cos(theta) = 1 - Q^2/(2k^2) inverts the elastic branch
    # Q = 2k sin(theta/2) of convertor.angleCosine2Q; measured max error
    # 6e-14 over this range, so 1e-10 has real bite.
    energy = 0.0253
    k = convertor.eKin2k(energy)
    q = np.geomspace(0.02 * k, 1.99 * k, 20)
    cos = 1.0 - (q / k)**2 / 2.0
    assert np.all(np.abs(cos) <= 1.0)
    np.testing.assert_allclose(convertor.angleCosine2Q(cos, energy), q,
                               rtol=1e-10, atol=0.0)


def test_roundtrip_angle_via_q():
    # inverse pair: theta = 2*asin(Q/2k) inverts Q = 2k sin(theta/2)
    # (elastic, theta in degrees - the module's full-angle convention)
    energy = 0.0253
    k = convertor.eKin2k(energy)
    theta = np.linspace(0.5, 179.5, 20)
    q = hp.angle2Q(theta, energy, energy)
    back = 2.0 * np.degrees(np.arcsin(q / (2.0 * k)))
    np.testing.assert_allclose(back, theta, rtol=1e-10, atol=0.0)


def test_multihop_chain_returns_to_start():
    # ekin -> lambda -> ekin -> v -> ekin -> k -> ekin -> omega -> ekin:
    # four different kernel constants must chain back onto the start
    e0 = np.geomspace(1e-6, 1.0, 20)
    e1 = convertor.wl2ekin(convertor.ekin2wl(e0))
    e2 = convertor.v2ekin(convertor.ekin2v(e1))
    e3 = hp.k2eKin(convertor.eKin2k(e2))
    e4 = hp.angularFre2eKin(hp.eKin2AngularFre(e3))
    np.testing.assert_allclose(e4, e0, rtol=1e-10, atol=0.0)


# --------------------------------------------------------------------------
# vectorized numpy input vs scalar consistency
# --------------------------------------------------------------------------
VECTOR_FNS = [convertor.eKin2k, convertor.wl2ekin, convertor.ekin2wl,
              convertor.ekin2v, convertor.v2ekin]


@pytest.mark.parametrize("fn", VECTOR_FNS, ids=lambda f: f.__name__)
def test_scalar_and_vectorized_agree_bitwise(fn):
    # np.vectorize just loops the same C scalar kernel, so the array path
    # must be bit-for-bit identical to per-element scalar calls
    vals = np.geomspace(1e-5, 1.0, 12)
    arr = fn(vals)
    scal = np.array([fn(float(x)) for x in vals])
    assert arr.dtype == np.float64
    assert arr.shape == vals.shape
    assert np.array_equal(arr, scal)


def test_container_and_shape_inputs():
    # plain python containers route through the vectorized path
    out = convertor.wl2ekin([1.0, 2.0, 4.0])
    assert isinstance(out, np.ndarray) and out.shape == (3,)
    assert out == pytest.approx(convertor.wl2ekin(np.array([1.0, 2.0, 4.0])))
    assert convertor.ekin2v((0.0253,)).shape == (1,)
    # a 0-d numpy array is array-like: returns a 0-d ndarray, not a float
    res = convertor.ekin2wl(np.array(2.0))
    assert isinstance(res, np.ndarray) and res.shape == ()
    assert float(res) == convertor.ekin2wl(2.0)


def test_units_wrappers_shapes_and_broadcast():
    wl = np.geomspace(0.5, 5.0, 8)
    ekin = convertor.wl2ekin_units(wl, 'meV')
    assert ekin.shape == (8,)
    assert ekin == pytest.approx(convertor.wl2ekin(wl) * 1e3)
    assert convertor.ekin2wl_units(ekin, 'meV') == pytest.approx(wl, rel=1e-12)
    # a (5,1) cosine grid broadcasts against (2,) energies to (5,2)
    cos = np.linspace(-0.9, 0.9, 5)[:, None]
    ein = np.array([0.01, 0.03])
    assert convertor.angleCosine2Q_units(cos, ein).shape == (5, 2)


# --------------------------------------------------------------------------
# energy prefix ladder and the *_units wrappers
# --------------------------------------------------------------------------
def test_prefix_ladder_exact_powers_of_ten():
    # exact double literals: 1.0 * 1e3 == 1e3 bit-for-bit
    assert convertor.meV2eV(1.0) == 1e-3
    assert convertor.eV2meV(1.0) == 1e3
    assert convertor.keV2eV(1.0) == 1e3
    assert convertor.eV2keV(1.0) == 1e-3
    assert convertor.MeV2eV(1.0) == 1e6
    assert convertor.eV2MeV(1.0) == 1e-6


def test_prefix_roundtrips_dense_grid():
    e = np.geomspace(1e-9, 1e9, 33)
    for forth, back in ((convertor.eV2meV, convertor.meV2eV),
                        (convertor.eV2keV, convertor.keV2eV),
                        (convertor.eV2MeV, convertor.MeV2eV)):
        assert back(forth(e)) == pytest.approx(e, rel=1e-15)


@pytest.mark.parametrize("unit,factor", [("eV", 1.0), ("meV", 1e3),
                                         ("keV", 1e-3), ("MeV", 1e-6)])
def test_units_wrapper_roundtrip_per_unit(unit, factor):
    wl = np.geomspace(0.3, 8.0, 20)
    ekin = convertor.wl2ekin_units(wl, unit)
    assert ekin == pytest.approx(convertor.wl2ekin(wl) * factor, rel=1e-12)
    np.testing.assert_allclose(convertor.ekin2wl_units(ekin, unit), wl,
                               rtol=1e-10, atol=0.0)


def test_anglecosine_units_mixed_units():
    # enin in meV and enout in keV must match the hand-converted eV call
    q = convertor.angleCosine2Q_units(-0.5, 25.3, enin_unit='meV',
                                      enout=0.05, enout_unit='keV')
    assert q == pytest.approx(convertor.angleCosine2Q(-0.5, 25.3e-3, 50.0),
                              rel=1e-15)


def test_unit_strings_are_case_sensitive():
    # 'meV' and 'MeV' differ by 9 orders of magnitude, and Q ~ sqrt(E)
    q_meV = convertor.angleCosine2Q_units(0.5, 25.3, enin_unit='meV')
    q_MeV = convertor.angleCosine2Q_units(0.5, 25.3, enin_unit='MeV')
    assert q_MeV / q_meV == pytest.approx(np.sqrt(1e9), rel=1e-12)


def test_unknown_unit_strings_raise_valueerror():
    # unknown units must fail loudly, not fall back to eV (a 1000x error
    # for meV input); matching is exact, so no case folding either
    for bad in ('EV', 'kev', 'GeV', '', ' meV', 'meV '):
        with pytest.raises(ValueError, match='unsupported energy unit'):
            convertor.angleCosine2Q_units(0.5, 1.0, enin_unit=bad)
        with pytest.raises(ValueError, match='unsupported energy unit'):
            convertor.ekin2wl_units(1.0, bad)
        with pytest.raises(ValueError, match='unsupported energy unit'):
            convertor.wl2ekin_units(1.0, bad)
    # the offending argument name is reported for debuggability
    with pytest.raises(ValueError, match='enin_unit'):
        convertor.angleCosine2Q_units(0.5, 1.0, enin_unit='GeV')
    with pytest.raises(ValueError, match='ekin_unit'):
        convertor.ekin2wl_units(1.0, 'GeV')


# --------------------------------------------------------------------------
# helper.py closed forms on dense grids
# --------------------------------------------------------------------------
def test_angle2q_dense_elastic_closed_form():
    # Convention pin: helper.angle2Q takes the FULL scattering angle in
    # degrees and returns Q = 2k*sin(theta/2) for elastic scattering.
    # Grid starts at 0.5 deg: below that the 1-cos(theta) cancellation in
    # the kernel dominates the rounding (measured 2.5e-10 rel at 0.02 deg).
    energy = 0.0253
    k = hp.eKin2k(energy)
    theta = np.linspace(0.5, 179.98, 512)
    q = hp.angle2Q(theta, energy, energy)
    assert q == pytest.approx(2.0 * k * np.sin(np.radians(theta) / 2.0),
                              rel=1e-11)
    # a second energy keeps it from being a one-constant accident
    e2 = 1.3e-3
    k2 = hp.eKin2k(e2)
    sub = theta[::4]
    assert hp.angle2Q(sub, e2, e2) == pytest.approx(
        2.0 * k2 * np.sin(np.radians(sub) / 2.0), rel=1e-11)


def test_helper_and_convertor_anglecosine_agree_dense():
    # the python helper and the C-backed convertor implement the same
    # closed form; they must agree over a dense (cos, energy-ratio) grid
    cosg = np.linspace(-0.99, 0.99, 41)
    rat = np.geomspace(0.25, 4.0, 41)
    cc, rr = np.meshgrid(cosg, rat, indexing='ij')
    ei = 0.019
    assert convertor.angleCosine2Q(cc, ei, ei * rr) == \
        pytest.approx(hp.angleCosine2Q(cc, ei, ei * rr), rel=1e-13)


def test_anglecosine_law_of_cosines_dense():
    # general branch: Q = |k1 - k0| = sqrt(k0^2 + k1^2 - 2 k0 k1 cos(theta)).
    # Cosines stop at 0.95 because the forward limit (k1 ~ k0, theta ~ 0)
    # cancels catastrophically in BOTH formulations and only agrees to the
    # cancellation error, not to the formula.
    ei = 0.041
    cosg = np.linspace(-1.0, 0.95, 61)
    rat = np.geomspace(0.25, 4.0, 61)
    cc, rr = np.meshgrid(cosg, rat, indexing='ij')
    k0 = np.sqrt(ei * u.eV2kk)
    k1 = k0 * np.sqrt(rr)
    expect = np.sqrt(k0**2 + k1**2 - 2.0 * k0 * k1 * cc)
    assert convertor.angleCosine2Q(cc, ei, ei * rr) == \
        pytest.approx(expect, rel=1e-12)


def test_q2alpha_codata_dense():
    # alpha = Q^2 * hbar^2/(2 m_n kT): the module folds hbar^2/2m into
    # eV2kk, here re-derived from CODATA instead
    kt = 0.0253
    q = np.geomspace(0.05, 30.0, 200)
    alpha = hp.q2Alpha(q, kt)
    assert alpha == pytest.approx(q**2 * HBAR2_2M_EV_AA2 / kt, rel=1e-6)
    # alpha is linear in 1/kT
    assert hp.q2Alpha(q, 10 * kt) == pytest.approx(alpha / 10.0, rel=1e-15)


def test_alpha2q_dense_roundtrip():
    kt = 0.045
    q = np.geomspace(0.01, 50.0, 200)
    assert hp.alpha2Q(hp.q2Alpha(q, kt), kt) == pytest.approx(q, rel=1e-12)


def test_angle2alpha_dense_closed_form():
    # angle2Alpha is the direct energy form:
    # alpha = (Ei + Ef - 2 sqrt(Ei Ef) cos(theta)) / kT
    kt = 0.03
    theta = np.linspace(0.0, 180.0, 181)
    ei = 0.02
    for ratio in (0.5, 1.0, 2.7):
        ef = ei * ratio
        alpha = hp.angle2Alpha(theta, ei, ef, kt)
        expect = (ei + ef - 2.0 * np.sqrt(ei * ef) * np.cos(np.radians(theta))) / kt
        assert alpha == pytest.approx(expect, rel=1e-13)
        # and it equals q2Alpha(angle2Q(...)) through the Q route
        assert alpha == pytest.approx(
            hp.q2Alpha(hp.angle2Q(theta, ei, ef), kt), rel=1e-12)


def test_minmaxq_dense_ratio_grid():
    # kinematic limits of the momentum transfer: qmin = |k0-k1| (forward),
    # qmax = k0+k1 (backward). Grid kept away from ratio 1 where the qmin
    # subtraction cancels; nearest ratio here is 0.95.
    ei = 0.062
    k0 = hp.eKin2k(ei)
    rat = np.geomspace(0.05, 20.0, 64)
    ef = ei * rat
    qmin, qmax = hp.minMaxQ(np.full_like(rat, ei), ef)
    assert qmin == pytest.approx(k0 * np.abs(1.0 - np.sqrt(rat)), rel=1e-12)
    assert qmax == pytest.approx(k0 * (1.0 + np.sqrt(rat)), rel=1e-12)
    # the bounds are exactly angle2Q evaluated at 0 and 180 degrees
    assert qmin == pytest.approx(hp.angle2Q(np.zeros_like(rat), ei, ef),
                                 rel=1e-12)
    assert qmax == pytest.approx(hp.angle2Q(np.full_like(rat, 180.0), ei, ef),
                                 rel=1e-12)


def test_bragg_dspacing_chain():
    # first-order Bragg: lambda = 2 d sin(theta_Bragg); elastic scattering
    # off that lattice plane gives Q = 2k sin(theta_full/2) with
    # theta_full = 2*theta_Bragg (the module's full-angle convention), so
    # the whole chain must collapse onto Q = 2*pi/d.
    theta_b = 45.0
    d = np.geomspace(0.5, 20.0, 50)
    lam = 2.0 * d * np.sin(np.radians(theta_b))
    ekin = convertor.wl2ekin(lam)
    q = hp.angle2Q(np.full_like(d, 2.0 * theta_b), ekin, ekin)
    # 1e-6, not roundoff: the chain crosses both the h^2/2m and hbar^2/2m
    # kernel constants, whose CODATA vintages differ by ~9e-8 relative
    assert q == pytest.approx(2.0 * np.pi / d, rel=1e-6)
