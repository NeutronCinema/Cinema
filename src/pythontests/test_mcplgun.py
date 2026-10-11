#!/usr/bin/env python3

import pytest
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


@pytest.mark.slow  # >0.7 s body: excluded from the pre-push hook, runs in cimbuild -t
def test_mcplgun(tmp_path):
    # write under tmp_path: MCPLBinaryWrite must never pollute the CWD
    f = str(tmp_path / 'test.mcpl')
    par = MCPLParticle(0.0253,  2,3,4,  5,6,7., 0.,1., 0)
    wrt = MCPLBinaryWrite(f)
    wrt.write(par)
    par.direction_x = 1.
    par.direction_y = 0.
    par.direction_z = 0.
    wrt.write(par)
    del wrt

    myfile = mcpl.MCPLFile(f + ".gz", blocklength=10)
    print(myfile.nparticles)
    for p in myfile.particle_blocks:
       print( p.ekin, p.polarisation, p.direction )
