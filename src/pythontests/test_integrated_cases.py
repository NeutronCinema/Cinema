#!/usr/bin/env python3

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Tube,Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun
from Cinema.Prompt.GidiSetting import GidiSetting


def test_integrated_cases():
    cdata=GidiSetting()
    cdata.setGidiThreshold(5)
    cdata.setEnableGidi(True)
    cdata.setGammaTransport(False)
    cdata.setGidiPops("/home/zypan/XS/ptdata/pops.xml")
    cdata.setGidiMap("/home/zypan/XS/ptdata/all.map")

    class Simulation(PromptMPI):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):

            # material defined in NCrystal configstring
            nccfg_Al = 'Al_sg225.ncmat;inelas=0'
            mat_Al = Material(nccfg_Al)

            nccfg_H2O = 'LiquidWaterH2O_T293.6K.ncmat'
            mat_H2O = Material(nccfg_H2O)

            # volume defined with shape, size and material
            vol_shell = Volume("shellSolid",Tube(0,74,54),matCfg=mat_Al.cfg)
            vol_shellofshell = Volume("sshellSolid",Tube(0,80,80),matCfg=mat_Al.cfg)
            vol_sample = Volume("sampleSolid",Tube(0,70,50),matCfg=mat_H2O.cfg)

            vol_shell.placeChild("pv_sample", vol_sample)
            vol_shellofshell.placeChild("pv_shell", vol_shell,)
            # TOF scorer/counter, 
            # tof = TOFHelper("TOF",ptstate='ABSORB')
            # make vol capable to score neutron absorbed by real physcis channel
            # tof.make(vol)

            # coordinate transformation in simulation world
            trf = Transformation3D(0,0, 100)

            # volume representing the simulation world, 
            world = Volume("world", Box(100, 100, 210))
            # volume location and transformation in simulation world
            world.placeChild("samplePhyVol",vol_shellofshell, transf=trf)
            # assign the simulation world
            self.setWorld(world)


