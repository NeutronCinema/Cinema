#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, MCPLOutHelper
from Cinema.Prompt.gun import PythonGun
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.component import makeTrapezoidGuide
from Cinema.Prompt.gun import UniModeratorGun
from Cinema.convertor import ekin2wl

import numpy as np

TOTALLENGTH = 2000

class MySim(PromptMPI):
    def __init__(self, seed=4096, gap_ratio = 0.001, total_length = TOTALLENGTH) -> None:
        super().__init__(seed)   
        self.makeWorld(gap_ratio, total_length)

    def makeWorld(self, gap_ratio, total_length):
        universe = Material('freegas::H1/1e-26kgm3')
        universe.setBiasScat(1.)
        universe.setBiasAbsp(1.)
        
        world = Volume("world", Box(500, 500, total_length * 1.5), )

        detector1 = Volume("det1", Box(25, 25, 0.0001))
        makePSD('psd1', detector1, 20, 20 )
        world.placeChild("det", detector1, Transformation3D(0., 0., -(total_length+10)))
        
        alwindow = Volume("alwindow", Box(35, 35, 1))
        world.placeChild("alwindow", alwindow, Transformation3D(0., 0., (total_length+1)))
        
        detector2 = Volume("det2", Box(35, 35, 0.0001))
        makePSD('psd2', detector2, 20, 20 )
        MCPLOutHelper('mcplout',compress=False).make(detector2)
        world.placeChild("det2", detector2, Transformation3D(0., 0., (total_length+10)))

        section_number = 21
        component_length = total_length / section_number
        sec_mirror_length = component_length * (1-gap_ratio)
        sec_gap_length = component_length * gap_ratio

        comp = Volume("component", Box(50, 50, component_length), "void.ncmat")
        sec_guide = makeTrapezoidGuide(sec_mirror_length, 25,25,25,25, 3, 30, "Al_sg225.ncmat")
        sec_gap = makeTrapezoidGuide(sec_gap_length, 25,25,25,25, 0, 30, "Al_sg225.ncmat")
        comp.placeChild("guide", sec_guide, Transformation3D(0., 0., -sec_gap_length))
        comp.placeChild("gap", sec_gap, Transformation3D(0., 0., sec_mirror_length))
        for i in range(section_number):
            i = i - (section_number // 2)
            world.placeChild(f"component_{i}", comp, Transformation3D(0., 0., i * component_length * 2))

        self.setWorld(world)



sim = MySim(seed=1010)


gun = UniModeratorGun()
wl = 2.25
gun.setWlMean(wl)
gun.setWlRange(0.5)
gun.setSlit([50,50,-TOTALLENGTH+10])
gun.setSource([50,50,-TOTALLENGTH*1.4])


# vis or production
if False:
    sim.show(gun, 100, zscale=0.1)
else:
    sim.simulate(gun, 1e8)

# destination = 0
# psd1 = sim.gatherHistData('psd1', dst=destination)
# psd2 = sim.gatherHistData('psd2', dst=destination)
# wlspec = sim.gatherHistData('wlspec', dst=destination)
# if sim.rank==destination:
#     psd1.plot(show=True, log=False)
#     psd2.plot(show=True, log=False)
#     wlspec.plot(show=True, log=False)
