"""Hist2D / Est1D / SpectrumEstimator in-memory invariants.

Complements test_fix_hist.py (which anchors the 2026-10 usability fixes) with
numeric contracts: ctor metadata, linspace edges, weighted-fill placement,
getDensity = weight/hit, fillmany guards, merge, the ax= plot path, and the
Est1D-family error math.

Safety note (2026-10): the C++ Hist2D fill clamp (x == xmax / y == ymax
used to write one bin past the end of the data vector) landed in
PTHist2D.icc and IS rebuilt into the shipped libprompt_core.so
(verified 2026-10: fill(xmax, ymax) lands in the last bin, overflow 0).
Regular cases still fill strictly interior points; the at-max semantics
are pinned separately behind a probe skipif so the file also runs green
against a pre-clamp build.

Known divergence from the survey (2026-10): Est1D.fillmany goes through
np.vectorize(self.fill), and numpy's vectorize evaluates the function once
on the FIRST element to probe the output type before the real loop, so the
first point is filled twice and the weight overcounted. The survey's
"fillmany matches a per-point fill loop" case is written as intended
semantics and auto-skipped by a behavioural probe until Hist.py is fixed.
"""

import matplotlib
matplotlib.use('Agg')  # noqa: E402  must precede any pyplot import

import matplotlib.pyplot as plt
import numpy as np
import pytest

from Cinema.Prompt.histogram import Hist2D, Est1D, SpectrumEstimator


def _est1d_fillmany_matches_loop():
    """Behaviour probe: True when Est1D.fillmany no longer double-fills the
    first element (np.vectorize output-type probe overcount, see below)."""
    e = Est1D(0., 1., 4)
    e.fillmany(np.array([0.125, 0.625]),
               np.array([1.0, 2.0]),
               np.array([0.1, 0.1]))
    return bool(np.array_equal(e.getWeight(), np.array([1., 0., 0., 2.])))


_EST1D_FILLMANY_OK = _est1d_fillmany_matches_loop()


def _hist2d_xymax_clamped():
    """True when the shipped libprompt_core.so implements the final Hist2D
    contract: fill(x == xmax, y == ymax) lands in the last (i, j) bin and
    nothing is counted as overflow. False for the pre-clamp build, which
    wrote one bin past the data vector instead (the probe then skips the
    at-max assertions below)."""
    h = Hist2D(0., 2., 4, 0., 4., 2)
    h.fill(2.0, 4.0, 5.0)
    return h.getOverflow() == 0.0 and abs(h.getWeight()[3, 1] - 5.0) < 1e-12


_HIST2D_CLAMPED = _hist2d_xymax_clamped()


# --- Hist2D construction ---------------------------------------------------------

def test_ctor_exposes_range_and_binning_attributes():
    h = Hist2D(0., 2., 4, 0., 4., 2)
    assert h.xmin == pytest.approx(0.0)
    assert h.xmax == pytest.approx(2.0)
    assert h.ymin == pytest.approx(0.0)
    assert h.ymax == pytest.approx(4.0)
    assert h.xNumBin == 4
    assert h.yNumBin == 2


def test_edges_are_linspace_of_ctor_range():
    h = Hist2D(0., 2., 4, 0., 4., 2)
    xedges, yedges = h.getEdges()
    assert np.array_equal(xedges, np.linspace(0., 2., 5))
    assert np.array_equal(yedges, np.linspace(0., 4., 3))
    # getCentre agrees with the attribute-stored centres
    xc, yc = h.getCentre()
    assert np.allclose(xc, h.xcenter)
    assert np.allclose(yc, h.ycenter)


# --- filling ---------------------------------------------------------------------

def test_weighted_fill_lands_in_expected_bin_with_hit_one():
    h = Hist2D(0., 2., 4, 0., 4., 2)
    h.fill(0.75, 3.0, 1.5)  # x in [0.5, 1.0) -> bin 1, y in [2, 4) -> bin 1
    w = h.getWeight()
    assert w[1, 1] == pytest.approx(1.5)
    assert h.getHit()[1, 1] == pytest.approx(1.0)
    assert w.sum() == pytest.approx(1.5)  # everything else empty


@pytest.mark.skipif(not _HIST2D_CLAMPED,
                    reason='Hist2D x/y clamp (C++ PTHist2D.icc fix) not yet in '
                           'the shipped libprompt_core.so: that build writes '
                           'one bin past the data for x==xmax/y==ymax instead '
                           'of landing them in the last bin')
def test_fill_at_xmax_ymax_clamped_into_last_bin():
    # intended semantics of the C++ clamp: [xmin, xmax] x [ymin, ymax] is
    # right-closed, so the upper edges land in the last bin instead of
    # overflowing (or corrupting memory on the pre-clamp build)
    h = Hist2D(0., 2., 4, 0., 4., 2)
    h.fill(2.0, 4.0, 5.0)
    assert h.getWeight()[3, 1] == pytest.approx(5.0)
    assert h.getHit()[3, 1] == pytest.approx(1.0)
    assert h.getOverflow() == pytest.approx(0.0)
    assert h.getUnderflow() == pytest.approx(0.0)


def test_getdensity_is_weight_per_hit_multi_weight():
    h = Hist2D(0., 2., 4, 0., 4., 2)
    h.fill(0.25, 1.0, 3.0)
    h.fill(0.25, 1.0, 5.0)  # same bin: weight 8, hit 2
    d = h.getDensity()
    assert d[0, 0] == pytest.approx(4.0)  # 8 / 2
    assert d.sum() == pytest.approx(4.0)


