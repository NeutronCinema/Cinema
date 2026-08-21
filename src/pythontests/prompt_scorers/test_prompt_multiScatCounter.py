#!/usr/bin/env python3

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Tube, Sphere
from Cinema.Prompt.scorer import ESpectrumHelper, MultiScatCounter
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import SimpleThermalGun
from Cinema.Prompt.GidiSetting import GidiSetting
import numpy as np


def test_prompt_multiScatCounter():
    cdata=GidiSetting()
    cdata.setEnableGidi(False)
    cdata.setGammaTransport(False)

    def test_direct_exit():
        class MySim(PromptMPI):
            def __init__(self, seed=4096) -> None:
                super().__init__(seed)   

            def makeWorld(self):
                length = 1e6
                world = Volume('world', Box(50, 50, length * 2 + 100))

                sample_mat = "void.ncmat"

                pensil = Volume('pensil', Tube(0,1e-9,length,), sample_mat)
                scatterCounter = MultiScatCounter()
                scatterCounter.make(pensil)

                world.placeChild('physicalSample', pensil, Transformation3D(z=length))

                self.setWorld(world)

        sim = MySim(seed=1010)
        sim.makeWorld()

        gun = SimpleThermalGun()
        gun.setEnergy(0.05)
        gun.setPosition([0,0,-150])


        if 0:
            partnum = 100
            sim.show(gun, partnum)
        else:
            partnum = 100
            sim.simulate(gun, partnum)

        dtt0 = sim.gatherHistData("ScatterCounter")
        score = dtt0.getWeight()
        print(score)
        np.testing.assert_allclose(score[2], 100.)
        sim.clear()


    def test_scatter_once():
        """Use a pensil model, all particle scatter once and exit"""
        g_scatNum = 1

        class MySim(PromptMPI):
            def __init__(self, seed=4096) -> None:
                super().__init__(seed)   

            def makeWorld(self):
                length = 1e6
                world = Volume('world', Box(50, 50, length * 2 + 100))

                sample_mat = 'physics=idealElaScat;xs_barn=1;density_per_aa3=0.01;energy_transfer_eV=0.01'

                pensil = Volume('pensil', Tube(0,1e-9,length,), sample_mat)
                scatterCounter = MultiScatCounter()
                scatterCounter.make(pensil)

                world.placeChild('physicalSample', pensil, Transformation3D(z=length))

                self.setWorld(world)

        sim = MySim(seed=1010)
        sim.makeWorld()

        gun = SimpleThermalGun()
        gun.setEnergy(0.05)
        gun.setPosition([0,0,-150])


        if 0:
            partnum = 100
            sim.show(gun, partnum)
        else:
            partnum = 100
            sim.simulate(gun, partnum)

        dtt0 = sim.gatherHistData("ScatterCounter")
        score = dtt0.getWeight()
        print(score)
        np.testing.assert_allclose(score[3], 100.)
        sim.clear()

    def test_scatter_twice():
        """Use a perfect scatter and a reflector model, all particle must scatter twice to exit"""
        g_scatNum = 1
        class MySim(PromptMPI):
            def __init__(self, seed=4096) -> None:
                super().__init__(seed)   

            def makeWorld(self):
                length = 20000
                world = Volume('world', Box(10000, 10000, length * 2 + 10000))

                sample_mat = 'physics=idealElaScat;xs_barn=100000;density_per_aa3=10000;energy_transfer_eV=0.01'
                surf_cfg = "physics=EnergyReflector;ekin=0.031;islessthan=0" # reflect particles whose energy > 0.031

                sample = Volume('samplebox', Tube(1000,1000,1000), sample_mat)
                reflector = Volume('reflector', Sphere(2000,2000+1e-6,0, 360, 0, 180-0.001), "void.ncmat", surf_cfg)
                reflector2 = Volume('reflector2', Box(1,1,1e-3), "void.ncmat", surf_cfg)

                scatterCounter = MultiScatCounter()
                scatterCounter.make(sample)

                world.placeChild('sample', sample)
                world.placeChild('reflector', reflector, Transformation3D(z=0))
                world.placeChild('reflector2', reflector2, Transformation3D(z=1800).applyRotX(45))

                self.setWorld(world)

        sim = MySim(seed=1010)
        sim.makeWorld()

        gun = SimpleThermalGun()
        gun.setEnergy(0.05)
        gun.setPosition([0,0,-150])


        if 0:
            partnum = 1
            sim.show(gun, partnum)
        else:
            partnum = 10 # keep it small to avoid long simulation
            sim.simulate(gun, partnum)

        dtt0 = sim.gatherHistData("ScatterCounter")
        score = dtt0.getWeight()
        print(score)

        # must scatter twice
        np.testing.assert_allclose(score[4], 10.)
        # when a particle scatter twice, it must scatter once before
        np.testing.assert_allclose(score[3], 10.)
        sim.clear()

    def test_direct_absorb():
        class MySim(PromptMPI):
            def __init__(self, seed=4096) -> None:
                super().__init__(seed)   

            def makeWorld(self):
                length = 5
                world = Volume('world', Box(50, 50, length * 2 + 100))

                sample_mat = "B4C_sg166_BoronCarbide.ncmat"

                sample = Volume('sample', Tube(0,5,length,), sample_mat)
                scatterCounter = MultiScatCounter()
                scatterCounter.make(sample)

                world.placeChild('physicalSample', sample, Transformation3D(z=length))

                self.setWorld(world)

        sim = MySim(seed=1010)
        sim.makeWorld()

        gun = SimpleThermalGun()
        gun.setWavelength(8)
        gun.setPosition([0,0,-100])


        if 0:
            partnum = 100
            sim.show(gun, partnum)
        else:
            partnum = 100
            sim.simulate(gun, partnum)

        dtt0 = sim.gatherHistData("ScatterCounter")
        score = dtt0.getWeight()
        print(score)
        np.testing.assert_allclose(score[2], 100.)
        sim.clear()


