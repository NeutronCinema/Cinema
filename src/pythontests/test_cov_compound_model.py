# Regression tests for ModelCollection.generate (compoundModel.py).
#
# The C bridge pt_ModelCollection_generate used to hand a default-constructed
# (null) incident direction to the samplers and never warmed the cross-section
# cache, which produced two misbehaviours on any isotropic NCrystal material:
#   - generate() after xs(same ekin) (the documented smoke-test order) armed
#     the cache, so the hot path reached NCrystal with dir=(0,0,0); NCrystal
#     normalises the direction, 1/sqrt(0) = inf produced NaN, and its
#     rejection test NaN < 0.99 never passed: an infinite hot loop (gdb
#     confirmed: randIsotropicDirection <- sampleScatter <- sampleReaction
#     <- pickAndSample <- pt_ModelCollection_generate).
#   - a cold generate() hit the cache-mismatch early return in
#     ModelCollection::pickAndSample and silently returned a dummy result
#     ("WARNING, sampling event with different incident energy and/or
#     direction") without sampling anything.
#
# The fixed bridge takes the direction as three doubles (python default
# (0, 0, 1)), rejects the null vector, evaluates the total cross section for
# (ekin, dir) before pickAndSample, and returns the sampled final energy.
#
# The generate() calls run in a subprocess guarded by a hard timeout: a
# reintroduced hang must fail the test, not wedge the suite (measured on the
# unfixed tree: xs then generate never returned; killed by timeout).
#
# The bridge pins at the bottom are EXPECTED-FAIL against the stale cinemabin
# .so and green after the round-2 gate rebuild (see the ledger block there).
#
# Everything here is NCrystal-backed (fast, but loads Al_sg225.ncmat and
# spawns python workers), so per the conftest tier table the tests are
# marked medium (skipped by the pre-push hook, run by cimbuild -tt/-ttt).

import ast
import subprocess
import sys

import pytest

from Cinema.Prompt.compoundModel import ModelCollection
from Cinema.Prompt.histogram import Hist1D, Hist2D

AL_CFG = "physics=ncrystal;nccfg='Al_sg225.ncmat'"
EKIN = 0.0253  # eV (25.3 meV thermal neutron)

# Thermal inelastic scattering can UP-scatter: the neutron may leave with the
# phonon energy it gained from the crystal (observed on Al at 25.3 meV:
# final_ekin = 0.043756 eV > ekin). So no upper bound at ekin; only
# non-negativity plus a far-above-any-phonon sanity ceiling (NaN fails both,
# and fails the comparison chain like any NaN bound would).
def _sane_ekin(v):
    return 0.0 <= v <= 10.0 * EKIN

# Runs in a fresh interpreter so a hang/abort inside the C++ call cannot
# wedge the pytest worker; the timeout turns both into a test failure.
WORKER = """
import sys
from Cinema.Prompt.compoundModel import ModelCollection

mode = sys.argv[1]
mc = ModelCollection({cfg!r})
if mode == 'xs_then_generate':
    print('xs', mc.xs({ekin!r}), flush=True)
    out = mc.generate({ekin!r})
elif mode == 'bare_generate':
    out = mc.generate({ekin!r})
elif mode == 'sample_spread':
    out = [mc.generate({ekin!r}) for _ in range(50)]
print('result', out, flush=True)
""".format(cfg=AL_CFG, ekin=EKIN)


def _run_worker(mode, timeout=60):
    return subprocess.run([sys.executable, "-c", WORKER, mode],
                          capture_output=True, text=True, timeout=timeout)


@pytest.mark.medium
def test_generate_after_xs_returns_within_energy_budget():
    """xs(ekin) then generate(ekin) - the documented smoke-test order - must
    return: it used to hang forever in NCrystal direction sampling."""
    res = _run_worker('xs_then_generate')
    assert res.returncode == 0, res.stderr
    assert 'WARNING, sampling event' not in res.stdout
    lines = [l for l in res.stdout.splitlines() if l.startswith('result')]
    final_ekin = float(lines[0].split()[1])
    assert _sane_ekin(final_ekin)


@pytest.mark.medium
def test_bare_generate_actually_samples():
    """A bare generate() (no preceding xs) must perform a real sampling: it
    used to hit the cold-cache early return in pickAndSample and print the
    'sampling event with different incident energy' warning instead."""
    res = _run_worker('bare_generate')
    assert res.returncode == 0, res.stderr
    assert 'WARNING, sampling event' not in res.stdout
    lines = [l for l in res.stdout.splitlines() if l.startswith('result')]
    final_ekin = float(lines[0].split()[1])
    assert _sane_ekin(final_ekin)


