#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Tube
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum
from Cinema.Prompt.physics import Material
from Cinema.Prompt.component import makeChopper
import numpy as np


def test_simulation():
    expWl = [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]

    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            sample_mat = "physics=idealElaScat;xs_barn=5;density_per_aa3=0.5;energy_transfer_eV=0.01"
            sample = Volume('sample', Box(2,2,2), sample_mat)
            world.placeChild('physicalSample', sample)

            chopper = makeChopper('chopper', 0.2, 0.1, 100, 293, 0., 0.)
            world.placeChild('chopper', chopper, Transformation3D(0,0,20))

            dtt = Volume('detector', Box(10, 10, 1))
            scorerWl = WlSpectrum()
            scorerWl.cfg_name = 'WavelengthSp'
            scorerWl.cfg_min = 1
            scorerWl.cfg_max = 2
            scorerWl.cfg_numbin = 20
            dtt.addScorer(scorerWl)
            world.placeChild('detectorPhy', dtt, Transformation3D(0,0,99))

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('WavelengthSp')
    np.testing.assert_allclose(wlhist.getHit(), expWl)
