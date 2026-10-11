"""Histogram operation matrix: fill/scale/normalise/merge/rebin/plot for
Hist1D, Hist2D and Est1D, with exact hand-computed arrays.

Coverage plan (cluster cov-py3-histops):
- A: fill + scale + normalise sequences, every intermediate array hand-derived
- B: fill loops and fillmany vs the numpy histogram / histogram2d references
- C: merge (the histogram-module add) with exact weight/hit/ww bookkeeping
- D: histogram arithmetic in the analysis layer - ErrorPropagator add/sub/scale
     and RebinHist1D.mergeBin - including the documented error paths
- E: Est1D as a streaming mean/rms/variance accumulator over draw sets with
     exact discrete moments (uniform and triangular)
- F: savefig smoke into tmp_path (medium tier, ~0.2-0.3 s per body)
- G: op-matrix state machine comparing the ctypes fetchers after every step

EXPECTED-FAIL LEDGER (round-2 hist semantics). The tests flagged with
"EXPECTED-FAIL" below pin behaviour that lives in existing libprompt_core
symbols which the checked-out cinemabin build predates:
- HistBase::scale must scale the ww channel (sum(w^2)) by f^2, so getSdev()
  scales by |f| - the stale .so leaves ww untouched;
- Est1D must merge its error channel (m_hit) in quadrature (3+4 -> 5) and
  scale it by |f| - the stale .so adds it linearly and leaves it unscaled.
These tests are RED against the stale cinemabin .so and turn GREEN after the
round-2 gate rebuild, EXCEPT the two Est1D ones, which additionally need the
Est1D::merge/Est1D::scale overrides in src/cxx/Ana/libinc/PTEst1D.hh and
src/cxx/Ana/libsrc/PTEst1D.cc (files outside the b1 cluster's exclusive list,
reported to the lead); they stay red until that override lands and the .so is
rebuilt.

Deliberately NOT exercised here:
- HistBase.merge with mismatched binning: the C++ CalcError escapes the
  ctypes ABI and abort()s the interpreter (verified 2026-10, re-verified in
  round 2: SIGABRT with 'terminate called after throwing an instance of
  Prompt::Error::CalcError'), so there is no catchable Python error to pin;
  the python-side note-mismatch guard is covered by test_hist_invariants.py.
  The catchable mismatched-binning errors live in the analysis layer and are
  pinned in section D.
- Est1D.fillmany: np.vectorize double-fills the first element (documented in
  test_hist2d_est1d.py), so every Est1D fill below is a plain scalar loop.

All bodies except section F are pure in-memory numpy work, far below 50 ms.
"""

import matplotlib
matplotlib.use('Agg')  # noqa: E402  must precede any pyplot import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from Cinema.Prompt.histogram import Hist1D, Hist2D, Est1D, NumpyHist2D  # noqa: E402
from Cinema.Experiment.Analyser import ErrorPropagator  # noqa: E402
from Cinema.Experiment.Analyser.yn_ana_usefulClass import RebinHist1D  # noqa: E402


# --- A: fill + scale + normalise sequences (exact arrays) -----------------------

def test_weighted_fills_exact_bin_matrix():
    h = Hist1D(0., 2., 4)  # edges [0, 0.5, 1, 1.5, 2]
    h.fill(0.25, 2.0)   # bin 0
    h.fill(0.75, 3.0)   # bin 1
    h.fill(0.75, 1.0)   # bin 1 again
    h.fill(1.25, 0.5)   # bin 2
    assert np.array_equal(h.getWeight(), [2., 4., 0.5, 0.])
    # hit counts calls, not weights
    assert np.array_equal(h.getHit(), [1., 2., 1., 0.])
    assert h.getAccWeight() == pytest.approx(6.5)
    assert h.getTotalWeight() == pytest.approx(6.5)


def test_scale_then_refill_accumulates_scaled_base():
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 1.0)
    h.scale(10.0)       # stored weight becomes 10
    h.fill(0.5, 1.0)    # refills add to the scaled base
    assert np.array_equal(h.getWeight(), [11., 0.])
    assert h.getAccWeight() == pytest.approx(11.0)
    assert np.array_equal(h.getHit(), [2., 0.])  # hit counted both calls


def test_normalise_to_unit_total_exact_array():
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 2.0)
    h.fill(1.5, 6.0)    # total 8
    h.scale(1. / h.getTotalWeight())  # normalise
    # 2/8 and 6/8 are exact binary fractions
    assert np.array_equal(h.getWeight(), [0.25, 0.75])
    assert h.getAccWeight() == pytest.approx(1.0)
    assert h.getTotalWeight() == pytest.approx(1.0)


def test_scale_zero_clears_weights_keeps_counters():
    # EXPECTED-FAIL (round-2 ledger): needs HistBase::scale to scale the ww
    # channel by f^2; red against the stale cinemabin .so (ww stays [4, 36]),
    # green after the gate rebuild. See the module docstring.
    h = Hist1D(0., 2., 2)
    h.fill(0.25, 2.0)   # bin 0
    h.fill(1.5, 6.0)    # bin 1
    h.scale(0.)
    assert np.array_equal(h.getWeight(), [0., 0.])
    assert h.getAccWeight() == pytest.approx(0.0)
    assert h.getTotalWeight() == pytest.approx(0.0)
    # the hit counter counts fill calls and is never rescaled; the ww channel
    # (sum(w^2)) scales with f^2 = 0 and is cleared with the content
    assert np.array_equal(h.getHit(), [1., 1.])
    assert np.array_equal(h.getWW(), [0., 0.])
    assert np.array_equal(h.getSdev(), [0., 0.])


