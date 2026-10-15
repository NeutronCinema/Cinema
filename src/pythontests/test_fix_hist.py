"""Regression tests for the Hist.py usability/bug fixes.

Covers usability-report findings #4, #6, #13, #23, #35, #36:
- #4  Hist2D.fillmany size guard AND->OR (both out-of-bounds read modes)
- #6  Est1D/SpectrumEstimator.plot aligned with Hist1D.plot (savefig worked)
- #13 Hist2D.getDensity returns weight/hit, not raw weights
- #23 consistent plot/savefig contracts (raise, log defaults, fig returns)
- #35 NumpyHist1D.getYedges explicit error instead of AttributeError
- #36 Hist2D ctor failure message + silent __del__ on failed construction
"""

import gc
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pytest

from Cinema.Prompt.histogram import (Hist1D, Hist2D, Est1D, SpectrumEstimator,
                                     NumpyHist1D, NumpyHist2D)


def _filledHist1D():
    h = Hist1D(0., 1., 10)
    h.fillmany(np.linspace(0.05, 0.95, 100))
    return h


# --- #4: Hist2D.fillmany must reject every mismatched array size -------------

def test_fillmany_short_weight_raises():
    # report repro mode 1: x and y match, weight is short (was read OOB in C)
    h = Hist2D(0., 2., 4, 0., 2., 4)
    with pytest.raises(RuntimeError, match='different size'):
        h.fillmany(np.zeros(3), np.zeros(3), np.zeros(2))


def test_fillmany_short_y_raises():
    # report repro mode 2: default weight, y is short (was read OOB in C)
    h = Hist2D(0., 2., 4, 0., 2., 4)
    with pytest.raises(RuntimeError, match='different size'):
        h.fillmany(np.zeros(1000), np.zeros(10))


def test_fillmany_long_weight_raises():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    with pytest.raises(RuntimeError, match='different size'):
        h.fillmany(np.zeros(10), np.zeros(10), np.ones(11))


def test_fillmany_matching_sizes_still_works():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    h.fillmany(np.full(100, 0.25), np.zeros(100), np.full(100, 2.0))
    assert h.getTotalWeight() == pytest.approx(200.0)


def test_fillmany_1d_sibling_still_works():
    h = Hist1D(0., 2., 4)
    h.fillmany(np.zeros(5))
    assert h.getTotalWeight() == pytest.approx(5.0)


# --- #13: getDensity is weight/hit, not the raw weights -----------------------

def test_getDensity_is_weight_per_hit():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    h.fill(0.25, 0.25, 1.0)
    h.fill(0.25, 0.25, 3.0)
    assert h.getWeight()[0, 0] == pytest.approx(4.0)
    # was returning the raw weight (4.0); density is weight/hit = 2.0
    assert h.getDensity()[0, 0] == pytest.approx(2.0)


def test_getDensity_zero_hit_bins_stay_zero():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    h.fill(0.25, 0.25, 7.0)  # one bin only
    d = h.getDensity()
    assert d[0, 0] == pytest.approx(7.0)  # 7.0 weight / 1 hit
    # zero-hit bins are left at 0 rather than divided by zero
    assert d.sum() == pytest.approx(7.0)


# --- #23: consistent plot/savefig contracts -----------------------------------

def test_empty_hist2d_plot_raises_instead_of_returning_none():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    with pytest.raises(ValueError, match='vmin'):
        h.plot()  # swallowed its exception and returned None before the fix


def test_empty_hist2d_plot_linear_scale_still_works():
    h = Hist2D(0., 2., 4, 0., 2., 4)
    fig = h.plot(log=False)
    assert isinstance(fig, matplotlib.figure.Figure)
    plt.close(fig)


def test_hist1d_plot_returns_fig_or_ax():
    h = _filledHist1D()
    fig = h.plot()
    assert isinstance(fig, matplotlib.figure.Figure)
    _, ax = plt.subplots()
    assert h.plot(ax=ax) is ax
    plt.close(fig)


def test_hist1d_plot_log_list_honoured():
    # guard for the shared plot helper: the [logx, logy] list form must win
    h = _filledHist1D()
    fig = h.plot(log=[False, False])
    assert fig.axes[0].get_xscale() == 'linear'
    assert fig.axes[0].get_yscale() == 'linear'
    fig = h.plot(log=[True, True])
    assert fig.axes[0].get_xscale() == 'log'
    assert fig.axes[0].get_yscale() == 'log'
    plt.close(fig)


@pytest.mark.slow  # >0.7 s body: excluded from the pre-push hook, runs in cimbuild -t
def test_hist1d_savefig(tmp_path):
    out = tmp_path / 'h1.png'
    _filledHist1D().savefig(str(out))
    assert out.stat().st_size > 0


