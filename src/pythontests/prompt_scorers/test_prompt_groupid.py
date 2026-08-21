#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Tube
from Cinema.Prompt.scorer import ESpectrumHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting 
import numpy as np


def test_simulation():
    cdata=GidiSetting()
    cdata.setEnableGidi(False)
    cdata.setGammaTransport(False)

    class MySim(Prompt):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):

            world = Volume("world", Box(400, 400, 400))

            lw = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16') 

            lw.setBiasScat(1.)
            lw.setBiasAbsp(1.)
            sample = Volume("sample", Box(1,1,1), matCfg=lw)
            world.placeChild('sphere', sample)

            detector = Volume("DttLV", Box(100,100,1))
            ESpectrumHelper('energy_gp0', 1e-6, 20e6, 100, groupID=0).make(detector)
            ESpectrumHelper('energy_gp1', 1e-6, 20e6, 100, groupID=1).make(detector)
            ESpectrumHelper('energy_gp2', 1e-6, 20e6, 100, groupID=2).make(detector)
            world.placeChild('Dtt1', detector, Transformation3D(0,-200*1/np.sqrt(2),200*1/np.sqrt(2)).applyRotX(45), scorerGroup=1)
            world.placeChild('Dtt2', detector, Transformation3D(0,200*1/np.sqrt(2),200*1/np.sqrt(2)).applyRotX(-45), scorerGroup=2)
            self.setWorld(world)

    sim = MySim(seed=1010)
    sim.makeWorld()

    gun = IsotropicGun()
    gun.setEnergy(1)

    if 0:
        partnum = 100
        sim.show(gun, partnum)
    else:
        partnum = 1e6
        sim.simulate(gun, partnum)

    dtt0 = sim.gatherHistData('energy_gp0')
    dtt1 = sim.gatherHistData('energy_gp1')
    dtt2 = sim.gatherHistData('energy_gp2')
    print('TOTAL: ', dtt0.getHit().sum())
    print('GROUP1: ', dtt1.getHit().sum())
    print('GROUP2: ', dtt2.getHit().sum())
    print([dtt0.getHit().sum(),dtt1.getHit().sum(),dtt2.getHit().sum()])

    expected = [128756.0, 64291.0, 64465.0]
    np.testing.assert_allclose([dtt0.getHit().sum(),dtt1.getHit().sum(),dtt2.getHit().sum()], expected)
    from unittest import TestCase
    t = TestCase()
    t.assertTrue(dtt0.getHit().sum()==(dtt1.getHit().sum()+dtt2.getHit().sum()))