def test_scale_negative_sign_flip_exact():
    # f = -1: |f| = 1, so old and new scale semantics coincide (ww is left
    # untouched by the stale .so and scaled by (-1)^2 = 1 after the fix) -
    # this pin holds under both and guards the sign flip of the content
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 2.0)
    h.fill(1.5, 6.0)
    h.scale(-1.0)
    assert np.array_equal(h.getWeight(), [-2., -6.])
    assert h.getAccWeight() == pytest.approx(-8.0)
    assert h.getTotalWeight() == pytest.approx(-8.0)
    # |f| = 1: the variance (ww) is unchanged and so is the sdev
    assert np.array_equal(h.getWW(), [4., 36.])
    assert np.array_equal(h.getSdev(), [2., 6.])
    assert np.array_equal(h.getHit(), [1., 1.])


def test_scale_multiplies_overflow_underflow_counters():
    h = Hist1D(0., 1., 2)
    h.fill(0.25, 2.0)   # in range
    h.fill(-1.0, 3.0)   # underflow
    h.fill(2.0, 5.0)    # overflow
    h.scale(2.0)
    assert np.array_equal(h.getWeight(), [4., 0.])
    assert h.getAccWeight() == pytest.approx(4.0)
    assert h.getUnderflow() == pytest.approx(6.0)
    assert h.getOverflow() == pytest.approx(10.0)
    assert h.getTotalWeight() == pytest.approx(20.0)


def test_scale_ww_by_f_squared_and_sdev_by_absf():
    # EXPECTED-FAIL (round-2 ledger): needs HistBase::scale to scale the ww
    # channel (sum(w^2)) by f^2; red against the stale cinemabin .so (ww stays
    # [4, 9], sdev [2, 3]), green after the gate rebuild. The hit counter
    # counts fill calls and stays unscaled either way.
    h = Hist1D(0., 2., 2)
    h.fill(0.5, 2.0)
    h.fill(1.5, 3.0)
    h.scale(5.0)
    assert np.array_equal(h.getWeight(), [10., 15.])
    assert np.array_equal(h.getHit(), [1., 1.])
    # ww 4 and 9 scale by 5^2 = 25; sdev = sqrt(ww) scales by |5|
    assert np.array_equal(h.getWW(), [100., 225.])
    assert np.array_equal(h.getSdev(), [10., 15.])
    assert h.getAccWeight() == pytest.approx(25.0)
    assert h.getTotalHit() == pytest.approx(2.0)


def test_normalise_scales_sdev_unit_weights():
    # EXPECTED-FAIL (round-2 ledger): the classic normalise-by-sum idiom on
    # unit-weight data. ww is 1 per bin after the fills, so after scaling by
    # 0.5 the sdev must be 0.5 like the content; the stale cinemabin .so
    # leaves ww untouched and reports sdev 1 (green after the gate rebuild).
    # All quantities are exact binary fractions.
    h = Hist1D(0., 2., 2)
    h.fill(0.5)          # unit weight: ww = 1
    h.fill(1.5)          # unit weight: ww = 1
    assert h.getTotalWeight() == pytest.approx(2.0)
    h.scale(1. / h.getTotalWeight())     # normalise to unit total
    assert np.array_equal(h.getWeight(), [0.5, 0.5])
    assert np.array_equal(h.getWW(), [0.25, 0.25])
    assert np.array_equal(h.getSdev(), [0.5, 0.5])


def test_hist2d_scale_sdev_by_absf_weighted():
    # EXPECTED-FAIL (round-2 ledger): 2D variant - HistBase::scale must scale
    # the ww channel by f^2; red against the stale cinemabin .so (sdev stays
    # 3), green after the gate rebuild
    h = Hist2D(0., 2., 2, 0., 4., 2)
    h.fill(0.5, 1.0, 3.0)    # cell [0][0]: weight 3, ww 9, sdev 3
    h.scale(2.0)
    assert np.array_equal(h.getWeight(), [[6., 0.], [0., 0.]])
    assert np.array_equal(h.getWW(), [[36., 0.], [0., 0.]])
    assert np.array_equal(h.getSdev(), [[6., 0.], [0., 0.]])
    assert np.array_equal(h.getHit(), [[1., 0.], [0., 0.]])  # call counter


def test_fill_scale_fillmany_scale_sequence_exact():
    h = Hist1D(0., 2., 4)
    h.fill(0.25, 1.0)                                   # [1, 0, 0, 0]
    h.scale(2.0)                                        # [2, 0, 0, 0]
    h.fillmany(np.array([0.75, 1.25]), np.array([3., 1.]))  # [2, 3, 1, 0]
    h.scale(0.5)                                        # [1, 1.5, 0.5, 0]
    assert np.array_equal(h.getWeight(), [1., 1.5, 0.5, 0.])
    # accumulated: (1*2 + 3 + 1) * 0.5
    assert h.getAccWeight() == pytest.approx(3.0)
    assert np.array_equal(h.getHit(), [1., 1., 1., 0.])


