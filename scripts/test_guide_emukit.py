#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
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
from Cinema.Prompt.scorer import PSD

from Cinema.Prompt.gun import PythonGun
import numpy as np


from emukit.examples.gp_bayesian_optimization.single_objective_bayesian_optimization import GPBayesianOptimization
from emukit.core import ContinuousParameter, InformationSourceParameter, ParameterSpace
from emukit.core.initial_designs import RandomDesign
from emukit.core.loop import UserFunctionResult


class MySim(Prompt):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)

    def makeWorld(self, space=np.ones(2)*25):
        print(space, type(space))

        # define scorers
        det = PSD()
        det.cfg_name = 'apsd'
        det.cfg_xmin = -25.
        det.cfg_xmax = 25
        det.cfg_numbin_x = 20

        det.cfg_ymin = -25.
        det.cfg_ymax = 25
        det.cfg_numbin_y = 20
        self.scorer['PSD1'] = det.makeCfg()

        det.cfg_xmin=-10
        det.cfg_xmax=10
        det.cfg_ymin=-10
        det.cfg_ymax=10 
        self.scorer['PSD2'] = det.makeCfg()
      

        # Geometry
        air = "freegas::N78O22/1.225kgm3"
        worldsize = 6500.
        world = Volume("world", Box(worldsize*0.5, worldsize*0.5, worldsize*0.5))
        # world.setMaterial("freegas::N78O22/1.225e3kgm3")

        det1 = Volume("detector", Box(50, 50, 0.01) )
        det1.addScorer(self.scorer['PSD1'])

        world.placeChild('det1', det1, Transformation3D(0, 0, 1000))
        world.placeChild('guide', makeTrapezoidGuide(500., space[0], space[0], space[1], space[1], 3.), Transformation3D(0, 0, 1600))
     
        det2 = Volume("detector", Box(10, 10, 0.01))
        det2.addScorer(self.scorer['PSD2'] )
        world.placeChild('det2', det2, Transformation3D(0, 0, 2200))

        self.setWorld(world)




sim = MySim()
incident = 1e5
def target_function(X : np.ndarray) -> float:
    sim.clear()    
    sim.makeWorld(X)
    # set gun
    gunCfg = "gun=UniModeratorGun;src_w=50;src_h=50;src_z=0;slit_w=50;slit_h=50;slit_z=1100;mean_wl=10.39"
    sim.setGun(gunCfg)
    sim.simulate(incident)
    # sim.show(100)
    hist2 = sim.gatherHistData(sim.scorer['PSD2'])
    return -hist2.getWeight().sum() # it is a minimisation optimiser

space = ParameterSpace([ContinuousParameter("boxlenght1", 5, 50), ContinuousParameter("boxlenght2", 5, 50)])
design = RandomDesign(space) 
inti_size = 230
X = design.get_samples(inti_size)

Y = np.zeros([inti_size, 1])
for i in range(inti_size):
    Y[i, 0] = target_function(X[i])

bo = GPBayesianOptimization(variables_list=space.parameters, X=X, Y=Y)
bo.noiseless=False


results = None
num_iterations = 130
for _ in range(num_iterations):
    X_new = bo.get_next_points(results)
    Y_new = target_function(X_new[0])

    results = [UserFunctionResult(X_new[0], np.array([Y_new]))]
    print (X_new, Y_new)

X = bo.loop_state.X
Y = bo.loop_state.Y


print(X, Y)


## plot
import matplotlib.pyplot as plt

plt.figure()

print(f'size {X.size}')
for i, (xs, ys) in enumerate(zip(X, Y)):
    plt.plot(xs[0], -ys/incident, 'ro', markersize= 2 + 10 * (i+1.)/len(X))

plt.xlabel('Guide opening size, mm')
plt.ylabel('Neutron transmission eff.')

plt.figure()

print(f'size {X.size}')
for i, (xs, ys) in enumerate(zip(X, Y)):
    plt.plot(xs[1], -ys/incident, 'ro', markersize= 2 + 10 * (i+1.)/len(X))

plt.xlabel('Guide opening size, mm')
plt.ylabel('Neutron transmission eff.')


plt.show()


# The best paramters found: 29.5329642  11.57057061, eff (ys/incident) 26.67%
# 28.41990654 16.0491007 28.1%, 
# 26.41687317 14.3383753 30.2%, 100, 100
# 20.83001173 12.03239256 33.3%, 500, 100
# 23.85848214 12.57996356