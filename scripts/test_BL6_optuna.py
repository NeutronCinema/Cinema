#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI, Optimiser
from Cinema.Prompt.solid import Box, Tube, Trapezoid, Sphere
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import makePSD
from Cinema.Prompt.component import EntityArray, FlatAnalyser, makeTrapezoidGuide, makeDiskChopper, make2CurveAnalyser


from Cinema.Prompt.gun import PythonGun
import numpy as np
import pyvista as pv
from scipy.spatial.transform import Rotation as scipyRot
# ---- inputs from mcstas guide_BL6.instr
# ll1 = 1.84;
# ll2 = 1.495;
# ll3 = 0.51;
# ll4 = 0.795;
# ll5 = 2.7;
# ll6 = 5.8;

ww1 = 0.09 * 1000 * 0.5
ww2 = 0.09 * 1000 * 0.5
ww3 = 0.084196 * 1000 * 0.5
ww4 = 0.079867 * 1000 * 0.5
ww5 = 0.075986 * 1000 * 0.5
ww6 = 0.064676 * 1000 * 0.5 

hh1 = 0.09 * 1000 * 0.5
hh2 = 0.084196 * 1000 * 0.5
hh3 = 0.082207 * 1000 * 0.5
hh4 = 0.076766 * 1000 * 0.5
hh5 = 0.065456 * 1000 * 0.5
hh6 = 0.042056 * 1000 * 0.5 


# double  T0length=0.48;   /* T0length=0.1 */
# double  T0Phase=64.67;  
# double  T0Frequency=50;
# double dtheta = 45;
# double mos=120;    
# int ord_mcm=1;   
# ----

# --- inputs from pptx ---
dist_z_g1 = 2360.
dist_z_g2 = 4200.
dist_z_g3 = 5695.
dist_z_g4 = 6805.
dist_z_g5 = 7800.
dist_z_g6 = 10500.   # deviation