# --- B: fill loops / fillmany vs the numpy references ----------------------------

def test_fill_loop_matches_numpy_histogram_int_weights():
    # integer weights make both accumulations exact, so the comparison can
    # be bitwise
    x = np.array([0.1, 0.3, 0.55, 0.8, 1.05, 1.3, 1.55, 1.8, 0.5, 1.0])
    w = np.array([1., 2., 3., 4., 5., 6., 7., 8., 2., 4.])
    edges = np.linspace(0., 2., 5)
    # hand-derived placement: bins [0,0.5),[0.5,1),[1,1.5),[1.5,2]
    # bin0: 1+2=3, bin1: 3+4+2=9, bin2: 5+6+4=15, bin3: 7+8=15
    expected = np.array([3., 9., 15., 15.])
    h = Hist1D(0., 2., 4)
    for xi, wi in zip(x, w):
        h.fill(xi, wi)
    ref, _ = np.histogram(x, bins=edges, weights=w)
    assert np.array_equal(h.getWeight(), expected)
    assert np.array_equal(ref, expected)
    assert np.array_equal(h.getHit(), [2., 3., 3., 2.])
    assert h.getTotalWeight() == pytest.approx(42.0)  # sum of all weights


def test_fillmany_matches_numpy_histogram_float_weights():
    x = np.linspace(0.05, 1.95, 39)
    w = x.copy()  # float weights
    h = Hist1D(0., 2., 8)
    h.fillmany(x, w)
    ref, _ = np.histogram(x, bins=np.linspace(0., 2., 9), weights=w)
    # both accumulate in fill order; agreement to ~1e-15
    assert np.allclose(h.getWeight(), ref, rtol=1e-12, atol=0.)
    assert h.getTotalWeight() == pytest.approx(w.sum())


def test_hist2d_fill_loop_matches_numpy_histogram2d():
    pts = [(0.25, 0.5, 1.), (0.75, 0.5, 2.), (0.25, 1.5, 3.),
           (0.75, 1.5, 4.), (0.75, 0.25, 5.)]
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    w = np.array([p[2] for p in pts])
    # hand-derived matrix over x bins [0,0.5),[0.5,1] and y bins [0,1),[1,2]:
    # (0.75,0.5) and (0.75,0.25) share bin [1][0] -> 2+5 = 7
    expected = np.array([[1., 3.], [7., 4.]])
    h = Hist2D(0., 1., 2, 0., 2., 2)
    for px, py, pw in pts:
        h.fill(px, py, pw)
    ref, _, _ = np.histogram2d(x, y, bins=[np.linspace(0, 1, 3),
                                           np.linspace(0, 2, 3)], weights=w)
    assert np.array_equal(h.getWeight(), expected)
    assert np.array_equal(ref, expected)  # same [xbin, ybin] convention
    assert np.array_equal(h.getHit(), [[1., 1.], [2., 1.]])
    # density = weight/hit: the double-hit bin averages to 3.5
    assert np.array_equal(h.getDensity(), [[1., 3.], [3.5, 4.]])


def test_hist2d_fillmany_matches_numpy_histogram2d():
    rng = np.random.default_rng(7)
    xs = rng.uniform(0.01, 0.99, 200)
    ys = rng.uniform(0.01, 1.99, 200)
    ws = xs + ys
    h = Hist2D(0., 1., 4, 0., 2., 4)
    h.fillmany(xs, ys, ws)
    ref, _, _ = np.histogram2d(xs, ys, bins=[np.linspace(0, 1, 5),
                                             np.linspace(0, 2, 5)], weights=ws)
    assert np.allclose(h.getWeight(), ref, rtol=1e-12, atol=0.)
    assert h.getTotalWeight() == pytest.approx(ws.sum())


def test_numpyhist2d_crosscheck_bit_identical_counts():
    # NumpyHist2D exists to validate Hist2D: unit-weight fills give integer
    # counts, so the 2D agreement can be checked bitwise
    rng = np.random.default_rng(42)
    xs = rng.uniform(0.02, 1.98, 300)
    ys = rng.uniform(0.05, 3.95, 300)
    fast = Hist2D(0., 2., 4, 0., 4., 2)
    fast.fillmany(xs, ys)
    ref = NumpyHist2D(4, 2, [[0., 2.], [0., 4.]])
    ref.fill(xs, ys)
    assert np.array_equal(fast.getWeight(), ref.getHistVal())
    assert fast.getTotalWeight() == pytest.approx(300.0)


# --- C: merge, the histogram-module add -----------------------------------------

def test_merge_adds_weight_hit_accweight_exactly():
    a = Hist1D(0., 2., 2)
    a.fill(0.5, 3.0)
    b = Hist1D(0., 2., 2)
    b.fill(1.5, 4.0)
    a.merge(b)
    assert np.array_equal(a.getWeight(), [3., 4.])
    assert np.array_equal(a.getHit(), [1., 1.])
    assert a.getAccWeight() == pytest.approx(7.0)
    assert a.getTotalWeight() == pytest.approx(7.0)


