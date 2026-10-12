# Unit tests for launcher.py and promptCore.py paths not covered by
# test_fix_core.py: ensureDisplayUsable branches, the Launcher.setWorld
# guard, getHist dimension dispatch, Prompt basics, the python-gun
# simulate loop batch/remainder math, simulateSecondStack forwarding and
# the PromptMPI rank split.
#
# Everything is pure Python: ctypes entry points are monkeypatched, MPI is
# only exercised through the singleton COMM_WORLD (rank 0 / size 1 outside
# mpirun) or faked via the _rank/_size attributes. No geometry is built and
# no particle is transported.

import os

import pytest

from Cinema.Prompt import launcher as launcher_mod
from Cinema.Prompt import promptCore as prompt_core_mod
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.promptCore import Prompt, PromptMPI


def launcher_cls():
    # 'Launcher' in the module namespace is the @singleton factory; recover
    # the real class from an instance
    return type(Prompt(seed=1).l)


def fresh_display_state(monkeypatch):
    state = {'checked': False, 'forced_headless': False}
    monkeypatch.setattr(launcher_mod, '_display_state', state)
    return state


# ---------------------------------------------------------------------------
# ensureDisplayUsable
# ---------------------------------------------------------------------------

def test_ensure_display_unset_display_is_a_noop_true(monkeypatch):
    state = fresh_display_state(monkeypatch)
    monkeypatch.delenv('DISPLAY', raising=False)
    assert launcher_mod.ensureDisplayUsable() is True
    assert state == {'checked': True, 'forced_headless': False}
    assert 'DISPLAY' not in os.environ


def test_ensure_display_local_unix_socket_ok(monkeypatch):
    fresh_display_state(monkeypatch)
    monkeypatch.setenv('DISPLAY', ':0')
    real_exists = os.path.exists

    def fake_exists(path):
        if isinstance(path, str) and path.startswith('/tmp/.X11-unix/X'):
            return True
        return real_exists(path)

    monkeypatch.setattr(launcher_mod.os.path, 'exists', fake_exists)
    assert launcher_mod.ensureDisplayUsable() is True
    # reachable local display: nothing is forced or unset
    assert os.environ.get('DISPLAY') == ':0'
    assert launcher_mod._display_state['forced_headless'] is False


def test_ensure_display_unreachable_remote_forces_headless(monkeypatch, capsys):
    fresh_display_state(monkeypatch)
    monkeypatch.setenv('DISPLAY', 'far.host:12.0')

    def refusing(*args, **kwargs):
        raise OSError('connection refused (test stub)')

    monkeypatch.setattr(launcher_mod.socket, 'create_connection', refusing)
    assert launcher_mod.ensureDisplayUsable(timeout=0.05) is False
    # headless degradation: DISPLAY popped, matplotlib forced to Agg
    assert 'DISPLAY' not in os.environ
    import matplotlib
    assert 'agg' in matplotlib.get_backend().lower()
    err = capsys.readouterr().err
    assert 'WARNING' in err and 'far.host:12.0' in err


def test_ensure_display_malformed_display_fails_fast(monkeypatch):
    fresh_display_state(monkeypatch)

    def must_not_be_called(*args, **kwargs):
        raise AssertionError('socket probe reached for a malformed DISPLAY')

    monkeypatch.setattr(launcher_mod.socket, 'create_connection', must_not_be_called)
    for bogus in ('nonsense', ':no.digits'):
        monkeypatch.setenv('DISPLAY', bogus)
        assert launcher_mod.ensureDisplayUsable() is True
        # left alone, whatever set it may clean it up
        assert os.environ.get('DISPLAY') == bogus
    assert launcher_mod._display_state['forced_headless'] is False


def test_ensure_display_second_call_short_circuits(monkeypatch):
    state = fresh_display_state(monkeypatch)
    monkeypatch.delenv('DISPLAY', raising=False)
    assert launcher_mod.ensureDisplayUsable() is True

    # any DISPLAY would now trigger a probe if the cache were not honoured;
    # make the probe loudly fail if it is ever reached
    def must_not_probe(*args, **kwargs):
        raise AssertionError('display probed although already checked')

    monkeypatch.setattr(launcher_mod.socket, 'create_connection', must_not_probe)
    monkeypatch.setenv('DISPLAY', 'far.host:1.0')
    assert launcher_mod.ensureDisplayUsable() is True  # cached not-headless verdict
    # the cached forced-headless verdict inverts the answer
    state['forced_headless'] = True
    assert launcher_mod.ensureDisplayUsable() is False


