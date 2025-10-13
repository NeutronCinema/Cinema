#!/usr/bin/env python3

# Regression test for gidi model

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Sphere, Tube
from Cinema.Prompt.scorer import ESpectrumHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun, SimpleThermalGun, PythonGun
from Cinema.Prompt.GidiSetting import GidiSetting 
import matplotlib.pyplot as plt
from Cinema.Interface import plotStyle
import numpy as np
from testsuite import *


CDATA=GidiSetting()
isCompiled = CDATA.isCompiled
    
# plotStyle()
def promptRun(cfg, energy, gidiThreshold = -5, popsPath = None,
              numbin_en=100, loweredge=1e-5, upperedge=30e6,
              isGammaTransport=False, partnum = 1e5, setGidi= True,
              plot=False):
    skip_test_gidi_not_compile()
    CDATA.setEnableGidi(True)
    CDATA.setGidiThreshold(gidiThreshold)
    CDATA.setEnableGidiPowerIteration(False)
    CDATA.setGammaTransport(isGammaTransport)
    if not popsPath:
        CDATA.setGidiPops(popsPath)

    numbin_mu=10


    #########################################################


    nc_bxs=80.27
    endf_fxs=20.43608

    const_neutron_mass_amu =1.00866491588
    h1_mass =               1.00782503224
    awr=h1_mass/(h1_mass+const_neutron_mass_amu)

    nc_fxs = nc_bxs*awr*awr
    endf_bxs=endf_fxs/awr/awr


    ###############################################################

    cfg_ = cfg

    class MySim(Prompt):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):
            size = 1e-6

            world = Volume("world", Tube(0, size, 1.1e50))
            lw = Material(cfg_) 
            lw.setBiasAbsp(1)
            lw.setBiasScat(1)
            media = Volume("media", Tube(0, size*0.5, 1e50), matCfg= lw)
            world.placeChild('media', media)

            ESpectrumHelper('ESpec', min=loweredge, max=upperedge, numbin=numbin_en, pdg=2112, ptstate='EXIT').make(media)
            # media.addScorer(f'Scorer=Angular;name=SofAngle;sample_pos=0,0,1;beam_dir=0,0,1;dist=-100;ptstate=EXIT;linear=yes;min=-1;max=1;numbin={numbin_mu}')
            # DepositionHelper('dep', min=loweredge, max=upperedge, numbin=numbin_en, ptstate='PROPAGATE', linear=False).make(media)
            self.setWorld(world)



    sim = MySim(seed=1010)
    sim.makeWorld()

    class MyGun(PythonGun):
        def __init__(self, pdg, ekin):
            super().__init__(pdg)
            self.ekin = ekin

        def samplePosition(self):
            return 0,0,-1.e5
        
        def sampleEnergy(self):
            if isinstance(self.ekin, list):
                r=np.random.uniform(self.ekin[0], self.ekin[1], 1)[0]
                return r
            else:
                return self.ekin


    gun = MyGun(int(2112), energy)

    # vis or production
    sim.simulate(gun, partnum)
    hist = sim.gatherHistData('ESpec')
    if plot:
        plt.figure()
        hist.plot(False,log=True)
    return hist.getAccWeight(), hist.getTotalWeight(), hist.getWeight()
