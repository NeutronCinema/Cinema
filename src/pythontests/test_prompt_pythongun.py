#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Tube
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum, ESpectrum
import numpy as np


def test_simulation():
    expected_wl = [169.0, 175.0, 164.0, 155.0, 155.0, 173.0, 163.0, 202.0, 183.0, 183.0, 166.0, 175.0, 176.0, 175.0, 175.0, 177.0, 175.0, 160.0, 175.0, 185.0]
    expected_en = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    class MySim(PromptMPI):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):
            self.scorer['wl'] = "Scorer=WlSpectrum; name=wl; min=0.0; max=10; numbin=20;ptstate=ENTRY"
            self.scorer['en'] = "Scorer=ESpectrum; name=en; min=0.0; max=10; numbin=20;ptstate=ENTRY"

            world = Volume("world", Box(200, 200, 500))

            det1 = Volume("det1", Box(10, 10, 0.01) )
            det1.addScorer(self.scorer['wl'])
            det1.addScorer(self.scorer['en'])
            world.placeChild('det1', det1, Transformation3D(0, 0, 170))
            self.setWorld(world)

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

    gun = MyGun()
    sim.simulate(gun, 1e5)
    wlhist = sim.gatherHistData("wl")
    enhist = sim.gatherHistData("en")
    np.testing.assert_allclose(wlhist.getHit(), expected_wl)
    np.testing.assert_allclose(enhist.getHit(), expected_en)
