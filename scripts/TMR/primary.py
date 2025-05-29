#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube
from Cinema.Prompt.scorer import  ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper, PSDHelper
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import UniModeratorGun
from Cinema.Prompt.GidiSetting import GidiSetting 

import numpy as np

cdata=GidiSetting()
cdata.setGidiThreshold(-5)
cdata.setEnableGidi(True)
cdata.setGammaTransport(True)
cdata.setGidiPops("/home/panzy/project/ml/external/ptdata/pops_added2.xml")

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def make_symetric_vol(self, ):
        pass

    def makeWorld(self):
        # >>> set material
        void = "void.ncmat"
        mat_aluminium =         "Al_sg225.ncmat"
        mat_chm_water =         "LiquidWaterH2O_T293.6K.ncmat"
        mat_prem_water =        "LiquidWaterH2O_T293.6K.ncmat"
        mat_reflector_be =      "Be_sg194.ncmat"
        mat_reflector_fe =      "freegas::Fe/7.874gcm3/Fe_is_Fe56"
        mat_target_w =          "W_sg229.ncmat"
        # >>> CHM 
        chmdim_radius = 75
        chmdim_height = 100 * 0.5 # half height
        chmdim_shell_thickness = 4

        vol_chm_water = Volume("vol_chm_water", Tube(0, chmdim_radius, chmdim_height), mat_chm_water)
        vol_chm_Alshell = Volume("vol_chm_Alshell", Tube(0, chmdim_radius+chmdim_shell_thickness, chmdim_height+chmdim_shell_thickness), mat_aluminium)
        vol_chm_Alshell.placeChild("pv_chm_water", vol_chm_water, )


        # >>> premoderator
        prem_top_r = chmdim_radius + 10
        prem_top_h = 20 * 0.5

        prem_side_rin = chmdim_radius
        prem_side_rext = chmdim_radius + 10
        prem_side_h = chmdim_height + chmdim_shell_thickness
        prem_side_starta = 0
        prem_side_deltaa = 120

        prem_bot_r = prem_top_r
        prem_bot_h = 10 * 0.5

        chm_central_plane = prem_bot_h-prem_top_h

        vol_prem_top = Volume("vol_prem_top", Tube(0, prem_top_r, prem_top_h),mat_prem_water)
        vol_prem_side = Volume("vol_prem_side", Tube(prem_side_rin, prem_side_rext, prem_side_h, prem_side_starta, prem_side_deltaa),mat_prem_water)
        vol_prem_bot = Volume("vol_prem_bot", Tube(0, prem_bot_r, prem_bot_h),mat_prem_water)

        # >>> prem al shell
        premsh_t = 8
        premsh_r = prem_top_r + premsh_t
        premsh_h = chmdim_height + chmdim_shell_thickness +prem_top_h +  prem_bot_h + premsh_t
        vol_premo_shell = Volume("vol_premo_shell", Tube(0, premsh_r, premsh_h),mat_aluminium)

        # >>> beam channel taken from Al shell 
        beamc_rin = prem_side_rin
        beamc_rext = prem_side_rext + premsh_t
        beamc_h = prem_side_h
        beamc_starta = prem_side_deltaa
        beamc_deltaa = 180 - beamc_starta
        vol_beamc_inshell = Volume("vol_beamc_inshell", Tube(beamc_rin, beamc_rext, beamc_h, beamc_starta, beamc_deltaa),void)

        
        vol_premo_shell.placeChild("pv_moderater", vol_chm_Alshell, Transformation3D(z=chm_central_plane))
        vol_premo_shell.placeChild("pv_prem_top", vol_prem_top, Transformation3D(z=premsh_h-prem_top_h-premsh_t))
        vol_premo_shell.placeChild("pv_prem_bot", vol_prem_bot, Transformation3D(z=-premsh_h+prem_bot_h+premsh_t))
        vol_premo_shell.placeChild("pv_side_1", vol_prem_side, Transformation3D(z=chm_central_plane))
        vol_premo_shell.placeChild("pv_side_2", vol_prem_side, Transformation3D(z=chm_central_plane).applyRotZ(180))
        vol_premo_shell.placeChild("pv_beamc_1", vol_beamc_inshell, Transformation3D(z=chm_central_plane))
        vol_premo_shell.placeChild("pv_beamc_2", vol_beamc_inshell, Transformation3D(z=chm_central_plane).applyRotZ(180))

        # >>> Be reflector wing
        beref_rin = 121.5
        beref_rext = 270.
        beref_h = premsh_h
        beref_starta = prem_side_starta
        beref_deltaa = prem_side_deltaa
        vol_beref = Volume("vol_beref_wing", Tube(beref_rin, beref_rext, beref_h, beref_starta, beref_deltaa), mat_reflector_be)

        # >>> Be reflector bot
        botberef_rin = 0
        botberef_rext = beref_rext
        botberef_h =  (192.0 - 79.0 ) * 0.5
        botberef_zplane = - beref_h - botberef_h
        vol_botberef = Volume("vol_botberef", Tube(botberef_rin, botberef_rext, botberef_h),mat_reflector_be)

        # >>> Fe 316 wing
        fe316_wing_rin = beref_rext
        fe316_wing_rext = 500.
        fe316_wing_h = beref_h
        fe316_wing_starta = prem_side_starta
        fe316_wing_deltaa = prem_side_deltaa
        vol_fe316_wing = Volume("vol_fe316_wing", Tube(fe316_wing_rin, fe316_wing_rext, fe316_wing_h, fe316_wing_starta, fe316_wing_deltaa),mat_reflector_fe)

        # >>> Fe 316 wing bot
        wingbot_fe316_rin = beref_rext
        wingbot_fe316_rext = fe316_wing_rext
        wingbot_fe316_h = botberef_h
        wingbot_fe316_zplane = botberef_zplane
        vol_wingbot_fe316 = Volume("vol_wingbot_fe316", Tube(wingbot_fe316_rin, wingbot_fe316_rext, wingbot_fe316_h),mat_reflector_fe)

        # >>> Fe 316 wing bot bot
        wbb_fe316_rin = 0.
        wbb_fe316_rext = wingbot_fe316_rext
        wbb_fe316_h = (- 350. - -460. ) * 0.5
        wbb_zplane = wingbot_fe316_zplane - wbb_fe316_h - wingbot_fe316_h
        vol_wbb_fe316 = Volume("vol_wbb_fe316", Tube(wbb_fe316_rin, wbb_fe316_rext, wbb_fe316_h), mat_reflector_fe)

        # >>> Bottom part box 
        botpart_rin = 0.
        botpart_rext = wbb_fe316_rext
        botpart_h = wbb_fe316_h + wingbot_fe316_h + fe316_wing_h
        vol_botpart = Volume("vol_botpart", Tube(botpart_rin, botpart_rext, botpart_h), void)

        botpart_zplane_insimbox = (89. - 139.) - botpart_h
        premo_zplane_inbotpart = botpart_h - premsh_h
        
        vol_botpart.placeChild("pv_preMplusM", vol_premo_shell, Transformation3D(z=premo_zplane_inbotpart))

        vol_botpart.placeChild("pv_beref_1", vol_beref, Transformation3D(z=premo_zplane_inbotpart))
        vol_botpart.placeChild("pv_beref_2", vol_beref, Transformation3D(z=premo_zplane_inbotpart).applyRotZ(180))
        vol_botpart.placeChild("pv_botberef", vol_botberef, Transformation3D(z=premo_zplane_inbotpart + botberef_zplane))

        vol_botpart.placeChild("pv_fe316_wing1", vol_fe316_wing, Transformation3D(z=premo_zplane_inbotpart))
        vol_botpart.placeChild("pv_fe316_wing2", vol_fe316_wing, Transformation3D(z=premo_zplane_inbotpart).applyRotZ(180))
        vol_botpart.placeChild("pv_wingbot_fe316", vol_wingbot_fe316, Transformation3D(z=premo_zplane_inbotpart + wingbot_fe316_zplane))
        vol_botpart.placeChild("pv_wbb_fe316", vol_wbb_fe316, Transformation3D(z=premo_zplane_inbotpart + wbb_zplane))

        # >>> target W 
        target_x = (654.4 - -89.8) * 0.5
        target_z = (85. - -85.) * 0.5
        target_y = 35. 
        vol_target = Volume("vol_target", Box(target_x,target_y,target_z),mat_target_w)
        ztrf_in_simbox = target_x - 89.8


        # >>> 
        para_box_size = 1000
        para_world_size = para_box_size + 200
        para_globalpsd_size = 600
        para_res = 5 
        para_bin = int(para_box_size / (para_res) * 5 )
       
        cfg_void = "void.ncmat"
        cfg_universe = 'freegas::H1/1e-26kgm3'

        universe = Material(cfg_void)
        world = Volume("world", Box(para_world_size , para_world_size, para_world_size), matCfg=void)
        simbox = Volume("simbox", Box(para_box_size, para_box_size, para_box_size), matCfg=void)
        simbox.placeChild("pv_botpart", vol_botpart, Transformation3D(z=botpart_zplane_insimbox).applyRotZ(60))
        simbox.placeChild("pv_target", vol_target, Transformation3D(y=-ztrf_in_simbox).applyRotX(90).applyRotY(90)) #fixme

        name_moderator = 'moderator'
        mat_moderator = Material('LiquidWaterH2O_T293.6K.ncmat;density=1gcm3;temp=293.6')
        sol_moderator = Tube(0, 90, 80)
        vol_moderator = Volume(f"vol_{name_moderator}", sol_moderator, universe)
        # simbox.placeChild(f"pv_{name_moderator}", vol_moderator, Transformation3D().applyRotX(90))
        
        detector2 = Volume("det2", Box(35, 35, 0.0001))
        ESpectrumHelper('espec').make(detector2)
        WlSpectrumHelper('wlspec').make(detector2)
        TOFHelper('tof').make(detector2)

        obxz = PSDHelper('PSDXZ',-para_globalpsd_size,para_globalpsd_size,para_bin,-para_globalpsd_size,para_globalpsd_size,para_bin,ptstate='ENTRY',psdtype='XZ',isGlobal=True)
        allvol = []
        for vol in Volume.volume_list:
            obxz.make(vol)

        world.placeChild("pv_simulation_box", simbox, Transformation3D().applyRotX(-90))
        self.setWorld(world)


class PositionTestGun(PythonGun):
    def samplePosition(self):
        x = np.random.uniform(-600,600)
        return np.array([x, -100, -700])

    def sampleDirection(self):
        x = np.random.uniform(-1,1)
        return np.array([x, 0, 1])
    
    def sampleEnergy(self):
        x = np.random.uniform(0.9,1)
        return x * 20e6

class TestGun(PythonGun):
    def samplePosition(self):
        return np.array([0, 0, -500])

    def sampleDirection(self):
        x = np.random.uniform(-1,1)
        return np.array([0, 0, 1])
    
    def sampleEnergy(self):
        x = np.random.uniform(0.9,1)
        return x * 20e6
    

# gun = PositionTestGun()
gun = TestGun()

sim = MySim(seed=1010)
sim.makeWorld()


# vis or production
if True:
    sim.show(gun, 1, byMat=1, mergeMesh=0, addLegend=1, geoClip=1)
else:
    sim.simulate(gun, 100)
    draw_xz = sim.gatherHistData('PSDXZ')
    destination = 0
    # if sim.rank==destination:
        # draw_xz.plot(1)