@pytest.mark.slow  # >0.7 s body: excluded from the pre-push hook, runs in cimbuild -t
def test_hist2d_savefig(tmp_path):
    h = Hist2D(0., 2., 4, 0., 2., 4)
    h.fill(0.25, 0.25, 1.0)
    out = tmp_path / 'h2.png'
    h.savefig(str(out))
    assert out.stat().st_size > 0


# --- #6: Est1D/SpectrumEstimator aligned with the Hist1D contract -------------

def _filledEst1D():
    e = Est1D(0., 1., 10)
    e.fillmany(np.linspace(0.05, 0.95, 10), np.ones(10), np.full(10, 0.1))
    return e


def _filledSpectrumEstimator():
    s = SpectrumEstimator(0., 1., 10)
    s.fillmany(np.linspace(0.05, 0.95, 10), np.ones(10), np.full(10, 1.0))
    return s


def test_est1d_savefig(tmp_path):
    out = tmp_path / 'est1d.png'
    _filledEst1D().savefig(str(out))  # was: TypeError on the title kwarg
    assert out.stat().st_size > 0


def test_spectrumestimator_savefig(tmp_path):
    out = tmp_path / 'spec.png'
    _filledSpectrumEstimator().savefig(str(out))  # was: TypeError
    assert out.stat().st_size > 0


def test_est1d_plot_returns_fig_and_ax():
    fig = _filledEst1D().plot()  # was: always None
    assert isinstance(fig, matplotlib.figure.Figure)
    _, ax = plt.subplots()
    assert _filledEst1D().plot(ax=ax) is ax
    plt.close(fig)


def test_spectrumestimator_plot_returns_fig():
    fig = _filledSpectrumEstimator().plot()  # was: always None
    assert isinstance(fig, matplotlib.figure.Figure)
    plt.close(fig)


def test_est1d_plot_positional_show_label_compat():
    # legacy positional (show, label) calls must keep working
    fig = _filledEst1D().plot(False, 'mylabel')
    assert isinstance(fig, matplotlib.figure.Figure)
    assert fig.axes[0].get_legend() is not None
    plt.close(fig)


def test_est1d_plot_log_kwargs():
    fig = _filledEst1D().plot(False, 'lbl', title='T', log=[True, False])
    assert fig.axes[0].get_xscale() == 'log'
    assert fig.axes[0].get_yscale() == 'linear'
    assert fig.axes[0].get_title() == 'T'
    plt.close(fig)


# --- #36: ctor failure message and quiet __del__ ------------------------------

def test_hist2d_ctor_failure_names_hist2d():
    with pytest.raises(RuntimeError, match='Failed to create Hist2D'):
        Hist2D(0., 2., 4)  # was: 'Failed to create Hist1D'


def test_hist1d_ctor_failure_message_unchanged():
    with pytest.raises(RuntimeError, match='Failed to create Hist1D'):
        Hist1D(0., 2.)


def test_failed_construction_does_not_raise_in_del():
    # a failed (or never-run) __init__ must not make __del__ raise
    unraisable = []
    old_hook = sys.unraisablehook
    sys.unraisablehook = unraisable.append
    try:
        with pytest.raises(RuntimeError):
            Hist2D(0., 2., 4)
        # also cover objects whose __init__ never ran at all
        for cls in (Hist1D, Hist2D):
            obj = object.__new__(cls)
            del obj
        gc.collect()
    finally:
        sys.unraisablehook = old_hook
    # filter to our own defect so unrelated library noise cannot fail this
    bad = [u for u in unraisable
           if isinstance(u.exc_value, AttributeError) and
           ('managedBySelf' in str(u.exc_value) or "'cobj'" in str(u.exc_value))]
    assert bad == []


def test_owned_and_borrowed_hist1d_lifetimes():
    owner = Hist1D(0., 1., 10)
    assert owner.managedBySelf is True
    borrowed = Hist1D(cobj=owner.cobj)  # borrowed cobj must not be freed
    assert borrowed.managedBySelf is False
    del borrowed
    assert owner.numbin == 10  # owner still valid after the borrowed del
    del owner


# --- #35: NumpyHist1D.getYedges fails with an explicit message ----------------

def test_numpyhist1d_getyedges_explicit_error():
    n = NumpyHist1D(10, [0., 1.])
    with pytest.raises(RuntimeError, match='one-dimensional'):
        n.getYedges()  # was: AttributeError on the non-existing self.yedges


def test_numpyhist1d_getxedges_still_works():
    n = NumpyHist1D(10, [0., 1.])
    edges = n.getXedges()
    assert edges[0] == pytest.approx(0.0)
    assert edges[-1] == pytest.approx(1.0)


def test_numpyhist2d_getyedges_still_works():
    n = NumpyHist2D(10, 5, [[0., 1.], [0., 2.]])
    edges = n.getYedges()
    assert edges[0] == pytest.approx(0.0)
    assert edges[-1] == pytest.approx(2.0)
