#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Sphere
from Cinema.Prompt.scorer import VolFluenceHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting 
from testsuite import *
import numpy as np
import numpy.testing as npt


def test_simulation():
    skip_test_gidi_not_compile()
    cdata=GidiSetting()
    cdata.setEnableGidi(True)
    cdata.setGammaTransport(False)

    class MySim(Prompt):
        def __init__(self, seed=4096, **kwargs) -> None:
            super().__init__(seed, **kwargs)   

        def makeWorld(self):

            world = Volume("world", Box(400, 400, 400))

            lw = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16')
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
    sim.simulate(gun, partnum)

    spct = sim.gatherHistData('spct')
    print(spct.getWeight().sum())
    print(spct.getHit().sum())

    npt.assert_array_almost_equal(spct.getWeight().sum(), 0.0004503254359124584, decimal = 15)
