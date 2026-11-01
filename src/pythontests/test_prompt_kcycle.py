# K-cycle batched power iteration (plan appendix 13) unit tests.
#
# Covers the API contract (bridge arg conversion, estimator, skew
# instrument) without transport, plus one real-transport gate: K=1 must be
# bit-identical to the per-cycle goWithSecondStack path (same RNG stream —
# the generation-range scan reads but never draws). The bit-identity arms
# run in fresh subprocesses because the Launcher is a process-wide
# singleton whose world/bank state cannot be reset.
import os
import subprocess
import sys

import pytest

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt import launcher as launcher_mod
from Cinema.Prompt.promptCore import keff_from_block

_DRIVER = r'''
import sys
sys.path.insert(0, "/data/caixx/cinema/src/python")
from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Tube
from Cinema.Prompt.physics import Material
from Cinema.Prompt.GidiSetting import GidiSetting


class P(Prompt):
    def __init__(self):
        super().__init__(1010)

    def makeWorld(self):
        c = GidiSetting()
        c.setEnableGidi(True)
        c.setEnableGidiPowerIteration(True)
        c.setGidiThreshold(5)
        fuel = Material("freegas::U/18.8gcm3/U_is_0.965000_U238_0.035000_U235;temp=293.6K")
        water = Material("freegas::H2O/1gcm3/H_is_H1/O_is_O16;temp=293.6K")
        world = Volume("world", Box(25.4, 25.4, 1e6), matCfg=water,
                       surfaceCfg="physics=Mirror;m=-1")
        world.placeChild("frod", Volume("fuel", Tube(0, 6.350, 1e6), matCfg=fuel))
        self.setWorld(world)


sim = P()
sim.makeWorld()
sim.simulate("gun=SimpleThermalGun;position=0,0,-100;direction=0,0,1;energy=0.0253",
             20000)
mode, k, cycles = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
births = []
for _ in range(cycles):
    if mode == 'plain':
        births.append(sim.simulateSecondStack(2000))
    else:
        b, c = sim.l.goKWithSecondStacks(k, 2000, 0)
        assert c == k
        births.append(b)
print("BIRTHS " + " ".join(str(b) for b in births))
'''


@pytest.fixture(scope='module')
def _gidi_ready():
    from Cinema.Prompt.GidiSetting import GidiSetting
    if not getattr(GidiSetting, 'isCompiled', True):
        pytest.skip('gidi not compiled into this build')
    if not GidiSetting().available():
        pytest.skip('gidi data (pops/map) not available')


def test_keff_from_block_plain_ratio():
    # births do not compound across a block: every cycle renormalises its
    # source back to num, so the estimate is the plain ratio
    assert keff_from_block(18700, 5, 20000) == pytest.approx(0.187)
    assert keff_from_block(20000, 1, 20000) == pytest.approx(1.0)
    # K=1 degenerates to the per-cycle births/num of simulateSecondStack
    assert keff_from_block(1234, 1, 2000) == pytest.approx(1234 / 2000)


def test_keff_from_block_rejects_zero_cycles():
    with pytest.raises(ValueError):
        keff_from_block(100, 0, 2000)


def test_gok_bridge_arg_conversion(monkeypatch):
    # int() coercion of k/num/genMax and the (births, cycles) tuple return,
    # mirroring the goWithSecondStack bridge contract
    seen = {}

    def fake_gok(cobj, k, num, genmax, births_out, cycles_out):
        seen.update(k=k, num=num, genmax=genmax)
        births_out.value = 4321
        cycles_out.value = 3
        return 0

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_goKWithSecondStacks', fake_gok)
    b, c = Prompt(seed=1).l.goKWithSecondStacks(3.0, 2000.7, 40)
    assert (b, c) == (4321, 3)
    assert seen == {'k': 3, 'num': 2000, 'genmax': 40}


def test_gok_bridge_error_surfaces(monkeypatch):
    def failing_gok(cobj, k, num, genmax, births_out, cycles_out):
        return 1

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_goKWithSecondStacks', failing_gok)
    with pytest.raises(RuntimeError):
        Prompt(seed=1).l.goKWithSecondStacks(1, 100, 0)


def test_gok_rejects_zero_k():
    with pytest.raises(ValueError):
        Prompt(seed=1).l.goKWithSecondStacks(0, 100, 0)


def test_simulateKStacks_serial_returns_launcher_tuple(monkeypatch):
    # size-1 PromptMPI forwards the block to the launcher entry verbatim
    def fake_gok(cobj, k, num, genmax, births_out, cycles_out):
        births_out.value = 99
        cycles_out.value = 2
        return 0

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_goKWithSecondStacks', fake_gok)
    sim = PromptMPI(seed=5)
    assert sim.size == 1  # outside mpirun this is the identity path
    assert sim.simulateKStacks(100, 2) == (99, 2)


def test_simulateKStacks_rejects_zero_k():
    sim = PromptMPI(seed=5)
    with pytest.raises(ValueError):
        sim.simulateKStacks(100, 0)


def test_k1_bit_identity_serial(_gidi_ready):
    """K=1 births match goWithSecondStack exactly, cycle for cycle."""
    py = sys.executable
    env = dict(os.environ, CINEMAPATH=os.environ.get('CINEMAPATH', '/data/caixx/cinema'))
    outs = {}
    for mode, k in (('plain', 1), ('k1', 1)):
        r = subprocess.run([py, '-c', _DRIVER, mode, str(k), '12'],
                           capture_output=True, text=True, env=env, timeout=600)
        assert r.returncode == 0, r.stderr[-2000:]
        outs[mode] = [line for line in r.stdout.splitlines()
                      if line.startswith('BIRTHS ')][-1]
    assert outs['plain'] == outs['k1']


def test_k5_births_match_plain_stream(_gidi_ready):
    """The serial K=5 block must reproduce the same chain as plain: the
    per-cycle renormalise/swap sequence is unchanged, so the summed births
    per 5-cycle group must equal the plain path's group sums exactly."""
    py = sys.executable
    env = dict(os.environ, CINEMAPATH=os.environ.get('CINEMAPATH', '/data/caixx/cinema'))

    def run(mode, k):
        r = subprocess.run([py, '-c', _DRIVER, mode, str(k), '10'],
                           capture_output=True, text=True, env=env, timeout=600)
        assert r.returncode == 0, r.stderr[-2000:]
        line = [line for line in r.stdout.splitlines() if line.startswith('BIRTHS ')][-1]
        return [int(x) for x in line.split()[1:]]

    plain = run('plain', 1)
    k5 = run('k5', 5)
    assert len(plain) == 10 and len(k5) == 2
    for block in range(2):
        assert sum(plain[5 * block:5 * block + 5]) == k5[block]
