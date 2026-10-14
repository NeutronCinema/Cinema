"""Coverage tests for Cinema.Experiment.Analyser and MPI2022ExpInfo.

Covers four pure-python analysis modules with no simulation involved:

- Analyser/DataLoader.py: ErrorPropagator array container (construction from
  arrays, derived errors, arithmetic, slicing) and the HDF5 DataLoader
  (round-trip through a synthetic file written to tmp_path, malformed inputs).
- Analyser/Data.py: RunData normalisation and the +=/-=//=/SampleData
  combination arithmetic on top of the synthetic file.
- Analyser/PixelLocator.py: KDTree pixel index math on a synthetic detector,
  DD multimap, generateDD text round-trip and IDFLoader unit conversion.
- Experiment/MPI2022ExpInfo.py: pure-logic invariants of the experiment
  catalogue dicts and detector corner table shipped under data/MPI2022Exp.
- Prompt/component.py: FlatAnalyser.make_plane curvature tilts (pure
  geometry, no simulation) - the single-curve branches must tilt about the
  same centred coordinates as the double-curve branch.
- Prompt/scorer.py: doc-level pin of the DirectSqw omega sign convention
  (omega = E_initial - E_final, positive = downscatter), matching the C++
  scorer fill in PTScorerDirectSqw.cc.

Every numeric pin below is derived in closed form from the synthetic inputs
(comments show the arithmetic); no expected value is copied from the code
under test. Note: error arrays carry an exact 0.0 in empty (zero-count) bins
- the np.divide calls pass out=np.zeros(...), so where-masked slots can never
inherit uninitialised heap memory (mechanism pinned by
test_masked_npdivide_always_carries_zeroed_out; the heap-poison churn in
test_loader_detector_error_is_sqrt_10w and
test_ep_itruediv_zero_divisor_slots_carry_exact_zero is the end-to-end
counterpart).
"""
import numpy as np
import pytest
import h5py

from Cinema.Experiment.Analyser import (
    DataLoader,
    ErrorPropagator,
    Normalise,
    RunData,
    SampleData,
    PixelLocator,
    IDFLoader,
)
from Cinema.Experiment.Analyser.DataLoader import readKeys
from Cinema.Experiment.Analyser.PixelLocator import DD

# MPI2022ExpInfo resolves its data file via CINEMAPATH at import time; the
# catalogue dictionaries are plain data, so only pure-logic parts are tested.
from Cinema.Experiment.MPI2022ExpInfo import MPIRuns, ModuleCorner_Exp


# --------------------------------------------------------------------------
# Synthetic HDF5 detector files in the exact layout DataLoader parses:
#   /csns/instrument/<mod>/time_of_flight   - bin edges, microseconds
#   /csns/instrument/<mod>/pixel_id         - pixel ids (flattened on read)
#   /csns/instrument/<mod>/histogram_data   - (npix, ntof) counts matrix
#   /csns/histogram_data/monitor01/histogram_data - (1, ntof) monitor counts
# --------------------------------------------------------------------------
def _write_detector_file(path, module_name, tof_edges_us, pixel_id, counts,
                         monitor):
    with h5py.File(path, "w") as hf:
        grp = hf.create_group(f"csns/instrument/{module_name}")
        grp.create_dataset("time_of_flight", data=tof_edges_us)
        grp.create_dataset("pixel_id", data=pixel_id)
        grp.create_dataset("histogram_data", data=counts)
        hf.create_dataset("csns/histogram_data/monitor01/histogram_data",
                          data=monitor)
    return path


# 5 tof bins; pixel_id stored 2-D on purpose to pin DataLoader's flatten().
# counts[i, j] = 10*i + j + 1; monitor counts all 7.
SMALL_EDGES = np.array([10., 20., 30., 40., 50., 60.])
SMALL_PID = np.array([[7, 8, 9]], dtype=np.int64)
SMALL_COUNTS = np.array([[1, 2, 3, 4, 5],
                         [11, 12, 13, 14, 15],
                         [21, 22, 23, 24, 25]], dtype=np.int64)
SMALL_MON = np.full((1, 5), 7, dtype=np.int64)


# 34 bins: SampleData hardcodes its internal tofcut at 30, so only a file
# with more than 30 bins leaves deterministic surviving columns for it.
NBASE = 34
WIDE_EDGES = np.arange(NBASE + 1, dtype=float) * 10.0
WIDE_PID = np.array([7, 8, 9], dtype=np.int64)
WIDE_COUNTS = np.zeros((3, NBASE), dtype=np.int64)
WIDE_COUNTS[0, 30:] = [1, 2, 3, 4]
WIDE_COUNTS[1, 30:] = [5, 6, 7, 8]
WIDE_COUNTS[2, 30:] = [9, 10, 11, 12]
WIDE_MON = np.full((1, NBASE), 3, dtype=np.int64)


@pytest.fixture(scope="module")
def det_file(tmp_path_factory):
    return _write_detector_file(tmp_path_factory.mktemp("ana") / "mod.h5",
                                "mod", SMALL_EDGES, SMALL_PID, SMALL_COUNTS,
                                SMALL_MON)


