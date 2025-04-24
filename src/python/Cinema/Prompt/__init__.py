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
import warnings

from ..Interface import *

def has_pyvista():
    try:
        status = True
        import pyvista
    except:
        status = False
        warnings.warn("pyvista not install in current environment")
    return status

from . import solid
from . import launcher
from .launcher import *

from . import PromptFileReader
from .PromptFileReader import *

from . import Mesh
from .Mesh import *

if has_pyvista():
    from .Visualiser import *

from . import histogram
from .histogram import *

from .geo import *

from .scorer import *

# __all__ = launcher.__all__
# __all__ += PromptFileReader.__all__
# __all__ += Mesh.__all__
# __all__ += Visualiser.__all__
__all__ = histogram.__all__


# from . import Launcher, Visualiser
# from .geo import Box, Volume, Transformation3D, Tessellated
from .gun import PythonGun
from mpi4py import MPI
import numpy as np


_pt_ResourceManager_clear = importFunc('pt_ResourceManager_clear', None, [])


class Parameter:
    def __init__(self, name : str, lower, upper, promptval) -> None:
        self.name = name
        self.upper_lim = upper
        self.lower_lim = lower
        self.promptval = promptval
        if self.promptval>self.upper_lim or self.promptval<self.lower_lim:
            raise RuntimeError(f'promptval {promptval} is not in the range [{self.lower_lim},{self.upper_lim}]')
        if self.lower_lim>=self.upper_lim:
            raise RuntimeError(f'wrong parameter range [{self.lower_lim},{self.upper_lim}]')


    def get(self, trail = None):
        if trail:
            return trail.suggest_float(self.name, self.lower_lim, self.upper_lim)
        else:
            return self.promptval
        
    def __repr__(self) -> str:
        return f'Parameter "{self.name}", [{self.lower_lim},{self.upper_lim}], Prompt value {self.promptval}\n'
     
def analysisdb(study=None, name=None, target=None, storage=None ):
    if study is None:
        import optuna
        study = optuna.load_study(study_name=name, storage=storage)
    
    # Visualize the optimization history.
    from optuna.visualization import plot_contour
    from optuna.visualization import plot_intermediate_values
    from optuna.visualization import plot_optimization_history
    from optuna.visualization import plot_parallel_coordinate
    from optuna.visualization import plot_param_importances
    from optuna.visualization import plot_slice
    plot_optimization_history(study, target=target).show()

    # Visualize the learning curves of the trials.
    # plot_intermediate_values(study).show()

    # Visualize high-dimensional parameter relationships.
    plot_parallel_coordinate(study, target=target).show()

    # # Select parameters to visualize.
    # plot_parallel_coordinate(study, params=["x", "y"]).show()

    # Visualize hyperparameter relationships.
    plot_contour(study, target=target).show()

    # # Select parameters to visualize.
    # plot_contour(study, params=["x", "y"]).show()

    # Visualize individual hyperparameters.
    plot_slice(study, target=target).show()

    # # Select parameters to visualize.
    # plot_slice(study, params=["x", "y"]).show()

    # Visualize parameter importances.
    plot_param_importances(study, target=target).show()



class Optimiser:
    def __init__(self, sim, trailNeutronNum=1e5, directions= ["maximize"]) -> None:
        self.parameters = []
        self.sim = sim
        self.trailNeutronNum = trailNeutronNum
        self.directions = directions

    def addParameter(self, name, lower, upper, val=None):
        if val is None:
            val = 0.5*(lower + upper)
        self.parameters.append(Parameter(name, lower, upper, val))

    def getParameters(self, trail = None):
        l = {}
        for p in self.parameters:
            l[p.name] =p.get(trail)
        return l       

    def objective(self, trial):
        raise NotImplementedError('')

    def visInitialGeometry(self, num=100):
        self.sim.clear() 
        self.sim.makeWorld(self.getParameters())
        self.sim.show(int(num))


    def optimize(self, name, n_trials, localhost=False, storage='mysql://prompt:csnsPrompt_2023@da07.csns.ihep.ac.cn/optuna'):
        import optuna
        if localhost:
            self.study = optuna.create_study(study_name=name, 
                                    directions=self.directions
                                    )
        else:
            self.study = optuna.create_study(study_name=name, 
                                            storage=storage, 
                                            directions=self.directions,
                                            load_if_exists=True
                                            )
        

        self.study.optimize(self.objective, n_trials)

        return self.study
    
    def analysis(self):
        analysisdb(self.study)
    

    def optimize_botorch(self, name, n_trials, localhost=False, storage='mysql://prompt:csnsPrompt_2023@da07.csns.ihep.ac.cn/optuna'):
        from botorch.settings import validate_input_scaling
        import optuna

        # Show warnings from BoTorch such as unnormalized input data warnings.
        validate_input_scaling(True)

        sampler = optuna.integration.BoTorchSampler(
            n_startup_trials=int(n_trials*0.5),
        )

        if localhost:
            self.study = optuna.create_study(study_name=name, 
                                    directions=self.directions,
                                    sampler=sampler
                                    )
        else:
            self.study = optuna.create_study(
                study_name=name, 
                storage=storage, 
                directions=self.directions,
                sampler=sampler,
                load_if_exists=True
            )

        self.study.optimize(self.objective, n_trials=n_trials)

        return self.study
  
        
