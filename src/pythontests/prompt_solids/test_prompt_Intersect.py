#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere, SolidIntersection, SolidUnion, SolidSubtraction
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper
from Cinema.Prompt.histogram import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun

import numpy as np

from Cinema.Prompt.GidiSetting import GidiSetting 
from testsuite import skip_test_gidi_not_compile

skip_test_gidi_not_compile()
cdata=GidiSetting()
cdata.setGidiThreshold(5)
cdata.setEnableGidi(True)
cdata.setEnableGidiPowerIteration(False)
cdata.setGammaTransport(False)

class MySim(Prompt):
    def __init__(self, seed=4096, test_geo=False) -> None:
        super().__init__(seed)   
        self.test_geo = test_geo

    def makeWorld(self):
        self.clear()
        world = Volume("world", Box(400, 400, 400))

        lw = Material("'LiquidWaterH2O_T293.6K.ncmat;density=1gcm3'") 
        if self.test_geo:
            ssphere = Sphere(0, 300)
            sbox = Box(100, 100, 100)
            solid = SolidIntersection(ssphere, sbox, Transformation3D(0,0,0,0,0,0))
        else:
            solid = Box(100, 100, 100)     
        
        vwater = Volume("water", solid, matCfg=lw)
        world.placeChild('water', vwater)

        VolFluenceHelper('spct', max=20, numbin=300 ).make(vwater)
        self.setWorld(world)

gun = IsotropicGun()
gun.setEnergy(1)

# geo under test
sim = MySim(test_geo=True)
sim.makeWorld()

partnum = 1e3
sim.simulate(gun, partnum)
spct = sim.gatherHistData('spct')
sum1 = spct.getWeight().sum()
np.testing.assert_allclose(sum1, 0.05853522444914256)

# geo reference
sim.clear()
sim.test_geo=False
sim.makeWorld()

sim.simulate(gun, partnum)
spct = sim.gatherHistData('spct')
sumref = spct.getWeight().sum()
np.testing.assert_allclose(sumref, 0.06053628305891873)

print(sum1, sumref)

