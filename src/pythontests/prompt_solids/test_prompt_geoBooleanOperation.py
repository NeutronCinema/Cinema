#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere,  SolidIntersection, SolidUnion, SolidSubtraction
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun, UniModeratorGun

import numpy as np

from Cinema.Prompt.GidiSetting import GidiSetting 
from testsuite import *


def test_simulation():
    skip_test_visual_check_required()

    class MySim(PromptMPI):
        def __init__(self, seed=4096, test_geo=False) -> None:
            super().__init__(seed)   
            self.test_geo = test_geo
            self.mat_chm = Material("LiquidWaterH2O_T293.6K.ncmat")
            self.mat_al = Material("Al_sg225.ncmat")
            self.chm_radius = 7.5 * 10
            self.chm_halfheight = 10 * 10 * 0.5
            self.chm_shell_radius = self.chm_radius + 4
            self.chm_shell_halfheight = self.chm_halfheight + 4
            self.prem_shell_radius = (8.5 + 0.4) * 10
            self.prem_shell_halfheight = self.chm_shell_halfheight + (20 + 10 + 8)*0.5

        def _create_chm(self):
            sol_chm = Tube(0, self.chm_radius, self.chm_halfheight)
            sol_chm_shell = Tube(0, self.chm_shell_radius, self.chm_shell_halfheight)
            vol_chm = Volume("chm_water", sol_chm, matCfg=self.mat_chm)
            vol_chm_shell = Volume("chm_shell", sol_chm_shell, matCfg=self.mat_al)
            vol_chm_shell.placeChild('P_chm_water', vol_chm)
            return vol_chm_shell

        def _create_premod(self):
            sol_premod_shell = Tube(self.chm_shell_radius+4, self.prem_shell_radius, self.prem_shell_halfheight)
            sol_premod_shell_top = Tube(0, self.prem_shell_radius, (20+4*2)*0.5)
            sol_premod_shell_bot = Tube(0, self.prem_shell_radius, (10+4*2)*0.5)
            sol_premod = SolidUnion(sol_premod_shell, sol_premod_shell_bot, 
                                    Transformation3D(z=self.prem_shell_halfheight-(10+4*2)*0.5))
            sol_premod = SolidUnion(sol_premod, sol_premod_shell_top, 
                                    Transformation3D(z=-(self.prem_shell_halfheight-(20+4*2)*0.5)))
            vol_premod = Volume("premod", sol_premod, matCfg=self.mat_al)
            return vol_premod

        def makeWorld(self):
            self.clear()
            worldsize = 500
            simboxsize = worldsize - 1
            world = Volume("world", Box(worldsize, worldsize, worldsize), "void.ncmat")
            simbox = Volume("simbox", Box(simboxsize, simboxsize, simboxsize), "void.ncmat")

            vol_chm = self._create_chm()
            vol_premod = self._create_premod()

            simbox.placeChild('PHYchm', vol_chm, Transformation3D(z=self.chm_shell_halfheight-self.chm_halfheight + 10 + 4))
            simbox.placeChild('PHYpremod', vol_premod)
            world.placeChild('PHYsimbox', simbox, Transformation3D().applyRotX(90))

            self.setWorld(world)

    size = 250
    gun = UniModeratorGun([size, size, -200], [size, size, 1e5])

    # geo under test
    sim = MySim(test_geo=True)
    sim.makeWorld()

    partnum = 1e3
    sim.show(gun, 0, byMat=1, addLegend=True, geoClip=0, mergeMesh=1)
