#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import PSDHelper
from Cinema.Prompt.geo import Transformation3D as Tsf
import numpy as np


def test_simulation():
    accweight = 4435.0
    expWeight = [21.0, 25.0, 19.0, 16.0, 17.0, 22.0, 15.0, 16.0, 18.0, 2080.0, 2004.0, 20.0, 30.0, 22.0, 13.0, 21.0, 20.0, 21.0, 10.0, 25.0]

    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            sample_mat = "physics=idealElaScat;xs_barn=5;density_per_aa3=0.5;energy_transfer_eV=0.01"
            sample = Volume('sample', Box(2,2,2), sample_mat)
            world.placeChild('physicalSample', sample)

            dtt = Volume('detector', Box(10, 10, 1))
            scorerTest = PSDHelper('testObj', xnumbin=20, ynumbin=20)
            scorerTest.make(dtt)
            world.placeChild('detectorPhy', dtt, Tsf(0,0,20), 100)

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, 1e4)
    testbasic = sim.gatherHistData('testObj')
    # print(testbasic.getAccWeight(), sep=',')
    # print(list(testbasic.getWeight().sum(0)), sep=',')
    np.testing.assert_allclose(testbasic.getWeight().sum(0), expWeight)
    np.testing.assert_allclose(testbasic.getAccWeight(), accweight)
