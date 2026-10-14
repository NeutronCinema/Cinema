#!/usr/bin/env python3
"""Every script in doc/wiki/examples must run cleanly from an empty directory.

CI smoke test for the wiki examples: each example is executed in a subprocess
of its own (so the process-global Launcher singleton sees exactly one world),
with the working directory set to a fresh tmp_path — the examples are
contracted to write their output only into the current directory. Each run
must exit 0, and each example that promises a PNG must have written it.

The rendering examples need pyvista and are skipped gracefully (importorskip)
when it is absent; the materials/units example runs without any of the viz
dependencies.

Run forked like every test that touches the Cinema bridge, so a hard C++
failure in one example cannot take down the pytest process:

    pytest test_wiki_examples.py --forked -q

Set MPLBACKEND=Agg in the environment for fully headless runs (the examples
force pyvista off-screen rendering themselves, and the display probe inside
Cinema degrades automatically when DISPLAY is set but unreachable).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow  # full render chain per example: seconds each

_REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = _REPO_ROOT / "doc" / "wiki" / "examples"

# example script -> PNG it must write into the current directory (None:
# prints its checks only and must not leave any file behind)
_EXPECTED_OUTPUT = {
    "ex_headless_show.py": "headless_show.png",
    "ex_materials_units.py": None,
    "ex_mesh_iterator.py": None,
    "ex_minimal_show.py": "minimal_show.png",
    "ex_nested_volumes.py": "nested_volumes.png",
    "ex_scorer_show.py": "tof.png",
    "ex_show_options.py": "show_options.png",
}

# everything that renders needs the plotting stack; the units example does not
_NEEDS_PYVISTA = frozenset(_EXPECTED_OUTPUT) - {"ex_materials_units.py"}

# generous per-example ceiling: normal runtimes are 4-7 s, but CI machines
# can be slow at VTK/EGL initialization
_TIMEOUT_S = 300


def _run_example(tmp_path, monkeypatch, name):
    monkeypatch.chdir(tmp_path)
    script = EXAMPLES_DIR / name
    assert script.is_file(), f"example script missing from the repo: {script}"
    # CINEMAPATH must point at the directory holding cinemabin/ (the built
    # bridge library) and ncmat/ (repo data files like Cd.ncmat). In-tree
    # runs normally get it from the environment; default it to the repo root
    # so the test does not depend on the caller's shell profile.
    env = dict(os.environ)
    env.setdefault("CINEMAPATH", str(_REPO_ROOT))
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        env=env,
    )


@pytest.mark.parametrize("name,expected_png", sorted(_EXPECTED_OUTPUT.items()))
def test_wiki_example(tmp_path, monkeypatch, name, expected_png):
    if name in _NEEDS_PYVISTA:
        pytest.importorskip("pyvista")

    proc = _run_example(tmp_path, monkeypatch, name)
    assert proc.returncode == 0, (
        f"{name} exited with {proc.returncode}:\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")

    if expected_png is not None:
        out = tmp_path / expected_png
        assert out.is_file() and out.stat().st_size > 0, (
            f"{name} did not write a non-empty {expected_png}; "
            f"directory contents: {sorted(p.name for p in tmp_path.iterdir())}")
    else:
        leftovers = sorted(p.name for p in tmp_path.iterdir())
        assert not leftovers, f"{name} wrote unexpected files: {leftovers}"
