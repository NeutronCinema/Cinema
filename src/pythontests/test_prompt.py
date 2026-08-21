#!/usr/bin/env python3

import numpy as np
import os
from Cinema.Prompt import PromptFileReader


def test_simulation():
    f1='ScorerDeltaMomentum_SofQ_seed4096.mcpl.gz'
    os.system(f'rm {f1}')
    os.system('prompt -g watersphere_bias.gdml -n 1e4')


    f = PromptFileReader(f1)

    hist_weight = f.getData('content').sum()
    hist_hit = f.getData('hit').sum()
    hist_edge = f.getData('edge').sum()

    np.set_printoptions(precision=16)
    res = np.array([hist_edge, hist_weight, hist_hit])
    print(res)
    np.testing.assert_allclose(res, [5894.344942918124, 160.2983287154957, 398.], rtol=1e-15)
