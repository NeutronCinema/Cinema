#!/usr/bin/env python3
"""The show() keyword options: byMat, addLegend and axis scaling.

Demonstrates the most useful keyword arguments of ``sim.show(gun, n)`` on the
starter world:

- ``byMat=True``  — one colour per material instead of per volume; volumes
  sharing a material share a colour and the label becomes ``name[material]``;
- ``addLegend=True`` — a legend box built from the geometry-tree nodes;
- ``zscale`` (with ``xscale``/``yscale``) — anisotropic axis scaling for
  scene layout. Geometry coordinates themselves stay in mm; this only
  stretches the drawing. A long beamline with mm-sized parts needs it to be
  readable.

The same options exist on the Visualiser class, which is then used to save a
PNG (sim.show() itself writes no files).

Expected runtime: about 8 s (two off-screen renders: the show() call and the
screenshot pass, plus the 30-event trajectory re-simulation).
Output: ``show_options.png`` in the current directory.
"""

import pyvista

pyvista.OFF_SCREEN = True

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.gun import UniModeratorGun


class Simulation(PromptMPI):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        nccfg = ('Ge_sg227.ncmat;mos=0.0267deg;'
                 'dir1=@crys_hkl:5,1,1@lab:0,0,1;'
                 'dir2=@crys_hkl:0,1,-1@lab:1,0,0')
        mat = Material(nccfg)
        vol = Volume("sampleSolid", Box(10, 10, 1), matCfg=mat.cfg)  # half-lengths: 20x20x2 mm

        shield = Volume("shield", Box(30, 30, 2), matCfg='Cd.ncmat')
        world = Volume("world", Box(50, 50, 210))  # default material: dilute H1 gas, not vacuum
        world.placeChild("shieldPhy", shield, Transformation3D(0, 0, 60))
        world.placeChild("samplePhyVol", vol, Transformation3D(0, 0, 100).applyRotX(45))
        self.setWorld(world)


if __name__ == "__main__":
    gun = UniModeratorGun()
    gun.setSource([10, 10, -200])
    gun.setSlit([5, 5, -20])

    sim = Simulation()
    sim.makeWorld()

    # geometry + 30 trajectories, coloured by material, with a legend.
    # (The world's default material is the dilute H1 gas — it is a real
    # material and gets its own colour under byMat, which makes it obvious.)
    sim.show(gun, 30, byMat=True, addLegend=True, zscale=0.6)

    # the same scene saved to a file: drive the Visualiser with the same
    # options and squash the beam axis the same way
    from Cinema.Prompt.Visualiser import Visualiser

    vis = Visualiser([], byMat=True, addLegend=True)
    vis.plotter.set_scale(1.0, 1.0, 0.6)
    vis.show()
    vis.plotter.screenshot("show_options.png")
    print("wrote show_options.png")
