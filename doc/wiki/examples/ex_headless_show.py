#!/usr/bin/env python3
"""Headless rendering: no display, no X server, still a PNG.

Demonstrates the environment recipe for clusters and CI, where there is no
X server (or only a stale SSH forward). Three ingredients, all set BEFORE
Cinema/matplotlib/pyvista are imported:

1. ``DISPLAY`` removed — VTK then renders through its off-screen (EGL)
   fallback instead of trying to open an X window;
2. ``MPLBACKEND=Agg`` — matplotlib's non-interactive backend, needed by the
   histogram/plot layer;
3. ``pyvista.OFF_SCREEN = True`` — plotter windows render off-screen and
   ``show()`` returns instead of blocking.

Cinema also protects itself: when ``DISPLAY`` is set but unreachable (a dead
SSH forward), a probe warns on stderr — "forcing headless rendering
(matplotlib Agg backend, VTK off-screen); interactive show() is disabled." —
and degrades the same way automatically. This script shows the manual,
explicit version of that recipe.

Expected runtime: about 5 s. Output: ``headless_show.png`` in the current
directory.
"""

import os

os.environ.pop("DISPLAY", None)  # pretend there is no X server at all
os.environ.setdefault("MPLBACKEND", "Agg")  # before matplotlib is imported

import pyvista

pyvista.OFF_SCREEN = True

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.solid import Box


class Sim(Prompt):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        # sizes in mm; Box takes HALF-lengths (world spans -250..250 mm)
        world = Volume("world", Box(250, 250, 250), matCfg='void.ncmat')
        det = Volume("detector", Box(60, 60, 5), matCfg='Cd.ncmat')
        world.placeChild("detPhy", det, Transformation3D(0, 0, 150))
        self.setWorld(world)


if __name__ == "__main__":
    sim = Sim()
    sim.makeWorld()

    sim.show(None, 0)  # completes off-screen instead of opening a window

    from Cinema.Prompt.Visualiser import Visualiser

    vis = Visualiser([])
    vis.show()
    vis.plotter.screenshot("headless_show.png")
    print("wrote headless_show.png")