@pytest.fixture(scope="module")
def wide_file(tmp_path_factory):
    return _write_detector_file(tmp_path_factory.mktemp("ana") / "wide.h5",
                                "wide", WIDE_EDGES, WIDE_PID, WIDE_COUNTS,
                                WIDE_MON)


# ------------------------------------------------- ErrorPropagator: container
def test_ep_ctor_copies_inputs_and_keeps_dtype():
    w = np.arange(6, dtype=np.int32).reshape(2, 3)
    x = np.array([10, 20, 30], dtype=np.int64)
    ep = ErrorPropagator(w, x, count=np.ones((2, 3)))
    # inputs are copied: later mutation of the caller's arrays must not leak in
    w[0, 0] = -1
    x[0] = -1
    assert ep.weight.dtype == np.int32          # dtype invariant preserved
    assert ep.weight.shape == (2, 3)
    assert ep.xcentre.dtype == np.int64
    assert ep.weight[0, 0] == 0
    assert ep.xcentre[0] == 10


def test_ep_ctor_error_direct_and_optional_ycentre():
    err = np.full((2, 3), 0.5)
    ep = ErrorPropagator(np.ones((2, 3)), np.arange(3.), error=err)
    # explicitly given errors are used as-is instead of being derived
    assert np.array_equal(ep.error, err)
    assert not hasattr(ep, "ycentre")            # ycentre stays optional
    yedge = np.array([0., 1., 2., 3.])
    ep2 = ErrorPropagator(np.ones((3, 3)), np.arange(3.), ycentre=yedge,
                          error=err)
    yedge[0] = 99.                               # ycentre is copied too
    assert ep2.ycentre[0] == 0.


def test_ep_default_error_is_weight_over_sqrt_count_over_10():
    # error = weight / sqrt(count/10):
    #   10/sqrt(40/10) = 10/2 = 5 ; 20/sqrt(10/10) = 20/1 = 20
    ep = ErrorPropagator(np.array([10., 20.]), np.array([0., 1.]),
                         count=np.array([40., 10.]))
    assert np.array_equal(ep.error, [5., 20.])


def test_ep_sum_axes():
    ep = ErrorPropagator(np.arange(6.).reshape(2, 3), np.arange(3.),
                         error=np.ones((2, 3)))
    assert np.array_equal(ep.sum(0), [3., 5., 7.])   # column sums
    assert np.array_equal(ep.sum(1), [3., 12.])      # row sums


def test_ep_scale_error_takes_abs_of_factor():
    ep = ErrorPropagator(np.array([1., -2.]), np.arange(2.),
                         error=np.array([3., 4.]))
    ep.scale(-2.)
    # weights take the sign, errors the magnitude: |factor| = 2
    assert np.array_equal(ep.weight, [-2., 4.])
    assert np.array_equal(ep.error, [6., 8.])


def test_ep_itruediv_combines_relative_errors():
    a = ErrorPropagator(np.array([10., 20.]), np.arange(2.),
                        error=np.array([1., 2.]))
    b = ErrorPropagator(np.array([4., 8.]), np.arange(2.),
                        error=np.array([0.4, 0.8]))
    a /= b
    # weights: 10/4, 20/8 ; relative errors per bin: a 1/10, 2/20 and
    # b 0.4/4, 0.8/8 (all 0.1); error = sqrt(0.1^2+0.1^2)*|ratio| = sqrt(0.02)*2.5
    assert np.allclose(a.weight, [2.5, 2.5], rtol=1e-13, atol=0.)
    assert a.error[0] == pytest.approx(2.5 * np.sqrt(0.02), rel=1e-13)
    assert a.error[1] == pytest.approx(2.5 * np.sqrt(0.02), rel=1e-13)


def test_ep_itruediv_zero_self_weight_gives_zero_ratio():
    # a zero-count numerator bin yields a zero ratio and an exact 0.0 error
    # (the masked selferr slot is pinned to 0.0, so no NaN/garbage can leak
    # through sqrt(...) into the empty bin)
    a = ErrorPropagator(np.array([0., 20.]), np.arange(2.),
                        error=np.array([0., 2.]))
    b = ErrorPropagator(np.array([4., 8.]), np.arange(2.),
                        error=np.array([0.4, 0.8]))
    a /= b
    assert a.weight[0] == 0.
    assert a.weight[1] == pytest.approx(2.5, rel=1e-13)
    assert a.error[0] == 0.