def test_merge_ww_variances_add_100_unit_fills():
    # regression: m_ww stores sum(w^2) (the variance), so merge() must ADD
    # the ww channels. The old code combined the stored variances in
    # quadrature (sqrt(100^2 + 100^2) = 141.42 instead of 200), which
    # underestimated the merged sdev. Integer weights keep every
    # accumulation exact, so the equality can be bitwise.
    a = Hist1D(0., 1., 2)
    b = Hist1D(0., 1., 2)
    for _ in range(100):
        a.fill(0.25, 1.0)   # bin 0, ww = 100
        b.fill(0.25, 1.0)   # bin 0, ww = 100
    a.merge(b)
    assert a.getWW()[0] == 200.0
    assert a.getSdev()[0] == pytest.approx(np.sqrt(200.0), rel=1e-15)
    assert a.getWeight()[0] == pytest.approx(200.0)
    assert a.getHit()[0] == pytest.approx(200.0)


def test_merge_ww_variances_add_weighted():
    # weighted variant: sum(w^2) channels 400 and 25 must add to 425
    # (0.5 and 2.0 are exact binary fractions, so all sums are exact)
    h1 = Hist1D(0., 1., 2)
    for _ in range(100):
        h1.fill(0.25, 2.0)   # ww = 100 * 4 = 400
    h2 = Hist1D(0., 1., 2)
    for _ in range(100):
        h2.fill(0.25, 0.5)   # ww = 100 * 0.25 = 25
    h1.merge(h2)
    assert h1.getWW()[0] == 425.0
    assert h1.getSdev()[0] == pytest.approx(np.sqrt(425.0), rel=1e-15)
    # sdev of the merged hist exceeds each single-run sdev (20 and 5):
    # the old quadrature-on-variance bug gave sqrt(400^2 + 25^2) = 400.78
    assert h1.getSdev()[0] > 20.0


def test_merge_carries_underflow_overflow_counters():
    a = Hist1D(0., 1., 2)
    a.fill(-1.0, 2.0)
    a.fill(0.5, 1.0)
    a.fill(3.0, 4.0)    # overflow
    b = Hist1D(0., 1., 2)
    b.fill(-1.0, 3.0)   # underflow
    b.fill(0.25, 1.0)
    a.merge(b)
    assert a.getUnderflow() == pytest.approx(5.0)   # 2 + 3
    assert a.getOverflow() == pytest.approx(4.0)
    assert a.getAccWeight() == pytest.approx(2.0)   # bin weights 1 + 1
    assert a.getTotalWeight() == pytest.approx(11.0)
    assert np.array_equal(a.getWeight(), [1., 1.])


def test_merge_weight_commutes_bitwise():
    def make_a():
        h = Hist1D(0., 1., 4)
        h.fill(0.1, 2.0)
        h.fill(0.9, 1.0)
        return h

    def make_b():
        h = Hist1D(0., 1., 4)
        h.fill(0.3, 4.0)
        h.fill(0.9, 0.5)
        return h

    ab = make_a()
    ab.merge(make_b())
    ba = make_b()
    ba.merge(make_a())
    assert np.array_equal(ab.getWeight(), ba.getWeight())
    assert np.array_equal(ab.getHit(), ba.getHit())
    assert np.array_equal(ab.getWW(), ba.getWW())


def test_hist2d_merge_exact_weight_hit_matrices():
    a = Hist2D(0., 2., 2, 0., 4., 2)
    a.fill(0.5, 1.0, 1.0)
    b = Hist2D(0., 2., 2, 0., 4., 2)
    b.fill(0.5, 1.0, 2.0)
    b.fill(1.5, 3.0, 3.0)
    a.merge(b)
    assert np.array_equal(a.getWeight(), [[3., 0.], [0., 3.]])
    assert np.array_equal(a.getHit(), [[2., 0.], [0., 1.]])
    assert a.getAccWeight() == pytest.approx(6.0)


def test_hist2d_merge_ww_variances_add_weighted():
    # 2D companion of the 1D variance pins above: merge must ADD the sum(w^2)
    # channels (errors of independent runs combine in quadrature through the
    # sqrt in getSdev). 0.5 and 2.0 are exact binary fractions, so ww 400 and
    # 25 add bitwise to 425. Green against the round-1 merge fix.
    a = Hist2D(0., 1., 1, 0., 1., 1)
    for _ in range(100):
        a.fill(0.5, 0.5, 2.0)    # ww = 100 * 4 = 400
    b = Hist2D(0., 1., 1, 0., 1., 1)
    for _ in range(100):
        b.fill(0.5, 0.5, 0.5)    # ww = 100 * 0.25 = 25
    a.merge(b)
    assert a.getWW()[0, 0] == 425.0
    assert a.getSdev()[0, 0] == pytest.approx(np.sqrt(425.0), rel=1e-15)
    assert a.getWeight()[0, 0] == pytest.approx(250.0)
    assert a.getHit()[0, 0] == pytest.approx(200.0)


# --- D: analysis-layer arithmetic (ErrorPropagator, RebinHist1D) -----------------

def test_errorpropagator_iadd_exact_weights_quadrature_errors():
    ep = ErrorPropagator(weight=np.array([1., 2., 3., 4.]),
                         xcentre=np.arange(4.),
                         error=np.array([0.1, 0.2, 0.3, 0.4]))
    ep += ErrorPropagator(weight=np.ones(4), xcentre=np.arange(4.),
                          error=np.ones(4))
    # weights add linearly, errors add in quadrature: sqrt(e^2 + 1^2)
    assert np.allclose(ep.weight, [2., 3., 4., 5.], rtol=1e-13, atol=0.)
    assert np.allclose(ep.error, np.sqrt([1.01, 1.04, 1.09, 1.16]),
                       rtol=1e-13, atol=0.)


