#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import SimpleThermalGun
from Cinema.Prompt.scorer import ESpectrumHelper

class MySim(Prompt):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def makeWorld(self):
        world = Volume("world", Box(50, 50, 100))
        filter = Volume("det1", Tube(0, 25, 50), 
                        matCfg=Material('''Al2O3_sg167_Corundum.ncmat;mos=2deg;
                                        dir1=@crys_hkl:0,0,6@lab:0,0,1;
                                        dir2=@crys_hkl:3,0,0@lab:1,0,0''') )
        
        world.placeChild("filter", filter, Transformation3D(0., 0., 0))

        detector = Volume("det", Box(35, 35, 0.0001))
        world.placeChild("det", detector, Transformation3D(0., 0., 60))
        ESpectrumHelper('espec').make(detector)

        self.setWorld(world)

sim = MySim()
sim.makeWorld()

gun = SimpleThermalGun()
gun.setPosition([0,0,-99])
sim.simulate(gun, 1000)

import numpy as np
np.testing.assert_allclose(sim.gatherHistData('espec').getTotalWeight(), 310., rtol=1e-15)
