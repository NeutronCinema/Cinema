#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, PolyCone
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum
import numpy as np

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume


def test_simulation():
    expectWl = [413., 400., 436., 427., 404., 393., 370., 395., 328., 306., 271.,
           267., 254., 228., 212., 169., 182., 186., 152., 147.]



    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))
            vec_z = np.array([0,5,10])
            vec_rmin = np.array([2, 2, 4])
            vec_rmax = np.array([5, 7, 5])
            sphi = 0
            dphi = 360

            sample = Volume('sample', PolyCone(vec_z, vec_rmin, vec_rmax, sphi, dphi), 'Al_sg225.ncmat')
            world.placeChild('entity', sample, Transformation3D(0,2,0).applyRotX(90))

            dtt = Volume('detector', Box(10, 10, 1))
            scorerWl = WlSpectrum()
            scorerWl.cfg_name = 'WavelengthSp'
            scorerWl.cfg_min = 1
            scorerWl.cfg_max = 2
            scorerWl.cfg_numbin = 20
            dtt.addScorer(scorerWl)
            world.placeChild('detectorPhy', dtt, Transformation3D(0,0,90))

            self.setWorld(world)



    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.001;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    VIZ = False
    if VIZ:
        sim.show(gunCfg, 100)
    else:
        sim.simulate(gunCfg, 1e4)
        wlhist = sim.gatherHistData('WavelengthSp')
        print(wlhist.getHit())
        np.testing.assert_allclose(wlhist.getHit(), expectWl)
