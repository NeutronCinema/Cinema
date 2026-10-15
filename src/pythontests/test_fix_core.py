#!/usr/bin/env python3
# Regression tests for the Prompt/promptCore.py + Prompt/launcher.py fixes
# (usability audit findings #1, #15, #30).
#
# Everything here is pure Python: C++ entry points are stubbed or never
# reached, so no test builds geometry or transports particles. Each test is
# written to fail on the pre-fix code and pass on the fixed code.

import inspect
import warnings

import pytest

from Cinema.Prompt import launcher as launcher_mod
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.promptCore import Prompt, PromptMPI


def launcher_cls():
    # the module-level name 'Launcher' is the @singleton factory function,
    # so take the real class from an instance
    return type(Prompt(seed=1).l)


def fake_gethist_cfunc(cstr):
    # stands in for pt_ResourceManager_getHist; must never be reached with a
    # name the Python-side validation should have rejected
    raise AssertionError('ctypes getHist reached with unvalidated name: %r' % (cstr,))


# ---------------------------------------------------------------- finding #1

def test_setworld_guard_fires_before_setseed(monkeypatch):
    # old code called setSeed first, which aborts the whole process in C++
    # ("seed is already set") before the worldExist guard could fire
    sim = Prompt(seed=1)
    sim.l.worldExist = True  # simulate an already-set world, no geometry built
    seed_calls = []
    monkeypatch.setattr(sim.l, 'setSeed', lambda seed: seed_calls.append(seed))
    try:
        with pytest.raises(RuntimeError, match='one world'):
            sim.setWorld(object())
        assert seed_calls == []  # guard must fire before any ctypes call
    finally:
        sim.l.worldExist = False


def test_setworld_message_covers_second_prompt_instance():
    # Launcher is a process-wide singleton, so a second Prompt() in the same
    # process hits the guard on its *first* setWorld; the message must not
    # suggest clear() (it would destroy the other instance's world)
    first = Prompt(seed=1)
    second = Prompt(seed=2)
    assert second.l is first.l
    first.l.worldExist = True
    try:
        with pytest.raises(RuntimeError) as excinfo:
            second.setWorld(object())
        msg = str(excinfo.value)
        assert 'one world' in msg and 'process' in msg
        assert 'clear()' not in msg
    finally:
        first.l.worldExist = False


# ---------------------------------------------------------------- finding #15

def test_serial_show_accepts_visualisation_kwargs():
    # serial show() must accept the same kwargs that already worked via PromptMPI
    params = inspect.signature(Prompt.show).parameters
    for name in ('mergeMesh', 'xscale', 'yscale', 'zscale', 'byMat', 'addLegend', 'geoClip'):
        assert name in params, name
    assert params['byMat'].default is False


def test_serial_show_forwards_visualisation_kwargs(monkeypatch):
    recorded = {}

    def fake_showWorld(self, gun, particles=None, mergeMesh=False, xscale=1.0, yscale=1.0,
                       zscale=1.0, byMat=False, addLegend=False, geoClip=False):
        recorded.update(gun=gun, particles=particles, mergeMesh=mergeMesh,
                        byMat=byMat, addLegend=addLegend, geoClip=geoClip)

    monkeypatch.setattr(launcher_cls(), 'showWorld', fake_showWorld)
    Prompt(seed=1).show('gun=MaxwellianGun;', 7, byMat=True, addLegend=True)
    assert recorded == {'gun': 'gun=MaxwellianGun;', 'particles': 7, 'mergeMesh': False,
                        'byMat': True, 'addLegend': True, 'geoClip': False}


def test_promptmpi_simulate_accepts_timer_save2disk():
    params = inspect.signature(PromptMPI.simulate).parameters
    assert params['timer'].default is True
    assert params['save2Disk'].default is False


def test_promptmpi_simulate_forwards_timer_save2disk(monkeypatch):
    recorded = {}

    def fake_simulate(self, gun, num=0, timer=True, save2Disk=False):
        recorded.update(num=num, timer=timer, save2Disk=save2Disk)

    monkeypatch.setattr(Prompt, 'simulate', fake_simulate)
    sim = PromptMPI(seed=1)  # rank 0, size 1 outside mpirun
    sim.simulate('gun=MaxwellianGun;', 100, timer=False, save2Disk=True)
    assert recorded == {'num': 100, 'timer': False, 'save2Disk': True}


def test_prompt_simulate_forwards_save2disk_canonical(monkeypatch):
    # the cfg-string path must pass the corrected kwarg name down to Launcher.go
    Lcls = launcher_cls()
    recorded = {}
    monkeypatch.setattr(Lcls, 'setGun', lambda self, cfg: recorded.update(gun=cfg))

    def fake_go(self, numPrimary, printPercent=0.1, recordTrj=False, timer=True,
                save2Disk=True, **kw):
        assert not kw, 'legacy typo kwargs leaked through: %s' % list(kw)
        recorded.update(num=numPrimary, timer=timer, save2Disk=save2Disk)

    monkeypatch.setattr(Lcls, 'go', fake_go)
    Prompt(seed=1).simulate('gun=MaxwellianGun;', 100, save2Disk=True)
    assert recorded == {'gun': 'gun=MaxwellianGun;', 'num': 100, 'timer': True,
                        'save2Disk': True}