@pytest.mark.medium
def test_generate_samples_a_real_distribution():
    """Repeated generate() calls must reach the physics: 50 draws on Al at
    25.3 meV mix elastic events (final_ekin == ekin), absorption (0.0) and
    inelastic lines, so a constant or dummy return value cannot appear."""
    res = _run_worker('sample_spread')
    assert res.returncode == 0, res.stderr
    lines = [l for l in res.stdout.splitlines() if l.startswith('result')]
    values = ast.literal_eval(lines[0].split('result', 1)[1])
    assert len(values) == 50
    assert all(_sane_ekin(v) for v in values)
    assert len(set(values)) >= 2


def test_generate_rejects_null_direction():
    """dir=(0,0,0) must raise before entering C++: the direction samplers
    divide by zero on it, and a C++ exception crossing the raw ctypes
    boundary would abort the whole process instead of raising."""
    mc = ModelCollection("physics=idealElaScat;xs_barn=5;density_per_aa3=0.05")
    with pytest.raises(ValueError, match='null incident direction'):
        mc.generate(EKIN, dir=(0., 0., 0.))


# ---------------------------------------------------------------- bridge pins
#
# EXPECTED-FAIL LEDGER (wave 2b, cluster b2): red against the stale cinemabin
# .so. The two CREATION pins turn green after the round-2 gate rebuild alone;
# the two MERGE pins additionally need the int-status conversion of the hist
# merge entry points (pt_HistBase_merge/pt_Hist2D_merge in PTPythonHist.cc and
# the restype/raiseOnBridgeError wiring in histogram/Hist.py - files outside
# b2's exclusive list, reported to the lead; reference bridge:
# pt_HistBase_merge_checked in PTPythonResource.cc) - until that lands they
# stay red (SIGABRT) even after the gate rebuild.
#
# On the stale library the creation and merge bridges let the C++ exception
# escape the extern "C" boundary, so std::terminate aborts the forked worker
# at the call itself and pytest.raises never gets to evaluate anything. Every
# test below fails there with (recorded 2026-10-11 against the stale .so,
# pytest --forked; the child's stderr additionally shows the terminate text,
# e.g. "terminate called after throwing an instance of
# 'Prompt::Error::BadInput'"):
#   running the test CRASHED with signal 6 (SIGABRT)
#
# After the gate rebuild (plus the merge conversion above) the checked bridges
# return a nonzero status with the message in pt_last_error() and
# raiseOnBridgeError turns it into the RuntimeError matched below (creation:
# pt_makeModelCollection_checked; merge: the converted hist entry points).
# The match alternatives accept the C++ message either bare or with its
# exception type name prefixed.

def test_model_collection_bad_physics_name_raises_instead_of_abort():
    """physics=nosuchphysics used to abort: Prompt::Error::BadInput ('unknown
    physics nosuchphysics') escaped pt_makeModelCollection."""
    with pytest.raises(RuntimeError, match=r'unknown physics|BadInput'):
        ModelCollection('physics=nosuchphysics;xs_barn=5;density_per_aa3=0.05')


def test_model_collection_bad_nccfg_raises_instead_of_abort():
    """An nccfg naming a data file NCrystal cannot find used to abort: the
    NCrystal::Error (not a Prompt::Error) escaped the raw bridge."""
    with pytest.raises(RuntimeError, match=r'NoSuchMat_xyz\.ncmat'):
        ModelCollection("physics=ncrystal;nccfg='NoSuchMat_xyz.ncmat'")


def test_histbase_merge_mismatched_bins_raises_instead_of_abort():
    """HistBase.merge with different nbins used to abort: the CalcError
    ('m_nbins 4 is different with the m_nbins of another histogram 8')
    escaped pt_HistBase_merge. No notes are set, so the python-side note
    guard in HistBase.merge passes and the call really reaches C++."""
    a = Hist1D(0., 1., 4)
    b = Hist1D(0., 1., 8)
    with pytest.raises(RuntimeError, match=r'different with the m_nbins'):
        a.merge(b)


def test_hist2d_merge_cross_type_raises_instead_of_abort():
    """Hist2D.merge with a Hist1D used to abort: the reference dynamic_cast
    in Hist2D::merge throws std::bad_cast ('std::bad_cast') which escaped
    pt_Hist2D_merge. Same note (none) on both sides keeps the python-side
    guard silent."""
    a = Hist2D(0., 1., 4, 0., 1., 4)
    b = Hist1D(0., 1., 4)
    with pytest.raises(RuntimeError, match=r'bad_cast'):
        a.merge(b)
