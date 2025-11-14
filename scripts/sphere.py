#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun

import numpy as np

from Cinema.Prompt.GidiSetting import GidiSetting 

cdata=GidiSetting()
cdata.setGidiThreshold(5)
cdata.setEnableGidi(True)
cdata.setEnableGidiPowerIteration(False)
cdata.setGammaTransport(False)

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def makeWorld(self):
        self.clear()
        world = Volume("world", Box(400, 400, 400))

        lw = Material("'LiquidWaterH2O_T293.6K.ncmat;density=1gcm3'") # v2, 4.630884342994241. ml, 4.630884342994241. full spec 4.691033674854935 should 4.7046
        # lw = Material('freegas::H2O/1gcm3/H_is_1.00_H1/O_is_1.00_O16') # v2, 4.5781432733636525. ml, 4.5781432733636525. full spec 4.638707241003883, should be 4.6490. gidi 3.615059805936363                                           
        # lw = Material('Ag_sg225.ncmat') # v2, 4.5781432733636525. ml, 4.5781432733636525. full spec 4.638707241003883, should be 4.6490. gidi 3.615059805936363                                           


        lw.setBiasScat(1.)
        lw.setBiasAbsp(1.)
        sphere = Volume("sphere", Sphere(0, 300), matCfg=lw)
        world.placeChild('sphere', sphere)

        VolFluenceHelper('spct', max=20, numbin=300 ).make(sphere)
        self.setWorld(world)



sim = MySim(seed=1010)
sim.makeWorld()

gun = IsotropicGun()
gun.setEnergy(1)

partnum = 1e6
# vis or production
if False:
    sim.show(gun, 1)
else:
    sim.simulate(gun, partnum)

destination = 0
spct = sim.gatherHistData('spct', dst=destination)
if sim.rank==destination:
    print('total flux', spct.getWeight().sum())
    spct.plot(show=True, log=True)
