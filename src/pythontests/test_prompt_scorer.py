#!/usr/bin/env python3

import numpy as np
import os
from Cinema.Prompt import PromptFileReader

scorertest_dict ={}
scorertest_dict['ESpectrum'] = {'gdml': 'ESpectrum.gdml', 'mcpl': 'ScorerESpectrum_detector_seed113.mcpl.gz', 'value': [1.27765, 94., 94.,  2.065998]}
scorertest_dict['WlSpectrum'] = {'gdml': 'WlSpectrum.gdml', 'mcpl': 'ScorerWlSpectrum_detector_seed113.mcpl.gz', 'value': [5050., 819.,  819.,  840.]}
scorertest_dict['MultiScat'] = {'gdml': 'MultiScat.gdml', 'mcpl': 'ScorerMultiScat_D2O_seed113.mcpl.gz', 'value': [18., 365., 365.,  266.5]}
scorertest_dict['DeltaMomentum'] = {'gdml': 'DeltaMomentum.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed113.mcpl.gz', 'value': [25275.25, 56.228110442047424, 169., 167.61660094948903]}
scorertest_dict['Angular'] = {'gdml': 'Angular.gdml', 'mcpl': 'ScorerAngular_SofAngle_seed113.mcpl.gz', 'value': [30030., 756., 756., 4607.1]}
scorertest_dict['RotatingObj'] = {'gdml': 'RotatingObj.gdml', 'mcpl': 'ScorerRotatingObj_roen_seed113.mcpl.gz', 'value': [50.49999999999999, 2752., 2752., 83.44]}
scorertest_dict['TOF'] = {'gdml': 'TOF.gdml', 'mcpl': 'ScorerTOF_detector_seed113.mcpl.gz', 'value': [250.25, 819., 819., 0.]}
scorertest_dict['VolFluence'] = {'gdml': 'VolFluence.gdml', 'mcpl': 'ScorerVolFluence_Sflux_seed113.mcpl.gz', 'value': [60.600505, 0.005264443047830176, 14948., 0.0002324042989916737]}
scorertest_dict['PSD'] = {'gdml': 'PSD.gdml', 'mcpl': 'ScorerPSD_NeutronHistMap_seed113.mcpl.gz', 'value': [0., 0., 812., 812., 1130., 1130.]}
scorertest_dict['guide'] = {'gdml': 'guide.gdml', 'mcpl': 'ScorerPSD_Monitor2_seed113.mcpl.gz', 'value': [0., 0., 186.29931081917783, 207., -196.196441756424, -196.196441756424]}
scorertest_dict['WlAngle'] = {'gdml': 'WlAngle_ela.gdml', 'mcpl': 'ScorerWlAngle_wl_angle_seed113.mcpl.gz', 'value': [1.515e+02, 9.090e+03, 1.100e+01, 1.100e+01, 4.800e+00, 2.880e+02]}

for scorername in scorertest_dict:
    scorer = scorertest_dict[scorername]
    os.system('rm %s'%scorer['mcpl'])
    os.system('prompt -g %s -s 113 -n 1e3' % scorer['gdml'])
    
    f = PromptFileReader(scorer['mcpl'])
    hist_weight = f.getData('content').sum()
    hist_hit = f.getData('hit').sum()
    if(scorername=='PSD' or scorername=='guide' or scorername=='WlAngle'):
        hist_xedge = f.getData('xedge').sum()
        hist_yedge = f.getData('yedge').sum()
        hist_content_xedge = (f.getData('content')*f.getData('xedge')[:-1]).sum()
        hist_content_yedge = (f.getData('content')*f.getData('yedge')[:-1]).sum()
        res = np.array([hist_xedge, hist_yedge, hist_weight, hist_hit, hist_content_xedge, hist_content_yedge])
    else:
        hist_edge = f.getData('edge').sum()
        hist_content_edge = (f.getData('content')*f.getData('edge')[:-1]).sum()
        res = np.array([hist_edge, hist_weight, hist_hit, hist_content_edge])
    
    np.set_printoptions(precision=16)
    print(res)
    np.testing.assert_allclose(res, scorer['value'], rtol=1e-15)

print('passed prompt_scorer test')
