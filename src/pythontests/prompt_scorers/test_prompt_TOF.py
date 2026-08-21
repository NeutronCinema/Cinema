#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import TOFHelper
import numpy as np


def test_simulation():
    exptof = [7998.0, 1815.0, 144.0, 27.0, 8.0, 3.0, 5.0, 0.0, 0.0, 0.0]

    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            dtt = Volume('detector', Box(10, 10, 1))
            scorertof = TOFHelper('testObj', 0., 0.0005, 10, 2112, 'ENTRY',100)
            scorertof.make(dtt)

            world.placeChild('detectorPhy', dtt, scorerGroup=100)

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('testObj')
    np.testing.assert_allclose(wlhist.getHit(), exptof)
    # print(list(wlhist.getHit()), sep=',')
