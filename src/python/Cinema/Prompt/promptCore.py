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

import numpy as np
from .launcher import Launcher
from .geo import Volume
from ..Interface import importFunc
import warnings
from mpi4py import MPI

_pt_ResourceManager_clear = importFunc('pt_ResourceManager_clear', None, [])
__all__ = ["Prompt", "PromptMPI"]

class Prompt:
    """
    Core class for particle transport and ray-tracing simulation with Monte Carlo method.
    
    This class encapsulates the methods to visualize the simulation, simulate in production mode, 
    and collect data. 

    Derived from Prompt class to run simulations. 
    Or to inherit its child class PromptMPI to run in parallel.
    
    Attributes:
        _l (Launcher): Simulator launcher instance, responsible for calling the underlying physics engine
        _seed (int): Random seed for reproducible simulations
        world: Geometry world object (only used when isSubmodel is True)
    
    Examples:
        >>> prompt = Prompt(seed=1234)
        >>> prompt.makeWorld()  # Must be implemented in subclass
        >>> prompt.simulate(gun_config, num_events=1000)
    """
    
    def __init__(self, seed: int = 4096) -> None:
        """
        Initialize a Prompt instance.
        
        Args:
            seed: Random seed, defaults to 4096
        """
        self._l = Launcher()
        self._seed = seed

    @property
    def seed(self):
        """Random seed of the simulation (read-only property)."""
        return self._seed

    @property
    def l(self):
        """Launcher instance (read-only property)."""
        return self._l
    
    @property
    def scorer(self):
        """Get the dictionary of all current scorers (read-only property)."""
        return Volume.scorer_dict

    def makeWorld(self):
        """
        Build the geometry world (abstract method, must be implemented in subclass).
        
        Raises:
            NotImplementedError: Must be implemented in subclass
        """
        raise NotImplementedError('') 
    
    def scorerNameConfig(self, name):
        """
        Configure scorer name, handling duplicate names.
        
        Args:
            name: Original scorer name
            
        Returns:
            str: Processed scorer name (adds '`' suffix if duplicate)
        """
        if name in self.scorer.keys():
            newName = name + '`'
            warnings.warn(f"Duplicated scorer name {name}. Changed to {newName}")
            return newName

    def clear(self):
        """
        Clean up resources and reset simulation environment.
        
        Clears resource manager, resets world existence flag, and scorer dictionary.
        """
        _pt_ResourceManager_clear()
        self.l.worldExist = False
        Volume.scorer_dict = {}
    
    def setWorld(self, world):
        """
        Set the geometry world.
        
        Args:
            world: Geometry world object
            
        Note:
            sets world through Launcher and applies random seed.
        """
        self.l.setSeed(self.seed)
        self.l.setWorld(world)

    def show(self, gun, num: int = 0):
        """
        Display geometries and particle trajectories.
        
        Args:
            gun: Particle gun configuration or object
            num: Number of particles to display, defaults to 0 (no trajectory, only show geometries)
        """
        self.l.showWorld(gun, num)

    def simulateSecondStack(self, num):
        """
        Simulate using second stack.
        
        Args:
            num: Number of simulation events
            
        Returns:
            Simulation result
        """
        return self.l.goWithSecondStack(int(num))

    def simulate(self, gun, num: int = 0, timer=True, save2Disk=False):
        """
        Execute particle transport/ray-tracing simulation.
        
        Args:
            gun: Particle gun, an instance of class Gun
            num: Number of simulation events, defaults to 0
            timer: Whether to enable timer, defaults to True
            save2Disk: Whether to save to disk, defaults to False
        """
        if hasattr(gun, 'items'):
            self.l.setGun(gun.cfg)
            self.l.go(int(num), timer=timer, save2Dis=save2Disk)
        elif isinstance(gun, str):
            self.l.setGun(gun)
            self.l.go(int(num), timer=timer, save2Dis=save2Disk)
        else:
            # it is a python gun
            from tqdm import tqdm
            show_progress = not hasattr(self, 'rank') or self.rank == 0
            
            # Calculate actual number of iterations based on vectorized size
            vectorized_size = getattr(gun, 'vectorized', 1)
            actual_iterations = int(num) // vectorized_size
            remaining_particles = int(num) % vectorized_size
            
            # Create progress bar with batch size information
            desc = f'Progress (batch_size={vectorized_size}):'
            event_range = tqdm(range(actual_iterations), desc=desc, unit=" batches") if show_progress else range(actual_iterations)
        
            for _ in event_range:
                gun.generate()
                self.l.simOneEvent(False)
            
            # Handle remaining particles if any
            if remaining_particles > 0:
                # Temporarily set vectorized to remaining particles
                original_vectorized = gun.vectorized
                gun.vectorized = remaining_particles
                gun.generate()
                self.l.simOneEvent(False)
                # Restore original vectorized size
                gun.vectorized = original_vectorized

    def gatherHistData(self, cfg, raw=False):
        """
        Collect histogram data from scorer.
        
        Args:
            cfg: Scorer configuration or name
            raw: Whether to return raw data, defaults to False (uses scorer dictionary)
            
        Returns:
            Hist: Histogram data object
        """
        if raw:
            return self.l.getHist(cfg)
        else:
            return self.l.getHist(self.scorer[cfg])

    def save_all_scorers(self, savepdf=False):
        """
        Save data for all scorers.
        
        Args:
            savepdf: Whether to also save PDF format images, defaults to False
            
        Note:
            Only executed on rank 0 process, other processes skip.
        """
        for sc in self.scorer.values():
            sc_value = self.gatherHistData(sc)
            if savepdf:
                if self.rank == 0:
                    sc_value.savefig(f"{sc}.pdf", log=False)
            if self.rank == 0:
                sc_value.save(f"{sc}.h5")
                
