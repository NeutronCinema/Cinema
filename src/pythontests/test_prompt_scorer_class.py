#!/usr/bin/env python3
# Cover also the scorer list

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import PSD, WlSpectrum, ESpectrum, VolFluence, TOF
import numpy as np
import pprint

expected_wl = [0.0000e+00,4.0000e+00,6.4000e+01,4.8500e+02,2.1220e+03,5.8450e+03,
               1.0758e+04,1.4210e+04,1.3159e+04,9.4790e+03,5.2440e+03,2.2600e+03,
               8.5600e+02,2.7700e+02,6.2000e+01,9.0000e+00,5.0000e+00,1.0000e+00,
               0.0000e+00,0.0000e+00]

expected_dict = {'ESpectrum': 'Scorer=ESpectrum;name=ESpectrum;scoreTransfer=0;min=1e-05;max=0.25;numbin=100;ptstate=ENTRY;',
 'PSDMap': 'Scorer=PSD;name=PSDMap;xmin=-180;xmax=180;numbin_x=10;ymin=-180;ymax=180;numbin_y=10;ptstate=ENTRY;type=XZ;',
 'TOF': 'Scorer=TOF;name=TOF;min=0.0025;max=0.008;numbin=100;ptstate=ENTRY;',
 'VolFluence': 'Scorer=VolFluence;name=VolFluence;min=0;max=1;numbin=100;ptstate=ENTRY;linear=yes;',
 'WavelengthSp': 'Scorer=WlSpectrum;name=WavelengthSp;min=1.6;max=2.1;numbin=20;ptstate=ENTRY;'}

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)

    def makeWorld(self, anyUserParameters=np.zeros(2)):
        world = Volume("world", Box(200, 200, 500))

        detector = Volume("Det", Box(180, 180, 0.0001))
        
        scorerPSD = PSD()
        scorerPSD.cfg_name = 'PSDMap'
        scorerPSD.cfg_xmin = -180
        scorerPSD.cfg_xmax = 180
        scorerPSD.cfg_numbin_x = 10
        scorerPSD.cfg_ymin = -180
        scorerPSD.cfg_ymax = 180
        scorerPSD.cfg_numbin_y = 10

        scorerWl = WlSpectrum()
        scorerWl.cfg_name = 'WavelengthSp'
        scorerWl.cfg_min = 1.6
        scorerWl.cfg_max = 2.1
        scorerWl.cfg_numbin = 20

        scorerEn = ESpectrum()
        scorerTOF = TOF()
        scorerFluence = VolFluence()

        detector.addScorer(scorerPSD)
        detector.addScorer(scorerWl)
        detector.addScorer(scorerEn)
        detector.addScorer(scorerTOF)
        detector.addScorer(scorerFluence)

        world.placeChild("physicalbox", detector, Transformation3D(0., 0., 190))
        self.l.setWorld(world)


class MyGun(PythonGun):
    def __init__(self):
        super().__init__()
        self.rds = [np.random.RandomState(300 + i) for i in range(4)]
    
    def sampleEnergy(self, dummy):
        self.pdata['ekin'] = self.rds[0].normal(0.0253, 0.0253 * 0.05)
    
    def sampleTime(self, dummy):
        self.pdata['t'] =  self.rds[1].normal(0, 0.05)
    
    def sampleDirection(self, dummy):
        dirs = self.rds[2].rand(3)
        self.pdata['dir'] = [ dirs[0] - 0.5, dirs[1] - 0.5, dirs[2]]
    
    def samplePosition(self, dummy):
        pos = self.rds[3].rand(3)
        self.pdata['pos'] = [(pos[0] - 0.5) * 20, (pos[1] - 0.5) * 20, pos[2] - 0.5]


sim = MySim(seed=1010)
sim.makeWorld()

# set gun
gun = MyGun()

# vis or production
sim.simulate(gun, 1e5)
wlhist = sim.gatherHistData("WavelengthSp")
PSDhist = sim.gatherHistData("PSDMap")
print(sim.scorer, expected_dict)
np.testing.assert_equal(sim.scorer, expected_dict)
np.testing.assert_allclose(PSDhist.getHit().sum(), 64840.0)
np.testing.assert_allclose(wlhist.getHit(), expected_wl)

