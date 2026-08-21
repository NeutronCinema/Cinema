#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Sphere, Tube, Trapezoid, ArbTrapezoid, Cone
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum
import numpy as np

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume


def test_simulation():
    expectWl = [425., 454., 427., 456., 425., 447., 392., 415., 362., 334., 295.,
           276., 271., 234., 243., 194., 192., 183., 157., 156.]


    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))
            rminBot = 5
            rmaxBot = 10
            rminTop = 3
            rmaxTop = 3
            z = 20
            startPhi = -30
            deltaPhi = 120

            sample = Volume('sample', Cone(rmaxBot, rmaxTop, z, rminBot, rminTop, startPhi, deltaPhi), 'Al_sg225.ncmat')
            world.placeChild('entity', sample, Transformation3D().applyRotX(30))

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
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('WavelengthSp')
    # print(wlhist.getHit())
    np.testing.assert_allclose(wlhist.getHit(), expectWl)
