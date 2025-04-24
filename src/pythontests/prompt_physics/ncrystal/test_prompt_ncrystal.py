#!/usr/bin/env python3

from Cinema.Prompt.scorer import WlSpectrum, PSDHelper
import numpy as np

import Cinema.Prompt as cpt

RANDOM_CHECK = [5.0, 5.0, 4.0, 5.0, 2.0, 3.0, 4.0, 3.0, 1.0, 2.0, 
                2.0, 0.0, 1.0, 0.0, 2515.0, 2.0, 1.0, 0.0, 2.0, 1.0]

WEIGHT_CHECK = 2674.

def testgun():
    gunCfg = "gun=UniModeratorGun;mean_wl=2;range_wl=0.001;src_w=0.01;src_h=0.01;src_z=-190;slit_w=0.01;slit_h=0.01;slit_z=1e99;"
    return gunCfg

def nc_cfgs():
    cfgs = [
        "Al_sg225.ncmat", # pure NC kernel
        "physics=ncrystal;nccfg='Al_sg225.ncmat';scatter_bias=2.0;abs_bias=1.0" # should be the same as above when NC changes
    ]
    return cfgs

class MySim(cpt.PromptMPI):
    def __init__(self, seed, cfg) -> None:
        super().__init__(seed)
        self.sample = cfg

    def makeWorld(self):
        world = cpt.geo.Volume('world', cpt.solid.Box(50, 50, 200))
        sample = cpt.geo.Volume('sample', cpt.solid.Box(2, 2, 0.5), self.sample)
        world.placeChild('entity', sample)

        dttx = 40
        dtty = 40
        dttz = 1

        dtt = cpt.geo.Volume('detector', cpt.solid.Box(dttx, dtty, dttz))

        scorerWl = WlSpectrum()
        scorerWl.cfg_name = 'WavelengthSp'
        scorerWl.cfg_min = 1.5
        scorerWl.cfg_max = 2.2
        scorerWl.cfg_numbin = 20
        dtt.addScorer(scorerWl)

        pos_bins = 100
        dtt_zpos = 20
        PSDHelper('psd', -dttx, dttx, pos_bins, -dtty, dtty, pos_bins).make(dtt)
        world.placeChild('detectorPhy', dtt, cpt.geo.Transformation3D(0,0,dtt_zpos))

        beamstop = cpt.geo.Volume('bs', cpt.solid.Box(0.1,0.1,1), 'solid::B4C/2.52gcm3/B_is_0.95_B10_0.05_B11')
        world.placeChild('bsphy', beamstop, cpt.geo.Transformation3D(0,0,10))

        self.setWorld(world)

def build(cfg):
    sim = MySim(seed=4096, cfg=cfg)
    sim.makeWorld()
    return sim

def result_plot(sim : MySim):
    psd = sim.gatherHistData('psd')
    if sim.rank == 0:
        psd.plot(1)

def test_case_restrict(sim : MySim): # This one might be too restrictive
    wlhist = sim.gatherHistData('WavelengthSp')
    print(wlhist.getHit().tolist(), sep=',')
    np.testing.assert_array_equal(wlhist.getHit(), RANDOM_CHECK)

def test_case_relax(sim: MySim):
    psd = sim.gatherHistData('psd')
    w = psd.getAccWeight()
    tol = np.sqrt(10./WEIGHT_CHECK)
    print(f'weight: {w}', f'tolerance: {tol}', sep=', ')
    np.testing.assert_allclose(w,WEIGHT_CHECK,tol)

if __name__ == "__main__":
    nparticles = 1e6
    sim = build(nc_cfgs()[0])
    # sim.show(testgun(), 100, zscale=0.5) # visualize
    sim.simulate(testgun(), nparticles)
    # result_plot(sim)
    test_case_restrict(sim)
    test_case_relax(sim)

