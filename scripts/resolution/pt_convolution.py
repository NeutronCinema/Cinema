#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Sphere, Box
from Cinema.Prompt.scorer import ESpectrumHelper, MultiScatCounter
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.GidiSetting import GidiSetting 
import matplotlib.pyplot as plt
from Cinema.Interface import plotStyle
import numpy as np

cdata=GidiSetting()
cdata.setEnableGidi(False)
cdata.setGammaTransport(False)

class MyGun(PythonGun):
    def __init__(self, pdg, ekin):
        super().__init__(pdg)
        self.ekin = ekin

    def samplePosition(self):
        return 0,0,-100.
    
    def sampleEnergy(self):
        if isinstance(self.ekin, list):
            r=np.random.uniform(self.ekin[0],  self.ekin[1], 1)[0]
            return r
        else:
            return self.ekin

class MySim(Prompt):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def makeWorld(self, w=0.01):

        world = Volume("world", Box(200, 200, 400))

        lw = f"physics=idealElaScat;xs_barn=1;density_per_aa3=5;energy_transfer_eV={w}"
        # lw = Material('solid::CH2/1gcm3')

        monitor = Volume("mon", Box(1,1,1.e-6))
        eRange = [0., 0.2]
        binNum = (eRange[1] - eRange[0]) * 1000   #0.001 per bin
        ESpectrumHelper('incident_energy', eRange[0], eRange[1], int(binNum), groupID=1, linear=True).make(monitor)
        ESpectrumHelper('incident_energy_exit', eRange[0], eRange[1], int(binNum), groupID=2, linear=True).make(monitor)
        world.placeChild('monPV', monitor, Transformation3D(0.,0.,-50), scorerGroup=1)
        world.placeChild('monPV_exit', monitor, Transformation3D(0.,0.,190), scorerGroup=2)

        sample = Volume("sample", Box(1.e-6,1.e-6,1), matCfg=lw)
        ms = MultiScatCounter()
        ms.make(sample)
        world.placeChild('samplePV', sample)
        

        detMat = Material("freegas::He/0.0001347gcm3/He_is_He3") # Employ this (and also ABSORB pts) to boarden energy spectrum by detector efficiency
        detector = Volume("DttLV", Sphere(50, 51, 0 , 2*np.pi, starttheta=np.deg2rad(1), deltatheta=np.pi-np.deg2rad(2)))
        dttSc = ESpectrumHelper('energy_gp0', eRange[0], eRange[1], int(binNum*0.1)+1, ptstate='ENTRY', energyTransfer=True, groupID=0, linear=True)
        dttSc.make(detector)
        dttSc.addScatterCounter(ms, -1)
        world.placeChild('DttPV', detector)

        self.setWorld(world)

w_axi = []
i_value = []
sim = MySim(seed=1010)
for w in np.arange(0., 0.12, 0.04):
    sim.clear()
    sim.makeWorld(w)

    gun = MyGun(2112, [0.11, 0.12])

    if False:
        partnum = 1000
        sim.show(gun, partnum)
    else:
        partnum = 1e6
        sim.simulate(gun, partnum)

    dtt0 = sim.gatherHistData('energy_gp0')
    mon1 = sim.gatherHistData('incident_energy')
    mon2 = sim.gatherHistData('incident_energy_exit')

    print('TOTAL: ', dtt0.getHit().sum())
    w_axi.append(w)
    i_value.append(dtt0.getAccWeight())

import pt_convolution2

pt_convolution2.run()
plt.plot(w_axi, i_value, marker='o', label='Prompt simulation')
plt.grid()
plt.legend()
plt.show()
    # mon1.plot(show=False)
    # mon2.plot(show=False)
    # dtt0.plot(show=True, log=False)
    # plt.plot(dtt0.getEdges()[:-1], dtt0.getWeight(), label='@detector')
    # plt.plot(mon0.getEdges()[:-1], mon0.getWeight(), label='@monitor')
    # plt.legend()
    # plotStyle()
    # plt.show()

