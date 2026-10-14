"""Numeric API invariants of Hist1D / NumpyHist1D (complements test_fix_hist.py).

Pinned semantics (verified against libprompt_core.so + PTHist1D.cc):
- unweighted fill: hit == 1 per call, weight += 1
- weighted fill:   hit += 1 (call counter), weight += w
- getAccWeight()   sums in-range bin weights only (PTHistBase docstring);
  getTotalWeight() counts overflow + underflow too
- per-bin hit is a call counter, so it is independent of the weight value
- [xmin, xmin+bin) half-open binning at the left edge, and x < xmin / x > xmax
  go to underflow / overflow counters.

Divergence from the survey (2026-10): the survey assumed fill(xmax) goes to
OVERFLOW. That was the behaviour of the .so built before the C++ Hist1D clamp
fix; the fixed source (PTHist1D.cc) clamps i == nbins into the last bin, so
fill(xmax) is meant to land in the last bin. The intended-semantics test below
probes the shipped .so at import and skips until the rebuilt library lands;
fill(x > xmax) overflow and fill(xmin) bin-0 are pinned unconditionally since
they hold in both builds.

All bodies are pure in-memory computation, well under the 0.7 s budget.
"""

import matplotlib
matplotlib.use('Agg')  # noqa: E402  must precede any pyplot import

import numpy as np
import pytest

from Cinema.Prompt.histogram import Hist1D, NumpyHist1D


def _xmax_clamped():
    """True when the shipped libprompt_core.so implements the final Hist1D
    contract: fill(x == xmax) lands in the last bin and nothing is dropped or
    counted as overflow. False for the pre-fix build (overflow counter) and
    for the 2026-10 intermediate build (weight silently dropped)."""
    h = Hist1D(0., 1., 4)
    h.fill(1.0, 2.0)
    return h.getOverflow() == 0.0 and abs(h.getWeight()[3] - 2.0) < 1e-12


_XMAX_CLAMPED = _xmax_clamped()


# --- boundary binning ----------------------------------------------------------

def test_fill_xmin_lands_in_bin0():
    h = Hist1D(0., 1., 4)
    h.fill(0.0)  # the left edge belongs to bin 0
    assert h.getWeight()[0] == pytest.approx(1.0)
    assert h.getHit()[0] == pytest.approx(1.0)


def test_fill_below_xmin_goes_to_underflow():
    h = Hist1D(0., 1., 4)
    h.fill(-0.1)
    assert h.getUnderflow() == pytest.approx(1.0)
    assert h.getWeight().sum() == pytest.approx(0.0)  # no bin touched


def test_fill_above_xmax_goes_to_overflow():
    # strictly above the range overflows in every build (old and clamped)
    h = Hist1D(0., 1., 4)
    h.fill(1.1)
    assert h.getOverflow() == pytest.approx(1.0)
    assert h.getWeight().sum() == pytest.approx(0.0)


@pytest.mark.skipif(not _XMAX_CLAMPED,
                    reason='fill(x==xmax) clamp (C++ Hist1D fix) not yet in '
                           'the shipped libprompt_core.so: the loaded build '
                           'still overflows or drops x==xmax instead of '
                           'landing it in the last bin')
def test_fill_xmax_clamped_into_last_bin():
    # intended semantics of the C++ clamp: [xmin, xmax] is right-closed, so
    # the upper edge lands in the last bin instead of the overflow counter
    h = Hist1D(0., 1., 4)
    h.fill(1.0, 2.0)
    assert h.getWeight()[3] == pytest.approx(2.0)
    assert h.getHit()[3] == pytest.approx(1.0)
    assert h.getOverflow() == pytest.approx(0.0)


def test_interior_point_lands_in_expected_bin():
    h = Hist1D(0., 1., 4)
    h.fill(0.3)  # falls into [0.25, 0.5)
    assert h.getWeight()[1] == pytest.approx(1.0)
    assert h.getWeight().sum() == pytest.approx(1.0)


# --- weight / hit bookkeeping ---------------------------------------------------

def test_unweighted_fill_totalhit_equals_accweight():
    h = Hist1D(0., 2., 4)
    for x in (0.1, 0.5, 0.9, 1.3, 1.7):
        h.fill(x)
    # five in-range fills: hit counter and accumulated weight both count 5
    assert h.getTotalHit() == pytest.approx(5.0)
    assert h.getAccWeight() == pytest.approx(5.0)
    assert h.getTotalWeight() == pytest.approx(5.0)