m1 = 0.
m2 = 2.1
m3 = 4.1
m4 = 4.1
m5 = 4.1
m6 = 4.1
# --- end ---
class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)
        
    def makeWorld(self,pos_ana, pos_det, curve_h, curve_v):

        # self.l.setGun(gunCfg)

        world = Volume("world", Box(3000, 3000, 18000))

        g1_in = ww1
        g1_out = hh1

        g2_in = ww2
        g2_out = hh2

        g3_in = ww3
        g3_out = hh3

        g4_in = ww4
        g4_out = hh4

        g5_in = ww5
        g5_out = hh5

        g6_in = ww6
        g6_out = hh6

        # --------------- guide system --------------------
        # guide1 = makeTrapezoidGuide(1840.* 0.5, g1_in, g1_in, g1_out, g1_out, m1)
        # guide2 = makeTrapezoidGuide(1495.* 0.5, g2_in, g2_in, g2_out, g2_out, m2)
        # guide3 = makeTrapezoidGuide(510.* 0.5,  g3_in, g3_in, g3_out, g3_out, m3)
        # guide4 = makeTrapezoidGuide(795.* 0.5,  g4_in, g4_in, g4_out, g4_out, m4)
        # guide5 = makeTrapezoidGuide(2700.* 0.5, g5_in, g5_in, g5_out, g5_out, m5)
        # guide6 = makeTrapezoidGuide(5800.* 0.5, g6_in, g6_in, g6_out, g6_out, m6)
        # world.placeChild("guide1", guide1, self.translationZ(1840. * 0.5 + dist_z_g1))
        # world.placeChild("guide2", guide2, self.translationZ(1495. * 0.5 + dist_z_g2))
        # world.placeChild("guide3", guide3, self.translationZ(510. * 0.5 + dist_z_g3))
        # world.placeChild("guide4", guide4, self.translationZ(795. * 0.5 + dist_z_g4))
        # world.placeChild("guide5", guide5, self.translationZ(2700. * 0.5 + dist_z_g5))
        # world.placeChild("guide6", guide6, self.translationZ(5800. * 0.5 + dist_z_g6))

        # self.scorer['GUIDE_P'], vol_a_guide = makeFlatPSD('GUIDE_P', 100, 100, 1e-3, 100, 100)
        # vol_a_guide.addScorer("Scorer=WlSpectrum; name=wlAfterGuide; min=0.0; max=7.2; numbin=100")
        # vol_a_guide.addScorer("Scorer=TOF; name=tofAfterGuide; min=0.0025; max=0.008; numbin=500")
        # vol_a_guide.addScorer("Scorer=ESpectrum; name=EnBfSample; min=0.0; max=0.25; numbin=100")
        # self.scorer['NORM_TOF'] = "Scorer=TOF; name=tofAfterGuide; min=0.0025; max=0.008; numbin=500"
        # self.scorer['GUIDE_WL'] = "Scorer=WlSpectrum; name=wlAfterGuide; min=0.0; max=7.2; numbin=100"
        # self.scorer['GUIDE_EN'] = "Scorer=ESpectrum; name=EnBfSample; min=0.0; max=0.25; numbin=100"
        # self.scorer['GUIDE_M'], vol_b_guide = makeFlatPSD('GUIDE_M', 200, 200, 1e-3, 100, 100)
        # world.placeChild("monitor_bf", vol_b_guide, self.translationZ(2300.))
        # world.placeChild("monitor_af", vol_a_guide, self.translationZ(16500.))
        
        # --------------- chopper --------------------
        # chopper1 = makeDiskChopper(300, 300 - 74.7, 44.22, 1, 25, 82.94)
        # tunnel1 = Volume("tunnel1", Tube(300, 800, 50.* 0.5, 0, 360), "B4C.ncmat") # fixme: overlap
        # chopper2 = makeDiskChopper(300, 300 - 67., 58.81, 1, 25, 110.79)
        # tunnel2 = Volume("tunnel2", Tube(300, 800, 50.* 0.5, 0, 360), "B4C.ncmat") # fixme: overlap
        # sheild1 = self.makeChopperSheild()
        # sheild2 = self.makeChopperSheild()

        # world.placeChild("chopper1", chopper1, Transformation3D(0., - (300. - 74.7 * 0.5), 6800.))
        # world.placeChild("tunnel1_", tunnel1, Transformation3D(0., - (300 - 74.7 * 0.5), 6800.))
        # world.placeChild("chopper1sheild", sheild1, Transformation3D(0., 0., 6800. + 1e-2 * 0.5))
        # world.placeChild("chopper2", chopper2, Transformation3D(0., - (300 - 67. * 0.5), 9070.)) # input != mcstas
        # world.placeChild("tunnel2_", tunnel2, Transformation3D(0., - (300 - 67. * 0.5), 9070.)) # input != mcstas
        # world.placeChild("chopper2sheild", sheild2, Transformation3D(0., 0., 9070. + 1e-2 * 0.5))

        # --------------- sample --------------------
        # sample_mat = "physics=ncrystal;nccfg='Polyethylene_CH2.ncmat;temp=30'"
        sample_mat = "physics=idealElaScat;xs_barn=5;density_per_aa3=0.5;energy_transfer_eV=0.038"
        sample = Volume("sample", Box(2, 2, 2), sample_mat)
        hwCfg = "Scorer=ESpectrum; scoreTransfer=1; name=sampleHW; min=0.1; max=0.25; numbin=500"
        split = "Scorer=Split;name=split_hist;split=250"
        sample.addScorer(split)
        sample.addScorer(hwCfg)
        # self.scorer["hw"] = hwCfg
        world.placeChild("sample", sample, Transformation3D(0., 0., 17000.))

        # ----------adding a sphere around sample--------------
        sphere = Volume("Mon_af_sample", Sphere(80,85, starttheta=45/180*np.pi, deltatheta=90/180*np.pi))
        sphereCfgEn = "Scorer=ESpectrum; name=sphereEn; min=0.1; max=0.25; numbin=100"
        sphereCfgWl = "Scorer=WlSpectrum; name=spherewl; min=0.01; max=10; numbin=100"
        sphereCfgTof = f"Scorer=TOF; name=spheretof; min=0.0025; max=0.008; numbin=1000"
        sphere.addScorer(sphereCfgEn)
        sphere.addScorer(sphereCfgWl)
        sphere.addScorer(sphereCfgTof)
        # self.scorer['sphereEn'] = sphereCfgEn
        # self.scorer['sphereWl'] = sphereCfgWl
        # self.scorer['spheretof'] = sphereCfgTof
        world.placeChild("spheres", sphere, Transformation3D(0., 0., 17000.))

        # ----------adding sheilding between sample and detecters--------------
        sheild_mat = "physics=ncrystal;nccfg='Cd.ncmat;inelas=0'"
        sheild = Volume("sheild", Box(45, 80, 30), sheild_mat)
        # self.addPSD(sheild, "sheild_sam_det", -50, 50, -100, 100, ptstate='EXIT')
        makePSD("sheild_sam_det", sheild, 100, 100, ptstate='EXIT')
        sheildArray = EntityArray(sheild, refFrame=Transformation3D(0., - (pos_det-140), 17000.).applyRotxyz(90,90,0))
        sheildArray.make()
        sheildArray.make_rotate_z(45,6)
        sheildArray.rotate_z(-135)
        world.placeArray(sheildArray)

        # ----------- analyser -----------
        cry_mat = "physics=ncrystal;nccfg='C_sg194_pyrolytic_graphite.ncmat;mos=2.5deg;dir1=@crys_hkl:0,0,2@lab:0,0,1;dir2=@crys_hkl:1,0,0@lab:1,0,0;lcaxis=0,0,1;dcutoff=3;inelas=false'"
        crystal_plate = Volume("cry", Box(6, 6, 1), cry_mat)
        # crystal_plate = Volume("cry", Box(6, 6, 1), 'solid::Cd/8.65gcm3', surfaceCfg='physics=Mirror;m=2')
        # split2 = "Scorer=Split;name=split_hist;split=1"    
        # crystal_plate.addScorer(split2)

        analyser = FlatAnalyser(crystal_plate, spacings = [13, 13], 
                               refFrame=Transformation3D())
        analyser.make_trape_plane(80, 280, 350, curve_h, curve_v)
        arrayAna = EntityArray(analyser, refFrame=Transformation3D(0., - pos_ana, 16740.).applyRotZ(180))
        arrayAna.make()
        arrayAna.make_rotate_z(45, 6, 0, 0)
        arrayAna.rotate_z(-135)
        # arrayAna.reflect('XY', 17000)
        # arrayAna.selectByZ(17000, np.inf)
        world.placeArray(arrayAna)

        # ----------- filter -----------
        # nfilter_mat = "physics=ncrystal;nccfg='Be_sg194.ncmat;temp=35'"
        # nfilter = Volume("Be_filter", Trapezoid(63.5,63.5,220,100,60), nfilter_mat)
        # CdAbs1 = Volume("CdAbs1", Box(63.5, 60*np.sqrt(2), 1), "physics=ncrystal;nccfg='Cd.ncmat;temp=35'")
        # for i_cd in np.arange(0,7):
        #     nfilter.placeChild('CdAbsPlate1', CdAbs1, Transformation3D(0,200-i_cd*30,0).applyRotX(-45))

        # arrayFilter = EntityArray(nfilter, refFrame=Transformation3D(0., - (pos_det+100), 17000-100))
        # arrayFilter.make()
        # arrayFilter.make_rotate_z(45, 6, 0, 0)
        # arrayFilter.rotate_z(-135)
        # arrayFilter.reflect('XY', 17000)
        # world.placeArray(arrayFilter)

        # ----------- detector array -----------
        self.makeScorerArray(7, world, pos_det, 17000-12.7-13)
        self.makeScorerArray(7,world, pos_det, 17000+12.7+13)

        # ----------- sheild between forward and back detectors -----------
        midSheildMat = "physics=ncrystal;nccfg='Cd.ncmat;inelas=0'"
        midSheild = Volume("sheild", Tube(pos_det-400, pos_det+300, 12.5), midSheildMat)
        # self.addPSD(midSheild, 'sheild_forw_backw', -1000, 1000, -1000, 1000, ptstate='ABSORB')
        # makePSD('sheild_forw_backw', midSheild, 100, 100, ptstate='ABSORB')
        world.placeChild("midSheild", midSheild, Transformation3D(0, 0, 17000))

        self.l.setWorld(world)

    def makeScorerArray(self,  num, world : Volume, pos_det, zloc):
        for i_scor in np.arange(num):
            loc = Transformation3D(0., - pos_det, zloc)
            loc = Transformation3D().applyRotZ(45 * i_scor) * loc
            loc_world = Transformation3D().applyRotZ(-135) * loc
            location = [f'{x: .2f}' for x in loc_world._translation]
            name = f'BankNo.{i_scor + 1}@{location}'
            element = self.makeDetBank(name)
            # # self.scorer[name], vol = makeFlatPSD(name, 120, 200, 100, 100)
            world.placeChild(name, element, loc_world)

    def makeDetBank(self, name):
        vol_bank = Volume('vol_bank', Box(63.5, 100, 12.7))
        bankname = f'BankPSD@{name}'
        # self.addPSD(vol_bank, bankname, -70, 70, -110, 110)
        print(vol_bank)
        print(bankname)
        makePSD(bankname, vol_bank, 100, 100)

        for i_tube in np.arange(1, 6):
            vol_in = Volume('internal', Tube(0, 12.2, 100),"physics=ncrystal;nccfg='He3_Gas_10bar.ncmat;inelas=false'")
            vol_out = Volume('external', Tube(0, 12.7, 100))
            psdname = f'PSD@{name}_TubeNo.{i_tube}'
            psdCfg = f"Scorer=PSD;name={psdname};xmin=-12.2;xmax=12.2;numbin_x=10;ymin=-100;ymax=100;numbin_y=150; ptstate=ABSORB;type=YZ"
            vol_in.addScorer(psdCfg)
            enname = f'EN@{name}_TubeNo.{i_tube}'
            encfg = f"Scorer=ESpectrum; name={enname}; min=0.01; max=0.13; numbin=100; ptstate=ABSORB"
            vol_in.addScorer(encfg)
            wlname = f'WL@{name}_TubeNo.{i_tube}'
            wlcfg = f"Scorer=WlSpectrum; name={wlname}; min=0.01; max=7.2; numbin=100; ptstate=ABSORB"
            vol_in.addScorer(wlcfg)
            tofname = f'TOF@{name}_TubeNo.{i_tube}'
            tofCfg = f"Scorer=TOF; name={tofname}; min=0.0025; max=0.008; numbin=1000; ptstate=ABSORB"
            vol_in.addScorer(tofCfg)
            # self.scorer[enname] = encfg
            # self.scorer[wlname] = wlcfg
            # self.scorer[psdname] = psdCfg
            # self.scorer[tofname] = tofCfg
            
            tube = vol_out.placeChild('phy_tube', vol_in)
            # psdCfg = f"Scorer=PSD;name={name};xmin=-270;xmax=270;numbin_x=108;ymin=-125;ymax=125;numbin_y=50;type=YZ"
            # vol_in.addScorer(psdCfg)
            # # self.scorer[name], vol_bank = makeFlatPSD(name, 63.5, 100, 12.7, 100, 100)
            # vol_bank = Volume('bank', Box(63.5, 100, 12.7))
            vol_bank.placeChild('phy_bank', tube, Transformation3D(((i_tube-3) * 12.7 * 2), 0, 0).applyRotX(90))
        return vol_bank
    
    def makeChopperSheild(self):

        from Cinema.Prompt.component import DiskChopper
        vol = Volume('chopper', Box(1000., 1000.,1e-3))
        chp = DiskChopper()
        chp.cfg_rotFreq = 1
        chp.cfg_n = 1
        chp.cfg_phase = 0
        chp.cfg_r = 0
        chp.cfg_theta0 = 0
        vol.setSurface(chp.get_cfg())

        return vol

    def translationZ(self, dist_z):
        
        return Transformation3D(0., 0., dist_z)

    def quadSurface(self, coordinates, a, b, c, d):
        """
        Following: ax^2 + by^2 + cz^2 + d = 0
        Generally: ax^2 + by^2 + cz^2 + 2fyz + 2gzx + 2hxy + 2px + 2qy + 2rz + d = 0

        Args:
            a (_type_): _description_
            b (_type_): _description_
            c (_type_): _description_
            d (_type_): _description_

        Returns:
            _type_: _description_
        """
        x = coordinates[0]
        y = coordinates[1]
        z = coordinates[2]
        return a * x ** 2 + b * y ** 2 + c * z ** 2 + d

