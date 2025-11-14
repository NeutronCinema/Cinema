#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere
from Cinema.Prompt.scorer import DirectSqwHelper, MultiScatCounter
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun

import numpy as np


class MySim(PromptMPI):
    def __init__(self, mod_smp_dist, mean_ekin, seed=4096) -> None:
        super().__init__(seed)   
        self.mod_smp_dist = mod_smp_dist
        self.mean_ekin = mean_ekin

    def makeWorld(self):

        world = Volume("world", Box(2000, 2000, 21000))
        # mat = 'physics=idealElaScat;xs_barn=1;density_per_aa3=5;energy_transfer_eV=0.03'
        mat = "physics=ncrystal;nccfg='bzscope_c1_vol_77K.ncmat;bragg=0';scatter_bias=10.0;abs_bias=1.0;"
        # mat = 'bzscope_c1_vol_77K.ncmat;bragg=0'
        sample = Volume("sample", Sphere(0, 1), matCfg=mat)
        ms = MultiScatCounter()
        ms.make(sample)
        world.placeChild('samplePV', sample)

        deg = np.pi/180.

        monitor = Volume("mon", Sphere(1499.99, 1500, starttheta=1.*deg, deltatheta=178*deg ))
        # monitor = Volume("mon", Box(10,10,2))
        helper = DirectSqwHelper('sqw', self.mod_smp_dist, self.mean_ekin, [0,0,1.], [0,0,0],
                 qmin = 1e-1, qmax = 12, num_qbin = 500, 
                 ekinmin=-0.1, ekinmax=0.06,  num_ebin = 500,
                 pdg = 2112, groupID  = 0, ptstate = 'ENTRY')
        helper.make(monitor)
        helper.addScatterCounter(ms, 1)

        # world.placeChild('monPV', monitor,Transformation3D(0,1500,0).applyRotX(90))
        world.placeChild('monPV', monitor,Transformation3D(0,0,0))

        self.setWorld(world)


class MyGun(PythonGun):
    def __init__(self, mod_smp_dist, ekin ):
        super().__init__(2112)
        self.ekin = ekin
        self.mod_smp_dist = mod_smp_dist

    def samplePosition(self):
        return 0,0,-self.mod_smp_dist
    
    def sampleEnergy(self):
        if isinstance(self.ekin, list):
            r=np.random.uniform(self.ekin[0], self.ekin[1], 1)[0]
            return r
        else:
            return self.ekin

mod_smp_dist = 20000
mean_ekin = 0.0253

gun = MyGun(mod_smp_dist, mean_ekin)

sim = MySim(mod_smp_dist, mean_ekin, seed=1010)
sim.makeWorld()

# sim.show(gun, 100)

sim.simulate(gun, 1e9)
res = sim.gatherHistData('sqw')
destination = 0
if sim.rank==destination:
    # res.plot(False, log=False)
    # res.plot(True, title=f'Total Weight: {res.getAccWeight()}', log=True)
    fn = 'Si_bzscope_braggExcluded'
    plt=res.plot(title=f'{fn}', log=True)
    plt.xlabel(r'Q($\AA^{-1}$)')
    plt.ylabel(r'$\omega$(eV)')
    plt.tight_layout()
    plt.grid(False)
    plt.savefig(f'{fn}.pdf')
