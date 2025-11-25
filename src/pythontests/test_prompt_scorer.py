#!/usr/bin/env python3

import numpy as np
import os
from Cinema.Prompt import PromptFileReader

scorertest_dict ={}
scorertest_dict['ESpectrum'] = {'gdml': 'ESpectrum.gdml', 'mcpl': 'ScorerESpectrum_detector_seed113.mcpl.gz', 'value': [ 0.335562367659022, 88., 88., 1.8522594945025759]}
scorertest_dict['WlSpectrum'] = {'gdml': 'WlSpectrum.gdml', 'mcpl': 'ScorerWlSpectrum_detector_seed113.mcpl.gz', 'value': [5050.,813.,813.,832.]}
scorertest_dict['MultiScat'] = {'gdml': 'MultiScat.gdml', 'mcpl': 'ScorerMultiScat_D2O_seed113.mcpl.gz', 'value': [ 18., 444., 444., 315.]}
scorertest_dict['DeltaMomentum'] = {'gdml': 'DeltaMomentum.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed113.mcpl.gz', 'value': [25275.25, 63.69149327544164, 190., 188.4447368017572 ]}
scorertest_dict['Angular'] = {'gdml': 'Angular.gdml', 'mcpl': 'ScorerAngular_SofAngle_seed113.mcpl.gz', 'value': [30030. ,   743.  ,   743.  ,  5011.98]}
# fixme
# scorertest_dict['RotatingObj'] = {'gdml': 'RotatingObj.gdml', 'mcpl': 'ScorerRotatingObj_roen_seed113.mcpl.gz', 'value': [  50.5 , 1926.  , 1926.  ,   44.87]}
scorertest_dict['TOF'] = {'gdml': 'TOF.gdml', 'mcpl': 'ScorerTOF_detector_seed113.mcpl.gz', 'value': [250.25, 813.,813.,0.]}
scorertest_dict['VolFluence'] = {'gdml': 'VolFluence.gdml', 'mcpl': 'ScorerVolFluence_Sflux_seed113.mcpl.gz', 'value': [6.0600504999999998e+01, 5.6186115051861350e-03, 1.5993000000000000e+04, 2.4906084586065675e-04]}
scorertest_dict['PSD'] = {'gdml': 'PSD.gdml', 'mcpl': 'ScorerPSD_NeutronHistMap_seed113.mcpl.gz', 'value': [  0.,0., 805., 805., 120., 120.]}
scorertest_dict['guide'] = {'gdml': 'guide.gdml', 'mcpl': 'ScorerPSD_Monitor2_seed113.mcpl.gz', 'value': [  0.,0.,194.7600562359724, 211.,95.60145860572976,95.60145860572976]
}

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