# control paras
OPT = False
VIZ = False
num_neutrons = 100000
viz_num_neutrons = 1000

if not OPT:
    sim = MySim(seed=1050)
    sim.makeWorld(
        # ww1, hh1,
        # ww2, hh2,
        # ww3, hh3,
        # ww4, hh4,
        # ww5, hh5,
        # ww6, hh6
        300, 600, 0, 0 #372.8

    )
    # gunCfg = "gun=MaxwellianGun;src_w=40;src_h=40;src_z=0;slit_w=40;slit_h=40;slit_z=1e99;temperature=293;"
    gunCfg = "gun=UniModeratorGun;mean_wl=1;range_wl=0.001;src_w=2;src_h=2;src_z=0;slit_w=2;slit_h=2;slit_z=1e99"
    # gunCfg = "gun=SimpleThermalGun;energy=0.000002045105;position=0,0,-1500;direction=0,0,1"
    # gunCfg = "gun=IsotropicGun;energy=0.1;position=0,0,17000"

    # vis or production
    if VIZ:
        n_num = viz_num_neutrons
        sim.show(gunCfg, n_num)
    else:
        n_num = num_neutrons
        sim.simulate(gunCfg, n_num)
    
    totweight = 0
    tothit = 0

    enx = 0
    eny = 0

    wlx = 0
    wly = 0

    tofx = 0
    tofy = 0

    m = 0
    from Cinema.Prompt.histogram.Hist import Hist2D, Hist1D
    blankHist = Hist2D(-12.2,12.2,10,-100,100,150)

    wlHist=None
    enHist = None
    sphereEnHist = None
    sphereWlHist = None
    sphereTofHist = None
    tofHist = None
    normTof = None
    midSheildHist = None
    sheildHist = None
    hw = None

    for scor in sim.scorer.keys():
        hist = sim.gatherHistData(scor)
        if scor.startswith('WL'):
            # wlx = hist.getCentre()
            # wly += hist.getWeight()
            # totweight += hist.getWeight().sum()
            # tothit += hist.getHit().sum()
            if wlHist is None:
                wlHist = hist
            else:
                wlHist.merge(hist)
            # print(f'{scor} wavelength weight: {hist.getWeight().sum(): .2f}')
        if scor.startswith('BankPSD'):
            m+=1
            bankHist = hist
            bankHist.savefig(f"bankPSD{m}.png", title=scor)
            # print(f'{scor} PSD weight: {hist.getWeight().sum()}')
        # if scor.startswith('PSD'):
        #     # hist.plot(show=True, title=scor)
        #     blankHist.merge(hist)
        #     # print(f'{scor} PSD weight: {hist.getWeight().sum()}')
        if scor.startswith('TOF'):
            # hist.plot(show=True, title=scor)
            # print(f'{scor} TOF weight: {hist.getWeight().sum()}')
            if tofHist is None:
                tofHist = hist
            else:
                tofHist.merge(hist)
            # tofx = hist.getCentre()
            # tofy += hist.getWeight()
        if scor.startswith('EN'):
            # hist.plot(show=True, title=scor)
            # print(f'{scor} EN weight: {hist.getWeight().sum()}')
            if enHist is None:
                enHist = hist
            else:
                enHist.merge(hist)
            # enx = hist.getCentre()
            # eny += hist.getWeight()
        if scor == 'GUIDE_M':
            # print(f'Incident weight: {hist.getWeight().sum()}')
            inc = hist.getWeight().sum()
        if scor == 'GUIDE_P':
            # print(f'Outgoing weight: {hist.getWeight().sum()}')
            outgoingHit = hist.getHit().sum()
            out = hist.getWeight().sum()
        if scor == 'GUIDE_WL':
            guideWl = hist
        if scor == 'GUIDE_EN':
            guideEN = hist
        if scor == 'NORM_TOF':
            normTof = hist
        if scor == 'sphereEn':
            sphereEnHist = hist
        if scor == 'sphereWl':
            sphereWlHist = hist
        if scor == 'spheretof':
            sphereTofHist = hist
        if scor == 'sheild_sam_det':
            sheildHist = hist
        if scor == 'sheild_forw_backw':
            midSheildHist = hist
        if scor == 'hw':
            hw = hist

    if sim.rank == 0:
        # print(f'Guide system efficiency: {out/inc*100: .4f}%')
        # print(f'Outgoing hit: {outgoingHit}')
        # print(f'Total weight in detectors: {totweight: .2f}')
        # print(f'Total hit in detectors: {tothit: .2f}')
        # print(f'Efficiency: {totweight/n_num*100: .4f}%\n')
        # fig = plt.figure()
        # plt.plot(wlx, wly)
        # plt.savefig(fname="totWL.png")
        # fig = plt.figure()
        # plt.plot(tofx, tofy)
        # plt.savefig(fname="totTOF.png")
        # fig = plt.figure()
        # plt.plot(enx, eny)
        # plt.savefig(fname="totEnergy.png")
        # blankHist.savefig("totPSD.png")
        # bankHist.plot(title=scor)
        log = False
        print(f'Total hit: {tofHist.getHit().sum()}')
        print(f'Total weight: {tofHist.getWeight().sum()}')
        hw.savefig('energyTransfer.png', 'Energy transfer exit sample')
        normTof.savefig('normTof.png', 'Normalization tof before sample', log)
        normTof.savedata('normTof')
        tofHist.savefig('totTof.png', 'Total tof at detector array', log)
        tofHist.savedata('totTof')
        sphereEnHist.savefig('SphereEN.png', 'Energy Exit sample', log)
        sphereEnHist.savedata('SphereEN')
        sphereWlHist.savefig('SphereWl.png', 'Wl Exit sample', log)
        sphereWlHist.savedata('SphereWl')
        sphereTofHist.savefig('SphereTof.png', 'Tof Exit sample', log)
        sphereTofHist.savedata('SphereTof')
        guideWl.savefig('OutWL.png', 'Wavelength@guideOut', log)
        guideWl.savedata('OutWL')
        guideEN.savefig('OutEN.png', 'Energy@guideOut', log)
        enHist.savefig("totEn.png", "Energy at detector array", log)
        enHist.savedata('totEn')
        wlHist.savefig("totWL.png", "Wavelength at detector array", log)
        wlHist.savedata('totWL')
        sheildHist.savefig("sheild.png", "Exit sheild count")
        midSheildHist.savefig("midSheild.png", "Mid sheild count")
  