class Prompt:
    def __init__(self, seed : int = 4096) -> None:
        self.l = Launcher()
        self.l.setSeed(seed)

    @property
    def scorer(self):
        return Volume.scorerDict

    def makeWorld(self):
        raise NotImplementedError('') 
    
    def scorerNameConfig(self, name):
        if name in self.scorer.keys():
            newName = name + '`'
            warnings.warn(f"Dupicated scorer name {name}. Changed to {newName}")
            return newName

    def clear(self):
        _pt_ResourceManager_clear()
        self.l.worldExist = False
        Volume.scorerDict = {}
    
    def setWorld(self, world):
        self.l.setWorld(world)

     
    def show(self, gun, num : int = 0):
        self.l.showWorld(gun, num)

    def simulateSecondStack(self, num):
        return self.l.goWithSecondStack(int(num))


    def simulate(self, gun, num : int = 0, timer=True, save2Disk=False):
        if hasattr(gun, 'items'):
            self.l.setGun(gun.cfg)
            self.l.go(int(num), timer=timer, save2Dis=save2Disk)
        elif isinstance(gun, str):
            self.l.setGun(gun)
            self.l.go(int(num), timer=timer, save2Dis=save2Disk)
        else:
            from tqdm import tqdm
            if hasattr(self, 'rank'):
                if self.rank==0:
                    for i in tqdm(range(int(num)), desc = 'Progress:', unit =" events"):
                        gun.generate()
                        self.l.simOneEvent(False)
                else:
                    for i in range(int(num)):
                        gun.generate()
                        self.l.simOneEvent(False)
                
            else:
                for i in tqdm(range(int(num)), desc = 'Progress:', unit =" events"):
                    gun.generate()
                    self.l.simOneEvent(False)
    

    def gatherHistData(self, cfg, raw=False):
        if raw:
            return self.l.getHist(cfg)
        else:
            return self.l.getHist(self.scorer[cfg])
    

class PromptMPI(Prompt):
    def __init__(self, seed=4096) -> None:
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.size = self.comm.Get_size()
        super().__init__(seed+self.rank)
        

    def simulate(self, gun, num : int = 0):
        batchSize = int(num/self.size)
        if self.rank:
          super().simulate(gun, batchSize,  timer=False)
        else:
          super().simulate(gun, num-batchSize*(self.size-1))

    def show(self, gun, num : int = 0, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False):
        if self.rank==0:
            self.l.showWorld(gun, num, mergeMesh, xscale, yscale, zscale, byMat, addLegend=addLegend, geoClip=geoClip)
            self.comm.Barrier()
        else:
            self.comm.Barrier()

    def gatherHistData(self, cfg, raw=False, dst=0):
        hist = super().gatherHistData(cfg, raw)
        weight = hist.getWeight()
        hit = hist.getHit()
        ww = hist.getWW()
        print(f'Scorer {cfg} rank {self.rank}: weight {hist.getWeight().sum()}, hit {hist.getHit().sum()}')

        recvw = None
        recvh = None
        recww = None

        if self.rank == dst: # only create the buffer for rank0
            recvw = np.empty(weight.size, dtype='float')
            recvh = np.empty(hit.size, dtype='float')
            recww = np.empty(ww.size, dtype='float')
        self.comm.Reduce(weight, recvw, op = MPI.SUM, root=dst)
        self.comm.Reduce(hit, recvh, op = MPI.SUM, root=dst)
        self.comm.Reduce(ww, recww, op = MPI.SUM, root=dst)

        if self.rank == dst:
            hist.setHit(recvh)
            hist.setWeight(recvw)
            hist.setWW(recww)
        return hist
