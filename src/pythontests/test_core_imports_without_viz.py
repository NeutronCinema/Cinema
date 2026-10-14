#!/usr/bin/env python3
"""`import Cinema.Prompt` must work without the optional viz stack.

pyvista, matplotlib (and tetgen) belong to the optional ``viz`` extra
(``pip install neutron-cinema[viz]``); scipy and h5py stay core. Regression
guard for the decoupling work that moved every pyvista/matplotlib import out
of module import time:

  - ``import Cinema.Prompt`` (and the heavy Visualiser/Mesh modules) must
    import cleanly with pyvista/matplotlib/tetgen unimportable,
  - a small world must still build and simulate,
  - CONSTRUCTING a Visualiser must raise an ImportError whose message names
    the extra (``neutron-cinema[viz]``) instead of a bare ModuleNotFoundError.

The blocking runs in a fresh subprocess (the pytest process itself has the
viz stack installed, so only a child can prove the imports are gone): a
meta_path finder returns specs whose loader raises ImportError, and any
already-imported blocked modules are evicted from sys.modules first.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow  # subprocess spins up a full interpreter

# .../cinema/src/pythontests/test_...py -> .../cinema/src/python
_REPO_PYTHON = Path(__file__).resolve().parents[1] / "python"

_TIMEOUT = 180  # subprocess budget: ~2 s import + world build + simulate

_CHILD = r"""
import importlib.abc
import importlib.machinery
import sys

BLOCKED = ("pyvista", "matplotlib", "tetgen")


class _BlockingLoader(importlib.abc.Loader):
    def create_module(self, spec):
        raise ImportError("viz stack blocked for this test: %r" % spec.name)

    def exec_module(self, module):
        raise ImportError("viz stack blocked for this test: %r"
                          % module.__name__)


class _VizBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            return importlib.machinery.ModuleSpec(fullname, _BlockingLoader())
        return None


sys.meta_path.insert(0, _VizBlocker())
for name in [m for m in sys.modules if m.split(".")[0] in BLOCKED]:
    del sys.modules[name]

# 1) the package - and the heavy viz modules - import without the stack
import Cinema.Prompt
import Cinema.Prompt.Visualiser  # noqa: F401  (module import must not need pyvista)
from Cinema.Prompt import Prompt
from Cinema.Prompt.Mesh import Mesh  # noqa: F401
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.solid import Box

# 2) a small two-volume world builds, registers and simulates
sim = Prompt(seed=1010)
world = Volume("world", Box(50, 50, 200), matCfg="void.ncmat")
child = Volume("cube", Box(10, 10, 10), matCfg="void.ncmat")
world.placeChild("phyvol_cube", child)
sim.setWorld(world)
gun = ("gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;"
       "slit_z=1e99;temperature=293;")
sim.simulate(gun, int(1e2))

# 3) construction (not import) is what needs the extra, with a clear message
try:
    Cinema.Prompt.Visualiser.Visualiser(blacklist=[])
except ImportError as exc:
    assert "neutron-cinema[viz]" in str(exc), str(exc)
else:
    raise AssertionError("Visualiser() constructed without pyvista")

# PtPlotter is built lazily on attribute access and needs pyvista too
try:
    Cinema.Prompt.Visualiser.PtPlotter
except ImportError as exc:
    assert "neutron-cinema[viz]" in str(exc), str(exc)
else:
    raise AssertionError("PtPlotter resolved without pyvista")

print("CHILD_OK")
"""


def _child_env():
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    if str(_REPO_PYTHON) not in existing.split(os.pathsep):
        env["PYTHONPATH"] = (
            str(_REPO_PYTHON) + (os.pathsep + existing if existing else "")
        )
    env.setdefault("MPLBACKEND", "Agg")
    return env


def test_core_imports_and_simulate_without_viz():
    """Blocked pyvista/matplotlib/tetgen: import, build, simulate, error msgs."""
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD],
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )
    assert proc.returncode == 0, (
        f"child failed (rc={proc.returncode})\n--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}"
    )
    assert "CHILD_OK" in proc.stdout
