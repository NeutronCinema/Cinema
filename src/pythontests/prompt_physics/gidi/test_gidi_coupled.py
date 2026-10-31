#!/usr/bin/env python3
"""Coupled n-gamma transport anchor (P4.5b L3, 2026-10-31).

2.5 MeV isotropic neutron point source in a 15 cm water sphere, pure-gidi
neutron route (threshold<=0: ENDF free-gas thermal semantics; S(alpha,beta)
is NCrystal's job by mandate), gamma transport on so H1(n,g) 2.223 MeV
capture gammas enter the stack and are transported through the photo-atomic
route.

OpenMC 0.15.3 reference (same geometry, 200k source particles, official
endfb80-lowtemp library, no sab; harness /tmp/p45b_l3_openmc.py, record in
out/wikimaker/gidi_rewrite_plan.md 附10):

  n leakage fraction   0.5427          cinema 200k: 0.5449  (0.4%)
  n deposition eV/src  2.1497e6        cinema 200k: 2.1538e6 (0.19%)
  gamma yield          0.4497          cinema 200k: 0.4424  (1.6%)
  gamma leak spectrum  median 3.9% per bin (Compton tail agrees to 2.3%)
  gamma leaked energy  6.987e5 vs 6.982e5 eV/src (0.07%)
  gamma deposition     NOT comparable: this OpenMC build does not score
                       secondary-photon heating (collisions happen - the
                       leak spectrum is properly Compton-degraded - but the
                       recoil energy is never tallied). Cinema's 2.77e5
                       eV/src is corroborated by the source-photon benchmark
                       (2.223 MeV source deposits 732 keV/src) and an
                       independent hand integral.

The deposition seam flagged during L3 scoping (PTGIDIModel counts ekin+Q
minus secondary kinetic energy while the gamma is also stacked) is REFUTED
for capture at this kernel: dep_n agrees with OpenMC to 0.19%, where a Q
double count would add ~1 MeV (0.457 captures x 2.223 MeV).

The windows below anchor gross regressions only (losing the coupled chain,
double counting Q, losing capture gammas). Energy bookkeeping note: dep_n
includes the capture Q by convention on BOTH sides, so dep_n+dep_g+leaked
energies intentionally overshoots E0 by ~the created-gamma energy.
"""

import os

import numpy as np
import pytest

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Sphere
from Cinema.Prompt.scorer import ESpectrumHelper, DepositionHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.GidiSetting import GidiSetting

gidi = GidiSetting()

PTDATA = ('pops.xml', 'all.map')


@pytest.fixture(autouse=True)
def _require_ptdata():
    if not gidi.isCompiled:
        pytest.skip('gidi not compiled')
    cpath = os.environ.get('CINEMAPATH')
    if not cpath:
        pytest.skip('CINEMAPATH is not set')
    for f in PTDATA:
        p = os.path.join(cpath, 'external', 'ptdata', f)
        if not (os.path.isfile(p) and os.access(p, os.R_OK)):
            pytest.skip(f'gidi data not available: {p}')


class IsotropicNeutronGun(PythonGun):
    """2.5 MeV isotropic neutron pencil source at the origin."""

    def __init__(self, ekin):
        super().__init__(2112)
        self.ekin = ekin

    def samplePosition(self, num=None):
        self.pdata['pos'] = [0., 0., 0.]
        n = num if num is not None else 1
        u = np.random.uniform(-1., 1., n)
        phi = np.random.uniform(0., 2. * np.pi, n)
        s = np.sqrt(np.maximum(0., 1. - u * u))
        self.pdata['dir'] = np.stack([s * np.cos(phi), s * np.sin(phi), u], axis=1)

    def sampleEnergy(self, num):
        self.pdata['ekin'] = self.ekin


def _run_coupled(nprim, seed=1010):
    gidi.setEnableGidi(True)
    gidi.setGammaTransport(True)
    gidi.setGidiThreshold(-5)
    gidi.setGammaCutEkin(1000.)
    gidi.setEnableGidiPowerIteration(False)
    cpath = os.environ['CINEMAPATH']
    gidi.setGidiPops(os.path.join(cpath, 'external', 'ptdata', 'pops.xml'))
    gidi.setGidiMap(os.path.join(cpath, 'external', 'ptdata', 'all.map'))

    class CoupledSim(Prompt):
        def __init__(self):
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Sphere(0, 165))
            wat = Material('freegas::H2O/1gcm3')
            wat.setBiasAbsp(1)
            wat.setBiasScat(1)
            media = Volume('media', Sphere(0, 150), matCfg=wat)
            world.placeChild('media', media)
            ESpectrumHelper('nleak', min=1e-2, max=3e6, numbin=60,
                            pdg=2112, ptstate='EXIT').make(media)
            ESpectrumHelper('gleak', min=1e3, max=3e6, numbin=60,
                            pdg=22, ptstate='EXIT').make(media)
            DepositionHelper('ndep', min=1., max=3e6, numbin=120,
                             pdg=2112, ptstate='PEA_POST').make(media)
            DepositionHelper('gdep', min=1., max=3e6, numbin=120,
                             pdg=22, ptstate='PEA_POST').make(media)
            self.setWorld(world)

    sim = CoupledSim()
    sim.makeWorld()
    sim.simulate(IsotropicNeutronGun(2.5e6), nprim)
    return {name: sim.gatherHistData(name)
            for name in ('nleak', 'gleak', 'ndep', 'gdep')}


def test_l3_coupled_water_sphere_neutron_gamma():
    """L3 anchor: coupled n-gamma transport gross-regression windows.

    Reference values in the module docstring (200k OpenMC vs 200k cinema).
    The dep_n upper bound doubles as the Q-double-count regression anchor:
    a capture-Q double count would push dep_n to ~3.1e6 eV/src."""
    nprim = 20000
    h = _run_coupled(nprim)

    n_leak = h['nleak'].getTotalWeight() / nprim
    g_yield = h['gleak'].getTotalWeight() / nprim

    def dep_total(hist):
        w = np.ravel(np.asarray(hist.getWeight(), dtype=float))
        c = np.ravel(np.asarray(hist.getCentre(), dtype=float))
        return float(np.dot(c, w)) / nprim

    dep_n = dep_total(h['ndep'])
    dep_g = dep_total(h['gdep'])
    print(f'n_leak: {n_leak:.5f} (ref 0.5449)')
    print(f'g_yield: {g_yield:.5f} (ref 0.4424)')
    print(f'dep_n: {dep_n:.4g} eV/src (ref 2.1538e6, OpenMC 2.1497e6)')
    print(f'dep_g: {dep_g:.4g} eV/src (ref 2.7730e5)')

    assert 0.50 < n_leak < 0.59, 'neutron leakage off the coupled kernel'
    assert 0.40 < g_yield < 0.48, 'capture-gamma yield off the kernel'
    assert 1.9e6 < dep_n < 2.4e6, \
        'neutron deposition off the kernel (upper bound also catches a Q double count)'
    assert 1.5e5 < dep_g < 4.5e5, 'gamma deposition off the kernel'
    # leaked-energy sanity: the escape channels must carry plausible energy
    wn = np.ravel(np.asarray(h['nleak'].getWeight(), dtype=float))
    cen = np.ravel(np.asarray(h['nleak'].getCentre(), dtype=float))
    leaked_n = float(np.dot(cen, wn)) / nprim
    assert 2.5e5 < leaked_n < 5.0e5, 'leaked neutron energy off the kernel'