def test_ep_itruediv_zero_divisor_slots_carry_exact_zero():
    # dividing by an array holding zero-count bins: every where-masked
    # np.divide slot (both per-bin relative errors AND the ratio itself) must
    # come out as an exact 0.0, never inherited heap memory. Poison the heap
    # first so a reverted out= is likely to surface as 3.3 here (donor-buffer
    # luck can hide it - the np.divide spy test pins the mechanism itself).
    poison = [np.full(4096, 3.3) for _ in range(4)]
    del poison
    a = ErrorPropagator(np.array([10., 20.]), np.arange(2.),
                        error=np.array([1., 2.]))
    b = ErrorPropagator(np.array([4., 0.]), np.arange(2.),
                        error=np.array([0.4, 0.8]))
    a /= b
    # slot 0: ratio 10/4, relative errors 1/10 and 0.4/4 on the two sides
    assert a.weight[0] == pytest.approx(2.5, rel=1e-13)
    assert a.error[0] == pytest.approx(2.5 * np.sqrt(0.02), rel=1e-13)
    # slot 1: zero-count divisor -> zero ratio with an exact 0.0 error
    assert a.weight[1] == 0.
    assert a.error[1] == 0.


def test_masked_npdivide_always_carries_zeroed_out(det_file, monkeypatch):
    # deterministic mechanism pin: every where-masked np.divide issued by the
    # analyser must pass an all-zeros out=, so masked slots can never inherit
    # uninitialised heap memory (empty-bin error = 0.0 by construction).
    calls = []
    real_divide = np.divide

    def spy(num, den, out=None, where=None):
        if where is not None:
            calls.append(out is not None and bool(np.all(out == 0.)))
        return real_divide(num, den, out=out, where=where)

    monkeypatch.setattr(np, 'divide', spy)
    DataLoader(det_file, "mod", tofcut=2)      # detector + monitor ctor divides
    a = ErrorPropagator(np.array([10., 20.]), np.arange(2.),
                        error=np.array([1., 2.]))
    b = ErrorPropagator(np.array([4., 0.]), np.arange(2.),
                        error=np.array([0.4, 0.8]))
    a /= b                                     # selferr, othererr, ratio
    # 2 ctor divides + 3 divides in ErrorPropagator.divide, all with out=
    assert calls == [True, True, True, True, True]


def test_ep_arithmetic_rejects_mismatched_binning():
    ep = ErrorPropagator(np.ones(2), np.array([0., 1.]), error=np.ones(2))
    shifted = ErrorPropagator(np.ones(2), np.array([0., 2.]), error=np.ones(2))
    with pytest.raises(AssertionError):
        ep += shifted
    with pytest.raises(AssertionError):
        ep -= shifted
    # 2-D: ycentre is checked as well
    ep2 = ErrorPropagator(np.ones((2, 2)), np.arange(2.),
                          ycentre=np.array([0., 1.]), error=np.ones((2, 2)))
    other = ErrorPropagator(np.ones((2, 2)), np.arange(2.),
                            ycentre=np.array([0., 9.]), error=np.ones((2, 2)))
    with pytest.raises(AssertionError):
        ep2 += other


def test_ep_slicing_exposes_exact_subblocks():
    ep = ErrorPropagator(np.arange(6.).reshape(2, 3), np.arange(3.),
                         error=np.ones((2, 3)))
    assert np.array_equal(ep.weight[:, 1:3], [[1., 2.], [4., 5.]])
    assert np.array_equal(ep.weight[1], [3., 4., 5.])


# ------------------------------------------------------ DataLoader round-trip
def test_loader_tof_centres_are_bin_midpoints_in_seconds(det_file):
    # file stores microsecond edges; loader converts with *1e-6 and forms
    # (edge[:-1] + diff/2): midpoints of [10,20,30,40,50,60] us
    dl = DataLoader(det_file, "mod", tofcut=2)
    assert np.allclose(dl.tofCentre,
                       [1.5e-5, 2.5e-5, 3.5e-5, 4.5e-5, 5.5e-5],
                       rtol=1e-13, atol=0.)
    # ycentre keeps the raw (converted) edges, in seconds
    assert np.allclose(dl.detErrPro.ycentre,
                       [1e-5, 2e-5, 3e-5, 4e-5, 5e-5, 6e-5],
                       rtol=1e-13, atol=0.)


def test_loader_roundtrip_detector_counts_and_tofcut(det_file):
    dl = DataLoader(det_file, "mod", tofcut=2)
    # first `tofcut` columns are zeroed, the rest survive verbatim as int64
    assert np.array_equal(dl.detErrPro.weight,
                          [[0, 0, 3, 4, 5],
                           [0, 0, 13, 14, 15],
                           [0, 0, 23, 24, 25]])
    assert dl.detErrPro.weight.dtype == np.int64
    # pixel_id was stored as a (1,3) array and comes back flattened
    assert dl.detErrPro.xcentre.shape == (3,)
    assert np.array_equal(dl.detErrPro.xcentre, [7, 8, 9])


def test_loader_detector_error_is_sqrt_10w(det_file):
    # counts are reused as count and weight, so error = w/sqrt(w/10) = sqrt(10w):
    # row 0 -> sqrt(30), sqrt(40), sqrt(50) in the surviving columns.
    # Churn the heap with poison floats before the DataLoader construction:
    # a divide that drops its out= is likely to surface 3.3 in the tofcut-
    # zeroed slots below instead of the empty-bin 0.0 (donor-buffer luck can
    # hide it - the np.divide spy test pins the mechanism itself).
    poison = [np.full(4096, 3.3) for _ in range(4)]
    del poison
    dl = DataLoader(det_file, "mod", tofcut=2)
    expected = np.sqrt(10. * SMALL_COUNTS[:, 2:])
    assert np.allclose(dl.detErrPro.error[:, 2:], expected, rtol=1e-13, atol=0.)
    # empty-bin convention: the cut columns carry an exact 0.0 error
    assert np.all(dl.detErrPro.error[:, :2] == 0.)
    assert np.all(dl.moniErrPro.error[:2] == 0.)


