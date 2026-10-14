#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box,Tube, Sphere, SolidIntersection, SolidUnion, SolidSubtraction
from Cinema.Prompt.scorer import makePSD, ESpectrumHelper, WlSpectrumHelper, TOFHelper, VolFluenceHelper
from Cinema.convertor import wl2ekin
from Cinema.Prompt.physics import Material, Mirror
from Cinema.Prompt.gun import IsotropicGun, PythonGun

import numpy as np

from Cinema.Prompt.GidiSetting import GidiSetting 
from testsuite import skip_test_gidi_not_compile


def test_simulation():
    skip_test_gidi_not_compile()
    cdata=GidiSetting()
    cdata.setGidiThreshold(5)
    cdata.setEnableGidi(True)
    cdata.setEnableGidiPowerIteration(False)
    cdata.setGammaTransport(False)

    class MySim(Prompt):
        def __init__(self, seed=4096, test_geo=False) -> None:
            super().__init__(seed)   
            self.test_geo = test_geo

        def makeWorld(self):
            self.clear()
            world = Volume("world", Box(400, 400, 400))

            # no embedded quotes: NCrystal (and its python-side pre-check)
            # rejects "'" in configuration strings
            lw = Material('LiquidWaterH2O_T293.6K.ncmat;density=1gcm3')
            if self.test_geo:
                ssphere = Sphere(0, 300)
                sbox = Box(100, 100, 100)
                solid = SolidIntersection(ssphere, sbox, Transformation3D(0,0,0,0,0,0))
            else:
                solid = Box(100, 100, 100)     

            vwater = Volume("water", solid, matCfg=lw)
            world.placeChild('water', vwater)

            VolFluenceHelper('spct', max=20, numbin=300 ).make(vwater)
            self.setWorld(world)

    gun = IsotropicGun()
    gun.setEnergy(1)

    # geo under test
    sim = MySim(test_geo=True)
    sim.makeWorld()

    partnum = 1e3
    sim.simulate(gun, partnum)
    spct = sim.gatherHistData('spct')
    sum1 = spct.getWeight().sum()
    # Pins re-recorded 2026-10-11 on the gidi-enabled baseline (gidiplus 3.28.22,
    # external/ptdata GNDS-2.0 endf80, current NCrystal). The 2024-10-24 pins
    # (0.05853522444914256 / 0.06053628305891873) predate NCrystal/gidi drift;
    # their 3.4% spread was RNG-stream vintage, not geometry: sphere(300) n box
    # (100) IS box(100), so sum1 and sumref must agree to numerical noise.
    # 2026-10-12: VolFluence now accumulates raw track length, so the pins are
    # the 2026-10-11 fluence values times the volume 200^3 = 8e6 mm^3 (Box takes
    # half-lengths). Divide the histogram by vol.getCapacity() for the fluence.
    np.testing.assert_allclose(sum1, 473843.23441)

    # geo reference
    sim.clear()
    sim.test_geo=False
    sim.makeWorld()

    sim.simulate(gun, partnum)
    spct = sim.gatherHistData('spct')
    sumref = spct.getWeight().sum()
    np.testing.assert_allclose(sumref, 473843.2344021093)  # 0.059230404300263766 * 8e6
    # semantic anchor: SolidIntersection must reproduce the equivalent solid.
    # Tightened from rtol=1e-5 (2026-10-11): the old scorer normalised by the
    # VecGeom capacity, whose ~3e-6 numerical error for the intersection shape
    # was baked into sum1; raw track length removes that noise entirely.
    np.testing.assert_allclose(sum1, sumref, rtol=1e-9)

    print(sum1, sumref)
