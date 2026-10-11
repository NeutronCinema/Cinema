#!/usr/bin/env python3
import os
import sys
# Root of the bl9 script tree (two levels up from this file), holding the
# local modules (mcgd, jsonReader) and geo_data/.
projectpath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + '/'
sys.path.append(projectpath)

from Cinema.Prompt import Launcher, Visualiser
from Cinema.Prompt.solid import Box, Tessellated
from Cinema.Prompt.gun import PythonGun

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Sphere, Tube, Trapezoid, ArbTrapezoid, Cone
from Cinema.Prompt.gun import PythonGun, MCPLGun
from Cinema.Prompt.scorer import WlSpectrum, PSDHelper, ESpectrumHelper
from mcgd import GuideSectionCollection
from jsonReader import JsonParser
import numpy as np

GEO_FILE = os.path.join(projectpath, 'geo_data/section.json')

class MySim(PromptMPI):
    def __init__(self, seed) -> None:
        super().__init__(seed)

    def makeWorld(self):
        # worldx, worldy, worldz, xbds, ybds, zbds = self.get_world_size()
        guideinfo = JsonParser(GEO_FILE)
        zmin,zmax,zmid = guideinfo.bound_zinfo()
        xmin,xmax,_ = guideinfo.bound_xinfo()
        ymin,ymax,_ = guideinfo.bound_yinfo()
        zlength = zmax - zmin
        world = Volume('world', Box(3*xmax, 3*ymax, zmax+2000), 'void.ncmat')

        gb = Volume('guide_box', Box(2*xmax, 2*ymax, zmax+1000), 'void.ncmat')
        mon_vol = Volume('monitor_vol', Box(20,40,1))
        PSDHelper('monitor_entry', -20,20,101,-40,40,100,groupID=1).make(mon_vol)
        ESpectrumHelper('eg_entry', 1e-4, 100, 100, groupID=1).make(mon_vol)
        PSDHelper('monitor_exit', -20,20,101,-40,40,100,groupID=2).make(mon_vol)
        ESpectrumHelper('eg_exit', 1e-4, 100, 100, groupID=2).make(mon_vol)
        # vol_mon = self.make_psd(xbds[1], ybds[1])

        gsc = GuideSectionCollection.from_json(GEO_FILE)
        gsc.placeInto(gb)
        
        gb.placeChild('pv_mon_entry', mon_vol, Transformation3D(0,0, zmin - 700),1)
        gb.placeChild('pv_mon_exit', mon_vol, Transformation3D(0,0, zmax + 200),2)

        world.placeChild('detectorPhy', gb, Transformation3D(0,0,0))

        self.setWorld(world)

if __name__ == "__main__":

    # >>>> Transport run
    outdir = 'prompt_out'

    sim = MySim(seed=102)
    sim.makeWorld()
    # sec1_entry = [15.1 * 2, 47.7 *2]
    # gunCfg = f"gun=MaxwellianGun;src_w={sec1_entry[0]};src_h={sec1_entry[1]};src_z={zmin-5000};slit_w={sec1_entry[0]};slit_h={sec1_entry[1]};slit_z={zmin};temperature=293;"
    gunfile = projectpath + 'source/source.xml'
    gun = MCPLGun(gunfile)
    if False:
        sim.show(gun, 1000, zscale=0.01)
    else:
        sim.simulate(gun, 1e8)
        monitor_entry = sim.gatherHistData('monitor_entry')
        monitor_exit = sim.gatherHistData('monitor_exit')
        mon_entry_eg = sim.gatherHistData('eg_entry')
        mon_exit_eg = sim.gatherHistData('eg_exit')
        if sim.rank == 0:
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            plt = monitor_entry.plot(show=False,log=True,title=f"Entry, weight {monitor_entry.getAccWeight():.2f}")
            plt.savefig(os.path.join(outdir,'entry.svg'))
            monitor_entry.save(os.path.join(outdir,'entry.h5'))

            plt = monitor_exit.plot(show=False,log=True,title=f"Exit, weight {monitor_exit.getAccWeight():.2f}")
            plt.savefig(os.path.join(outdir,'exit.svg'))
            monitor_exit.save(os.path.join(outdir,'exit.h5'))

            # plt.figure()
            # plt.title('p loc weight')
            # plt.plot(monitor_exit.getCentre()[0], monitor_exit.getWeight().sum(0))
            # plt.savefig(os.path.join(outdir,'exit_ploc_w.svg'))

            # plt.figure()
            # plt.title('p loc height')
            # plt.plot(monitor_exit.getCentre()[1], monitor_exit.getWeight().sum(1))
            # plt.savefig(os.path.join(outdir,'exit_ploc_h.svg'))

            plt.figure()
            mon_exit_eg.plot(show=False,log=True,title=f'Exit Energy, weight {mon_exit_eg.getAccWeight():.2f}')
            plt.savefig(os.path.join(outdir,'exit_energy.svg'))
            mon_exit_eg.save(os.path.join(outdir,'exit_energy.h5'))

            plt.figure()
            mon_entry_eg.plot(show=False,log=True,title=f'Entry Energy, weight {mon_entry_eg.getAccWeight():.2f}')
            plt.savefig(os.path.join(outdir,'entry_energy.svg'))
            mon_entry_eg.save(os.path.join(outdir,'entry_energy.h5'))
    # >>>> print cad info
    # read_box_from_inner_info(ifprint=1)

    # >>>> inspect geo
    # fpath = 'guides_simple.stl'
    # pv_show(fpath)




