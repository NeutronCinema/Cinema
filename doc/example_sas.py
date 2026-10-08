#!/usr/bin/env python3
#
# Small angle scattering (SAS) example with the SasCSNS NCrystal plugin.
#
# The sample is a thin slab of amorphous SiO2 spheres of 100 Angstrom radius
# (see ncmat/sascsns_sio2_spheres.ncmat, @CUSTOM_SASCSNS section). A 9
# Angstrom neutron beam hits the sample, and a 2D PSD one metre downstream
# records the small angle scattering ring around the direct beam.
#
# Requires the SasCSNS plugin to be installed in the NCrystal environment.
#
# Run:  python3 doc/example_sas.py

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import PSDHelper

class Simulation(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)

    def makeWorld(self):
        # material carrying the SasCSNS small angle scattering model
        mat = Material('sascsns_sio2_spheres.ncmat')

        # 1 mm thick sample slab
        sample = Volume("sample", Box(10, 10, 1), matCfg=mat.cfg)

        # PSD detector 1 m downstream, 200x200 bins over +-100 mm
        detector = Volume('detector', Box(200, 200, 0.1))
        psd = PSDHelper('sansPSD', xmin=-100, xmax=100, xnumbin=200,
                        ymin=-100, ymax=100, ynumbin=200)
        psd.make(detector)

        world = Volume("world", Box(300, 300, 2200))
        world.placeChild("samplePhyVol", sample)
        world.placeChild("detectorPhyVol", detector, Transformation3D(0, 0, 1000))

        self.setWorld(world)

if __name__ == "__main__":
    # 9 Angstrom neutron beam along +z
    gunCfg = "gun=SimpleThermalGun;position=0,0,-999;direction=0,0,1;energy=1e-3"

    sim = Simulation()
    sim.makeWorld()

    # to visualize geometry and trajectories:
    # sim.show(gunCfg, 100)

    # production run
    sim.simulate(gunCfg, 100000)

    # save the 2D PSD histogram: the SANS ring shows up around the direct beam
    hist = sim.gatherHistData('sansPSD')
    hist.savefig('sas_psd.png', title='SiO2 spheres, R=100 AA, 9 AA beam')
