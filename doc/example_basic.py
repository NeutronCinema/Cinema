#!/usr/bin/env python3

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class Simulation(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def makeWorld(self):

        # material defined in NCrystal configstring
        nccfg = 'Ge_sg227.ncmat;mos=0.267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'
        mat = Material(nccfg)

        # volume defined with shape, size and material
        vol = Volume("sampleSolid",Box(10,10,1),matCfg=mat.cfg)

        # TOF scorer/counter, 
        tof = TOFHelper("TOF",ptstate='ABSORB')
        # make vol capable to score neutron absorbed by real physcis channel
        tof.make(vol)

        # coordinate transformation in simulation world
        trf = Transformation3D(0,0, 100).applyRotX(45)

        # volume representing the simulation world, 
        world = Volume("world", Box(50, 50, 210))
        # volume location and transformation in simulation world
        world.placeChild("samplePhyVol",vol, transf=trf)
        # assign the simulation world
        self.setWorld(world)

if __name__ == "__main__":
    # gun, beamline
    gun = UniModeratorGun()
    gun.setSource([10,10,-200])
    gun.setSlit([5,5,-20])

    # initialize
    sim = Simulation()
    sim.makeWorld()

    # to visualize
    sim.show(gun,100)
    # or to run in production
    # sim.simulate(gun,1e7)