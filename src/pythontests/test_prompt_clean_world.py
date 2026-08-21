#!/usr/bin/env python3
# Aims to test gun and scorer change, there is no other material along the neutron rays path,
# except world default: 'freegas::H1/1e-26kgm3/H_is_1_H1'

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Sphere, Tube, Trapezoid, ArbTrapezoid
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import WlSpectrum
import numpy as np

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume


def test_simulation():
    expWl = [419.,447.,452.,477.,436.,444.,395.,386.,349.,316.,302.,290.,294.,250.,235.,199.,220.,179.,162.,143.]

    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200), 'void.ncmat')
            xy1 = np.array([-10, -10])
            xy2 = np.array([-5, 5])
            xy3 = np.array([5, 5])
            xy4 = np.array([10, -10])
            xy5 = np.array([-10, -10]) * 0.8
            xy6 = np.array([-5, 5]) * 0.8
            xy7 = np.array([5, 5]) * 0.8
            xy8 = np.array([10, -10]) * 0.8
            hz = 20

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
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, int(1e4))
    wlhist = sim.gatherHistData('WavelengthSp')
    np.testing.assert_allclose(wlhist.getHit(), expWl)
    # print(wlhist.getHit())