def test_loader_monitor_roundtrip(det_file):
    dl = DataLoader(det_file, "mod", tofcut=2)
    assert np.array_equal(dl.moniErrPro.weight, [0, 0, 7, 7, 7])
    # sqrt(10*7) = sqrt(70) where the monitor kept counts
    assert np.allclose(dl.moniErrPro.error[2:], np.full(3, np.sqrt(70.)),
                       rtol=1e-13, atol=0.)
    # the monitor ErrorPropagator carries no ycentre
    assert not hasattr(dl.moniErrPro, "ycentre")


def test_loader_full_tofcut_zeroes_everything(wide_file):
    dl = DataLoader(wide_file, "wide", tofcut=NBASE)
    assert dl.detErrPro.weight.sum() == 0
    assert dl.moniErrPro.weight.sum() == 0
    # bin centres still cover all 34 bins: last midpoint is (330+340)/2 us
    assert dl.tofCentre.size == NBASE
    assert dl.tofCentre[-1] == pytest.approx(3.35e-4, rel=1e-13)


def test_loader_malformed_inputs_raise_clean_exceptions(tmp_path):
    # missing HDF5 file
    with pytest.raises(OSError):
        DataLoader(tmp_path / "absent.h5", "mod")
    # existing file that is not HDF5 at all
    junk = tmp_path / "junk.h5"
    junk.write_text("definitely not hdf5\n")
    with pytest.raises(OSError):
        DataLoader(junk, "mod")
    # valid file but wrong module name -> absent group path
    good = _write_detector_file(tmp_path / "mod.h5", "mod", SMALL_EDGES,
                                SMALL_PID, SMALL_COUNTS, SMALL_MON)
    with pytest.raises(KeyError):
        DataLoader(good, "nomod")


def test_readkeys_enumerates_all_node_paths(det_file, capsys):
    keys = []
    with h5py.File(det_file, "r") as hf:
        readKeys(keys, hf)
    # 1 root group + 2 intermediate groups + 1 monitor parent + 1 module group
    # + 4 datasets = 9 nodes, each listed once with its full HDF5 path
    assert len(keys) == 9
    assert set(keys) == {
        "/csns",
        "/csns/histogram_data",
        "/csns/histogram_data/monitor01",
        "/csns/histogram_data/monitor01/histogram_data",
        "/csns/instrument",
        "/csns/instrument/mod",
        "/csns/instrument/mod/histogram_data",
        "/csns/instrument/mod/pixel_id",
        "/csns/instrument/mod/time_of_flight",
    }
    # recursion into datasets hits the documented except branch: one
    # AttributeError message per dataset (4 datasets)
    assert capsys.readouterr().out.count("has no attribute 'keys'") == 4


# --------------------------------------------------- RunData / SampleData
def test_normalise_enum_members():
    assert Normalise.skip.value == 0
    assert Normalise.byMonitor.value == 1
    assert Normalise.byMonitorTOF.value == 2
    assert Normalise.byProtonCharge.value == 3


def test_rundata_bymonitor_scales_by_total_monitor(det_file):
    # monitor keeps 3 bins of 7 counts -> total 21; every detector count is
    # divided by 21 (e.g. 3 -> 1/7, 4 -> 4/21)
    rd = RunData(det_file, "mod", tofcut=2)
    assert rd.moduleName == "mod"
    assert np.allclose(rd.detErrPro.weight[0, 2:], [1. / 7., 4. / 21., 5. / 21.],
                       rtol=1e-13, atol=0.)
    assert np.allclose(rd.detErrPro.weight[2, 2:],
                       [23. / 21., 24. / 21., 25. / 21.], rtol=1e-13, atol=0.)
    # errors scale with the same factor: sqrt(30)/21
    assert rd.detErrPro.error[0, 2] == pytest.approx(np.sqrt(30.) / 21.,
                                                     rel=1e-13)


def test_rundata_skip_keeps_raw_counts(det_file):
    rd = RunData(det_file, "mod", tofcut=2, normMethod=Normalise.skip)
    assert np.array_equal(rd.detErrPro.weight[0], [0, 0, 3, 4, 5])
    assert rd.detErrPro.weight.dtype == np.int64


def test_rundata_unknown_norm_method_raises(det_file):
    with pytest.raises(RuntimeError, match='Unknown normalise method'):
        RunData(det_file, "mod", tofcut=2, normMethod=None)


