#!/usr/bin/env python3
# Cover also the scorer list

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
import numpy as np

expected_wl = [0.0000e+00,4.0000e+00,6.4000e+01,4.8500e+02,2.1220e+03,5.8450e+03,
               1.0758e+04,1.4210e+04,1.3159e+04,9.4790e+03,5.2440e+03,2.2600e+03,
               8.5600e+02,2.7700e+02,6.2000e+01,9.0000e+00,5.0000e+00,1.0000e+00,
               0.0000e+00,0.0000e+00]

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)

    def makeWorld(self, anyUserParameters=np.zeros(2)):
        world = Volume("world", Box(200, 200, 500))

        detector = Volume("Det", Box(180, 180, 0.0001))
        scorerCfg_detpsd = "Scorer= PSD ;name =  NeutronHistMap  ;xmin=-180;xmax=180;numbin_x=10;ymin=-180;ymax=180;numbin_y=10;ptstate=SURFACE;type=XY"
        scorerCfg_detwl = "Scorer=WlSpectrum; name=detector; min=1.6; max=2.1; numbin=20"
        detector.addScorer(scorerCfg_detpsd)
        detector.addScorer(scorerCfg_detwl)

        world.placeChild("physicalbox", detector, Transformation3D(0., 0., 190))
        self.setWorld(world)


class MyGun(PythonGun):
    def __init__(self):
        super().__init__(vectorized=1)
        self.rds = [np.random.RandomState(300 + i) for i in range(4)]
    
    def sampleEnergy(self, dummy):
        self.pdata['ekin'] = self.rds[0].normal(0.0253, 0.0253 * 0.05)
    
    def sampleTime(self, dummy):
        self.pdata['t'] = self.rds[1].normal(0, 0.05)
    
    def sampleDirection(self, dummy):
        dirs = self.rds[2].rand(3)
        self.pdata['dir'] = [dirs[0] - 0.5, dirs[1] - 0.5, dirs[2]]
    
    def samplePosition(self, dummy):
        pos = self.rds[3].rand(3)
        self.pdata['pos'] = [(pos[0] - 0.5) * 20, (pos[1] - 0.5) * 20, pos[2] - 0.5]


sim = MySim(seed=1010)
sim.makeWorld()

# set gun
gun = MyGun()

# vis or production
sim.simulate(gun, 1e5)
wlhist = sim.gatherHistData("detector")
PSDhist = sim.gatherHistData("NeutronHistMap")
np.testing.assert_allclose(PSDhist.getHit().sum(), 64840.0)
np.testing.assert_allclose(wlhist.getHit(), expected_wl)