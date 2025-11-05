#!/usr/bin/env python3

# Model description from
# https://www.sciencedirect.com/science/article/pii/S016890021301423X


from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere
from Cinema.Prompt.scorer import DirectSqwHelper, MultiScatCounter, TOFHelper, ESpectrumHelper
from Cinema.Prompt.histogram import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun
from Cinema.Prompt.component import makeDiskChopper

import numpy as np

do_optimization = True
para_lsp = 10000
para_lpm = 25000
para_lsd = 3000
para_lms = 1300
para_source_Ekin_mean = 0.1
para_source_delta_Ekin = 0.006
para_souce_inten = 1e7

class MySim(PromptMPI):
    def __init__(self, mod_smp_dist, mean_ekin, seed=4096) -> None:
        super().__init__(seed)   
        self.mod_smp_dist = mod_smp_dist
        self.mean_ekin = mean_ekin
        self.z_origin = 0 # sample position
        self.y_monoChopper = self.y_pulseShaping = -17.5
        self.z_pulseShaping = self.z_origin - para_lpm - para_lms
        self.z_monoChopper = self.z_pulseShaping + para_lpm

    def makeWorld(self, sample_radius=1):
        world = Volume("world", Box(5000, 5000, 40000))

        pulseShapingChopperVol = makeDiskChopper(20,15,-150, 1,633.05950569037,30)
        monochromaticChopperVol = makeDiskChopper(20,15, -110,1, 668.229478228,5)

        transformationPS = Transformation3D(0,self.y_pulseShaping,self.z_pulseShaping)
        transformationMono = Transformation3D(0, self.y_monoChopper, self.z_monoChopper)
        world.placeChild('pulseShapingChopperLV', pulseShapingChopperVol, transformationPS)
        world.placeChild('monochromaticChopperLV', monochromaticChopperVol, transformationMono)

        mat = 'physics=idealElaScat;xs_barn=1;density_per_aa3=0.1;energy_transfer_eV=0.003'
        # mat = "physics=ncrystal;nccfg='bzscope_c1_vol_77K.ncmat;bragg=0';scatter_bias=10.0;abs_bias=1.0;"
        # mat = 'bzscope_c1_vol_77K.ncmat;bragg=0'
        sample = Volume("sample", Tube(0, sample_radius, 1), matCfg=mat)
        ms = MultiScatCounter()
        ms.make(sample)
        world.placeChild('samplePV', sample, Transformation3D(0,0,self.z_origin).applyRotX(90))
        mon = Volume("mon", Box(1,1,0.01))
        tofScorerPS = TOFHelper("tofMonScorerPulseShaping", 0.00215, 0.00232, groupID=1)
        tofScorerPS.make(mon)

        spliter = Volume("spliter", Box(1,1,0.01))
        splitercfg = "Scorer=Split;name=split_hist;split=100"
        spliter.addScorer(splitercfg)
        # world.placeChild("spliterPV", spliter, Transformation3D(0,0,self.z_monoChopper+20))

        # Bf = Before; Af = After
        tofScorerBfMono = TOFHelper("tofBfMonScorerMono", 0.0075, 0.0082, groupID=2)
        tofScorerBfMono.make(mon)
        tofScorerAfMono = TOFHelper("tofAfMonScorerMono", 0.0075, 0.0082, groupID=21)
        tofScorerAfMono.make(mon)
        
        engScorerBeforeMonoc = ESpectrumHelper("engMonBeforeMonoc", 
                                               para_source_Ekin_mean-5*para_source_delta_Ekin, 
                                               para_source_Ekin_mean+5*para_source_delta_Ekin, groupID=3)
        engScorerBeforeMonoc.make(mon)
        engScorerAfterMonoc = ESpectrumHelper("engMonAfterMonoc", 
                                               para_source_Ekin_mean-5*para_source_delta_Ekin, 
                                               para_source_Ekin_mean+5*para_source_delta_Ekin, groupID=31)
        engScorerAfterMonoc.make(mon)
        engScorerAfterSource = ESpectrumHelper("engMonAfterSource", 
                                               para_source_Ekin_mean-5*para_source_delta_Ekin, 
                                               para_source_Ekin_mean+5*para_source_delta_Ekin, groupID=4)
        engScorerAfterSource.make(mon)

        world.placeChild("tofMonPSLV", mon, Transformation3D(0,0,self.z_pulseShaping+0.01), scorerGroup=1)
        world.placeChild("tofMonBfMonoLV", mon, Transformation3D(0, 0, self.z_monoChopper-0.01), scorerGroup=2)
        world.placeChild("tofMonAfMonoLV", mon, Transformation3D(0, 0, self.z_monoChopper+0.01), scorerGroup=21)
        world.placeChild("engMonBeforeMonocLV", mon, Transformation3D(0, 0, self.z_monoChopper-5), scorerGroup=3)
        world.placeChild("engMonAfterMonocLV", mon, Transformation3D(0, 0, self.z_monoChopper+5), scorerGroup=31)
        world.placeChild("engMonAfterSourceLV", mon, Transformation3D(0, 0, self.z_pulseShaping-5000), scorerGroup=4)

        deg = np.pi/180.

        monitor = Volume("mon", Sphere(3000, 3000.01, starttheta=1.*deg, deltatheta=178*deg ))
        sqw = DirectSqwHelper('sqw', self.mod_smp_dist, self.mean_ekin, [0,0,1.], [0,0,0],
                 qmin = 1e-1, qmax = 12, num_qbin = 450, 
                 ekinmin=0.002, ekinmax=0.004,  num_ebin = 500,
                 pdg = 2112, groupID  = 0, ptstate = 'ENTRY')
        # helper = ESpectrumHelper("engScorerDetector", 0.0029, 0.0031, 400, energyTransfer= True ,linear=True)
        sqw.make(monitor)
        sqw.addScatterCounter(ms, 1)
        
        # for Si149
        # tofScorerDet = TOFHelper("tofMonScorerDet", 0.00882, 0.0093, numbin=100, groupID=101) 
        # for ideal scatter
        tofScorerDet = TOFHelper("tofMonScorerDet", 0.00889, 0.008955, numbin=100, groupID=101)
        tofScorerDet.make(monitor)
        tofScorerDet.addScatterCounter(ms, 1)

        world.placeChild('monPV', monitor,Transformation3D(0,0,0), scorerGroup=101)

        self.setWorld(world)