def test_rundata_iadd_doubles_counts_and_quadratures_errors(det_file):
    rd = RunData(det_file, "mod", tofcut=2)
    rd2 = RunData(det_file, "mod", tofcut=2)
    before = rd
    rd += rd2
    assert rd is before                              # in-place, returns self
    assert np.allclose(rd.detErrPro.weight[0, 2:], [2. / 7., 8. / 21., 10. / 21.],
                       rtol=1e-13, atol=0.)
    # identical runs -> error grows by sqrt(2): sqrt(2*30)/21
    assert rd.detErrPro.error[0, 2] == pytest.approx(np.sqrt(60.) / 21.,
                                                     rel=1e-13)
    # the monitor is accumulated the same way
    assert np.array_equal(rd.moniErrPro.weight, [0, 0, 14, 14, 14])
    assert rd.moniErrPro.error[2] == pytest.approx(np.sqrt(2. * 70.),
                                                   rel=1e-13)


def test_rundata_isub_cancels_detector_but_adds_monitor(det_file):
    # documented quirk of RunData.__isub__: the detector is subtracted while
    # the monitor is ADDED (monitor charges of both runs accumulate)
    rd = RunData(det_file, "mod", tofcut=2)
    rd -= RunData(det_file, "mod", tofcut=2)
    assert np.array_equal(rd.detErrPro.weight, np.zeros((3, 5)))
    assert np.array_equal(rd.moniErrPro.weight, [0, 0, 14, 14, 14])


def test_rundata_itruediv_gives_unit_ratio_and_keeps_monitor(det_file):
    rd = RunData(det_file, "mod", tofcut=2)
    rd /= RunData(det_file, "mod", tofcut=2)
    # self-division: surviving bins collapse to exactly 1
    assert np.array_equal(rd.detErrPro.weight[:, 2:], np.ones((3, 3)))
    # only the detector is divided; the monitor stays untouched
    assert np.array_equal(rd.moniErrPro.weight, [0, 0, 7, 7, 7])


def test_sampledata_without_subtractions_normalises_by_monitor(wide_file):
    # SampleData uses its internal tofcut=30: 4 monitor bins of 3 survive
    sd = SampleData(wide_file, "wide")
    assert sd.moniErrPro.weight.sum() == 12
    assert np.allclose(sd.detErrPro.weight[0, 30:], [1. / 12., 1. / 6., 0.25,
                                                     1. / 3.],
                       rtol=1e-13, atol=0.)


def test_sampledata_subtracts_background_and_holder(wide_file):
    # bkg and holder are each normalised to the same 12-count monitor, so the
    # sample becomes det/12 - det/12 - det/12 = -det/12, and three equal
    # uncertainty contributions give error = sqrt(3)*sqrt(10w)/12
    bkg = RunData(wide_file, "wide")
    holder = RunData(wide_file, "wide")
    sd = SampleData(wide_file, "wide", bkgRun=bkg, holderRun=holder)
    w = WIDE_COUNTS[0, 30:].astype(float)
    assert np.allclose(sd.detErrPro.weight[0, 30:], -w / 12.,
                       rtol=1e-13, atol=0.)
    assert np.allclose(sd.detErrPro.error[0, 30:], np.sqrt(3. * 10. * w) / 12.,
                       rtol=1e-13, atol=0.)
    # monitor is added once per subtraction: 3 + 3 + 3
    assert np.array_equal(sd.moniErrPro.weight[30:], [9, 9, 9, 9])


# ------------------------------------------------------------- PixelLocator
# Synthetic detector: 3x3 pixels on a 10 mm pitch in the x/y plane at z=1 m,
# row-major so the KDTree index == pixel id == 3*row + col.
GRID_XY = [0., 10., 20.]
GRID_POS = np.array([[x, y, 1000.] for y in GRID_XY for x in GRID_XY])
GRID_IDS = np.arange(9)


@pytest.fixture(scope="module")
def locator():
    return PixelLocator(GRID_IDS, GRID_POS)


def test_locator_corner_pixels_hit_exactly(locator):
    for (x, y), want in [((0., 0.), 0), ((20., 0.), 2),
                         ((0., 20.), 6), ((20., 20.), 8)]:
        pid, dist = locator.locate(np.array([[x, y, 1000.]]))
        assert pid[0] == want
        assert dist[0] == 0.                # exact hit, zero distance


def test_locator_offcentre_point_snaps_to_nearest(locator):
    # (6, 2) mm: distances sqrt(4^2+2^2)=sqrt(20) to pixel 1,
    # sqrt(6^2+2^2)=sqrt(40) to pixel 0 -> pixel 1 wins
    pid, dist = locator.locate(np.array([[6., 2., 1000.]]))
    assert pid[0] == 1
    assert dist[0] == pytest.approx(np.sqrt(20.), rel=1e-13)


def test_locator_out_of_fov_returns_nearest_with_distance(locator):
    # documented behaviour: a point outside the active area still resolves to
    # the nearest pixel; the caller must judge by the returned distance
    pid, dist = locator.locate(np.array([[100., 100., 1000.]]))
    assert pid[0] == 8                                # nearest corner pixel
    assert dist[0] == pytest.approx(80. * np.sqrt(2.), rel=1e-13)