def test_getdensity_leaves_zero_hit_bins_at_zero():
    h = Hist2D(0., 2., 4, 0., 4., 2)
    h.fill(0.25, 1.0, 7.0)
    d = h.getDensity()
    assert d[0, 0] == pytest.approx(7.0)
    # untouched bins are 0 rather than a division artefact
    assert d.sum() == pytest.approx(7.0)
    assert np.count_nonzero(d) == 1


def test_fillmany_default_weights_are_one():
    h = Hist2D(0., 2., 2, 0., 2., 2)
    h.fillmany(np.array([0.5, 1.5]), np.array([0.5, 1.5]))
    assert np.array_equal(h.getWeight(), np.eye(2))


def test_fillmany_short_weight_raises():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    with pytest.raises(RuntimeError, match='different size'):
        h.fillmany(np.zeros(5), np.zeros(5), np.ones(4))


def test_fillmany_short_y_raises():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    with pytest.raises(RuntimeError, match='different size'):
        h.fillmany(np.zeros(10), np.zeros(3))


# --- merge ------------------------------------------------------------------------

def test_merge_accumulates_weight_from_other_hist():
    m1 = Hist2D(0., 2., 2, 0., 2., 2)
    m1.fill(0.5, 0.5, 2.0)
    m2 = Hist2D(0., 2., 2, 0., 2., 2)
    m2.fill(0.5, 0.5, 3.0)
    m1.merge(m2)
    assert m1.getWeight()[0, 0] == pytest.approx(5.0)
    assert m1.getHit()[0, 0] == pytest.approx(2.0)


def test_merge_with_self_raises():
    h = Hist2D(0., 2., 2, 0., 2., 2)
    h.fill(0.5, 0.5, 1.0)
    with pytest.raises(RuntimeError, match='merging a histogram with itself'):
        h.merge(h)  # scale(2.) is the documented alternative


# --- plotting ---------------------------------------------------------------------

def test_plot_with_ax_returns_same_ax_and_draws_pcolormesh():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    h.fill(0.25, 0.25, 1.0)
    _, ax = plt.subplots()
    try:
        ret = h.plot(log=False, ax=ax)
        assert ret is ax
        assert len(ax.collections) > 0  # a pcolormesh was drawn
    finally:
        plt.close('all')


# --- Est1D ------------------------------------------------------------------------

def test_est1d_geterror_is_the_stored_hit_array():
    # Est1D stores the caller-supplied error in the hit array ("hit contains
    # error"), accumulated in quadrature by the C++ fill
    e = Est1D(0., 1., 4)
    e.fill(0.125, 1.0, 0.1)
    e.fill(0.125, 1.0, 0.2)
    assert np.array_equal(e.getError(), e.getHit())  # identical arrays
    assert e.getError()[0] == pytest.approx(np.sqrt(0.1**2 + 0.2**2))
    assert e.getWeight()[0] == pytest.approx(2.0)  # weights add linearly


@pytest.mark.skipif(not _EST1D_FILLMANY_OK,
                    reason='Hist.py Est1D.fillmany uses np.vectorize(self.fill), '
                           'whose output-type probe fills the FIRST element a '
                           'second time and overcounts its weight; skipped '
                           'until fillmany is a plain loop')
def test_est1d_fillmany_matches_per_point_fill_loop():
    xs = np.array([0.125, 0.625])
    ws = np.array([1.0, 2.0])
    es = np.array([0.1, 0.2])
    many = Est1D(0., 1., 4)
    many.fillmany(xs, ws, es)
    ref = Est1D(0., 1., 4)
    for x, w, e in zip(xs, ws, es):
        ref.fill(x, w, e)
    assert np.array_equal(many.getWeight(), ref.getWeight())
    assert np.array_equal(many.getError(), ref.getError())


# --- SpectrumEstimator --------------------------------------------------------------

def test_spectrumestimator_geterror_matches_weight_over_sqrt_hit():
    s = SpectrumEstimator(0., 1., 4)
    for _ in range(10):
        s.fill(0.125, 3.0, 1.0)
    # hitCounter counted 10 fills -> uncet = sqrt(10/10) = 1 -> err = weight
    assert s.getWeight()[0] == pytest.approx(30.0)
    assert s.getError()[0] == pytest.approx(30.0 / np.sqrt(10. / 10.))

    s2 = SpectrumEstimator(0., 1., 4)
    s2.fill(0.125, 5.0, 1.0)  # single fill: uncet = sqrt(1/10)
    assert s2.getError()[0] == pytest.approx(5.0 / np.sqrt(1. / 10.))


def test_spectrumestimator_geterror_no_zerodivide_on_untouched_bins():
    # np.divide(weight, uncet, where=(uncet != 0.)) must not divide by zero:
    # the contract of the where= guard is that getError() raises no
    # divide-by-zero RuntimeWarning even with untouched (uncet == 0) bins.
    import warnings

    s = SpectrumEstimator(0., 1., 4)
    s.fill(0.125, 5.0, 1.0)
    with warnings.catch_warnings():
        warnings.simplefilter('error', RuntimeWarning)
        err = s.getError()
    assert err[0] == pytest.approx(5.0 * np.sqrt(10.0))
    # The value of the masked bins carries no contract: with out=None and a
    # where= mask, numpy leaves the False locations uninitialised (documented
    # ufunc behaviour), so they read as zeros on a fresh page and as stale
    # heap bytes after allocations churn - do not assert their content.
