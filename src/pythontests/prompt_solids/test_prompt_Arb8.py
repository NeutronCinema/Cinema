#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Sphere, Tube, Trapezoid, ArbTrapezoid
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum
import numpy as np

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume


def test_simulation():
    expWl = [350., 367., 347., 367., 335., 342., 315., 312., 256., 253., 239., 217., 214., 161., 175., 146., 159., 147., 136., 108.]

    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))
            xy1 = np.array([-10, -10])
            xy2 = np.array([-5, 5])
            xy3 = np.array([5, 5])
            xy4 = np.array([10, -10])
            xy5 = np.array([-10, -10]) * 0.8
            xy6 = np.array([-5, 5]) * 0.8
            xy7 = np.array([5, 5]) * 0.8
            xy8 = np.array([10, -10]) * 0.8
            hz = 20

            sample = Volume('sample', ArbTrapezoid(xy1, xy2, xy3, xy4, xy5, xy6, xy7, xy8, hz), 'Al_sg225.ncmat')
            trs = Transformation3D().applyRotX(30)
            world.placeChild('entity', sample, trs)

            dtt = Volume('detector', Box(10, 10, 1))
            scorerWl = WlSpectrum()
            scorerWl.cfg_name = 'WavelengthSp'
            scorerWl.cfg_min = 1
            scorerWl.cfg_max = 2
            scorerWl.cfg_numbin = 20
            scorerWl.cfg_ptstate = 'ENTRY'
            dtt.addScorer(scorerWl)
            world.placeChild('detectorPhy', dtt, Transformation3D(0,0,90))

            self.setWorld(world)



    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('WavelengthSp')
    np.testing.assert_allclose(wlhist.getHit(), expWl)
    # print(wlhist.getHit())
