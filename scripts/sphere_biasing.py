#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun
import matplotlib.pyplot as plt
import numpy as np


class MySim(PromptMPI):
    def __init__(self, seed=2) -> None:
        super().__init__(seed)   

    def makeWorld(self):
        self.clear()
        world = Volume("world", Box(4000, 4000, 4000))

        lw = Material('freegas::H2O/1gcm3/H_is_1.00_H1/O_is_1.00_O16') # v2, 4.5781432733636525. ml, 4.5781432733636525. full spec 4.638707241003883, should be 4.6490. gidi 3.615059805936363                                           
        sphere = Volume("sphere", Sphere(0, 70), matCfg=lw)
        world.placeChild('sphere', sphere)

        detector1 = Volume("det1", Box(50, 50, 0.0001))
        makePSD('psd', detector1, 11, 11 )
        ESpectrumHelper('ESpec',  min=1e-5, max=10e6, numbin=100, ptstate='ENTRY').make(detector1)
        world.placeChild('det', detector1, Transformation3D(0,0,2200))

        detector2 = Volume("det2", Box(50, 50, 0.0001))
        makePSD('psd2', detector2, 11, 11 )
        ESpectrumHelper('ESpec2',  min=1e-5, max=10e6, numbin=100, ptstate='ENTRY').make(detector2)
        world.placeChild('det2', detector2, Transformation3D(0,0,-2200))

        self.setWorld(world)



sim = MySim(seed=1010)
sim.makeWorld()

gun = IsotropicGun()
gun.setEnergy(3e6)

# class MyGun(PythonGun):
#     def __init__(self, pdg, ekin):
#         super().__init__(pdg)
#         self.ekin = ekin

#     def samplePosition(self):
#         return 0,0,0
    
#     def sampleEnergy(self):
#         if isinstance(self.ekin, list):
#             r=np.random.uniform(self.ekin[0], self.ekin[1], 1)[0]
#             return r
#         else:
#             return self.ekin
# gun = MyGun(2112, 1)

# sim.show(gun, 1)

partnum = 1e5
# vis or production
if False:
    sim.show(gun, 10)
else:
    sim.simulate(gun, partnum)

destination = 0
spct = sim.gatherHistData('ESpec', dst=destination)
psd = sim.gatherHistData('psd', dst=destination)
spct2 = sim.gatherHistData('ESpec2', dst=destination)
psd2 = sim.gatherHistData('psd2', dst=destination)

if sim.rank==destination:
    # print('total flux', spct.getWeight().sum())
    spct.plot(show=False, log=True, title='biased')
    # plt.figure()
    # spct2.plot(show=False, log=True, title='analog')
    # print('total count', spct.getHit().sum(), spct.
    print('det count', psd.getHit().sum(), psd.getSdev().sum())
    psd.plot(show=True, title=f'biased {psd.getHit().sum():.0f}, w {psd.getWeight().sum():.4e}, std {psd.getSdev().sum():.4e}')
    # psd2.plot(show=True, title=f'analog {psd2.getHit().sum():.0f}, w {psd2.getWeight().sum():.4e}, std {psd2.getSdev().sum():.4e}')
