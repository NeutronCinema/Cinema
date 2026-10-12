#!/usr/bin/env python3
import numpy as np
import prompt_suite as ps
import os

cpath = os.getenv('CINEMAPATH')
popsPATH = os.path.join(cpath, 'external', 'ptdata', 'pops.xml')
# Re-recorded 2026-10-12 for gidiplus 3.35 (P1.2/P1.4): the archived 3.28 .so
# still reproduces the previous pins exactly (dual-library check), so the shift
# is attributed to the 3.35 sampling-internal restructure (RNG stream divergence)
# plus float cross sections: bulk bins move within ~1.5%, low-statistics wings
# more, bin sum -33 of ~98.6k (no systematic loss).
expected = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1653.0, 1948.0, 8384.0, 86119.0, 186.0, 141.0, 9.0, 0.0, 0.0]


def test_gidi_U():
    cfg ='freegas::U92/18gcm3/U_is_U238'
    incidentEnergy = 1e6
    energyBinNum = 20
    energyRange = [1, 1e8]
    partnum = 100000
    
    counts = ps.promptRun(cfg, incidentEnergy, -5, popsPATH, energyBinNum, energyRange[0], energyRange[1], partnum=partnum)
    np.testing.assert_allclose(counts[2], expected, rtol=1e-15)