class PromptMPI(Prompt):
    """
    MPI parallel augmented Prompt.

    Auto-ranking of processes and auto-reduce of histogram data.
    
    Attributes:
        comm: MPI communicator
        rank (int): Current process MPI rank
        size (int): Total number of MPI processes
    """
    
    def __init__(self, seed=4096) -> None:
        """
        Initialize MPI version of Prompt instance.
        
        Args:
            seed: Initial random seed, each process gets different seed (seed + rank)
        """
        self._comm = MPI.COMM_WORLD
        self._rank = self._comm.Get_rank()
        self._size = self._comm.Get_size()
        super().__init__(seed + self._rank)

    @property
    def comm(self):
        return self._comm
    
    @property
    def rank(self):
        return self._rank

    @property
    def size(self):
        return self._size

    def simulate(self, gun, num: int = 0):
        """
        MPI version of simulation method, automatically distributes events to processes.
        
        Args:
            gun: Particle gun, an instance of class Gun
            num: Total number of events
            
        """
        batchSize = int(num / self.size)
        if self.rank:
            super().simulate(gun, batchSize, timer=False)
        else:
            super().simulate(gun, num - batchSize * (self.size - 1))

    def show(self, gun, num: int = 0, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False):
        """
        MPI version of display method, only shows on rank 0 process.
        
        Args:
            gun: Particle gun configuration
            num: Number of particles to display
            mergeMesh: Whether to merge meshes
            xscale, yscale, zscale: Coordinate scaling factors
            byMat: color by material
            addLegend: Add legend
            geoClip: Geometry clipping
        """
        if self.rank == 0:
            self.l.showWorld(gun, num, mergeMesh, xscale, yscale, zscale, byMat, addLegend=addLegend, geoClip=geoClip)
            self.comm.Barrier()
        else:
            self.comm.Barrier()

    def gatherHistData(self, cfg, raw=False, dst=0):
        """
        MPI version of data collection method, aggregates data from all processes to target process.
        
        Args:
            cfg: Scorer configuration
            raw: Whether to use raw configuration
            dst: Target process rank, defaults to 0 (master process)
            
        Returns:
            Hist: Aggregated histogram data
        """
        hist = super().gatherHistData(cfg, raw)
        weight = hist.getWeight()
        hit = hist.getHit()
        ww = hist.getWW()
        print(f'Scorer {cfg} rank {self.rank}: weight {hist.getWeight().sum()}, hit {hist.getHit().sum()}')

        recvw = None
        recvh = None
        recww = None

        if self.rank == dst:  # only create the buffer for rank0
            recvw = np.empty(weight.size, dtype='float')
            recvh = np.empty(hit.size, dtype='float')
            recww = np.empty(ww.size, dtype='float')
        self.comm.Reduce(weight, recvw, op=MPI.SUM, root=dst)
        self.comm.Reduce(hit, recvh, op=MPI.SUM, root=dst)
        self.comm.Reduce(ww, recww, op=MPI.SUM, root=dst)

        if self.rank == dst:
            hist.setHit(recvh)
            hist.setWeight(recvw)
            hist.setWW(recww)
        return hist