else: # optimization
    from Cinema.Prompt import Optimiser
    from Cinema.Prompt.dataReduction import tof2hw_INS, getPeakReso
    class CurveOpt(Optimiser):
        def __init__(self, sim):
            super().__init__(sim, 1e6)
            self.directions = ['maximize', 'minimize']
            # self.addParameter('cv', lower = 350*0.7, upper = 5000)
            # self.addParameter('ch', lower = 280*0.7, upper = 5000)
            # self.addParameter('pos_det', lower = 300, upper = 1000)

        def getTotalWeight(self):
            totweight = 0
            # print(f'# printing total weigth: {totweight}')
            for scor in sim.scorer.keys():
                hist = sim.gatherHistData(scor)
                if scor.startswith('WL'):
                    totweight += hist.getWeight().sum()
            return totweight
        
        def getResolution(self, r2, z2 = 260.):
            tofHist = None
            for scor in sim.scorer.keys():
                if scor.startswith('TOF'):
                    hist = sim.gatherHistData(scor)
                    if tofHist is None:
                        tofHist = hist
                    else:
                        tofHist.merge(hist)
            x,y = tof2hw_INS(z2, r2, tofHist.getCentre(), tofHist.getWeight())
            return getPeakReso(x, y)

            
        def objective(self, trial):
            self.sim.clear() 
            # pos_ana = trial.suggest_float('pos_ana', 300, 1000)
            pos_det = trial.suggest_float('pos_det', 550, 700)
            cur_h = trial.suggest_float('cur_h', 150, 800)
            cur_v = trial.suggest_float('cur_v', 180, 800)
            # trial.set_user_attr('constraint', (c))

            if True: # allowed space
                self.sim.clear()             
                self.sim.makeWorld(260, pos_det, cur_h, cur_v)
                self.sim.simulate(self.trailNeutronNum)
                return self.getTotalWeight(), self.getResolution().min()
            else:
                return self.trailNeutronNum
            
    sim = MySim(seed=1010)

    opt = CurveOpt(sim)
    # opt.visInitialGeometry()
    opt.optimize(name = 'BL6_detPos_anaCuv', n_trials = 2, storage='sqlite:///optuna_study.db')
    # print(opt.study.best_params, opt.study.best_value)
    # opt.analysis()


    # from botorch.settings import validate_input_scaling
    # import optuna
    # import numpy as np
    # sim = MySim()
    # incident = 1e5

    # from optuna import trial as trial_module
    # def objective(trial : trial_module.Trial) -> float:
    #     sim.clear() 
        
    #     g2_in  = trial.suggest_float("g2_in", 15, 50)
    #     g2_out = trial.suggest_float("g2_out", 15, 50)
    #     g3_in  = trial.suggest_float("g3_in", 15, 50)
    #     g3_out = trial.suggest_float("g3_out", 15, 50)
    #     g4_in  = trial.suggest_float("g4_in", 15, 50)
    #     g4_out = trial.suggest_float("g4_out", 15, 50)
    #     g5_in  = trial.suggest_float("g5_in", 15, 50)
    #     g5_out = trial.suggest_float("g5_out", 15, 50)
    #     g6_in  = trial.suggest_float("g6_in", 15, 50)
    #     g6_out = trial.suggest_float("g6_out", 15, 50)

        

    #     sim.makeWorld(g2_in, g2_out, g3_in, g3_out, g4_in, g4_out, g5_in, g5_out, g6_in, g6_out)
    #     # set gun
    #     gunCfg = "gun=UniModeratorGun;mean_wl=100;range_wl=99;src_w=100;src_h=100;src_z=0;slit_w=100;slit_h=100;slit_z=2250"
    #     sim.setGun(gunCfg)
    #     sim.simulate(incident)
    #     # sim.show(100)
    #     hist2 = sim.getScorerHist(sim.scorer['PSD2'])
    #     return -hist2.getWeight().sum() # it is a minimisation optimiser


    # if __name__ == "__main__":
    #     # Show warnings from BoTorch such as unnormalized input data warnings.
    #     validate_input_scaling(True)

    #     sampler = optuna.integration.BoTorchSampler(n_startup_trials=500,)

    #     study = optuna.create_study(
    #         directions=["minimize"],
    #         sampler=sampler,)
        
    #     study.optimize(objective, n_trials=100, timeout=6000)

    #     # print("Number of finished trials: ", len(study.trials))

    #     # print("Pareto front:")

    #     trials = sorted(study.best_trials, key=lambda t: t.values)

    #     for trial in trials:
    #         # print("  Trial#{}".format(trial.number))
    #         # print(
    #             "    Values: Values={}".format(
    #                 trial.values
    #             )
    #         )
    #         # print("    Params: {}".format(trial.params))