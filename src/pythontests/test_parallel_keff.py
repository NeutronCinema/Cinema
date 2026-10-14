#!/usr/bin/env python3
# Parallel power iteration (PromptMPI.simulateSecondStack).
#
# The identity anchor of this feature is the regression test: a size-1 MPI
# run must reproduce the serial births sequence bit-for-bit, because the
# override takes the plain serial path when size == 1 (no collectives, no
# extra RNG draws). The multi-rank case is covered as smoke runs per bank
# exchange mode ('nearest', the default, and 'pooled'): any breakdown of
# the exchange (blob format, uneven split, collective mismatch) crashes the
# ranks loudly, and the keff band check catches gross physics breakage
# without flaking on 3-cycle noise.
#
# Both kinds of cases launch a fresh mpirun subprocess instead of running
# in-process: mpi4py requires MPI_Init before any communicator use, which
# pytest's forked workers can not provide. The toy model is the U7H993 keff
# sphere with a reduced cycle count; the gidi build costs ~5 s per rank, so
# each subprocess stays in the ~10-20 s range.

import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import pytest

try:
    import mpi4py  # noqa: F401 — the mpirun tests need it inside the subprocess
    _HAVE_MPI4PY = True
except ImportError:
    _HAVE_MPI4PY = False

# deliberately NOT pytest.importorskip at module level: the two pure-python
# exchange tests below run without mpi4py, and a module-level gate would
# silently skip them exactly where the MPI smoke tests are unavailable too
MPIRUN = shutil.which('mpirun') if _HAVE_MPI4PY else None
_MPIRUN_FLAGS = []
if MPIRUN:
    # probe the launcher before using it: '--oversubscribe' is Open MPI
    # specific (MPICH rejects the flag but oversubscribes by default), and
    # Open MPI refuses to run as root without --allow-run-as-root — in
    # both cases the tests must skip, not fail
    try:
        probe = subprocess.run([MPIRUN, '--oversubscribe', 'true'],
                               capture_output=True, timeout=120)
        if probe.returncode == 0:
            _MPIRUN_FLAGS = ['--oversubscribe']
        elif subprocess.run([MPIRUN, '-np', '1', 'true'],
                            capture_output=True, timeout=120).returncode != 0:
            MPIRUN = None # launcher unusable here (e.g. root container)
    except (subprocess.TimeoutExpired, OSError):
        MPIRUN = None

_TOY_TEMPLATE = r'''
import numpy as np
from Cinema.Prompt import {sim_class}
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Sphere
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting

cdata = GidiSetting()
cdata.setEnableGidi(True)
cdata.setEnableGidiPowerIteration(True)
cdata.setGidiThreshold(5)


class MySim({sim_class}):
    def makeWorld(self):
        radius = 87.407
        fuel = Material('freegas::U7H993/1.1gcm3/'
                        'U_is_0.8571428571428572_U238_0.14285714285714285_U235/H_is_H1;temp=293.6')
        world = Volume("world", Sphere(0, radius + 2))
        godiva = Volume('Godiva', Sphere(0, radius), matCfg=fuel)
        world.placeChild('frod', godiva)
        self.setWorld(world)


sim = MySim(seed=1010{exchange_arg})
sim.makeWorld()
gun = IsotropicGun()
gun.setEnergy(3e6)
gun.setPosition([0, 0, 0])
batchsize = 2000
sim.simulate(gun, batchsize)
births = []
for i in range(3):
    births.append(sim.simulateSecondStack(batchsize))
{rank_guard}
    print('BIRTHS ' + ' '.join(str(b) for b in births), flush=True)
'''


def _toy_script(sim_class='PromptMPI', exchange=None, cycles=3):
    """The toy keff script for a given Prompt class and bank exchange."""
    exchange_arg = f", bank_exchange='{exchange}'" if exchange else ''
    rank_guard = 'if sim.rank == 0:' if sim_class == 'PromptMPI' else 'if True:'
    script = _TOY_TEMPLATE.replace('{sim_class}', sim_class)
    script = script.replace('{exchange_arg}', exchange_arg)
    script = script.replace('{rank_guard}', rank_guard)
    script = script.replace('for i in range(3):', f'for i in range({cycles}):')
    return script


def _keff_estimate(births, skip=3, batchsize=2000):
    """keff and its cycle-to-cycle standard error over the active cycles.

    The first cycles of a power iteration are a transient: the source-cycle
    fission bank still carries the fixed-source spectrum, and successive
    cycles only relax toward k with ratio ~k. Early cycles must be skipped,
    and a short estimate is dominated by the realization of that transient —
    two runs of the SAME chain differ by far more than the naive
    sigma/sqrt(n) of three cycles (observed: 0.96 vs 1.05 at 3 cycles,
    both correct)."""
    active = np.asarray(births[skip:], dtype=float) / batchsize
    keff = float(active.mean())
    se = float(active.std(ddof=1) / math.sqrt(active.size)) if active.size > 1 else 0.0
    return keff, se


def _run_toy(script, np_value):
    env = dict(os.environ)
    # unpinned OpenBLAS worker threads spin on the core mpirun bound the
    # rank to, roughly doubling the cycle time; the numbers are identical
    env.setdefault('OPENBLAS_NUM_THREADS', '1')
    proc = subprocess.run(
        [MPIRUN] + _MPIRUN_FLAGS + ['-np', str(np_value),
         sys.executable, '-c', script],
        capture_output=True, text=True, timeout=600, env=env)
    assert proc.returncode == 0, f'mpirun -np {np_value} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}'
    m = re.findall(r'^BIRTHS (.+)$', proc.stdout, re.M)
    assert m, f'no BIRTHS line in output:\n{proc.stdout[-2000:]}'
    return [int(x) for x in m[-1].split()]


