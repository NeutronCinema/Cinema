#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Sphere
from Cinema.Prompt.scorer import VolFluenceHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting 
from testsuite import *

skip_test_gidi_not_compile()
# pt_main_test()
cdata=GidiSetting()
cdata.setEnableGidi(True)
cdata.setGammaTransport(False)

class MySim(Prompt):
    def __init__(self, seed=4096, **kwargs) -> None:
        super().__init__(seed, **kwargs)   

    def makeWorld(self):

        world = Volume("world", Box(400, 400, 400))

        # lw = Material("'LiquidWaterH2O_T293.6K.ncmat;density=1gcm3'") # v2, 4.630884342994241. ml, 4.630884342994241. full spec 4.691033674854935 should 4.7046
        lw = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16') # v2, 4.5781432733636525. ml, 4.5781432733636525. full spec 4.638707241003883, should be 4.6490. gidi 3.615059805936363                                           

        lw.setBiasScat(1.)
        lw.setBiasAbsp(1.)
        sphere = Volume("sphere", Sphere(0, 300), matCfg=lw)
        world.placeChild('sphere', sphere)

        VolFluenceHelper('spct', 1e-6, 20e6, 100).make(sphere)
        self.setWorld(world)



sim = MySim(seed=1010)
sim.makeWorld()


gun = IsotropicGun()
gun.setEnergy(1)

partnum = 100
# vis or production
sim.simulate(gun, partnum)

spct = sim.gatherHistData('spct')
print(spct.getWeight().sum())
print(spct.getHit().sum())
# spct.plot(show=True, log=True)

import numpy.testing as npt
npt.assert_array_almost_equal(spct.getWeight().sum(), 0.0004503254359124584, decimal =  15)