def test_launcher_go_save2disk_canonical_with_deprecated_alias(monkeypatch):
    Lcls = launcher_cls()
    params = inspect.signature(Lcls.go).parameters
    assert 'save2Disk' in params      # the typo is fixed in the signature
    assert 'printPercent' in params
    assert 'save2Dis' in params       # typo kept as deprecated alias
    assert 'printPrecent' in params

    recorded = {}

    def fake_go_cfunc(cobj, numPrimary, printPercent, recordTrj, timer, save2Disk):
        recorded.update(num=numPrimary, printPercent=printPercent, save2Disk=save2Disk)

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_go', fake_go_cfunc)
    inst = Prompt(seed=1).l

    # old misspelled keyword still works, with a DeprecationWarning
    with pytest.warns(DeprecationWarning, match='save2Disk'):
        inst.go(10, save2Dis=False)
    assert recorded['save2Disk'] is False
    with pytest.warns(DeprecationWarning, match='printPercent'):
        inst.go(10, printPrecent=0.5)
    assert recorded['printPercent'] == 0.5

    # canonical keywords emit no warning
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        inst.go(10, printPercent=0.2, save2Disk=True)
    assert recorded == {'num': 10, 'printPercent': 0.2, 'save2Disk': True}


def test_launcher_go_positional_call_unchanged(monkeypatch):
    # pre-fix positional order (numPrimary, printPrecent, recordTrj, timer, save2Dis)
    recorded = {}

    def fake_go_cfunc(cobj, numPrimary, printPercent, recordTrj, timer, save2Disk):
        recorded.update(printPercent=printPercent, recordTrj=recordTrj,
                        timer=timer, save2Disk=save2Disk)

    monkeypatch.setattr(launcher_mod, '_pt_Launcher_go', fake_go_cfunc)
    Prompt(seed=1).l.go(10, 0.25, True, False, False)
    assert recorded == {'printPercent': 0.25, 'recordTrj': True, 'timer': False,
                        'save2Disk': False}


# ---------------------------------------------------------------- finding #30

def test_gatherhistdata_unknown_name_lists_registered(monkeypatch):
    monkeypatch.setattr(Volume, 'scorer_dict', {'TOF': 'ScorerTOF_TOF;min=0;max=1'})
    sim = Prompt(seed=1)
    with pytest.raises(KeyError) as excinfo:
        sim.gatherHistData('never_made_scorer')
    msg = str(excinfo.value)
    assert "no scorer named 'never_made_scorer'" in msg
    assert 'TOF' in msg  # old code raised a bare KeyError('never_made_scorer') here


def test_gethist_unknown_name_fails_in_python_before_ctypes(monkeypatch):
    # raw=True used to SIGABRT in C++ ("Histogram not found"); now validated
    # in Python before the ctypes call
    monkeypatch.setattr(launcher_mod, '_pt_ResourceManager_getHist', fake_gethist_cfunc)
    monkeypatch.setattr(Volume, 'scorer_dict', {'TOF': 'ScorerTOF_TOF;min=0'})
    inst = Prompt(seed=1).l
    inst.worldExist = True
    try:
        with pytest.raises(KeyError) as excinfo:
            inst.getHist('no_such_scorer')
        msg = str(excinfo.value)
        assert "no scorer named 'no_such_scorer'" in msg
        assert 'ScorerTOF_TOF' in msg
    finally:
        inst.worldExist = False


def test_gatherhistdata_raw_unknown_name_keyerror(monkeypatch):
    monkeypatch.setattr(launcher_mod, '_pt_ResourceManager_getHist', fake_gethist_cfunc)
    monkeypatch.setattr(Volume, 'scorer_dict', {'TOF': 'ScorerTOF_TOF;min=0'})
    sim = Prompt(seed=1)
    sim.l.worldExist = True
    try:
        with pytest.raises(KeyError, match='registered scorers'):
            sim.gatherHistData('typo_name', raw=True)
    finally:
        sim.l.worldExist = False


def test_gethist_known_name_still_reaches_ctypes(monkeypatch):
    # the guard must not block names registered through the Python API
    calls = []
    monkeypatch.setattr(launcher_mod, '_pt_ResourceManager_getHist',
                        lambda cstr: calls.append(cstr) or 1234)
    monkeypatch.setattr(launcher_mod, '_pt_HistBase_dimension', lambda cobj: 1)
    monkeypatch.setattr(launcher_mod, 'Hist1D', lambda cobj: ('hist1d', cobj))
    monkeypatch.setattr(Volume, 'scorer_dict', {'TOF': 'ScorerTOF_TOF;min=0'})
    inst = Prompt(seed=1).l
    inst.worldExist = True
    try:
        assert inst.getHist('ScorerTOF_TOF;min=0') == ('hist1d', 1234)
    finally:
        inst.worldExist = False
    assert calls == [b'ScorerTOF_TOF;min=0']


def test_gethist_check_skipped_without_python_world(monkeypatch):
    # GDML-declared scorers (loadGeometry) register on the C++ side only, so
    # the Python-side name check must not fire when no Python-API world exists
    calls = []
    monkeypatch.setattr(launcher_mod, '_pt_ResourceManager_getHist',
                        lambda cstr: calls.append(cstr) or 1234)
    monkeypatch.setattr(launcher_mod, '_pt_HistBase_dimension', lambda cobj: 1)
    monkeypatch.setattr(launcher_mod, 'Hist1D', lambda cobj: ('hist1d', cobj))
    monkeypatch.setattr(Volume, 'scorer_dict', {})
    inst = Prompt(seed=1).l
    assert inst.worldExist is False
    assert inst.getHist('gdml_scorer') == ('hist1d', 1234)
    assert calls == [b'gdml_scorer']