def test_errorpropagator_isub_exact_errors_still_grow():
    ep = ErrorPropagator(weight=np.array([1., 2., 3., 4.]),
                         xcentre=np.arange(4.),
                         error=np.array([0.1, 0.2, 0.3, 0.4]))
    ep += ErrorPropagator(weight=np.ones(4), xcentre=np.arange(4.),
                          error=np.ones(4))
    ep -= ErrorPropagator(weight=np.full(4, 0.5), xcentre=np.arange(4.),
                          error=np.full(4, 0.5))
    # subtracted weights leave, but the error still grows in quadrature
    # (independent uncertainties), e.g. sqrt(1.01 + 0.25) = sqrt(1.26)
    assert np.allclose(ep.weight, [1.5, 2.5, 3.5, 4.5], rtol=1e-13, atol=0.)
    assert np.allclose(ep.error, np.sqrt([1.26, 1.29, 1.34, 1.41]),
                       rtol=1e-13, atol=0.)


def test_errorpropagator_scale_negative_factor():
    ep = ErrorPropagator(weight=np.array([1., -2.]), xcentre=np.arange(2.),
                         error=np.array([0.5, 2.]))
    ep.scale(-4.)
    # weights take the sign, errors scale with |factor|
    assert np.array_equal(ep.weight, [-4., 8.])
    assert np.array_equal(ep.error, [2., 8.])


def test_errorpropagator_iadd_mismatched_xcentre_raises():
    ep = ErrorPropagator(weight=np.ones(4), xcentre=np.arange(4.),
                         error=np.ones(4))
    # compatible() guards the binning with assert_almost_equal: same length
    # but shifted centres is a documented AssertionError, not silent mixing
    other = ErrorPropagator(weight=np.ones(4), xcentre=np.arange(4.) + 0.5,
                            error=np.ones(4))
    with pytest.raises(AssertionError, match='not almost equal'):
        ep += other


def test_errorpropagator_2d_iadd_with_ycentre_exact():
    w = np.arange(6.).reshape(2, 3)
    xc = np.arange(2.)
    yc = np.linspace(0., 1., 3)
    ep = ErrorPropagator(weight=w, xcentre=xc, ycentre=yc,
                         error=np.ones((2, 3)))
    ep += ErrorPropagator(weight=np.ones((2, 3)), xcentre=xc, ycentre=yc,
                          error=np.full((2, 3), 2.))
    assert np.allclose(ep.weight, w + 1., rtol=1e-13, atol=0.)
    assert np.allclose(ep.error, np.sqrt(5.), rtol=1e-13, atol=0.)  # sqrt(1+4)


def test_errorpropagator_2d_mismatched_ycentre_raises():
    ep = ErrorPropagator(weight=np.ones((2, 3)), xcentre=np.arange(2.),
                         ycentre=np.linspace(0., 1., 3), error=np.ones((2, 3)))
    other = ErrorPropagator(weight=np.ones((2, 3)), xcentre=np.arange(2.),
                            ycentre=np.linspace(0., 2., 3),
                            error=np.ones((2, 3)))
    with pytest.raises(AssertionError, match='not almost equal'):
        ep += other


def test_rebinhist1d_mergebin2_exact_arrays():
    # 4 unit bins [0,1,2,3,4] with content [1,2,3,4] and unit errors 1
    r = RebinHist1D(np.array([0., 1., 2., 3., 4.]),
                    np.array([1., 2., 3., 4.]),
                    np.array([1., 1., 1., 1.]))
    assert np.array_equal(r.unitcontent, [1., 2., 3., 4.])  # content / 1
    r.mergeBin(2)  # pair the bins
    assert np.array_equal(r.edge, [0., 2., 4.])
    assert np.array_equal(r.content, [3., 7.])              # 1+2, 3+4
    assert np.allclose(r.error, np.sqrt(2.), rtol=1e-13, atol=0.)
    assert np.array_equal(r.unitcontent, [1.5, 3.5])        # [3,7] / 2
    assert np.allclose(r.uniterror, np.sqrt(2.) / 2., rtol=1e-13, atol=0.)


def test_rebinhist1d_mergebin4_is_identity():
    # merging 4 bins into 4 bins must reproduce the input exactly
    edge = np.array([0., 1., 2., 3., 4.])
    content = np.array([1., 2., 3., 4.])
    error = np.array([1., 1., 1., 1.])
    r = RebinHist1D(edge.copy(), content.copy(), error.copy())
    r.mergeBin(4)
    assert np.array_equal(r.edge, edge)
    assert np.array_equal(r.content, content)
    assert np.array_equal(r.error, error)
    assert np.array_equal(r.unitcontent, content)  # unit widths are 1


def test_rebinhist1d_mergebin1_collapses_to_one_bin():
    r = RebinHist1D(np.array([0., 1., 2., 3., 4.]),
                    np.array([1., 2., 3., 4.]),
                    np.array([1., 1., 1., 1.]))
    r.mergeBin(1)
    assert np.array_equal(r.edge, [0., 4.])
    assert np.array_equal(r.content, [10.])                  # 1+2+3+4
    assert np.array_equal(r.error, [2.])                     # sqrt(4*1^2)
    assert np.array_equal(r.unitcontent, [2.5])              # 10 / 4
    assert np.array_equal(r.uniterror, [0.5])                # 2 / 4


