#!/usr/bin/env python3
import numpy as np
import prompt_suite as ps
import os

cpath = os.getenv('CINEMAPATH')
popsPATH = os.path.join(cpath, 'external', 'ptdata', 'pops.xml')
expected = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 3.0, 1682.0, 1916.0, 8474.0, 85992.0, 207.0, 115.0, 4.0, 0.0, 0.0]


def test_gidi_U():
    cfg ='freegas::U92/18gcm3/U_is_U238'
    incidentEnergy = 1e6
    energyBinNum = 20
    energyRange = [1, 1e8]
    partnum = 100000
    
    counts = ps.promptRun(cfg, incidentEnergy, -5, popsPATH, energyBinNum, energyRange[0], energyRange[1], partnum=partnum)
    np.testing.assert_allclose(counts[2], expected, rtol=1e-15)
