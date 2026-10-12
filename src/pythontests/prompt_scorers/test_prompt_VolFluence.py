#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import VolFluenceHelper
import numpy as np


def test_simulation():
    np.set_printoptions(precision=15)
    # Since 2026-10-12 the scorer accumulates RAW track length (weight*step):
    # the volume normalization moved out of the scorer, so these pins are the
    # pre-2026-10-12 expVolumicFluence values multiplied by the detector
    # volume V = (2*10)*(2*10)*(2*1) = 800 mm^3 (Box takes half-lengths).
    # Divide this histogram by vol.getCapacity() to recover the fluence.
    expTrackLength = [0.0, 0.32296444834721066, 15.195816699626127, 25.71939917149103,
                      108.0821509562728, 718.5683459712034, 3107.759200584599, 9791.091487137539,
                      13112.774216745142, 708.438798607301]


    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            sample_mat = "physics=idealElaScat;xs_barn=5;density_per_aa3=0.5;energy_transfer_eV=0.01"
            dtt = Volume('detector', Box(10, 10, 1), sample_mat)
            scorertof = VolFluenceHelper('testObj', 1e-6, 0.5, 10, 2112, groupID=1)
            scorertof.make(dtt)

            world.placeChild('detectorPhy', dtt, scorerGroup=1)

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()
    gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"
    # gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.1;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99"
    # sim.show(gunCfg, 100)
    sim.simulate(gunCfg, 1e4)
    wlhist = sim.gatherHistData('testObj')
    print(list(wlhist.getWeight()), sep=',')
    np.testing.assert_allclose(wlhist.getWeight(), expTrackLength, rtol=1e-15)