# ---------------------------------------------------------------------------
# Launcher.setWorld guard and getHist dimension dispatch
# ---------------------------------------------------------------------------

class _VolumeStub:
    cobj = 7


def test_launcher_setworld_guard_fires_before_pt_setworld(monkeypatch):
    calls = []
    monkeypatch.setattr(launcher_mod, '_pt_setWorld', lambda cobj: calls.append(cobj))
    inst = Prompt(seed=1).l
    inst.worldExist = True
    try:
        with pytest.raises(RuntimeError, match='World exist already'):
            inst.setWorld(_VolumeStub())
    finally:
        inst.worldExist = False
    assert calls == []  # guard must fire before the ctypes call


def test_gethist_dimension_three_raises(monkeypatch):
    monkeypatch.setattr(launcher_mod, '_pt_ResourceManager_getHist', lambda cstr: 555)
    monkeypatch.setattr(launcher_mod, '_pt_HistBase_dimension', lambda cobj: 3)
    inst = Prompt(seed=1).l
    assert inst.worldExist is False  # name check skipped, dim dispatch still runs
    with pytest.raises(RuntimeError, match='no implemented'):
        inst.getHist('some_3d_hist')


# ---------------------------------------------------------------------------
# Prompt basics
# ---------------------------------------------------------------------------

def test_prompt_seed_defaults_to_4096_and_is_readonly():
    p = Prompt()
    assert p.seed == 4096
    with pytest.raises(AttributeError):
        p.seed = 1234


def test_prompt_makeworld_is_abstract():
    with pytest.raises(NotImplementedError):
        Prompt(seed=1).makeWorld()


def test_prompt_clear_resets_world_and_scorers(monkeypatch):
    cleared = []
    monkeypatch.setattr(prompt_core_mod, '_pt_ResourceManager_clear',
                        lambda: cleared.append(True))
    monkeypatch.setattr(Volume, 'scorer_dict', {'TOF': 'ScorerTOF_TOF;min=0'})
    p = Prompt(seed=1)
    p.l.worldExist = True
    p.clear()
    assert cleared == [True]
    assert p.l.worldExist is False
    assert Volume.scorer_dict == {}


def test_prompt_scorer_property_returns_scorer_dict(monkeypatch):
    sentinel = {'S1': 'ScorerTOF_S1;min=0', 'S2': 'ScorerPSD_S2'}
    monkeypatch.setattr(Volume, 'scorer_dict', sentinel)
    p = Prompt(seed=1)
    assert p.scorer is sentinel
    assert sorted(p.scorer) == ['S1', 'S2']


# ---------------------------------------------------------------------------
# python-gun simulate loop: batch and remainder math
# ---------------------------------------------------------------------------

class _FakeGun:
    """Python-gun stand-in: records the vectorized size seen at each generate()."""

    def __init__(self, vectorized):
        self.vectorized = vectorized
        self.generate_sizes = []

    def generate(self):
        self.generate_sizes.append(self.vectorized)


class _NoVecGun:
    """Python-gun stand-in without a .vectorized attribute at all."""

    def __init__(self):
        self.generate_calls = 0

    def generate(self):
        self.generate_calls += 1


def test_simulate_pythongun_exact_batches(monkeypatch):
    events = []
    monkeypatch.setattr(launcher_cls(), 'simOneEvent',
                        lambda self, recordTrj=False: events.append(recordTrj))
    gun = _FakeGun(vectorized=4)
    Prompt(seed=1).simulate(gun, 12)
    # 12 particles / batch 4 -> exactly 3 generate+simOneEvent rounds
    assert gun.generate_sizes == [4, 4, 4]
    assert events == [False, False, False]
    assert gun.vectorized == 4


