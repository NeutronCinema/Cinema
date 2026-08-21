#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2024 Prompt developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################



from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.solid import Box, Tube, Trapezoid
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.component import makeTrapezoidGuide
from Cinema.Prompt.gun import PythonGun
import numpy as np

from scipy.spatial.transform import Rotation as R


def test_simulation():
    r = R.from_quat([0, 0, np.sin(np.pi/4), np.cos(np.pi/4)])
    r.as_matrix


    class MySim(Prompt):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)

        def makeWorld(self, anyUserParameters=np.zeros(2)):
            self.scorer['wl'] = "Scorer=WlSpectrum; name=detector; min=0.0; max=10; numbin=100;ptstate=ENTRY"

            worldsize = 200.
            world = Volume("world", Box(worldsize*0.5, worldsize*0.5, worldsize*0.5))

            guide = makeTrapezoidGuide(50., 8, 8, 5, 5, m=10)

            r=Transformation3D(0, 1)
            world.placeChild('guide', guide, r.applyRotAxis(30, np.array([0,0,1])))

            det1 = Volume("detector", Box(10, 10, 0.01) )
            det1.addScorer(self.scorer['wl'])
            world.placeChild('det1', det1, Transformation3D(0, 0, 60))
            self.setWorld(world)



    sim = MySim()
    # set gun
    gunCfg = "gun=MaxwellianGun;src_w=5;src_h=5;src_z=-80;slit_w=50;slit_h=50;slit_z=100"
    sim.makeWorld()
    # vis or production
    if False:
        sim.show(gunCfg, 110)
    else:
        sim.simulate(gunCfg, 1e4)


    hist1 = sim.gatherHistData('wl')
    w=hist1.getWeight().sum()
    x=hist1.getCentre().sum()
    wx=(hist1.getWeight()*hist1.getCentre()).sum()
    print(f'{w, x, wx}')
    np.testing.assert_allclose([w, x, wx], [796.1124588280122, 500.00000000000006, 1264.0639561959943], rtol=1e-15, atol=1e-15)

    # hist1.plot(show=True)
