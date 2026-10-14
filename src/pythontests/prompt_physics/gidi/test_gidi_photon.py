#!/usr/bin/env python3
"""End-to-end photon transport tests on the gidi photo-atomic models.

Regression anchor for the 2026-10-13 photon-unblock round: gammaTransport
used to segfault at the first photon collision in any material (the gidi map
hands back a ProtareSingle for element entries and the factory cast it to
ProtareComposite), the atomic data was double-counted by both passes, and
there was no production threshold for low-energy photons.
"""

import os

import numpy as np
import pytest

from Cinema.Prompt import Prompt
from Cinema.Prompt.compoundModel import ModelCollection
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Sphere
from Cinema.Prompt.scorer import ESpectrumHelper, DepositionHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.GidiSetting import GidiSetting

gidi = GidiSetting()

PTDATA = ('pops.xml', 'all.map')


def _ptdata_paths():
    cpath = os.environ.get('CINEMAPATH')
    if not cpath:
        pytest.skip('CINEMAPATH is not set')
    return {f: os.path.join(cpath, 'external', 'ptdata', f) for f in PTDATA}


@pytest.fixture(autouse=True)
def _require_photon_data():
    """The photon tests need the full data root: the reduced neutron
    testdata map has no photo-atomic entries."""
    if not gidi.isCompiled:
        pytest.skip('gidi not compiled')
    for f, p in _ptdata_paths().items():
        if not (os.path.isfile(p) and os.access(p, os.R_OK)):
            pytest.skip(f'gidi photon data not available: {p}')


def _configure_photons(cutoff=1000.):
    """Configure the GidiSetting singleton. The cutoff is set explicitly on
    every call: the setting lives in a process-wide singleton, so leaving it
    from a previous test would leak into the next one."""
    gidi.setEnableGidi(True)
    gidi.setGidiThreshold(-5)  # pure gidi: no NCrystal channel at any energy
    gidi.setGammaTransport(True)
    gidi.setGammaCutEkin(cutoff)
    paths = _ptdata_paths()
    gidi.setGidiPops(paths['pops.xml'])
    gidi.setGidiMap(paths['all.map'])


class GammaGun(PythonGun):
    """A monochromatic photon pencil gun at the origin, along +z."""

    def __init__(self, ekin):
        super().__init__(pdg=22)
        self.ekin = ekin

    def samplePosition(self, num=None):
        self.pdata['pos'] = [0., 0., 0.]
        self.pdata['dir'] = [0., 0., 1.]

    def sampleEnergy(self, num):
        self.pdata['ekin'] = self.ekin


def _run_photons(ekin, nprim=20000, radius=150., seed=1010, cutoff=1000.):
    """Transport nprim gammas of ekin eV through a water sphere (mm, eV).

    Returns (absorb_hist, exit_hist): the ABSORB-state deposition histogram
    (pdg 22) and the EXIT-state energy spectrum (pdg 22).
    """
    _configure_photons(cutoff=cutoff)

    class PhotonSim(Prompt):
        def __init__(self):
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Sphere(0, radius * 1.2))
            lw = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16')
            lw.setBiasAbsp(1)
            lw.setBiasScat(1)
            media = Volume('media', Sphere(0, radius), matCfg=lw)
            world.placeChild('media', media)
            DepositionHelper('dep', min=0., max=ekin * 1.2, numbin=60,
                             pdg=22, ptstate='ABSORB', log=False).make(media)
            ESpectrumHelper('espec', min=1., max=ekin * 1.2, numbin=60,
                            pdg=22, ptstate='EXIT', log=False).make(media)
            self.setWorld(world)

    sim = PhotonSim()
    sim.makeWorld()
    sim.simulate(GammaGun(ekin), nprim)
    return sim.gatherHistData('dep'), sim.gatherHistData('espec')


def test_gamma_transport_water_smoke():
    """1 MeV gammas in water: the formerly segfaulting path end to end.

    The atomic data must be registered exactly once (isotope pass photonuclear
    only, element pass photo-atomic only), so both absorption and escape
    happen at physical rates and nothing crashes. The absolute per-atom cross
    sections are pinned separately (test_photoatomic_absolute_xs).
    """
    dep, espec = _run_photons(1e6, nprim=20000, radius=150.)
    absorbed = dep.getTotalWeight()
    escaped = espec.getTotalWeight()
    print(f'absorbed: {absorbed}, escaped: {escaped}')
    assert absorbed > 0., 'no photon was absorbed: photo-atomic data missing?'
    assert escaped > 0., 'no photon escaped a 15 cm water sphere at 1 MeV: transport broken?'


