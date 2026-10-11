# Regression guards for the extern "C" ctypes bridge: a C++ cfg rejection
# must surface as a normal python exception instead of unwinding through the
# bare pt_* wrappers, which used to end in std::terminate and abort the whole
# process (SIGABRT, core dump) on documented everyday inputs.
#
# The bridged entry points (Launcher.setGun/go/loadGeometry,
# Volume.addScorer/setSurface) return an int status and record the C++ message
# in a thread-local buffer exposed as pt_last_error(); raiseOnBridgeError
# turns a nonzero status into a RuntimeError carrying that message.
#
# One test per reachable failure mode. The Launcher is a process-global
# singleton (one world per process), so these tests rely on the pytest
# --forked run mode like every other test that touches the Launcher. None of
# them runs a simulation or writes to disk (save2Disk=False throughout), so
# they are all fast tier (no marker).

import pytest

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box

SEED = 20261011


def _guarded_volume():
    # A plain Volume is enough for the addScorer paths: constructing it
    # registers the volume ID with the C++ ResourceManager, no setWorld
    # (and no geometry build) required.
    return Volume("abortguard_world", Box(100, 100, 400), matCfg='vacuum.ncmat')


def test_addscorer_unknown_scorer_type_raises_instead_of_abort():
    sim = Prompt(seed=SEED)
    vol = _guarded_volume()
    with pytest.raises(RuntimeError, match='Scorer type NoSuchScorer is not supported'):
        vol.addScorer('Scorer=NoSuchScorer; name=guard1; '
                      'min=1e-4; max=1e-1; numbin=10; ptstate=ENTRY')


def test_addscorer_unknown_ptstate_raises_instead_of_abort():
    sim = Prompt(seed=SEED)
    vol = _guarded_volume()
    with pytest.raises(RuntimeError, match='ptstate does not support NoSuchState'):
        vol.addScorer('Scorer=ESpectrum; name=guard2; '
                      'min=1e-4; max=1e-1; numbin=10; ptstate=NoSuchState')


def test_addscorer_zero_edge_log_binning_raises_and_state_recovers():
    # The shipped ESpectrum example with min=max=0: log binning demands
    # positive edges, and this exact cfg used to abort the process
    sim = Prompt(seed=SEED)
    vol = _guarded_volume()
    with pytest.raises(RuntimeError, match='xmin and xmax must be positive'):
        vol.addScorer('Scorer=ESpectrum; name=x; min=0.0; max=0.0253; '
                      'numbin=100; ptstate=ENTRY')

    # recovery: the failed registration must not have corrupted the
    # ResourceManager - a valid scorer registers cleanly afterwards
    vol.addScorer('Scorer=ESpectrum; name=guard3_recovery; min=1e-6; max=0.0253; '
                  'numbin=100; ptstate=ENTRY')
    assert 'guard3_recovery' in Volume.scorer_dict


def test_setgun_unknown_gun_key_raises_and_launcher_recovers():
    sim = Prompt(seed=SEED)
    with pytest.raises(RuntimeError, match='Gun NoSuchGun is not supported'):
        sim.l.setGun('gun=NoSuchGun')

    # recovery: the Launcher accepts a valid gun after the rejected one
    sim.l.setGun('gun=SimpleThermalGun;energy=0.0253;position=0,0,-500;direction=0,0,1')


def test_go_zero_particles_with_timer_raises_instead_of_abort():
    sim = Prompt(seed=SEED)
    with pytest.raises(RuntimeError, match='The number of tasks is zero'):
        sim.l.go(0, timer=True, save2Disk=False)

    # recovery: the same call without the timer runs through (zero
    # primaries, nothing saved)
    sim.l.go(0, timer=False, save2Disk=False)
