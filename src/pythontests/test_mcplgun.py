#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper
from Cinema.Prompt.gun import PythonGun
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.component import makeTrapezoidGuide
from Cinema.Prompt.gun import UniModeratorGun, MCPLGun

import numpy as np
from Cinema.Prompt.files import MCPLParticle, MCPLBinaryWrite
import mcpl


def test_mcplgun():
    par = MCPLParticle(0.0253,  2,3,4,  5,6,7., 0.,1., 0)
    wrt = MCPLBinaryWrite('test.mcpl')
    wrt.write(par)
    par.direction_x = 1.
    par.direction_y = 0.
    par.direction_z = 0.
    wrt.write(par)
    del wrt

    myfile = mcpl.MCPLFile("test.mcpl.gz", blocklength=10)
    print(myfile.nparticles)
    for p in myfile.particle_blocks:
       print( p.ekin, p.polarisation, p.direction )