def test_rebinhist1d_lossy_factor_reports_and_keeps_data(capsys):
    # 3 content bins cannot be paired: the documented contract is a printed
    # 'can not be rebined' report and the histogram left untouched
    edge = np.array([0., 1., 2., 3.])
    content = np.array([1., 2., 3.])
    r = RebinHist1D(edge.copy(), content.copy())
    r.mergeBin(2)
    assert 'can not be rebined' in capsys.readouterr().out
    assert np.array_equal(r.edge, edge)
    assert np.array_equal(r.content, content)
    assert np.array_equal(r.unitcontent, content)  # unit widths are 1


# --- E: Est1D mean / rms / var accumulation vs closed form -----------------------
# The draws below are deterministic sets with exact discrete moments:
# uniform5  = {0.1, 0.3, 0.5, 0.7, 0.9}:  mean 1/2, sum(x^2) = 1.65
# triangular = {0, 1/2, 1/2, 1} (P(0)=P(1)=1/4, P(1/2)=1/2):
#              mean 1/2, E[x^2] = 3/8, var = 1/8

def test_est1d_uniform_draws_weight_rms_mean_exact():
    e = Est1D(0., 1., 1)  # single bin catches every draw
    for xi in [0.1, 0.3, 0.5, 0.7, 0.9]:
        e.fill(xi, 1.0, xi)  # error channel carries the drawn value
    assert np.array_equal(e.getWeight(), [5.])
    # quadrature over draws: sqrt(sum x_i^2) = sqrt(1.65)
    assert e.getError()[0] == pytest.approx(np.sqrt(1.65))
    # rms of the draw set = sqrt(sum(x^2)/N) = sqrt(0.33)
    assert e.getError()[0] / np.sqrt(5.) == pytest.approx(np.sqrt(0.33))
    # single-bin getMean() is the bin centre 0.5, which equals both the
    # discrete-set mean and the closed-form uniform(0,1) mean
    assert e.getMean() == pytest.approx(0.5)


def test_est1d_triangular_draws_variance_closed_form():
    e = Est1D(0., 1., 1)
    for xi in [0., 0.5, 0.5, 1.]:
        # error channel carries |x - mean|; quadrature accumulates the
        # centered sum of squares
        e.fill(xi, 1.0, abs(xi - 0.5))
    assert np.array_equal(e.getWeight(), [4.])
    # sum of squared deviations = 0.25 + 0 + 0 + 0.25
    assert e.getError()[0] == pytest.approx(np.sqrt(0.5))
    # population variance = 0.5 / 4 = 0.125, exactly E[x^2] - mean^2 = 3/8 - 1/4
    assert e.getError()[0] ** 2 / 4. == pytest.approx(0.125)
    assert e.getMean() == pytest.approx(0.5)


def test_est1d_weighted_multibin_mean_exact():
    e = Est1D(0., 4., 4)  # centres 0.5, 1.5, 2.5, 3.5
    for xc, wgt in zip([0.5, 1.5, 2.5, 3.5], [1., 2., 3., 4.]):
        e.fill(xc, wgt, 0.)
    assert np.array_equal(e.getWeight(), [1., 2., 3., 4.])
    # (0.5*1 + 1.5*2 + 2.5*3 + 3.5*4) / 10 = 25/10
    assert e.getMean() == pytest.approx(2.5)
    assert np.array_equal(e.getError(), [0., 0., 0., 0.])  # zero errors stay 0


def test_est1d_per_bin_weighted_error_exact():
    e = Est1D(0., 4., 4)
    for xc, wgt in zip([0.5, 1.5, 2.5, 3.5], [1., 2., 3., 4.]):
        e.fill(xc, wgt, wgt * xc)  # one draw per bin -> error = w*x exactly
    assert np.array_equal(e.getError(), [0.5, 3., 7.5, 14.])
    # total quadrature: sqrt(0.5^2 + 3^2 + 7.5^2 + 14^2) = sqrt(261.5)
    assert np.sqrt((e.getError() ** 2).sum()) == pytest.approx(np.sqrt(261.5))
    # weight-normalised rms of the (w*x) samples
    assert np.sqrt((e.getError() ** 2).sum() / 10.) == pytest.approx(
        np.sqrt(26.15))


def test_est1d_error_quadrature_order_independent():
    e1 = Est1D(0., 1., 2)
    e1.fill(0.25, 1., 0.3)
    e1.fill(0.25, 1., 0.4)
    e2 = Est1D(0., 1., 2)
    e2.fill(0.25, 1., 0.4)
    e2.fill(0.25, 1., 0.3)
    assert np.array_equal(e1.getError(), e2.getError())
    assert e1.getError()[0] == pytest.approx(np.sqrt(0.3 ** 2 + 0.4 ** 2))
    assert e1.getError()[0] == pytest.approx(0.5)


def test_est1d_ww_channel_stays_zero():
    # Est1D overrides fill() and never touches the ww channel; the error
    # lives in the hit array instead (getError() IS getHit())
    e = Est1D(0., 1., 2)
    e.fill(0.25, 2.0, 0.1)
    assert np.array_equal(e.getWW(), [0., 0.])
    assert np.array_equal(e.getSdev(), [0., 0.])
    assert np.array_equal(e.getError(), [0.1, 0.])
    assert np.array_equal(e.getWeight(), [2., 0.])


