#!/usr/bin/env python3
# Regression tests for the MPI gather idempotency fix:
#  - PromptMPI.gatherHistData must write the reduced content into an
#    independent clone of the scorer histogram (new pt_HistBase_clone C++
#    bridge), never into the live scorer histogram. Pre-fix code wrote into
#    the live histogram, so every later gather and the re-gather inside
#    save_all_scorers cumulatively inflated the data; the round-2 adversarial
#    audit reproduced mpirun -n 2 -> g1=20000, g2=30000, g3=40000 and a
#    TOF.h5 weight.sum of 30000 instead of 20000.
#
# green after round-2 gate rebuild: the tests need pt_HistBase_clone in
# libprompt_core.so (HistBase::copyTrivialFrom + Hist1D/Hist2D copy ctors +
# clone dispatch), which the checked-in build lacks until the round-2 gate
# rebuild; until then they fail with the clear "lacks pt_HistBase_clone"
# RuntimeError from HistBase.clone().
#
# The repo has no mpirun-pytest harness, so every test subprocess-wraps one
# "mpirun --allow-run-as-root -n 2 <python> helper.py <mode>" run in a tmp
# cwd (one Launcher/world per process, per rank). Modules without mpirun on
# PATH (dev machines without MPI) are skipped cleanly at collection.

import os
import shutil
import subprocess
import sys
import textwrap

import pytest

if shutil.which('mpirun') is None:
    pytest.skip('mpirun not found on PATH; MPI gather tests need an MPI runtime',
                allow_module_level=True)

pytestmark = pytest.mark.slow  # three real 2-rank MPI simulations, seconds each

_N_EVENTS = 20000  # weight-1 MaxwellianGun events, 10000 per rank at -n 2

_HELPER = textwrap.dedent('''
    import sys

    from Cinema.Prompt.geo import Volume, Transformation3D
    from Cinema.Prompt.promptCore import PromptMPI
    from Cinema.Prompt.scorer import TOFHelper
    from Cinema.Prompt.solid import Box

    N_EVENTS = 20000
    GUN_CFG = ("gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;"
               "slit_w=2;slit_h=2;slit_z=1e99;temperature=293;")

    class SimMPI(PromptMPI):
        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200), 'void.ncmat')
            # void detector too: no absorption, so every generated neutron is
            # scored, and the TOF default range 0..40 ms covers every 293K
            # Maxwellian neutron -> gathered weight sum is exactly 20000
            det = Volume('detector', Box(10, 10, 1), 'void.ncmat')
            TOFHelper('TOF').make(det)
            world.placeChild('detectorPhy', det, Transformation3D(0, 0, 90))
            self.setWorld(world)

    mode = sys.argv[1]
    sim = SimMPI(seed=4096)
    sim.makeWorld()
    sim.simulate(GUN_CFG, N_EVENTS)

    if mode == 'gather3':
        g = [float(sim.gatherHistData('TOF').getWeight().sum()) for _ in range(3)]
        if sim.rank == 0:
            with open('sums_gather3.txt', 'w') as fh:
                fh.write(repr(g))
    elif mode == 'gather_then_save':
        g = float(sim.gatherHistData('TOF').getWeight().sum())
        sim.save_all_scorers()  # collective; every rank, h5 written on rank 0
        if sim.rank == 0:
            with open('sums_gather_then_save.txt', 'w') as fh:
                fh.write(repr(g))
    elif mode == 'save_then_gather':
        sim.save_all_scorers()  # collective; every rank, h5 written on rank 0
        g = float(sim.gatherHistData('TOF').getWeight().sum())
        if sim.rank == 0:
            with open('sums_save_then_gather.txt', 'w') as fh:
                fh.write(repr(g))
    else:
        sys.exit('unknown mode ' + mode)
''')


def _run_mpi(mode, tmp_path):
    helper = tmp_path / 'helper.py'
    helper.write_text(_HELPER)
    return subprocess.run(
        ['mpirun', '--allow-run-as-root', '-n', '2', sys.executable,
         str(helper), mode],
        cwd=tmp_path, env=dict(os.environ), capture_output=True, text=True,
        timeout=300)


def _assert_ran_clean(proc):
    assert proc.returncode == 0, f'stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}'


def test_repeated_gathers_are_idempotent(tmp_path):
    # pre-fix identity: g2 == 2*g1 - local0 (30000 at -n 2), because the first
    # gather doubled the scorer content before the second reduce saw it
    proc = _run_mpi('gather3', tmp_path)
    _assert_ran_clean(proc)
    g1, g2, g3 = eval((tmp_path / 'sums_gather3.txt').read_text())
    assert g1 == _N_EVENTS
    assert g2 == g1
    assert g3 == g1


def test_gather_then_save_writes_uncorrupted_h5(tmp_path):
    # the documented gather-then-save flow: the h5 written by the internal
    # re-gather of save_all_scorers must still hold the single-gather total
    proc = _run_mpi('gather_then_save', tmp_path)
    _assert_ran_clean(proc)
    assert float((tmp_path / 'sums_gather_then_save.txt').read_text()) == _N_EVENTS
    h5py = pytest.importorskip('h5py')
    with h5py.File(tmp_path / 'TOF.h5', 'r') as f:
        assert f['weight'][()].sum() == _N_EVENTS


def test_save_then_gather_writes_uncorrupted_h5(tmp_path):
    # reverse order: the h5 from save_all_scorers must be correct on its own,
    # and a standalone gather after it must return the same total again
    proc = _run_mpi('save_then_gather', tmp_path)
    _assert_ran_clean(proc)
    assert float((tmp_path / 'sums_save_then_gather.txt').read_text()) == _N_EVENTS
    h5py = pytest.importorskip('h5py')
    with h5py.File(tmp_path / 'TOF.h5', 'r') as f:
        assert f['weight'][()].sum() == _N_EVENTS
