#!/usr/bin/env python3
"""Minimal world, rendered off-screen and saved to a PNG.

Demonstrates the smallest complete Cinema geometry (a void world box with one
cadmium box placed inside it) and the two visualization entry points:

1. ``sim.show(gun, n)`` — the simple call; renders the closed world (here with
   ``n=0``, i.e. geometry only). It opens a window when a display is available
   and degrades to off-screen rendering otherwise, but it writes no files.
2. ``Visualiser`` — the class behind ``show``; driving it directly gives
   access to the pyvista plotter, so a screenshot can be saved.

The script forces off-screen rendering explicitly (``pyvista.OFF_SCREEN``),
so it also runs on machines with no display at all; see ``ex_headless_show.py``
for the full headless/cluster recipe.

Expected runtime: about 5 s (Python/C++ start-up and VTK initialization
dominate; meshing two boxes is instantaneous). Output: ``minimal_show.png``
in the current directory.
"""

import pyvista

# Force off-screen rendering before any plotter is created. On a desktop you
# can comment this out to get the interactive window instead.
pyvista.OFF_SCREEN = True

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.solid import Box


class Sim(Prompt):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        # All sizes are mm, and Box takes HALF-lengths: the world box below
        # spans -300..300 mm in x, y and z. 'void.ncmat' is true vacuum; a
        # material is named by an NCrystal config string (here a data file).
        world = Volume("world", Box(300, 300, 300), matCfg='void.ncmat')
        sample = Volume("sample", Box(20, 20, 40), matCfg='Cd.ncmat')
        world.placeChild("samplePhy", sample, Transformation3D(0, 0, 50))
        self.setWorld(world)  # closes the geometry


if __name__ == "__main__":
    sim = Sim()
    sim.makeWorld()

    # The simple entry point. gun=None and num=0: no trajectories, geometry
    # only. There is no file output; on a desktop this opens the interactive
    # window (blocked until closed), here it renders off-screen and returns.
    sim.show(None, 0)

    # To save an image, drive the Visualiser directly and take a screenshot
    # from its pyvista plotter. The world must be closed already (it is).
    from Cinema.Prompt.Visualiser import Visualiser

    vis = Visualiser([])  # empty blacklist: render every volume
    vis.show()
    vis.plotter.screenshot("minimal_show.png")
    print("wrote minimal_show.png")
