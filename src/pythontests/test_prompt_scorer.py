#!/usr/bin/env python3

import numpy as np
import os
from Cinema.Prompt import PromptFileReader


def test_simulation(tmp_path, monkeypatch):
    # run inside a tmp dir: the prompt CLI writes the .mcpl.gz result files and
    # *_view.py scripts into the working directory, which must not be the repo
    monkeypatch.chdir(tmp_path)
    # Full re-recording 2026-10-12 (seed 113, 1e3 primaries, current build).
    # The old pins predated the GDML reader dimension-convention fix: boxes and
    # tubes declared in gdml were read 2x too large per axis, so geometries were
    # effectively 8x in volume and, e.g., the ESpectrum detector caught 88 hits
    # instead of today's 720 (spec-sized geometry; the D2O sample in
    # ESpectrum.gdml is r=5/z=10 as declared). Six of nine entries were
    # bit-identical or last-digit before this re-record (WlSpectrum, MultiScat,
    # Angular, TOF, PSD unchanged; DeltaMomentum one ulp), confirming the drift
    # was confined to the geometry-convention-era entries. 'guide' drifted by
    # moderator/NCrystal sampling vintage (-4% content, monitor mean x +0.5 ->
    # -1.1 mm, physical for this laterally structured guide: segments sit at
    # x=+-26.5 mm). VolFluence additionally reflects the raw-track-length
    # scorer semantics of 2026-10-12 (old fluence pin x box capacity 6.4e7 mm^3).
    scorertest_dict ={}
    scorertest_dict['ESpectrum'] = {'gdml': 'ESpectrum.gdml', 'mcpl': 'ScorerESpectrum_detector_seed113.mcpl.gz', 'value': [ 0.33556236765902203, 720., 720., 16.636751073361253]}
    scorertest_dict['WlSpectrum'] = {'gdml': 'WlSpectrum.gdml', 'mcpl': 'ScorerWlSpectrum_detector_seed113.mcpl.gz', 'value': [5050.,813.,813.,832.]}
    scorertest_dict['MultiScat'] = {'gdml': 'MultiScat.gdml', 'mcpl': 'ScorerMultiScat_D2O_seed113.mcpl.gz', 'value': [ 18., 444., 444., 315.]}
    scorertest_dict['DeltaMomentum'] = {'gdml': 'DeltaMomentum.gdml', 'mcpl': 'ScorerDeltaMomentum_SofQ_seed113.mcpl.gz', 'value': [25275.25, 63.691493275441644, 190., 188.4447368017572 ]}
    scorertest_dict['Angular'] = {'gdml': 'Angular.gdml', 'mcpl': 'ScorerAngular_SofAngle_seed113.mcpl.gz', 'value': [30030. ,   743.  ,   743.  ,  5011.98]}
    scorertest_dict['TOF'] = {'gdml': 'TOF.gdml', 'mcpl': 'ScorerTOF_detector_seed113.mcpl.gz', 'value': [250.25, 813.,813.,0.]}
    scorertest_dict['VolFluence'] = {'gdml': 'VolFluence.gdml', 'mcpl': 'ScorerVolFluence_Sflux_seed113.mcpl.gz', 'value': [6.0600504999999998e+01, 3.595690152822593e+05, 1.5992000000000000e+04, 1.5938035761185401e+04]}
    scorertest_dict['PSD'] = {'gdml': 'PSD.gdml', 'mcpl': 'ScorerPSD_NeutronHistMap_seed113.mcpl.gz', 'value': [  0.,0., 805., 805., 120., 120.]}
    scorertest_dict['guide'] = {'gdml': 'guide.gdml', 'mcpl': 'ScorerPSD_Monitor2_seed113.mcpl.gz', 'value': [  0.,0.,186.29931081917783, 207.,-196.196441756424,-196.196441756424]
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