def test_locator_knn_orders_by_distance(locator):
    # (12, 4): sqrt(20) to pixel 1 (10,0), sqrt(40) to pixel 4 (10,10),
    # sqrt(80) to pixel 2 (20,0) -> the two closest are [1, 4] in ascending order;
    # a batched single-point query returns (1, 2) shaped arrays
    pid, dist = locator.locate(np.array([[12., 4., 1000.]]), numNearestPt=2)
    assert list(pid[0]) == [1, 4]
    assert dist[0][0] == pytest.approx(np.sqrt(20.), rel=1e-13)
    assert dist[0][1] == pytest.approx(np.sqrt(40.), rel=1e-13)


def test_locator_copies_inputs():
    pos = GRID_POS.copy()
    ids = GRID_IDS.copy()
    pl = PixelLocator(ids, pos)
    pos[0, 0] = 999.
    ids[4] = -1
    assert pl.location[0, 0] == 0.
    assert pl.pixelID[4] == 4


def test_locator_single_point_query_returns_scalars(locator):
    # a bare (unbatched) point degenerates to scalar results
    pid, dist = locator.locate((0., 0., 1000.))
    assert pid == 0
    assert dist == 0.
    assert isinstance(pid, np.integer)
    assert isinstance(dist, float)


# ------------------------------------------------------------ DD and files
def test_dd_multimap_semantics():
    dd = DD()
    assert dd.get(0, 1) is None              # empty map
    assert dd.get("missing", 1) is None      # unknown first key
    dd.set(0, 5, (1., 2.))
    dd.set(0, 5, (3., 4.))                   # same bin -> appends
    dd.set(0, 6, (9., 9.))                   # same pixel, other bin
    dd.set(1, 5, (7., 8.))                   # other pixel
    assert dd.get(0, 5) == [(1., 2.), (3., 4.)]
    assert dd.get(0, 6) == [(9., 9.)]
    assert dd.get(1, 5) == [(7., 8.)]
    assert dd.get(0, 7) is None
    assert dd.get(1, 6) is None


def test_generatedd_roundtrip_and_multifile_merge(tmp_path):
    pos = np.array([[-10., 0., 1000.], [0., 0., 1000.], [10., 0., 1000.]])
    loc = PixelLocator(np.array([5, 6, 7]), pos)
    # columns: tof_us, x, y, z [mm], Qe, Qt
    (tmp_path / "part0.txt").write_text(
        "100 -0.1 0.0 1000.0 11.0 21.0\n"    # tof bin 100//8=12, pixel idx 1
        "15  0.0  0.0 1000.0 12.0 22.0\n"    # tof bin 15//8=1,  pixel idx 1
        "16 10.0  0.0 1000.0 13.0 23.0\n")   # tof bin 16//8=2,  pixel idx 2
    (tmp_path / "part1.txt").write_text(
        "17 0.0 0.0 1000.0 14.0 24.0\n"      # tof bin 17//8=2,  pixel idx 1
        "16 0.0 0.0 1000.0 15.0 25.0\n")     # tof bin 16//8=2,  pixel idx 1
    dd = loc.generateDD(str(tmp_path / "part*.txt"), tofbinwidth=8)
    # pixel ids are rebased: key = pid - pixelID[0] (5 -> 0, 6 -> 1, 7 -> 2)
    assert sorted(int(k) for k in dd.dd.keys()) == [1, 2]
    assert np.array_equal(dd.get(1, 12), [[11., 21.]])
    assert np.array_equal(dd.get(1, 1), [[12., 22.]])
    assert np.array_equal(dd.get(2, 2), [[13., 23.]])
    # both rows of part1 land in pixel 1 / bin 2, in file order
    assert np.array_equal(dd.get(1, 2), [[14., 24.], [15., 25.]])
    assert dd.get(1, 2).dtype == np.float64
    # pixel 0 received nothing
    assert dd.get(0, 1) is None

    # coarser binning regroups: 100//5=20, and 15,16,17 all -> bin 3; the
    # merge order across glob-ed files is filesystem-defined, so compare sets
    dd5 = loc.generateDD(str(tmp_path / "part*.txt"), tofbinwidth=5)
    assert sorted(int(k) for k in dd5.dd[1].keys()) == [3, 20]
    rows = sorted(tuple(r) for r in dd5.get(1, 3))
    assert rows == sorted([(12., 22.), (14., 24.), (15., 25.)])


def test_idfloader_converts_metres_to_mm(tmp_path):
    # IDF text files store positions in metres; the loader scales by 1e3
    (tmp_path / "panelA.txt").write_text(
        "0 0.0 0.0 1.0\n"
        "3 0.0 0.05 1.0\n")
    loader = IDFLoader(str(tmp_path))
    pl = loader.query("panelA")              # key = file stem
    assert isinstance(pl, PixelLocator)
    assert np.array_equal(pl.pixelID, [0, 3])
    assert np.array_equal(pl.location, [[0., 0., 1000.], [0., 50., 1000.]])
    pid, dist = pl.locate(np.array([[0., 0., 1000.], [0., 50., 1000.]]))
    assert list(pid) == [0, 3]
    assert np.array_equal(dist, [0., 0.])
    with pytest.raises(KeyError):
        loader.query("nope")
    # a directory without IDF text files yields an empty registry
    empty = tmp_path / "nothing"
    empty.mkdir()
    assert IDFLoader(str(empty)).idf == {}


