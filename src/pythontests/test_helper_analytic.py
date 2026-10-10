"""Numeric coverage for Cinema.Interface.helper.

helper.py is used everywhere (S(q,w) post-processing, SANS reducers, VDOS)
but had zero numeric test coverage. Every function tested here is pure
python/numpy math, so each body runs in microseconds-to-milliseconds with a
seeded RNG. Behaviour that looks surprising but is intentional/known is
pinned as such (takfft's fftshift asymmetry, calHKL's half-space sampling).
"""
import time

import numpy as np
import pytest

from Cinema.Interface import helper as hp
from Cinema.Interface import units as u


# --------------------------------------------------------------- kinematics
def test_k2ekin_identity_and_definition():
    energy = 0.0253
    assert hp.k2eKin(hp.eKin2k(energy)) == pytest.approx(energy, rel=1e-15)
    k = 1.7
    assert hp.k2eKin(k) == pytest.approx(k * k / u.eV2kk, rel=1e-15)
    # the python eKin2k mirrors the convertor definition
    assert hp.eKin2k(energy) == pytest.approx(np.sqrt(energy * u.eV2kk), rel=1e-15)


def test_angle2q_elastic_closed_form():
    energy = 0.0253
    k = hp.eKin2k(energy)
    for t_deg in (1.0, 37.0, 90.0, 143.0, 179.0):
        assert hp.angle2Q(t_deg, energy, energy) == \
            pytest.approx(2 * k * np.sin(t_deg * u.deg2rad / 2), rel=1e-14)


def test_angle2q_backward_limit():
    # cos(pi) with a 4x energy gain: Q = k0 + k1, k1 = 2 k0
    energy = 0.0253
    k0 = hp.eKin2k(energy)
    assert hp.angle2Q(180.0, energy, 4 * energy) == \
        pytest.approx(k0 + 2 * k0, rel=1e-14)


def test_angle2q_forward_limit():
    energy = 0.0253
    k0 = hp.eKin2k(energy)
    # cos(0) elastic: Q = 0 ...
    assert hp.angle2Q(0.0, energy, energy) == pytest.approx(0.0, abs=1e-15)
    # ... and cos(0) with a 4x gain: Q = |k1 - k0| = k0
    assert hp.angle2Q(0.0, energy, 4 * energy) == \
        pytest.approx(2 * k0 - k0, rel=1e-14)


def test_angle2alpha_matches_q2alpha():
    # angle2Alpha is the direct energy form of q2Alpha(angle2Q(...))
    kt = 0.0253
    for t_deg in (10.0, 37.0, 90.0, 150.0):
        direct = hp.angle2Alpha(t_deg, 0.02, 0.05, kt)
        via_q = hp.q2Alpha(hp.angle2Q(t_deg, 0.02, 0.05), kt)
        assert direct == pytest.approx(via_q, rel=1e-12)


def test_alpha2q_inverse_of_q2alpha():
    q = np.array([0.5, 1.0, 3.0, 7.0])
    kt = 0.0253
    assert hp.alpha2Q(hp.q2Alpha(q, kt), kt) == pytest.approx(q, rel=1e-15)


def test_minmaxq_limits_and_error():
    energy_in, energy_out = 0.0253, 0.1012
    k0, k1 = hp.eKin2k(energy_in), hp.eKin2k(energy_out)
    qmin, qmax = hp.minMaxQ(np.array([energy_in]), np.array([energy_out]))
    assert qmin == pytest.approx(abs(k0 - k1), rel=1e-14)
    assert qmax == pytest.approx(k0 + k1, rel=1e-14)
    # the limits are angle2Q evaluated at 0 and 180 degrees
    assert qmin == pytest.approx(hp.angle2Q(0.0, energy_in, energy_out), rel=1e-14)
    assert qmax == pytest.approx(hp.angle2Q(180.0, energy_in, energy_out), rel=1e-14)
    with pytest.raises(RuntimeError, match='Negative energy'):
        hp.minMaxQ(np.array([0.02]), np.array([-0.01]))


def test_angular_frequency_energy_pair():
    energy = 0.033
    # roundtrip through hbar
    assert hp.angularFre2eKin(hp.eKin2AngularFre(energy)) == \
        pytest.approx(energy, rel=1e-15)
    # 1 THz ordinary frequency == 4.1357 meV; angularFre2eKin expects the
    # angular form, so the ordinary frequency enters as 2*pi*f
    assert hp.angularFre2eKin(2 * np.pi * 1e12) == \
        pytest.approx(u.planck * 1e12, rel=1e-15)
    assert hp.angularFre2eKin(2 * np.pi * 1e12) == pytest.approx(4.1357e-3, rel=1e-5)