class MyGun(PythonGun):
    def __init__(self, mod_smp_dist, ekin, normal = False ):
        super().__init__(2112)
        self.ekin = ekin
        self.mod_smp_dist = mod_smp_dist
        self.normal = normal

    def samplePosition(self):
        x = np.random.uniform(-5,5)
        y = np.random.uniform(-5,5)
        return x,y,self.mod_smp_dist
    
    def sampleEnergy(self):
        if self.normal:
            r=np.random.normal(self.ekin[0], self.ekin[1])
            return r
        elif isinstance(self.ekin, np.ndarray):
            r=np.random.uniform(self.ekin[0], self.ekin[1], 1)[0]
            return velocity2ekin(10/r)
        else:
            return self.ekin

mod_smp_dist = 0 - 1300 - 25000 - 10000
# ekin = [0.022, 0.024]
ekin = [para_source_Ekin_mean, para_source_delta_Ekin]

const_neutron_mass = 1.674e-27 #kg
const_neutron_mass_amu = 1.00866491588
const_c  = 299792458 # (m/s)/c
const_dalton2eVc2 =  931494095.17
const_neutron_mass_evc2 = const_neutron_mass_amu * const_dalton2eVc2  #[ eV/(Aa/s)^2 ]

def ekin2velocity(ekin):
    ekin = np.array(ekin)
    return np.sqrt(2 * ekin / (const_neutron_mass_evc2 / const_c**2))

def velocity2ekin(velocity):
    velocity = np.array(velocity)
    return 0.5 * const_neutron_mass_evc2 / const_c**2  * (velocity)**2

def ekin2time(ekin, distance):
    ekin = np.array(ekin)
    return distance / ekin2velocity(ekin)

def convert_tof2hw(scorermono, scorerdetector):
    tpm = scorermono.getMean() - scorermono.getMean() * para_lsp/(para_lpm+para_lsp)
    tmd = scorerdetector.getEdges() - scorermono.getMean()
    hw = const_neutron_mass_evc2 / const_c**2 * 0.5 * ((para_lpm*1e-3/tpm)**2 - (para_lsd*1e-3/(tmd-tpm*para_lms/para_lpm))**2)
    return hw


gun = MyGun(mod_smp_dist, ekin, normal=True)        # uniform time-of-flight
sim = MySim(-mod_smp_dist, 0.025100171020, seed=1010)



# destination = 0
# if sim.rank==destination:
#     # res.plot(False, log=False)
#     # res.plot(True, title=f'Total Weight: {res.getAccWeight()}', log=True)
#     fn = 'Si_bzscope_braggIncluded'
#     plt=res.plot(title=f'{fn}', log=True)
#     plt.xlabel(r'Q($\AA^{-1}$)')
#     plt.ylabel(r'$\omega$(eV)')
#     plt.tight_layout()
#     plt.grid(False)
#     plt.savefig(f'{fn}.pdf')

