#!/usr/bin/env python3

import numpy as np
import os
from Cinema.Prompt import PromptFileReader


def test_simulation():
    guntest_dict ={}
    guntest_dict['SimpleThermalGun'] = {'gdml': 'SimpleThermalGun.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed103.mcpl.gz', 'value': [5894.344942918124, 9.391573587953655, 14.]}
    guntest_dict['IsotropicGun'] = {'gdml': 'IsotropicGun.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed103.mcpl.gz', 'value': [5894.344942918124,61.16980141200024,58.]}
    guntest_dict['UniModeratorGun'] = {'gdml': 'UniModeratorGun.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed103.mcpl.gz', 'value': [5894.344942918124, 7885.12246837646, 805.]}
    guntest_dict['MPIGun'] = {'gdml': 'MPIGun.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed103.mcpl.gz', 'value': [5894.344942918124,3870.8779178858144,873.]}
    guntest_dict['MaxwellianGun'] = {'gdml': 'MaxwellianGun.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed103.mcpl.gz', 'value': [5894.344942918124, 4139.029283111744,  853.]}

    for gunname in guntest_dict:
        gun = guntest_dict[gunname]
        os.system('rm %s' % gun['mcpl'])
        os.system('prompt -g %s -s 103 -n 1e3' % gun['gdml'])
        
        f = PromptFileReader(gun['mcpl'])
        hist_weight = f.getData('content').sum()
        hist_hit = f.getData('hit').sum()
        hist_edge = f.getData('edge').sum()
        
        res = np.array([hist_edge, hist_weight, hist_hit])
        np.set_printoptions(precision=16)
        print(res)
        np.testing.assert_allclose(res, gun['value'], rtol=1e-15)