# ------------------------------------------------- MPI2022ExpInfo catalogues
def test_mpiruns_catalogue_is_consistent():
    # every entry carries a run id and a data path, both unique, and the run
    # number appears inside its data path (e.g. run17678 -> .../RUN0017678)
    assert len(MPIRuns) == 36
    runs = [v["run"] for v in MPIRuns.values()]
    paths = [v["data_path"] for v in MPIRuns.values()]
    assert all("run" in v and "data_path" in v for v in MPIRuns.values())
    assert len(set(runs)) == 36
    assert len(set(paths)) == 36
    assert all(v["run"][3:] in v["data_path"] for v in MPIRuns.values())
    # background runs follow the plain <runnumber> directory convention
    bg = MPIRuns["Background_NoAu"]
    assert bg["run"] == "run17261"
    assert bg["data_path"].endswith("/17261")


def test_mpiruns_exact_sample_entry():
    e = MPIRuns["D2O_Au"]
    assert e["run"] == "run17678"
    assert e["volume(ml)"] == 0.9
    assert e["height_sample(mm)"] == 14.3376
    assert e["dmin(mm)"] == 8.94
    assert e["dmax(mm)"] == 9.53
    assert e["data_path"].endswith("RUN0017678")
    rest = {k: v for k, v in e.items() if k != "data_path"}
    assert rest == {"run": "run17678", "volume(ml)": 0.9,
                    "height_sample(mm)": 14.3376,
                    "dmin(mm)": 8.94, "dmax(mm)": 9.53}


def test_modulecorner_catalogue_shape():
    # 31 modules, each with exactly the four named corners, each corner a
    # pixel id plus a 3-component position
    assert len(ModuleCorner_Exp) == 31
    corners = {"left_bottom", "right_bottom", "left_top", "right_top"}
    for name, mod in ModuleCorner_Exp.items():
        assert set(mod.keys()) == corners
        for c in mod.values():
            assert set(c.keys()) == {"pixelID", "pos"}
            assert isinstance(c["pixelID"], int)
            assert len(c["pos"]) == 3


def test_modulecorner_10701_exact_pins():
    m = ModuleCorner_Exp["module10701"]
    assert m["left_bottom"]["pixelID"] == 107010001
    assert m["right_bottom"]["pixelID"] == 107010060
    assert m["left_top"]["pixelID"] == 107010421
    assert m["right_top"]["pixelID"] == 107010480
    assert np.allclose(m["left_bottom"]["pos"],
                       [-513.9888, -413.4, -1226.2908], rtol=1e-13, atol=0.)
    assert np.allclose(m["left_top"]["pos"],
                       [-513.9888, -228.6, -1226.2908], rtol=1e-13, atol=0.)
    assert np.allclose(m["right_bottom"]["pos"],
                       [-213.9888, -413.4, -1226.2908], rtol=1e-13, atol=0.)
    assert np.allclose(m["right_top"]["pos"],
                       [-213.9888, -228.6, -1226.2908], rtol=1e-13, atol=0.)
    # closed-form module face dimensions: 300 mm wide, 184.8 mm high
    lb = m["left_bottom"]["pos"]
    rb = m["right_bottom"]["pos"]
    lt = m["left_top"]["pos"]
    assert rb[0] - lb[0] == pytest.approx(300.0, rel=1e-13)
    assert lt[1] - lb[1] == pytest.approx(184.8, rel=1e-13)
    # id layout: 60 columns (rb-lb = 59) x rows spaced 420 (lt-lb)
    assert m["right_bottom"]["pixelID"] - m["left_bottom"]["pixelID"] == 59
    assert m["left_top"]["pixelID"] - m["left_bottom"]["pixelID"] == 420


def test_modulecorner_parallelogram_and_naming_invariants():
    # every module face is a parallelogram: bottom edge vector equals top edge
    # vector, left edge equals right edge. The tolerance absorbs a genuine
    # ~1e-6 relative data discrepancy on the two tilted modules 10502/11002
    # (e.g. 117.6331 vs 117.633 mm in the shipped JSON). Also: every pixel id
    # is prefixed by the module number encoded in its key
    # ("module10701" -> "10701...")
    for name, mod in ModuleCorner_Exp.items():
        lb = mod["left_bottom"]["pos"]
        rb = mod["right_bottom"]["pos"]
        lt = mod["left_top"]["pos"]
        rt = mod["right_top"]["pos"]
        assert np.allclose(np.subtract(rb, lb), np.subtract(rt, lt),
                           rtol=1e-4, atol=0.)
        assert np.allclose(np.subtract(lt, lb), np.subtract(rt, rb),
                           rtol=1e-4, atol=0.)
        for c in mod.values():
            assert str(c["pixelID"]).startswith(name[len("module"):])
        # corners are ordered bottom -> top in y
        assert lt[1] > lb[1]