# ------------------------------------------------------------- array tools
def test_next_good_number():
    assert hp.nextGoodNumber(64) == 64
    assert hp.nextGoodNumber(65) == 128
    assert hp.nextGoodNumber(100) == 128
    assert hp.nextGoodNumber(1) == 1


def test_gen_log_spacing_layout():
    idx = hp.genLogSpacing(1000, 10)
    # starts at 0, strictly increasing, no duplicates
    assert idx[0] == 0
    assert np.all(np.diff(idx) > 0)
    assert idx.size == np.unique(idx).size
    # doubling heuristic: at most ~2*estSize samples survive
    assert idx.size <= 2 * 10
    # the non-doubled variant is a plain log-spaced index list starting at 0
    idx2 = hp.genLogSpacing(1000, 10, doubleSized=False)
    assert idx2[0] == 0
    assert np.all(np.diff(idx2) > 0)
    assert idx2.size <= 10 + 1


def test_nd2str_format():
    assert hp.nd2str(np.array([1.0, 2.5])) == '1.0 2.5'
    assert hp.nd2str(np.array([1, 2])) == '1 2'


def test_expand_hermitian_layout():
    arr = np.array([0, 1, 2, 3], dtype=complex)
    # conjugated tail [conj(2), conj(1)] prepended to the input
    assert np.array_equal(hp.expand(arr), np.array([2, 1, 0, 1, 2, 3], dtype=complex))
    # neg/pos factors scale the mirrored / original halves independently
    out = hp.expand(arr, neg_factor=2.0, pos_factor=3.0)
    assert np.array_equal(out, np.array([4, 2, 0, 3, 6, 9], dtype=complex))
    # the conjugation is visible for complex input: the tail walks indices
    # -2, -3, ... so for [1+2j, 3-1j, 0, 2+5j] it is [conj(0), conj(3-1j)]
    cexp = np.array([1 + 2j, 3 - 1j, 0.0, 2 + 5j])
    assert np.array_equal(hp.expand(cexp),
                          np.array([0.0, 3 + 1j, 1 + 2j, 3 - 1j, 0.0, 2 + 5j]))


# ------------------------------------------------------------ lineshapes
def test_lorentz_peak_and_symmetry():
    y0, area, xc, w = 1.0, 3.0, 0.0, 2.0
    # peak height is y0 + 2A/(pi*w)
    assert hp.Lorentz(xc, y0, area, xc, w) == pytest.approx(y0 + 2 * area / (np.pi * w))
    # even about xc
    assert hp.Lorentz(0.7, y0, area, xc, w) == \
        pytest.approx(hp.Lorentz(-0.7, y0, area, xc, w), rel=1e-15)
    # wings fall off as 1/x^2: (2A/pi)*w/x^2 ~ 3.8e-8 at x=1e4
    assert hp.Lorentz(1e4, y0, area, xc, w) == pytest.approx(y0, abs=1e-7)


def test_gaussian_peak_and_fwhm():
    y0, xc, sigma, height = 1.0, 0.0, 0.4, 5.0
    assert hp.Gaussian(xc, y0, xc, sigma, height) == pytest.approx(y0 + height)
    # half maximum sits one FWHM half-width away from the centre
    fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma
    assert hp.Gaussian(xc + fwhm / 2, y0, xc, sigma, height) == \
        pytest.approx(y0 + height / 2, rel=1e-6)
    assert hp.Gaussian(xc - fwhm / 2, y0, xc, sigma, height) == \
        pytest.approx(y0 + height / 2, rel=1e-6)


# ------------------------------------------------------- Q-grid seeds
def test_seed_constant_log_ratio():
    begin, num = 1.0, 10
    s = hp.seed(begin, num)
    # num-1 points spanning [begin, begin*sqrt(2)) with constant ratio
    assert s.size == num - 1
    assert s[0] == pytest.approx(begin, rel=1e-15)
    assert s[-1] < begin * np.sqrt(2)
    ratios = s[1:] / s[:-1]
    assert ratios == pytest.approx(2 ** (1.0 / (2 * (num - 1))), rel=1e-12)
    # a different origin scales the whole ladder
    s2 = hp.seed(4.0, num)
    assert s2 == pytest.approx(4.0 * s, rel=1e-12)


def test_brew_seed_is_power_of_sqrt2():
    s = hp.seed(1.0, 10)
    for power in (1, 2, 5):
        assert hp.brewSeed(s, power) == pytest.approx(s * np.sqrt(2.0) ** power, rel=1e-15)