def test_simulate_pythongun_remainder_event(monkeypatch):
    events = []
    monkeypatch.setattr(launcher_cls(), 'simOneEvent',
                        lambda self, recordTrj=False: events.append(recordTrj))
    gun = _FakeGun(vectorized=4)
    Prompt(seed=1).simulate(gun, 10)
    # 2 full batches of 4, then one remainder event generated with
    # vectorized temporarily equal to 10 % 4 == 2 ...
    assert gun.generate_sizes == [4, 4, 2]
    assert len(events) == 3
    # ... and the original batch size restored afterwards
    assert gun.vectorized == 4


def test_simulate_pythongun_without_vectorized_defaults_to_one(monkeypatch):
    events = []
    monkeypatch.setattr(launcher_cls(), 'simOneEvent',
                        lambda self, recordTrj=False: events.append(recordTrj))
    gun = _NoVecGun()
    Prompt(seed=1).simulate(gun, 5)
    assert gun.generate_calls == 5
    assert len(events) == 5
    assert not hasattr(gun, 'vectorized')


def test_simulate_second_stack_forwards_int(monkeypatch):
    seen = {}

    def fake_second_stack(cobj, num, out):
        # the checked bridge protocol: int status, particle count through
        # the out-pointer
        seen['num'] = num
        out[0] = 99
        return 0

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_goWithSecondStack', fake_second_stack)
    assert Prompt(seed=1).simulateSecondStack(7.9) == 99
    assert seen['num'] == 7  # int(7.9) truncation before the ctypes call


def test_simulate_second_stack_bridge_error(monkeypatch):
    # a nonzero bridge status (e.g. a C++ error inside the eigenvalue cycle)
    # surfaces as RuntimeError instead of being silently dropped
    def failing_second_stack(cobj, num, out):
        return 1

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_goWithSecondStack', failing_second_stack)
    with pytest.raises(RuntimeError):
        Prompt(seed=1).simulateSecondStack(5)


# ---------------------------------------------------------------------------
# PromptMPI rank split (singleton COMM_WORLD: rank 0, size 1 outside mpirun)
# ---------------------------------------------------------------------------

def test_promptmpi_ctor_keeps_seed_on_rank0():
    sim = PromptMPI(seed=100)
    assert sim.rank == 0 and sim.size == 1
    assert sim.seed == 100  # seed + rank, rank is 0 here
    assert sim.l is Prompt(seed=1).l  # shares the process-wide Launcher


def test_promptmpi_rank0_simulate_forwards_num_timer_save(monkeypatch):
    recorded = {}

    def fake_simulate(self, gun, num=0, timer=True, save2Disk=False):
        recorded.update(num=num, timer=timer, save2Disk=save2Disk)

    monkeypatch.setattr(Prompt, 'simulate', fake_simulate)
    sim = PromptMPI(seed=1)
    sim.simulate('gun=MaxwellianGun;', 100, timer=False, save2Disk=True)
    # size 1: rank 0 runs everything, timer/save2Disk forwarded unchanged
    assert recorded == {'num': 100, 'timer': False, 'save2Disk': True}


def test_promptmpi_nonroot_splits_batch_and_forces_quiet(monkeypatch):
    recorded = {}

    def fake_simulate(self, gun, num=0, timer=True, save2Disk=False):
        recorded.update(num=num, timer=timer, save2Disk=save2Disk)

    monkeypatch.setattr(Prompt, 'simulate', fake_simulate)
    sim = PromptMPI(seed=1)
    sim._rank = 1  # fake a non-root rank of a 2-rank job
    sim._size = 2
    sim.simulate('gun=MaxwellianGun;', 100)
    # non-root ranks run num//size events with timer and disk saving forced off
    assert recorded == {'num': 50, 'timer': False, 'save2Disk': False}


def test_promptmpi_nonroot_show_only_barriers(monkeypatch):
    class _FakeComm:
        def __init__(self):
            self.barriers = 0

        def Barrier(self):
            self.barriers += 1

    sim = PromptMPI(seed=1)
    sim._rank = 1
    comm = _FakeComm()
    sim._comm = comm

    def must_not_show(self, *args, **kwargs):
        raise AssertionError('showWorld reached on a non-root rank')

    monkeypatch.setattr(launcher_cls(), 'showWorld', must_not_show)
    sim.show('gun=MaxwellianGun;', 3)
    assert comm.barriers == 1
