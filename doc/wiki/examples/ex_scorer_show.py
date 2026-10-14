#!/usr/bin/env python3
"""A scorer plus visualization: trajectories in the viewer, histogram as PNG.

Builds the canonical starter world (a germanium crystal slab with a
time-of-flight scorer, lit by a moderated beam), then

1. calls ``sim.show(gun, 50)`` — the viewer renders the geometry overlaid
   with the trajectories of 50 gun events (re-simulated with trajectory
   recording; the cost scales with the event count),
2. runs a small production simulation and writes the scorer's histogram.

Expected runtime: about 10 s (VTK start-up, the 50-event trajectory
re-simulation and a 2e4-event transport run). Output: ``tof.png`` in the
current directory. The geometry render itself is off-screen; on a desktop
you can comment out ``pyvista.OFF_SCREEN = True`` to see the window.
"""

import pyvista

pyvista.OFF_SCREEN = True

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun


class Simulation(PromptMPI):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        # single-crystal germanium, mosaicity and orientation in the config
        nccfg = ('Ge_sg227.ncmat;mos=0.0267deg;'
                 'dir1=@crys_hkl:5,1,1@lab:0,0,1;'
                 'dir2=@crys_hkl:0,1,-1@lab:1,0,0')
        mat = Material(nccfg)

        # Box takes HALF-lengths: the sample is 20 x 20 x 2 mm
        vol = Volume("sampleSolid", Box(10, 10, 1), matCfg=mat.cfg)

        # a TOF scorer counting neutrons absorbed in the sample
        tof = TOFHelper("TOF", ptstate='ABSORB')
        tof.make(vol)  # mandatory: creates and registers the C++ scorer

        # sample 100 mm downstream (z), tilted 45 deg about x
        trf = Transformation3D(0, 0, 100).applyRotX(45)

        # the world spans z = -210..210 mm (Box half-lengths again), so the
        # gun position below (z = -200) lies inside it — it must, or every
        # primary is dropped before taking a step
        world = Volume("world", Box(50, 50, 210))
        world.placeChild("samplePhyVol", vol, transf=trf)
        self.setWorld(world)


if __name__ == "__main__":
    gun = UniModeratorGun()
    gun.setSource([10, 10, -200])
    gun.setSlit([5, 5, -20])

    sim = Simulation()
    sim.makeWorld()

    # geometry + 50 trajectories, off-screen
    sim.show(gun, 50)

    # a small production run, then fetch the histogram by scorer name
    sim.simulate(gun, int(2e4))
    hist = sim.gatherHistData("TOF")
    hist.savefig("tof.png")
    print("wrote tof.png")
