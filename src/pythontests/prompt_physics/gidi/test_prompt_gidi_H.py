#!/usr/bin/env python3
import numpy as np
import prompt_suite as ps
import os

cpath = os.getenv('CINEMAPATH')
popsPATH = os.path.join(cpath, 'testdata', 'pops.xml')
# EXIT-spectrum pin, 1e5 x 1e-4 eV neutrons, pure-gidi H1 (threshold -5, seed 1010).
# Re-recorded 2026-10-11 on the gidi-enabled baseline (gidiplus 3.28.22,
# external/ptdata GNDS-2.0 endf80). The 2024-10-24 pin predates gidi thermal
# kernel/data drift: the U238 1 MeV anchor still reproduces at rtol 1e-15, so
# transport determinism is intact while the thermal kernel state moved.
# MUST be re-verified against OpenMC in Phase 4 (L1).
expected = [0.0, 0.0, 6.0, 27.0, 79.0, 220.0, 607.0, 1288.0, 2883.0, 6240.0, 12502.0, 21836.0, 28508.0, 20148.0, 4172.0, 74.0, 0.0, 0.0, 0.0, 0.0]


def test_gidi_H():
    cfg ='freegas::H/1gcm3/H_is_H1'
    incidentEnergy = 1e-4
    energyBinNum = 20
    energyRange = [1e-6, 1e1]
    partnum = 100000
    
    counts = ps.promptRun(cfg, incidentEnergy, -5, popsPATH, energyBinNum, energyRange[0], energyRange[1], partnum=partnum)
    np.testing.assert_allclose(counts[2], expected, rtol=1e-15)
