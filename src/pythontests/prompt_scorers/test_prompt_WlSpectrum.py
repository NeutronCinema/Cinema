#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrumHelper
import numpy as np

expWl = [0.0, 14.0, 517.0, 1833.0, 2155.0, 1673.0, 1203.0, 777.0, 539.0, 365.0, 245.0, 168.0, 111.0, 90.0, 66.0, 60.0, 32.0, 28.0, 25.0, 16.0]

class MySim(Prompt):
    def __init__(self, seed) -> None:
        super().__init__(seed)

    def makeWorld(self):
        world = Volume('world', Box(50, 50, 200))
        
        dtt = Volume('detector', Box(10, 10, 1))
        scorerWl = WlSpectrumHelper('testObj', 0.1, 5, 20, 2112, 'ENTRY', 100, True)
        scorerWl.make(dtt)

        world.placeChild('detectorPhy', dtt, scorerGroup=100)

        self.setWorld(world)

sim = MySim(seed=4096)
sim.makeWorld()
gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
# gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
# sim.show(gunCfg, 100)
sim.simulate(gunCfg, 1e4)
wlhist = sim.gatherHistData('testObj')
np.testing.assert_allclose(wlhist.getHit(), expWl)
# print(list(wlhist.getHit()), sep=',')

