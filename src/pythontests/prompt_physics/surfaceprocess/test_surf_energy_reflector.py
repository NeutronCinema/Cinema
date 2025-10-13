#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Sphere
from Cinema.Prompt.gun import PythonGun, UniModeratorGun
from Cinema.Prompt.scorer import DirectSqHelper
import numpy as np

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume

expectWl = [83.0, 105.0, 167.0, 263.0, 398.0, 576.0, 915.0, 1183.0, 1555.0, 1394.0, 1036.0, 670.0, 294.0, 66.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

class MySim(PromptMPI):
    def __init__(self, seed) -> None:
        super().__init__(seed)
        self.makeWorld()

    def makeWorld(self):
        world = Volume('world', Box(100, 100, 200))

        sample = Volume('sample', Box(50,50,1),surfaceCfg="physics=EnergyReflector;ekin=0.22;islessthan=0")
        world.placeChild('entity', sample, Transformation3D(0,0,0).applyRotX(30).applyRotY(45))

        dtt = Volume('detector', Sphere(90, 90+1e-2, ))
        sc_espec_entry = DirectSqHelper("sq@exit",0.1,5,20,90)
        sc_espec_entry.make(dtt)
        world.placeChild('dttphy', dtt, Transformation3D())

        self.setWorld(world)


windowsize = 20
class MyGun(UniModeratorGun):
    def __init__(self, src_whz=[windowsize, windowsize, -50], slit_whz=[windowsize,windowsize, 1e6], wl_mean=1, wl_range=1):
        super().__init__(src_whz, slit_whz, wl_mean, wl_range)

if __name__ == '__main__':
    np.set_printoptions(
    suppress=True,    
    precision=0      
)
    sim = MySim(12345)
    gunCfg = MyGun()
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('sq@exit')
    arr = wlhist.getHit()
    arr_list = arr.tolist()
    arr_str = ', '.join(map(str, arr_list))
    print(arr_str)
    np.testing.assert_allclose(wlhist.getHit(), expectWl)