if do_optimization:
    from Cinema.Prompt import Optimiser
    import subprocess
    class SampleOpt(Optimiser):
        def __init__(self, sim):
            super().__init__(sim, 1e7)
            self.directions = ['minimize']

        def get_std(self):
            from pt_dataFitting import HistPost
            tofDet = self.sim.gatherHistData("tofMonScorerDet")
            tofAfMono = self.sim.gatherHistData("tofAfMonScorerMono")
            hw = convert_tof2hw(tofAfMono, tofDet)
            histpost = HistPost(hw, tofDet.getWeight())
            return histpost.getStd()

        def objective(self, trial):
            self.sim.clear() 
            sample_radius = trial.suggest_float('sample_radius', 0.01, 10)
            self.sim.makeWorld(sample_radius)
            self.sim.simulate(gun, self.trailNeutronNum)
            return self.get_std()
    
    opt = SampleOpt(sim)
    opt.optimize(name='sampleRadius_test', n_trials=10, localhost=False)
    print(opt.study.best_params, opt.study.best_value)
    opt.analysis()
else:
    sim.makeWorld()

    # sim.show(gun, 1000)

    sim.simulate(gun, para_souce_inten)
    tofPS = sim.gatherHistData("tofMonScorerPulseShaping")
    tofBfMono = sim.gatherHistData("tofBfMonScorerMono")
    tofAfMono = sim.gatherHistData("tofAfMonScorerMono")
    engBfMonoc = sim.gatherHistData("engMonBeforeMonoc")
    engAfSource = sim.gatherHistData("engMonAfterSource")
    tofDet = sim.gatherHistData("tofMonScorerDet")
    engAfMonoc = sim.gatherHistData("engMonAfterMonoc")

    # engDetector = sim.gatherHistData("engScorerDetector")
    res = sim.gatherHistData('sqw')


    import matplotlib.pyplot as plt
    from pt_dataFitting import gaussian_fit, gaussian_plot, plot_bar
    from Cinema.Interface import plotStyle
    plotStyle(8)


    def fit_and_plot(scorer, fname, bounds, scale=1):
        plt.figure()
        gaussian_plot(scorer.getEdges(), scorer.getWeight(), bounds, scale)
        plt.savefig(fname)

    def find_2nd_max(x : np.ndarray):
        value_2nd_max = np.sort(x)[-2]
        indice = np.where((x==value_2nd_max))[0]
        return x[indice]

    if sim.rank==0:
        print(f"Time of flight: {ekin2time(ekin, 10+25)}")
        print('Testing : ',tofBfMono.getTotalWeight())
        print(f"Energy before sample: {engBfMonoc.getMean()}")
        engBfMonoc.savefig('engBfMonoc.png')
        engAfMonoc.savefig('engAfMonoc.png')
        engAfSource.savefig('engSource.png')
        fit_and_plot(tofPS,'tofps.png', bounds = [(0,0.00470, 0.000001),(100000,0.00480,0.01)], scale=1e6)
        print(f"PS Standard Deviation: {tofPS.getStd()*1e6:.7f}")
        print(f"PS Mean: {tofPS.getMean():.7f}")
        tofBfMono.savefig('tofBfMono.png')
        tofAfMono.savefig('tofAfMono.png')
        print(f"MONO Standard Deviation: {tofAfMono.getStd()*1e6:.7f}")
        print(f"MONO Mean: {tofAfMono.getMean():.7f}")
        tofDet.savefig('tofDetector.png')
        # engDetector.savefig('engDetector.png')

        # plt.figure()
        # # plt.scatter(res.getEdges()[1][:-1], res.getWeight().sum(0), label="Histogram data" )
        # bmin , bmax = 185, 315
        # xx = res.getEdges()[1][bmin:bmax]
        # yy = res.getWeight().sum(0)[bmin:bmax]
        # gaussian_plot(xx, yy)
        # print(res.getTotalWeight())
        # plt.legend()
        # plt.savefig('sqwScorerEngDectect.png')
        hw = convert_tof2hw(tofAfMono, tofDet)

        from pt_h5Tool import read_hdf5, plot_sw
        from pt_dataFitting import HistPost
        file = '/home/panzy/project/ml/ncmat/c1_vol_77K.h5'
        w, q, s = read_hdf5(file)
        plt.figure(3001)
        plot_bar(hw, tofDet.getWeight())
        histpost = HistPost(hw, tofDet.getWeight())
        print(f'Mean of hist post: {histpost.getMean()}')
        print(f'Std of hist post: {histpost.getStd()}')
        yscale = tofDet.getWeight().max() / find_2nd_max(s.sum(0))
        # plot_sw(w, q, s, yscale=yscale)
        # gaussian_plot(hw, tofDet.getWeight(), ([0, 0.0025, 0.00001], [10000, 0.0035, 0.01]))
        plt.savefig('violini.png')