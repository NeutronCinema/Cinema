#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import ESpectrumHelper
from Cinema.Prompt.geo import Transformation3D as Tsf
import numpy as np


def test_simulation():
    expE = [0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 8.0, 23.0, 75.0, 287.0, 638.0, 1085.0, 1637.0, 648.0, 30.0, 0.0, 0.0, 0.0, 0.0]
    expdE = [0.0, 0.0, 0.0, 0.0, 358.0, 35.0, 0.0, 0.0]

    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            sample_mat = "physics=idealElaScat;xs_barn=5;density_per_aa3=0.5;energy_transfer_eV=0.01"
            sample = Volume('sample', Box(2,2,2), sample_mat)
            world.placeChild('physicalSample', sample)

            dtt = Volume('detector', Box(10, 10, 1))
            scorerTest1 = ESpectrumHelper('testObj', 1e-6, 10, 20, 2112, 'ENTRY', False, 100)
            scorerTest1.make(dtt)
            scorerTest2 = ESpectrumHelper('testObj2', 1e-6, 10, 8, 2112, 'ENTRY', True, 100)
            scorerTest2.make(dtt)
            world.placeChild('detectorPhy', dtt, Tsf(0,0,20), 100)

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('testObj')
    wlhist2 = sim.gatherHistData('testObj2')
    np.testing.assert_allclose(wlhist.getHit(), expE)
    np.testing.assert_allclose(wlhist2.getHit(), expdE)
    # print(list(wlhist.getHit()), sep=',')
    # print(wlhist.getHit().sum())
    # print(list(wlhist2.getHit()), sep=',')
    # print(wlhist2.getHit().sum())