def test_cal_brew_num_anchor_and_clamp():
    s = hp.seed(1.0, 10)
    # anchor: q=3 lands two doublings above the last seed point
    assert hp.calBrewNum(s, 3.0) == 2
    # below the first seed the value is clamped to s[0]: floor(log2(0.5)*2)
    assert hp.calBrewNum(s, 0.5) == -2
    # definition check for an interior q
    q = 2.0
    expected = int(np.floor(np.log2(q / s[-1])) * 2)
    assert hp.calBrewNum(s, q) == expected


def test_interp_log_exact_on_exponential():
    x = np.linspace(0.0, 5.0, 50)
    y = np.exp(0.7 * x)
    xnew = np.array([1.234, 2.71, 4.5])
    # log-space interpolation of an exponential is exact
    assert hp.interpLog(x, y, xnew) == pytest.approx(np.exp(0.7 * xnew), rel=1e-13)


# ------------------------------------------------------------- FFT utils
def test_convomt_matches_getomegafromtime_step():
    tsize, dt = 256, 1e-15
    itv_conv, axis = hp.convOmT(tsize, dt)
    itv_freq, fre = hp.getOmegaFromTime(tsize, dt)
    # convOmT divides the range by tsize-1, the fft grid by tsize: the two
    # step sizes agree to (tsize-1)/tsize, i.e. rel 1/255 ~ 3.9e-3 < 2e-2
    assert itv_conv == pytest.approx(itv_freq, rel=2e-2)
    # convOmT sweeps the negative half range [-2*pi/dt, 0] in ascending order
    assert np.all(axis <= 0.0)
    assert np.all(np.diff(axis) > 0)
    assert axis[0] == pytest.approx(-2 * np.pi / dt, rel=1e-15)
    # getOmegaFromTime returns the standard centred angular-frequency grid
    assert fre.size == tsize
    assert np.all(np.diff(fre) > 0)


def test_autocorr_spectrum_dc_and_guards():
    rng = np.random.default_rng(7)
    x = rng.normal(size=64)
    ac = hp.autoCorrSpectrum(x)
    # zero-padded double-size spectrum
    assert ac.size == 2 * x.size
    # DC bin (centre after fftshift) equals (sum x)^2
    assert ac[ac.size // 2] == pytest.approx(x.sum() ** 2, rel=1e-12)
    # |conj(F)*F| is non-negative everywhere
    assert np.all(ac >= 0)
    with pytest.raises(ValueError, match='1 dimensional'):
        hp.autoCorrSpectrum(rng.normal(size=(4, 4)))
    with pytest.raises(ValueError, match='too small'):
        hp.autoCorrSpectrum(x, n=2 * x.size - 1)


def test_takfft_definition_and_tone_peaks():
    n = 128
    tone = np.cos(2 * np.pi * 8 * np.arange(n) / n)
    spectrum = hp.takfft(tone)
    # definition pin: fftshift(fft(x)) * dt / (2 pi) with dt=1
    assert spectrum == pytest.approx(np.fft.fftshift(np.fft.fft(tone)) / (2 * np.pi))
    # an 8-cycle tone peaks in the two bins n/2 +- 8 after the shift
    top2 = np.sort(np.argsort(np.abs(spectrum))[-2:])
    assert np.array_equal(top2, np.array([n // 2 - 8, n // 2 + 8]))
    # known behaviour, not a bug to fix here: takfft/takifft is NOT an
    # identity because takfft applies fftshift without ifftshift on the way
    # back
    rng = np.random.default_rng(3)
    y = rng.normal(size=37) + 1j * rng.normal(size=37)
    assert not np.allclose(hp.takifft(hp.takfft(y)), y)


# ------------------------------------------------------------- HKL table
def test_calhkl_half_space_sampling():
    t0 = time.perf_counter()
    res = hp.calHKL(3)
    elapsed = time.perf_counter() - t0
    # keys are the full 0..maxNum range regardless of population
    assert sorted(res.keys()) == [0, 1, 2, 3]
    # the singularity (0,0,0) is removed
    assert res[0] == []
    # half-space sampling keeps, for shell 2, only the non-negative-axis
    # representatives: (0,0,2), (0,2,0), (2,0,0)
    shell2 = sorted(tuple(int(c) for c in v) for v in res[2])
    assert shell2 == [(0, 0, 2), (0, 2, 0), (2, 0, 0)]
    for entry in res[2]:
        assert np.linalg.norm(entry) == pytest.approx(2.0)
    # the 3x3x3 sweep is far below the 10 ms budget
    assert elapsed < 10e-3