def test_sub_kev_photons_absorb_locally():
    """500 eV photons sit below the 1 keV production default cutoff: they
    must all die inside the sphere and none may leave. (At 500 eV a working
    cutoff is indistinguishable from plain photo-atomic absorption, which
    deposits identically; the sharp cutoff-specific anchor is
    test_gamma_cutoff_kills_above_primary. This test pins the sub-keV
    transport behaviour end to end.)"""
    dep, espec = _run_photons(500., nprim=5000, radius=50.)
    assert dep.getTotalWeight() == pytest.approx(5000.)
    assert espec.getTotalWeight() == 0., 'a sub-cutoff photon escaped: transport broken?'
    # all weight in the bin holding 500 eV
    w = np.asarray(dep.getWeight())
    edges = np.asarray(dep.getEdges())
    hit = (edges[:-1] <= 500.) & (edges[1:] >= 500.)
    assert w[hit].sum() == pytest.approx(5000.), \
        'deposition of sub-cutoff photons is not their full energy'


def test_gamma_cutoff_kills_above_primary():
    """The sharp regression anchor for the cutoff block itself: with the cut
    ABOVE the primary energy, every photon must die at its FIRST collision
    depositing exactly its full energy. No other physics state produces
    that: without the cutoff, Compton scatters deposit small fractions first
    (spreading the histogram) and photons cross the boundary uncollided (the
    kill only happens at a collision). 50 keV primaries in a 50 cm water
    sphere: the uncollided-escape probability is ~1e-5 per photon, zero in
    this seeded run; the defaults check needs a pristine singleton, hence
    before _configure_photons (tests run forked)."""
    assert gidi.getGammaCutEkin() == pytest.approx(1000.), \
        'gammaCutEkin default is not 1 keV'
    ekin = 5e4
    nprim = 2000
    dep, espec = _run_photons(ekin, nprim=nprim, radius=500., cutoff=1e6)
    assert espec.getTotalWeight() == 0., \
        'a photon left the sphere uncollided although every collision kills'
    # the deposition histogram is event-weighted (one count per deposition):
    # every primary must die inside
    assert dep.getTotalWeight() == pytest.approx(nprim), \
        'not every photon was killed inside the sphere'
    # and every deposition in exactly the bin holding the primary energy:
    # a first-collision kill deposits the full energy, a sampled scatter
    # channel would spread counts over the partial bins below it
    w = np.asarray(dep.getWeight())
    edges = np.asarray(dep.getEdges())
    hit = (edges[:-1] <= ekin) & (edges[1:] >= ekin)
    assert w[hit].sum() == pytest.approx(nprim, rel=1e-9), \
        'deposition spread over partial-scatter bins: cutoff not applied?'


def test_photoatomic_absolute_xs():
    """Per-atom photo-atomic totals through the ModelCollection user path,
    pinned against xraylib 4.3 (EPDL97 lineage, independent of the gidi
    endf80_g files; measured agreement 0.4-1.1% at these points). Reverting
    the atomic-data double-count fix (both passes atomic) doubles the totals
    and fails here; so would a lost photo-atomic model."""
    _configure_photons(cutoff=0.)
    cases = [
        # cfg, ekin (eV), reference per-atom xs (barn)
        ("physics=ncrystal;nccfg='freegas::H/1gcm3/H_is_H1'", 1e3, 12.08),
        ("physics=ncrystal;nccfg='freegas::O/1gcm3/O_is_O16'", 1e4, 158.2),
    ]
    for cfg, ekin, ref in cases:
        mc = ModelCollection(cfg)
        xs = mc.xs(ekin, pdg=22)
        print(f'{cfg} xs({ekin:g} eV) = {xs:.5g} barn (reference {ref} barn)')
        assert xs == pytest.approx(ref, rel=0.05), \
            f'photo-atomic xs for {cfg} at {ekin} eV off reference'
