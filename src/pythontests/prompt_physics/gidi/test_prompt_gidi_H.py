#!/usr/bin/env python3
import numpy as np
import prompt_suite as ps
import os

cpath = os.getenv('CINEMAPATH')
popsPATH = os.path.join(cpath, 'testdata', 'pops.xml')
expected = [0.0, 0.0, 8.0, 28.0, 101.0, 250.0, 697.0, 1520.0, 3402.0, 7237.0, 14155.0, 23695.0, 28278.0, 16656.0, 2400.0, 23.0, 0.0, 0.0, 0.0, 0.0]


def test_gidi_H():
    cfg ='freegas::H/1gcm3/H_is_H1'
    incidentEnergy = 1e-4
    energyBinNum = 20
    energyRange = [1e-6, 1e1]
    partnum = 100000
    
    counts = ps.promptRun(cfg, incidentEnergy, -5, popsPATH, energyBinNum, energyRange[0], energyRange[1], partnum=partnum)
    np.testing.assert_allclose(counts[2], expected, rtol=1e-15)