def test_est1d_out_of_range_draws_hit_counters_only():
    e = Est1D(0., 1., 2)
    e.fill(-1., 2., 0.5)   # underflow
    e.fill(2., 3., 0.5)    # overflow
    assert e.getUnderflow() == pytest.approx(2.0)
    assert e.getOverflow() == pytest.approx(3.0)
    assert e.getTotalWeight() == pytest.approx(5.0)
    assert e.getAccWeight() == pytest.approx(0.0)
    assert np.array_equal(e.getWeight(), [0., 0.])
    assert np.array_equal(e.getError(), [0., 0.])  # no bin was touched


# --- E2: Est1D error channel under merge/scale (EXPECTED-FAIL ledger) ------------
# Est1D keeps its sdev in the hit array (m_ww stays 0), so the base-class
# HistBase semantics do not apply to it: merge must quadrature the error
# channel and scale must rescale it by |f|. Both need Est1D::merge /
# Est1D::scale overrides in PTEst1D.hh/.cc, which are outside the b1 cluster's
# exclusive file list (reported to the lead) - these two stay red until that
# override lands and the .so is rebuilt (see the module docstring).

def test_est1d_merge_error_channel_quadrature():
    # EXPECTED-FAIL (round-2 ledger): the stale .so merges the Est1D error
    # channel linearly (3 + 4 = 7); the 3-4-5 quadrature below needs the
    # Est1D::merge override (PTEst1D.hh/.cc) plus a rebuild
    a = Est1D(0., 2., 1)
    a.fill(1.0, 1.0, 3.0)
    b = Est1D(0., 2., 1)
    b.fill(1.0, 1.0, 4.0)
    a.merge(b)
    # 3-4-5 triangle: the classic quadrature of independent errors
    assert a.getError()[0] == pytest.approx(5.0)
    assert a.getWeight()[0] == pytest.approx(2.0)     # content adds linearly
    assert a.getAccWeight() == pytest.approx(2.0)


def test_est1d_scale_scales_error_channel_by_absf():
    # EXPECTED-FAIL (round-2 ledger): m_hit IS the sdev accumulator for
    # Est1D, linear in the factor - the stale .so leaves it untouched (3
    # instead of 6); needs the Est1D::scale override (PTEst1D.hh/.cc) plus a
    # rebuild. The content takes the sign, the error scales with |-2|.
    e = Est1D(0., 2., 1)
    e.fill(1.0, 2.0, 3.0)
    e.scale(-2.0)
    assert e.getWeight()[0] == pytest.approx(-4.0)
    assert e.getError()[0] == pytest.approx(6.0)
    assert np.array_equal(e.getWW(), [0.])    # ww stays the unused channel


# --- F: plot()/savefig() smoke (medium: 0.2-0.3 s per body) ----------------------

@pytest.mark.medium
def test_hist1d_savefig_smoke(tmp_path):
    h = Hist1D(0., 2., 8)
    h.fillmany(np.linspace(0.05, 1.95, 39), np.linspace(0.05, 1.95, 39) ** 2)
    out = tmp_path / 'h1.png'
    h.savefig(str(out))
    assert out.exists()
    assert out.stat().st_size > 0
    # savefig() closes its figure on the way out: nothing must be left open
    assert plt.get_fignums() == []


@pytest.mark.medium
def test_hist2d_savefig_smoke_log_and_linear(tmp_path):
    h = Hist2D(0., 2., 4, 0., 2., 4)
    h.fillmany(np.linspace(0.1, 1.9, 40), np.linspace(0.1, 1.9, 40),
               np.linspace(0.1, 1.9, 40) ** 2)
    out_log = tmp_path / 'h2_log.png'     # log=True default needs content
    out_lin = tmp_path / 'h2_lin.png'
    h.savefig(str(out_log))               # default log=True (LogNorm)
    h.savefig(str(out_lin), log=False)
    for f in (out_log, out_lin):
        assert f.exists()
        assert f.stat().st_size > 0
    assert plt.get_fignums() == []


@pytest.mark.medium
def test_est1d_savefig_smoke(tmp_path):
    e = Est1D(0., 1., 8)
    for i in range(8):
        e.fill(0.0625 + 0.125 * i, 1.0 + i, 0.1)
    out = tmp_path / 'est1d.png'
    e.savefig(str(out))
    assert out.exists()
    assert out.stat().st_size > 0
    assert plt.get_fignums() == []


# --- G: operation matrix, ctypes fetch after every step --------------------------