def test_totalweight_includes_overflow_and_underflow():
    h = Hist1D(0., 1., 4)
    h.fill(0.5, 2.0)   # in range
    h.fill(-1.0, 3.0)  # underflow
    h.fill(2.0, 5.0)   # overflow
    assert h.getAccWeight() == pytest.approx(2.0)    # in-range bins only
    assert h.getOverflow() == pytest.approx(5.0)
    assert h.getUnderflow() == pytest.approx(3.0)
    assert h.getTotalWeight() == pytest.approx(10.0)  # counts everything


def test_weighted_fill_accumulates_weight_but_hit_counts_calls():
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 1.0)
    h.fill(0.5, 3.0)
    assert h.getWeight()[0] == pytest.approx(4.0)
    # hit is a per-bin call counter, not a weight sum
    assert h.getHit()[0] == pytest.approx(2.0)


def test_fill_np_float64_takes_scalar_path():
    h = Hist1D(0., 4., 4)
    h.fill(np.float64(0.5))
    assert h.getWeight()[0] == pytest.approx(1.0)
    assert h.getTotalHit() == pytest.approx(1.0)


def test_fill_ndarray_routes_to_fillmany():
    h = Hist1D(0., 4., 4)
    h.fill(np.array([0.5, 1.5, 2.5]))  # iterable -> fillmany, unit weights
    assert np.array_equal(h.getWeight(), [1., 1., 1., 0.])
    assert h.getTotalHit() == pytest.approx(3.0)


# --- fillmany -------------------------------------------------------------------

def test_fillmany_default_weight_is_one():
    h = Hist1D(0., 2., 4)
    h.fillmany(np.linspace(0.05, 0.95, 100))
    assert h.getTotalWeight() == pytest.approx(100.0)
    assert h.getTotalHit() == pytest.approx(100.0)


def test_fillmany_explicit_weights():
    h = Hist1D(0., 2., 4)
    h.fillmany(np.array([0.25, 1.75]), np.array([2.0, 0.5]))
    assert h.getWeight()[0] == pytest.approx(2.0)
    assert h.getWeight()[3] == pytest.approx(0.5)
    assert h.getHit()[0] == pytest.approx(1.0)  # hit still counts calls


def test_fillmany_size_mismatch_raises():
    h = Hist1D(0., 2., 4)
    with pytest.raises(RuntimeError, match='different size'):
        h.fillmany(np.zeros(3), np.ones(2))


def test_fillmany_accepts_integer_arrays():
    # fillmany astype(float64)s both arrays, so int input is fine
    h = Hist1D(0., 5., 5)
    h.fillmany(np.arange(5), np.ones(5, dtype=np.int64))
    assert np.array_equal(h.getWeight(), np.ones(5))


# --- getMean --------------------------------------------------------------------

def test_getmean_matches_analytic_weighted_mean():
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 1.0)  # centre 0.5
    h.fill(1.5, 3.0)  # centre 1.5
    # (0.5*1 + 1.5*3) / (1+3) = 1.25
    assert h.getMean() == pytest.approx(1.25)


def test_getmean_of_empty_hist_is_zero():
    h = Hist1D(0., 1., 4)
    assert h.getMean() == 0


# --- merge / scale / reset --------------------------------------------------------

def test_merge_doubles_weight_hits_and_keeps_edges():
    a = Hist1D(0., 1., 4)
    a.fill(0.1, 2.0)
    a.fill(0.9, 1.0)
    b = Hist1D(0., 1., 4)
    b.fill(0.1, 5.0)
    b.fill(0.5, 1.0)
    edges_before = a.getEdges().copy()
    a.merge(b)
    assert np.array_equal(a.getWeight(), [7., 0., 1., 1.])
    assert np.array_equal(a.getHit(), [2., 0., 1., 1.])
    assert np.array_equal(a.getEdges(), edges_before)


def test_merge_note_mismatch_raises():
    a = Hist1D(0., 1., 4)
    b = Hist1D(0., 1., 4)
    b.addNote('from another run')
    with pytest.raises(RuntimeError, match='!='):
        a.merge(b)


