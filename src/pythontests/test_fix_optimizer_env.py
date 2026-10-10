#!/usr/bin/env python3
# Regression tests for the optimiser/packaging fix wave:
#  - parameterOptimizer.py no longer embeds a remote MySQL credential as the
#    default optuna storage (storage=None now means an in-memory study)
#  - promptCore.py imports without mpi4py; only PromptMPI requires it
#  - save_all_scorers works on plain Prompt (no rank attribute) and names
#    files after the scorer
#
# Collection of this module is itself a partial regression test: on pre-fix
# code, importing Cinema.Prompt fails outright when mpi4py is absent.

import inspect
import subprocess
import sys
import textwrap

import pytest

import Cinema.Prompt.parameterOptimizer as parameterOptimizer_mod
from Cinema.Prompt import promptCore as promptCore_mod
from Cinema.Prompt import Prompt
from Cinema.Prompt.parameterOptimizer import Optimiser


# ------------------------------------------------- de-credentialed optimiser

def test_no_mysql_credential_in_source():
    # the storage default must not carry a remote-MySQL URL (or any URL) anymore
    src = inspect.getsource(parameterOptimizer_mod)
    assert 'mysql://' not in src


def test_storage_default_is_none():
    # in-memory study is the new default; a persistent study needs an explicit
    # storage URL from the caller
    for meth in (Optimiser.optimize, Optimiser.optimize_botorch):
        params = inspect.signature(meth).parameters
        assert params['storage'].default is None
        assert 'localhost' in params  # deprecated, still accepted


@pytest.mark.medium  # optuna import + study-lookup in the body, ~0.07 s
def test_default_call_without_storage_raises_valueerror():
    # storage=None + localhost=False must refuse to run rather than silently
    # hit some external service; the error points at the local-sqlite escape
    pytest.importorskip('optuna')
    opt = Optimiser(sim=None)
    with pytest.raises(ValueError, match=r'sqlite:///optuna_study\.db'):
        opt.optimize(name='cinema_test_study', n_trials=1)


@pytest.mark.medium  # optuna import + one in-memory trial, ~0.07 s
def test_localhost_true_is_deprecated_in_memory():
    # localhost=True keeps working (in-memory study) but warns
    pytest.importorskip('optuna')

    class _Trivial(Optimiser):
        def objective(self, trial):
            return 0.0

    opt = _Trivial(sim=None)
    with pytest.warns(FutureWarning):
        study = opt.optimize(name='cinema_inmem_study', n_trials=1, localhost=True)
    assert study is opt.study
    assert len(study.trials) == 1


@pytest.mark.medium  # sqlite storage round-trip, ~0.6 s body
def test_explicit_storage_is_persistent(tmp_path):
    # only an explicitly supplied storage URL is passed down to optuna
    pytest.importorskip('optuna')

    class _Trivial(Optimiser):
        def objective(self, trial):
            return 0.0

    opt = _Trivial(sim=None)
    dbfile = tmp_path / 'study.db'
    opt.optimize(name='cinema_storage_study', n_trials=1,
                 storage=f'sqlite:///{dbfile}')
    assert dbfile.exists()


# ----------------------------------------------------------- mpi4py optional

def test_promptmpi_raises_clear_error_when_mpi_missing(monkeypatch):
    # serial Prompt has no rank and works; PromptMPI must say clearly that
    # mpi4py is the missing piece instead of dying on a None communicator
    sim = Prompt(seed=1)
    assert not hasattr(sim, 'rank')
    monkeypatch.setattr(promptCore_mod, 'MPI', None)
    with pytest.raises(ImportError, match=r'mpi4py'):
        promptCore_mod.PromptMPI(seed=1)


@pytest.mark.slow  # subprocess start + full Cinema.Prompt/kernel import, ~1.2 s body
def test_import_cinema_prompt_without_mpi4py():
    # fresh interpreter with mpi4py blocked by a meta_path finder: plain
    # Prompt must still import and construct, PromptMPI must raise clearly
    code = textwrap.dedent('''
        import importlib.abc
        import sys

        class _BlockMPI(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == 'mpi4py' or fullname.startswith('mpi4py.'):
                    raise ImportError('mpi4py blocked by test')
                return None

        sys.meta_path.insert(0, _BlockMPI())
        try:
            import mpi4py
        except ImportError:
            pass
        else:
            sys.exit('mpi4py was not blocked by the finder')

        import Cinema.Prompt as P
        sim = P.Prompt()
        assert not hasattr(sim, 'rank')
        try:
            P.PromptMPI()
        except ImportError as exc:
            assert 'mpi4py' in str(exc)
        else:
            sys.exit('PromptMPI did not raise without mpi4py')
        print('OK')
    ''')
    proc = subprocess.run([sys.executable, '-c', code],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, \
        f'stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}'
    # the C++ kernel prints an atexit banner to stdout after our 'OK' line
    assert 'OK' in proc.stdout.splitlines()


# -------------------------------------------------- save_all_scorers on plain

@pytest.mark.medium  # tiny real simulation (world build + 10 events), ~0.3 s body
def test_save_all_scorers_plain_prompt(tmp_path, monkeypatch):
    # pre-fix code died on AttributeError (self.rank) AFTER the simulation
    # finished, and gathering by the dict value instead of the scorer name
    # raised KeyError; the run must now leave one <scorer>.h5 behind
    import os

    from Cinema.Prompt.geo import Volume
    from Cinema.Prompt.scorer import WlSpectrum
    from Cinema.Prompt.solid import Box

    monkeypatch.chdir(tmp_path)

    class MySim(Prompt):
        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200), 'void.ncmat')
            dtt = Volume('detector', Box(10, 10, 1))
            scorer = WlSpectrum()
            scorer.cfg_name = 'WavelengthSp'
            scorer.cfg_min = 1
            scorer.cfg_max = 2
            scorer.cfg_numbin = 10
            dtt.addScorer(scorer)
            world.placeChild('detectorPhy', dtt)
            self.setWorld(world)

    sim = MySim(seed=4096)
    assert not hasattr(sim, 'rank')
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    sim.simulate(gunCfg, 10)
    sim.save_all_scorers()
    assert (tmp_path / 'WavelengthSp.h5').exists()
    assert os.path.getsize(tmp_path / 'WavelengthSp.h5') > 0
