#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube
from Cinema.Prompt.scorer import ESpectrumHelper,MultiScatCounter, WlSpectrumHelper, TOFHelper, VolFluenceHelper, PSDHelper, DirectSqwHelper,DirectSqHelper, KillMCPLHelper
from Cinema.Prompt.gun import PythonGun, SimpleThermalGun, MaxwellianGun
from Cinema.Prompt.histogram import wl2ekin
from Cinema.Prompt.physics import Material, Mirror

import matplotlib.pyplot as plt
import numpy as np

# >> parameters
## >> distance to moderator (mm)
slit_A1 =                7500
monitor2 =               10884
slit_A2 =                11231
slit_A3_short =	         12675
slit_A3_long =	         12931
sample_changer =         13000
monitor3 =               13485
window =                 13635
main_detector =          15200 / 18200


mod_sam_dist = 12000
gun_pos = np.array([0,0,-mod_sam_dist])
sam_pos = np.array([0,0,0])
det_radius_mm = 400.
beamstop_radius_mm = .001
det_pos = 6000.

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)  

    def makeWorld(self, wl, t, detpos):
        # matCfg_sample = Material('LiquidWaterH2O_T293.6K.ncmat')
        # matCfg_sample = Material('Al2O3_sg167_Corundum.ncmat')
        # matCfg_sample = Material('PTWaterH2O_T293.6K.ncmat')

        # matCfg_sample = Material('PTHeavyWater_T293.6K.ncmat;ucnmode=refine:0.01eV')
        # matCfg_sample = Material('PTHeavyWater_T293.6K.ncmat')

        # matCfg_sample = Material('LiquidHeavyWaterD2O_T293.6K.ncmat')V_sg229.ncmat
        matCfg_sample = Material('nanodiamond.ncmat')
        matCfg_sample.setBiasScat(2.0)
       
        world = Volume("world", Box(10000, 10000, 25000))
        sample = Volume('sample', Box(10, 10, t), matCfg = matCfg_sample)
        detector = Volume("det", Tube(beamstop_radius_mm, det_radius_mm, 0.0001))
        ms = MultiScatCounter()
        ms.make(sample)
        world.placeChild("sample", sample, Transformation3D(0., 0., 0))
        world.placeChild("det", detector, Transformation3D(0., 0., det_pos))

        helper = PSDHelper('psd', -det_radius_mm, det_radius_mm, 100,  -det_radius_mm, det_radius_mm, 100)
        helper.make(detector)
        helper.addScatterCounter(ms, 1)

        helper2 = PSDHelper('psd2', -det_radius_mm, det_radius_mm, 100,  -det_radius_mm, det_radius_mm, 100)
        helper2.make(detector)

        ESpectrumHelper('espec').make(detector)
        WlSpectrumHelper('wlspec').make(detector)
        TOFHelper('tof', max=50e-3).make(detector)
        DirectSqwHelper('sqw', mod_sam_dist, wl2ekin(wl), sample_position=sam_pos, qmin=1e-1, 
                        qmax=5, num_qbin=100, ekinmin=-0.1, ekinmax=0.1, num_ebin=110 ).make(detector)
        helpersqw = DirectSqwHelper('sqw_s', mod_sam_dist, wl2ekin(wl), sample_position=sam_pos, qmin=1e-3, 
                        qmax=.1, num_qbin=20, ekinmin=-.01, ekinmax=.01, num_ebin=101, logx=True )
        helpersqw.linear=False
        helpersqw.make(detector)

        helperSq = DirectSqHelper('sq', qmin=2e-3, qmax=0.1,
                                  numbin=50, distanceMS=mod_sam_dist, 
                                  linear=False)
        helperSq.make(detector)
        # self.kill = KillMCPLHelper('part_gen', 2112)
        # self.kill.make(detector)

        self.setWorld(world)

sim = MySim(seed=1010)

def sans_run(wl, n, t, det_pos, divergence, pyGun=True, sim=sim):

    class MyGun(PythonGun):
        def __init__(self, pdg):
            super().__init__(pdg)

        def sampleEnergy(self):
            return wl2ekin(wl)

        def samplePosition(self):
            return np.array(gun_pos)
        
        def sampleDirection(self):
            x = np.random.random() * divergence / mod_sam_dist
            y = np.random.random() * divergence / mod_sam_dist
            return np.array([x, y, 1])

    sim.makeWorld(wl,t,detpos=det_pos)

    usePythonGun=pyGun

    if usePythonGun:
        gun = MyGun(2112)
    else:
        gun = SimpleThermalGun()
        gun.setPosition(gun_pos) 
        gun.setDirection([0, 0, 1])
        gun.setWavelength(wl)

# vis or production
    if False:
        sim.show(gun, 100)
    else:
        sim.simulate(gun, n)
    sqw = sim.gatherHistData('sqw')
    sqw_s = sim.gatherHistData('sqw_s')
    sq = sim.gatherHistData('sq')

    psd = sim.gatherHistData('psd') # 1 scatter
    psd2 = sim.gatherHistData('psd2') # all
    espec = sim.gatherHistData('espec')
    wlspec = sim.gatherHistData('wlspec')
    tof = sim.gatherHistData('tof')
    all = psd2.getAccWeight()
    signal = psd.getAccWeight()
    res = signal
    return sim, sqw_s, sq


if __name__ == "__main__":
    class MyGun(PythonGun):
        def __init__(self, pdg):
            super().__init__(pdg)

        def sampleEnergy(self):
            wl = np.random.random() * 3 + 1
            return wl2ekin(wl)

        def samplePosition(self):
            return np.array(gun_pos)
        
        def sampleDirection(self):
            return np.array([0, 0, 1])
    wl = 1
    t = 10
    numNeutron = 1e8
    usePythonGun = True
    sim.makeWorld(wl,t,detpos=det_pos)
    if usePythonGun:
        gun = MyGun(2112)
    else:
        gun = SimpleThermalGun()
        gun.setPosition(gun_pos) 
        gun.setDirection([0, 0, 1])
        gun.setWavelength(wl)
    if False:
        sim.show(gun, 100)
    else:
        sim.simulate(gun, numNeutron)
    sqw = sim.gatherHistData('sqw')
    sqw_s = sim.gatherHistData('sqw_s')

    psd = sim.gatherHistData('psd') # 1 scatter
    psd2 = sim.gatherHistData('psd2') # all
    espec = sim.gatherHistData('espec')
    wlspec = sim.gatherHistData('wlspec')
    tof = sim.gatherHistData('tof')
    all = psd2.getAccWeight()
    signal = psd.getAccWeight()
    if sim.rank==0: 
    #     psd.save('psd.h5')
    #     espec.save('espec.h5')
    #     wlspec.save('wlspec.h5')
    #     tof.save('tof.h5')
    #     sqw.save('sqw.h5')
    #     sqw_s.save('sqw_s.h5')
        sq = sqw.getWeight().sum(1)
        q = sqw.getCentre()[0]
        fig = plt.figure(0)
        plt.plot(q,sq)
        fig.savefig('sq.pdf')
        sqw.savefig('sqw.pdf', log=True)


        # psd.plot(show=False)
        # sqw.plot(show=False, dynrange=1e-10)
        # sqw_s.plot(show=False, dynrange=1e-10, logx=True)
        # plt.figure()
        # espec.plot(show=False, log=True)
        # plt.figure()
        # wlspec.plot(show=False,  log=[False, True])
        # plt.figure()
        # tof.plot(show=True)