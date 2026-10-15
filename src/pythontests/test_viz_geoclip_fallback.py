#!/usr/bin/env python3
"""geoClip must degrade gracefully, not kill the process, when tetgen is absent.

Regression guard for the sys.exit(1) anti-pattern in Mesh.generateVolumetricMesh:
a missing optional dependency used to terminate the whole interpreter (sys.exit
is not an Exception, so Visualiser.loadMesh's `except Exception` fallback -
which exists precisely for this condition and prints "Fall back without
geoClip" - could never run). generateVolumetricMesh now raises
ModuleNotFoundError, which the documented geoClip fall-back path catches,
disables geoClip and finishes the visualization with plain surface meshes.

Two forked cases, both asserting that showWorld/show(..., geoClip=True)
RETURNS with the process alive and the fallback observable emitted:
  A. the environment genuinely lacks tetgen (skipped when it is installed)
  B. a fake tetgen module injected into sys.modules whose import raises,
     so the fallback is exercised even on machines that have tetgen

Off-screen rendering is forced via pyvista.OFF_SCREEN (set on the pyvista
module) so the bodies are deterministic with or without a usable DISPLAY.

The Launcher is a process-global singleton (one world per process): run with
pytest --forked like every other test that touches the Launcher.
"""

import importlib.util
import sys
import types

import pytest

pytest.importorskip("pyvista")

pytestmark = pytest.mark.slow  # >0.7 s body: plotting chain + EGL off-screen render

SEED = 1010

# Message printed by Visualiser.loadMesh when the geoClip attempt fails and
# the geometry is reloaded as plain surface meshes instead.
_FALLBACK_MSG = "Fall back without geoClip"


def _tetgen_available():
    # find_spec probes without importing (a real import here would double as
    # the very condition case A is supposed to exercise)
    return importlib.util.find_spec("tetgen") is not None


class _BrokenFakeTetgen(types.ModuleType):
    # a sys.modules entry whose every attribute access raises, standing in for
    # a tetgen install that is present but broken
    def __getattr__(self, name):
        raise ImportError(f"fake broken tetgen: cannot import {name}")


def _makeGeoClipSim():
    # the 2-volume world of the round-1 verifier repro: a big world cube with
    # a small cube child, both visualizable as plain VecGeom surface meshes
    from Cinema.Prompt import Prompt
    from Cinema.Prompt.geo import Volume, Transformation3D
    from Cinema.Prompt.solid import Box

    class Sim(Prompt):
        def __init__(self, seed=SEED):
            super().__init__(seed)

        def makeWorld(self):
            world = Volume("world", Box(100, 100, 100), matCfg='Cd.ncmat')
            child = Volume('child', Box(10, 10, 10), matCfg='Cd.ncmat')
            world.placeChild('det', child, Transformation3D(0., 0., 0))
            self.setWorld(world)

    sim = Sim()
    sim.makeWorld()
    return sim


@pytest.fixture
def off_screen(monkeypatch):
    # every Plotter created while this fixture is active renders off-screen,
    # regardless of DISPLAY, so plotter.show() never opens a window
    import pyvista
    monkeypatch.setattr(pyvista, "OFF_SCREEN", True)


def _assert_fallback_ran(capsys):
    out = capsys.readouterr().out
    assert _FALLBACK_MSG in out, (
        f"geoClip fallback did not fire; stdout was:\n{out}")
    assert "tetgen is required" in out, (
        f"missing-tetgen cause not reported; stdout was:\n{out}")


# ----------------------------------------------------------------------- (A)

@pytest.mark.skipif(_tetgen_available(), reason="tetgen installed; case A needs it absent")
def test_geoclip_falls_back_when_tetgen_missing(off_screen, capsys):
    # the real environment lacks tetgen: show(geoClip=True) must return with
    # the documented fallback instead of SystemExit-ing the process
    sim = _makeGeoClipSim()
    sim.show(None, 0, geoClip=True)  # SystemExit here would fail the test

    _assert_fallback_ran(capsys)
    # the interpreter and the C++ bridge are still alive afterwards
    assert sim.l.worldExist


# ----------------------------------------------------------------------- (B)

def test_geoclip_falls_back_when_tetgen_broken(off_screen, capsys, monkeypatch):
    # same fallback, but driven by a poisoned sys.modules entry so the case
    # also covers machines where tetgen IS installed
    monkeypatch.setitem(sys.modules, "tetgen", _BrokenFakeTetgen("tetgen"))
    sim = _makeGeoClipSim()
    sim.show(None, 0, geoClip=True)  # SystemExit here would fail the test

    _assert_fallback_ran(capsys)
    assert sim.l.worldExist