def test_hist1d_op_matrix_fetch_after_each_step():
    # every ctypes fetcher must agree with the independently derived state
    # after each operation of the matrix
    h = Hist1D(0., 2., 4)
    assert np.array_equal(h.getWeight(), [0., 0., 0., 0.])
    assert np.array_equal(h.getHit(), [0., 0., 0., 0.])
    assert np.array_equal(h.getWW(), [0., 0., 0., 0.])
    assert h.getAccWeight() == pytest.approx(0.0)

    h.fill(0.25, 2.0)
    assert np.array_equal(h.getWeight(), [2., 0., 0., 0.])
    assert np.array_equal(h.getHit(), [1., 0., 0., 0.])
    assert np.array_equal(h.getWW(), [4., 0., 0., 0.])
    assert h.getAccWeight() == pytest.approx(2.0)

    h.fillmany(np.array([0.75, 1.25]), np.array([3., 1.]))
    assert np.array_equal(h.getWeight(), [2., 3., 1., 0.])
    assert np.array_equal(h.getHit(), [1., 1., 1., 0.])
    assert np.array_equal(h.getWW(), [4., 9., 1., 0.])
    assert h.getAccWeight() == pytest.approx(6.0)
    assert h.getTotalHit() == pytest.approx(3.0)

    other = Hist1D(0., 2., 4)
    other.fill(1.75, 5.0)
    h.merge(other)
    assert np.array_equal(h.getWeight(), [2., 3., 1., 5.])
    assert np.array_equal(h.getHit(), [1., 1., 1., 1.])
    assert np.array_equal(h.getWW(), [4., 9., 1., 25.])
    assert h.getAccWeight() == pytest.approx(11.0)

    h.scale(0.5)
    assert np.array_equal(h.getWeight(), [1., 1.5, 0.5, 2.5])
    assert np.array_equal(h.getHit(), [1., 1., 1., 1.])      # unscaled
    # EXPECTED-FAIL (round-2 ledger): ww scales by 0.5^2 = 0.25; the stale
    # cinemabin .so leaves ww at [4, 9, 1, 25]. Green after the gate rebuild.
    assert np.array_equal(h.getWW(), [1., 2.25, 0.25, 6.25])
    assert np.allclose(h.getSdev(), [1., 1.5, 0.5, 2.5])     # sqrt(ww), |f| * w
    assert h.getAccWeight() == pytest.approx(5.5)

    h.reset()
    assert np.array_equal(h.getWeight(), [0., 0., 0., 0.])
    assert np.array_equal(h.getHit(), [0., 0., 0., 0.])
    assert np.array_equal(h.getWW(), [0., 0., 0., 0.])
    assert h.getAccWeight() == pytest.approx(0.0)
    assert h.getTotalHit() == pytest.approx(0.0)

    h.fill(0.25, 4.0)
    assert np.array_equal(h.getWeight(), [4., 0., 0., 0.])
    assert np.array_equal(h.getHit(), [1., 0., 0., 0.])
    assert np.array_equal(h.getWW(), [16., 0., 0., 0.])
    assert h.getAccWeight() == pytest.approx(4.0)


def test_hist2d_op_matrix_fetch_after_each_step():
    h = Hist2D(0., 2., 2, 0., 4., 2)
    assert np.array_equal(h.getWeight(), np.zeros((2, 2)))

    h.fill(0.5, 1.0, 2.0)   # x bin 0, y bin 0
    assert np.array_equal(h.getWeight(), [[2., 0.], [0., 0.]])
    assert np.array_equal(h.getHit(), [[1., 0.], [0., 0.]])

    h.fill(1.5, 3.0, 1.0)   # x bin 1, y bin 1
    assert np.array_equal(h.getWeight(), [[2., 0.], [0., 1.]])

    g = Hist2D(0., 2., 2, 0., 4., 2)
    g.fill(0.5, 1.0, 1.0)
    h.merge(g)
    assert np.array_equal(h.getWeight(), [[3., 0.], [0., 1.]])
    assert np.array_equal(h.getHit(), [[2., 0.], [0., 1.]])
    assert h.getAccWeight() == pytest.approx(4.0)

    h.scale(2.0)
    assert np.array_equal(h.getWeight(), [[6., 0.], [0., 2.]])
    assert np.array_equal(h.getHit(), [[2., 0.], [0., 1.]])
    assert h.getTotalHit() == pytest.approx(3.0)  # hit survives scaling

    # density after the whole matrix: 6/2 and 2/1
    assert np.array_equal(h.getDensity(), [[3., 0.], [0., 2.]])


def test_edges_immutable_across_operation_matrix():
    for h in (Hist1D(1., 3., 4), Hist1D(0.1, 10., 3, linear=False)):
        before = h.getEdges()
        h.fill(1.5, 2.0)
        assert np.array_equal(h.getEdges(), before)
        h.scale(3.0)
        assert np.array_equal(h.getEdges(), before)
        h.reset()
        assert np.array_equal(h.getEdges(), before)
        # centres are derived from the edges, so they move with them only
        assert np.allclose(h.getCentre(),
                           before[:-1] + np.diff(before) * 0.5)


def test_dimension_datasize_totalhit_parity():
    h1 = Hist1D(0., 1., 7)
    assert h1.dimension() == 1
    assert h1.getDataSize() == 7
    assert h1.getDataSize() == len(h1.getWeight())

    h2 = Hist2D(0., 1., 2, 0., 1., 3)
    assert h2.dimension() == 2
    assert h2.getDataSize() == 6 == h2.xNumBin * h2.yNumBin
    h2.fill(0.25, 0.25, 1.0)
    h2.fill(0.75, 0.75, 1.0)
    h2.fill(0.25, 0.75, 1.0)
    assert h2.getTotalHit() == pytest.approx(3.0)
    h2.scale(10.0)
    assert h2.getTotalHit() == pytest.approx(3.0)  # hit is call-based

    assert Est1D(0., 1., 3).dimension() == 1