# ------------------------------------------- Prompt.component: make_plane
# FlatAnalyser.make_plane tilts each plate about the position stored in its
# anchor; the tilt is read back as extrinsic xyz Euler angles (the same
# convention applyRotxyz uses). The Cinema.Prompt imports pull in the C++
# geometry libraries, so they are done lazily to keep the pure analysis
# tests above importable without them.
def _plate_placements(cur_h, cur_v, num_h, num_v):
    from scipy.spatial.transform import Rotation
    from Cinema.Prompt.component import FlatAnalyser
    from Cinema.Prompt.geo import Volume
    from Cinema.Prompt.solid import Box

    plate = Volume("plate", Box(2.5, 1, 1), matCfg='vacuum.ncmat')
    ana = FlatAnalyser(plate, spacings=[10., 10.])
    ana.make_rect_plane(num_h, num_v, cur_h=cur_h, cur_v=cur_v)
    cells = []
    for _vol, anc in ana.eleAncs:
        euler = Rotation.from_matrix(anc.refFrame.getRotMatrix()).as_euler(
            'xyz', degrees=True)
        cells.append((tuple(anc.refFrame.getTranslation()),
                      euler[0], euler[1]))
    return cells


def test_make_rect_plane_single_curve_h_uses_centred_grid():
    # regression: the horizontal single-curve branch used (ix - length*0.5)
    # although ix is already centred on 0 by set_rect_position, giving every
    # plate a constant spurious tilt of -arcsin(row_half_width/cur_h). The
    # tilt must be arcsin(ix/cur_h): zero for the centre plate, antisymmetric
    # -2e-5/+2e-5 rad at the edges of the 5x1 grid.
    cells = _plate_placements(1e6, 0., 5, 1)
    assert [c[0][0] for c in cells] == [-20., -10., 0., 10., 20.]
    tilts = [c[2] for c in cells]            # extrinsic y Euler angle
    want = np.degrees(np.arcsin(np.array([-20., -10., 0., 10., 20.]) / 1e6))
    # rtol absorbs the ~1e-12 relative noise of scipy's matrix -> Euler
    # conversion, far below the pinned arcsin profile
    assert np.allclose(tilts, want, rtol=1e-9, atol=0.)
    assert tilts[2] == 0.
    # cur_v == 0 must not introduce any vertical tilt
    assert all(c[1] == 0. for c in cells)


def test_make_rect_plane_single_curve_matches_double_curve():
    # single-curve (cur_v=0) must reproduce the double-curve branch for the
    # same cur_h; with cur_v huge the vertical tilt vanishes on this flat row
    single = [c[2] for c in _plate_placements(1e6, 0., 5, 1)]
    double = [c[2] for c in _plate_placements(1e6, 1e9, 5, 1)]
    assert single == double
    # pre-fix the leftmost plate sat at -1.718873e-03 deg (constant offset of
    # -arcsin(10 mm/1e6 mm)); the centred value is exactly arcsin(-20/1e6)
    assert single[0] == pytest.approx(np.degrees(np.arcsin(-20. / 1e6)),
                                      rel=1e-13)


def test_make_rect_plane_single_curve_v_uses_centred_grid():
    # same regression for the vertical single curve: tilt_v = -arcsin(iy/cur_v)
    # (pre-fix it used the un-centred (iy - height*0.5), so even the centre
    # plate was tilted)
    cells = _plate_placements(0., 1e6, 1, 3)
    assert [c[0][1] for c in cells] == [-10., 0., 10.]
    tilts = [c[1] for c in cells]            # extrinsic x Euler angle
    want = -np.degrees(np.arcsin(np.array([-10., 0., 10.]) / 1e6))
    # rtol absorbs the ~1e-12 relative noise of scipy's matrix -> Euler
    # conversion, far below the pinned arcsin profile
    assert np.allclose(tilts, want, rtol=1e-9, atol=0.)
    assert tilts[1] == 0.
    # and it matches the double-curve branch for the same cur_v
    double = [c[1] for c in _plate_placements(1e9, 1e6, 1, 3)]
    assert tilts == double


# ------------------------------------------------ Prompt.scorer: DirectSqw sign
def test_directsqw_doc_pins_ei_minus_ef_convention():
    # the C++ scorer fills omega = m_mean_ekin - ekin (PTScorerDirectSqw.cc):
    # POSITIVE omega = neutron energy loss (downscatter). The __init__
    # docstring used to promise the opposite sign; pin the corrected wording
    # here (the simulation-level sign pin lives in
    # test_cov_scorer_families.py).
    from Cinema.Prompt.scorer import DirectSqwHelper
    doc = DirectSqwHelper.__init__.__doc__ or ''
    assert 'E_initial - E_final' in doc
    assert 'E_final - E_initial' not in doc
    assert 'downscatter' in doc
