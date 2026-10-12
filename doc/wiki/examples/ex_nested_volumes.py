#!/usr/bin/env python3
"""Nested volumes: world -> box -> smaller box.

Demonstrates that volumes may contain volumes that contain volumes, authored
top-down in the natural direction ``world.placeChild(A); A.placeChild(B)``.
(Older Cinema versions aborted while building the geometry tree for this
placement order; it is fully supported now, and this script is a runnable
check of that.)

The scene is rendered off-screen and saved to a PNG.

Expected runtime: about 5 s (start-up and VTK initialization dominate).
Output: ``nested_volumes.png`` in the current directory.
"""

import pyvista

pyvista.OFF_SCREEN = True  # no window needed; see ex_headless_show.py

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.solid import Box


class Sim(Prompt):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        # All sizes are mm; Box takes HALF-lengths, so the world below spans
        # -400..400 mm along each axis and the core spans -50..50.
        world = Volume("world", Box(400, 400, 400), matCfg='void.ncmat')
        inner = Volume("inner", Box(200, 200, 200), matCfg='void.ncmat')
        core = Volume("core", Box(50, 50, 50), matCfg='Cd.ncmat')

        # the top-down direction: a child placed into a child, not straight
        # into the world. Each placement takes an optional Transformation3D;
        # the identity used here means "concentric".
        world.placeChild("innerPhy", inner, Transformation3D(0, 0, 0))
        inner.placeChild("corePhy", core)

        self.setWorld(world)


if __name__ == "__main__":
    sim = Sim()
    sim.makeWorld()

    # geometry only, off-screen
    sim.show(None, 0)

    # save a PNG via the Visualiser (sim.show() itself writes no files)
    from Cinema.Prompt.Visualiser import Visualiser

    vis = Visualiser([])
    vis.show()
    vis.plotter.screenshot("nested_volumes.png")
    print("wrote nested_volumes.png")