def test_nn_windows_partition_the_shared_sample():
    # pure-python part of the nearest-neighbour exchange, no MPI needed:
    # the per-rank windows must tile [0, num) exactly, first-ranks-first
    # on the remainder
    from Cinema.Prompt.promptCore import _nn_windows
    assert [hi - lo for lo, hi in _nn_windows(7, 3)] == [3, 2, 2]
    assert [hi - lo for lo, hi in _nn_windows(2000, 4)] == [500] * 4
    # num < size: the trailing ranks sit out with empty windows
    assert [hi - lo for lo, hi in _nn_windows(5, 8)] == [1] * 5 + [0] * 3
    for num, size in [(7, 3), (2000, 4), (5, 8), (1, 1), (0, 4)]:
        windows = _nn_windows(num, size)
        assert len(windows) == size
        assert windows[0][0] == 0
        assert windows[-1][1] == num
        for (_, b), (c, _) in zip(windows, windows[1:]):
            assert b == c


def test_nn_send_indices_exchange_is_exact():
    # the invariant that makes the request-less exchange correct: if every
    # rank derives its send lists from the shared sample and the lists are
    # alltoall'ed, rank j receives EXACTLY its own window of the sample —
    # no site lost, none duplicated, none misplaced, for any bank skew.
    # Emulates the C++ extract by offsetting local indices back to global.
    import numpy as np
    from Cinema.Prompt.promptCore import _nn_send_indices, _nn_windows
    rng = np.random.default_rng(7)
    checked = 0
    for _ in range(60):
        size = int(rng.integers(2, 9))
        num = int(rng.integers(0, 300))
        counts = [int(c) for c in rng.integers(0, 40, size=size)]
        total_bank = sum(counts)
        if total_bank == 0:
            continue
        sample = np.sort(rng.integers(0, total_bank, size=num, dtype=np.int64))
        received = [[] for _ in range(size)]
        for rank in range(size):
            cum, sends = _nn_send_indices(sample, counts, num, size, rank)
            # local indices must be inside the sender's own range
            assert all((idx < counts[rank]).all() for idx in sends)
            for j, idx in enumerate(sends):
                received[j].extend((idx + int(cum[rank])).tolist())
        for rank in range(size):
            lo, hi = _nn_windows(num, size)[rank]
            assert received[rank] == sample[lo:hi].tolist()
        checked += 1
    assert checked > 50


_CYCLES = 12   # 3-cycle keff estimates sit on the source transient; 12 with
_SKIP = 3      # a skip of 3 gives an active-cycle estimate worth banding


@pytest.mark.skipif(MPIRUN is None, reason="mpi4py or mpirun unavailable")
def test_parallel_keff_size1_is_bit_identical_to_serial():
    # the anchor: PromptMPI at size 1 must be the serial simulation
    # (the bank exchange never engages: the override bypasses at size 1)
    serial = _run_toy(_toy_script('Prompt'), 1)
    mpi1 = _run_toy(_toy_script('PromptMPI', exchange='nearest'), 1)
    assert len(serial) == len(mpi1) == 3
    assert serial == mpi1


@pytest.mark.skipif(MPIRUN is None, reason="mpi4py or mpirun unavailable")
def test_parallel_keff_nearest_neighbour_matches_serial():
    # 3 ranks over a batch size that leaves a remainder: exercises the
    # shared-sample exchange (allgather of counts + alltoall of site
    # blobs) with windows that are not equal, and checks the keff of the
    # parallel chain against a serial reference run at the same length
    serial = _run_toy(_toy_script('Prompt', cycles=_CYCLES), 1)
    births = _run_toy(_toy_script('PromptMPI', exchange='nearest', cycles=_CYCLES), 3)
    assert all(b > 0 for b in births)
    keff_s, se_s = _keff_estimate(serial, skip=_SKIP)
    keff_n, _ = _keff_estimate(births, skip=_SKIP)
    # the parallel chain is a different realization of the same stochastic
    # process, so the band is several serial standard errors wide; it still
    # catches gross breakage (a broken exchange shows up as births of the
    # wrong order of magnitude or a dead chain)
    assert abs(keff_n - keff_s) < max(0.02, 6 * se_s), \
        f'keff nearest={keff_n:.4f} vs serial={keff_s:.4f}+-{se_s:.4f}, births {births}'


@pytest.mark.skipif(MPIRUN is None, reason="mpi4py or mpirun unavailable")
def test_parallel_keff_pooled_matches_serial():
    # the allgather variant: every rank resamples its share from the pooled
    # bank with the exact serial sampling
    serial = _run_toy(_toy_script('Prompt', cycles=_CYCLES), 1)
    births = _run_toy(_toy_script('PromptMPI', exchange='pooled', cycles=_CYCLES), 3)
    assert all(b > 0 for b in births)
    keff_s, se_s = _keff_estimate(serial, skip=_SKIP)
    keff_p, _ = _keff_estimate(births, skip=_SKIP)
    assert abs(keff_p - keff_s) < max(0.02, 6 * se_s), \
        f'keff pooled={keff_p:.4f} vs serial={keff_s:.4f}+-{se_s:.4f}, births {births}'
