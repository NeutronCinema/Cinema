#!/usr/bin/env python3 * 10

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, GenTrapezoid
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum
import numpy as np

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume


def test_simulation():
    expectWl = [308., 348., 319., 304., 324., 327., 305., 282., 261., 208., 202.,198., 179., 175., 166., 153., 150., 121., 118.,  93.]


    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))
            dz, theta, phi, dy1, dx1, dx2, Alpha1, dy2, dx3, dx4, Alpha2 = 13, 45, 0, 6, 4, 4, 0, 6, 4, 4, 0
            sample = Volume('sample', GenTrapezoid(dz, theta, phi, dy1, dx1, dx2, Alpha1, dy2, dx3, dx4, Alpha2 ), 'Al_sg225.ncmat')
            world.placeChild('entity', sample, Transformation3D(0,0,0).applyRotY(-45))

            dtt = Volume('detector', Box(10, 10, 1))
            scorerWl = WlSpectrum()
            scorerWl.cfg_name = 'WavelengthSp'
            scorerWl.cfg_min = 1
            scorerWl.cfg_max = 2
            scorerWl.cfg_numbin = 20
            dtt.addScorer(scorerWl)
            world.placeChild('detectorPhy', dtt, Transformation3D(0,0,90))

            self.setWorld(world)



    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.001;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    VIZ = False
    if VIZ:
        sim.show(gunCfg, 100)
    else:
        sim.simulate(gunCfg, 1e4)
        wlhist = sim.gatherHistData('WavelengthSp')
        print(wlhist.getHit())
        np.testing.assert_allclose(wlhist.getHit(), expectWl)
