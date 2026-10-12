#!/usr/bin/env python3

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Sphere
from Cinema.Prompt.scorer import VolFluenceHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting 
from testsuite import *
import numpy as np


def test_simulation():
    skip_test_gidi_not_compile()
    cdata=GidiSetting()
    cdata.setEnableGidi(True)
    cdata.setGammaTransport(False)

    class MySim(Prompt):
        def __init__(self, seed=4096, **kwargs) -> None:
            super().__init__(seed, **kwargs)

        def makeWorld(self):

            world = Volume("world", Box(400, 400, 400))

            lw = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16')
            lw.setBiasScat(1.)
            lw.setBiasAbsp(1.)
            sphere = Volume("sphere", Sphere(0, 300), matCfg=lw)
            world.placeChild('sphere', sphere)

            VolFluenceHelper('spct', 1e-6, 20e6, 100).make(sphere)
            self.setWorld(world)

    sim = MySim(seed=1010)
    sim.makeWorld()

    gun = IsotropicGun()
    gun.setEnergy(1)

    partnum = 100
    sim.simulate(gun, partnum)

    spct = sim.gatherHistData('spct')
    print(spct.getWeight().sum())
    print(spct.getHit().sum())

    # Pin re-recorded 2026-10-11 on the gidi-enabled baseline (gidiplus 3.28.22,
    # external/ptdata GNDS-2.0 endf80). The 2024-10-24 pin 0.0004503254359124584
    # predates two legitimate drifts: NCrystal version drift (pure-NCrystal value
    # moved by 0.77%) and the ENDF80-gidi-above-5eV hybrid contribution (the mode
    # difference itself is ~10%). Both modes are pinned in the two tests below,
    # giving the gidi mode-influence axis its own regression anchors.
    # Re-recorded again 2026-10-12 for gidiplus 3.35 (P1.2/P1.4): dual-library
    # check confirms the 3.28 .so still reproduces the 2026-10-11 pin; the 3e-11
    # relative shift is attributed to the 3.35 sampling-internal restructure.
    # Re-recorded a third time 2026-10-12: VolFluence now accumulates RAW track
    # length, so the pin is the old fluence 0.0004055407043858582 times the
    # sphere volume 4/3*pi*300^3 (the 9e-9 relative residual of that product is
    # the old code's VecGeom capacity lookup vs the analytic volume). Divide the
    # histogram by vol.getCapacity() to recover the old fluence scale.
    np.testing.assert_allclose(spct.getWeight().sum(), 45865.57311468873, rtol=1e-15)


def test_simulation_pure_ncrystal():
    # Same geometry/source as test_simulation but with gidi disabled: the whole
    # energy range is handled by NCrystal. Anchor for the mode-influence axis
    # (D2): separates NCrystal-version drift from gidi physics when a pin moves.
    skip_test_gidi_not_compile()
    cdata=GidiSetting()
    cdata.setEnableGidi(False)
    cdata.setGammaTransport(False)

    class MySim(Prompt):
        def __init__(self, seed=4096, **kwargs) -> None:
            super().__init__(seed, **kwargs)

        def makeWorld(self):

            world = Volume("world", Box(400, 400, 400))

            lw = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16')
            lw.setBiasScat(1.)
            lw.setBiasAbsp(1.)
            sphere = Volume("sphere", Sphere(0, 300), matCfg=lw)
            world.placeChild('sphere', sphere)

            VolFluenceHelper('spct', 1e-6, 20e6, 100).make(sphere)
            self.setWorld(world)

    sim = MySim(seed=1010)
    sim.makeWorld()

    gun = IsotropicGun()
    gun.setEnergy(1)

    partnum = 100
    sim.simulate(gun, partnum)

    spct = sim.gatherHistData('spct')

    # 2026-10-12 re-pin for raw-track-length VolFluence: old fluence pin
    # 0.0004468548744264139 x 4/3*pi*300^3 (see the twin test above)
    np.testing.assert_allclose(spct.getWeight().sum(), 50538.0956658772, rtol=1e-15)
