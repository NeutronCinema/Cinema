#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Ellipsoid
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper
from Cinema.Prompt.gun import PythonGun
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.component import makeTrapezoidGuide
from Cinema.Prompt.gun import UniModeratorGun

import numpy as np

para_half_length = 1000
para_source_location = -2000

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def makeWorld(self):
        universe = Material('freegas::H1/1e-26kgm3')
        universe.setBiasScat(1.)
        universe.setBiasAbsp(1.)

        world = Volume("world", Box(200, 200, 2100), matCfg=universe)

        detector1 = Volume("det1", Box(40, 40, 0.0001))
        makePSD('psd1', detector1, 20, 20 )
        world.placeChild("det", detector1, Transformation3D(0., 0., para_source_location +1000))

        detector2 = Volume("det2", Box(40, 40, 0.0001))
        makePSD('psd2', detector2, 20, 20 )
        world.placeChild("det2", detector2, Transformation3D(0., 0., para_half_length + 200))

        ESpectrumHelper('espec').make(detector2)
        WlSpectrumHelper('wlspec').make(detector2)
        TOFHelper('tof').make(detector2)

        # guide = makeTrapezoidGuide(500, 25,25,25,25, 1.0, 10)
        wallMat = 'solid::Cd/8.65gcm3'
        guideWall = Volume('guideWall', Box(100, 100., para_half_length, ), matCfg=wallMat)
        mirror = Mirror(10)
        guide = Volume('guideEllipsoid', Ellipsoid(50, 50, 1200, -para_half_length, para_half_length), surfaceCfg=mirror.cfg)
        guideWall.placeChild("guide", guide)
        world.placeChild("guideWall", guideWall)

        self.setWorld(world)



sim = MySim(seed=1010)
sim.makeWorld()


gun = UniModeratorGun()
gun.setWlMean(3.39)
gun.setWlRange(0.3)
gun.setSlit([50,50,para_source_location+500])
gun.setSource([50,50,para_source_location])

destination = 0
psd1 = sim.gatherHistData('psd1', dst=destination)
psd2 = sim.gatherHistData('psd2', dst=destination)
wlspec = sim.gatherHistData('wlspec', dst=destination)

# vis or production
if False:
    sim.show(gun, 10)
    if sim.rank==destination:
        psd1.plot(show=False, log=False, title='GUIDE-')
        psd2.plot(show=True, log=False, title='GUIDE+')
else:
    sim.simulate(gun, 1e5)
    print(list(psd2.getWeight().sum(0)), sep=',')
    expected_value = [0.0, 0.0, 19.0, 99.0, 138.0, 192.0, 207.0, 206.0, 217.0, 231.0, 234.0, 191.0, 224.0, 181.0, 200.0, 158.0, 92.0, 11.0, 0.0, 0.0]
    np.testing.assert_allclose(psd2.getWeight().sum(0), expected_value)
