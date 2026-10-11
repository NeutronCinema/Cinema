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


@pytest.mark.slow
def test_mcplgun_roundtrip(tmp_path):
    # regression: pt_MCPLBinaryWrite_write used to take mcpl_particle_t by
    # value while ctypes passed a pointer, so stack garbage was written to
    # disk. A fully-populated particle must survive the write/read cycle.
    f = str(tmp_path / 'roundtrip.mcpl')
    par = MCPLParticle(1e-9,           # ekin [MeV]
                       0.1, -0.2, 0.3, # polarisation
                       1.5, -2.5, 3.5, # position [cm]
                       0., 0., 1.,     # direction (unit vector)
                       12.5,           # time [ms]
                       0.75,           # weight
                       2112, 42)       # pdgcode, userflags
    # double precision, polarisation and userflags must be enabled, else mcpl
    # drops those fields on disk
    wrt = MCPLBinaryWrite(f, True, True, True)
    wrt.write(par)
    wrt.close() # plain close (no gzip): file stays at f
    del wrt

    parts = list(mcpl.MCPLFile(f, blocklength=10).particle_blocks)
    assert len(parts) == 1
    p = parts[0]
    # the writer's mcpl_particle_t overload memcpy's the struct verbatim, so
    # values are stored already in MCPL standard units (MeV, cm, ms) and must
    # come back bit-identical under double precision. The mcpl reader wraps
    # fields in (block-shaped) numpy arrays, hence float() and array_equal
    # (exact, no tolerance) rather than tuple comparison.
    assert float(p.ekin) == 1e-9
    assert np.array_equal(np.asarray(p.polarisation).ravel(), (0.1, -0.2, 0.3))
    assert np.array_equal(np.asarray(p.position).ravel(), (1.5, -2.5, 3.5))
    assert np.array_equal(np.asarray(p.direction).ravel(), (0., 0., 1.))
    assert float(p.time) == 12.5
    assert float(p.weight) == 0.75
    assert int(p.pdgcode) == 2112
    assert int(p.userflags) == 42
