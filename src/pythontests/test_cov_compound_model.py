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
# Everything here is NCrystal-backed (fast, but loads Al_sg225.ncmat and
# spawns python workers), so per the conftest tier table the tests are
# marked medium (skipped by the pre-push hook, run by cimbuild -tt/-ttt).

import ast
import subprocess
import sys

import pytest

from Cinema.Prompt.compoundModel import ModelCollection

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