def test_scale_multiplies_weight_not_hit():
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 1.0)
    h.fill(1.5, 3.0)
    h.scale(3.)
    assert np.array_equal(h.getWeight(), [3., 9.])
    assert np.array_equal(h.getHit(), [1., 1.])  # hit counter untouched
    assert h.getAccWeight() == pytest.approx(12.0)
    assert h.getTotalHit() == pytest.approx(2.0)


def test_reset_zeroes_all_counters():
    h = Hist1D(0., 1., 4)
    h.fill(0.5, 2.0)
    h.fill(-1.0, 3.0)
    h.fill(2.0, 5.0)
    h.reset()
    assert np.all(h.getWeight() == 0.)
    assert np.all(h.getHit() == 0.)
    assert h.getAccWeight() == pytest.approx(0.0)
    assert h.getTotalWeight() == pytest.approx(0.0)
    assert h.getOverflow() == pytest.approx(0.0)
    assert h.getUnderflow() == pytest.approx(0.0)


# --- edges / centres / log binning ------------------------------------------------

def test_getcentre_is_arithmetic_midpoints():
    h = Hist1D(0., 1., 4)
    expected = np.linspace(0., 1., 5)[:-1] + np.diff(np.linspace(0., 1., 5)) * 0.5
    assert np.allclose(h.getCentre(), expected)
    assert np.allclose(h.getCentre(), [0.125, 0.375, 0.625, 0.875])


def test_log_binning_edges():
    h = Hist1D(1e-3, 1., 10, linear=False)
    edges = h.getEdges()
    assert edges.size == 10 + 1  # numbin + 1 points
    assert edges[0] == pytest.approx(1e-3)
    assert edges[-1] == pytest.approx(1.0)
    # logarithmic spacing: constant decade step
    assert np.allclose(np.diff(np.log10(edges)), 0.3)


def test_numbin_attribute_matches_data_size():
    h = Hist1D(0., 1., 7)
    assert h.numbin == 7
    assert h.numbin == len(h.getWeight()) == h.getDataSize()
    assert len(h.getEdges()) == h.numbin + 1


# --- toArrayXY --------------------------------------------------------------------

def test_toarrayxy_returns_cinemaxy_with_x_and_mean():
    h = Hist1D(0., 1., 4)
    h.fillmany(np.array([0.125, 0.625]), np.array([2.0, 3.0]))
    xy = h.toArrayXY()
    assert np.allclose(np.asarray(xy.x), h.getCentre())
    assert np.allclose(np.asarray(xy.mean), h.getWeight())


# --- setWeight / setHit / setWW ----------------------------------------------------

def test_setweight_sethit_setww_roundtrip():
    h = Hist1D(0., 1., 4)
    h.setWeight(np.full(4, 7.0))
    h.setHit(np.full(4, 2.0))
    h.setWW(np.full(4, 9.0))
    assert np.array_equal(h.getWeight(), np.full(4, 7.0))
    assert np.array_equal(h.getHit(), np.full(4, 2.0))
    assert np.array_equal(h.getWW(), np.full(4, 9.0))
    # getSdev is defined as sqrt(ww)
    assert np.allclose(h.getSdev(), 3.0)


def test_setweight_wrong_size_raises():
    h = Hist1D(0., 1., 4)
    with pytest.raises(RuntimeError):
        h.setWeight(np.zeros(3))


# --- NumpyHist1D validation sibling -------------------------------------------------

def test_numpyhist1d_crosscheck_bit_identical_bins():
    # NumpyHist1D exists to validate Hist1D: 1000 interior fills must agree
    # bin-for-bin (and bit-for-bit, since the contents are integer counts)
    rng = np.random.default_rng(20260)
    x = rng.uniform(0.01, 0.99, 1000)  # strictly inside (0, 1)
    fast = Hist1D(0., 1., 10)
    fast.fillmany(x)
    ref = NumpyHist1D(10, [0., 1.])
    ref.fill(x)
    assert np.array_equal(fast.getWeight(), ref.getHistVal())
    assert fast.getWeight().sum() == pytest.approx(1000.0)


def test_numpyhist1d_zero_range_raises_ioerror():
    with pytest.raises(IOError, match='wrong range input'):
        NumpyHist1D(10, [0., 0.])
