# Live-transport coverage for the scorer families that
# test_scorer_helpers.py (pure ctypes argument-order fakes) and
# test_fix_scorer.py (pure Python validation) deliberately do not touch:
# each test here runs a real simulation and pins the resulting histogram.
#
# Every sim uses a pencil beam of identical primaries (PythonGun with
# constant kinematics, vectorised batches), so all pins are closed-form:
# the flight geometry is one straight segment, nothing scatters in vacuum,
# and every particle produces exactly the same score. The binning math
# mirrored from the C++ side is
#     linear bins:  idx = floor((val - xmin) * nbins / (xmax - xmin))
#     log    bins:  idx = floor((log10(val) - log10(xmin)) * nbins
#                              / (log10(xmax) - log10(xmin)))
# and the physics constants are the ones from PTUnitSystem.hh
# (mm / eV / s internally; ekin2wl: E[eV] = 0.081804209605330899/wl^2).
#
# Conventions that the pins depend on (all verified against the C++
# scorers in src/cxx/Ana/libsrc):
# - a Box is built from half-lengths, so Box(10, 10, 2) spans 4 mm in z;
# - ENTRY/EXIT are scored exactly at the crossed faces;
# - TOF starts at the gun time (pdata['t'] = 0 here);
# - WlSpectrum scores ekin2wl(EKin), TOF scores getTime(),
#   ESpectrum scores EKin (or EKin0-EKin with energyTransfer),
#   Deposition scores getDeposition() (always 0 unless a process
#   registers one - no production process does);
# - VolFluence (PEA_PRE) weights each fill with step_length/V, so the
#   total weight of a straight-through beam is exactly N*L/V;
# - DeltaMomentum (DirectSqHelper) fills weight/Q, skipping Q == 0;
# - DirectSqw's x axis is Q (num_qbin bins) and its y axis is the energy
#   transfer mean_ekin - ekin with ekin reconstructed from time-of-flight
#   after subtracting the moderator->sample L1 time;
# - Angular scores the angle between the flight direction and beam_dir
#   (degrees with inDegree=yes, else the cosine mu);
# - WlAngle's x axis is ekin2wl(EKin0) (method=0) or the static-approx
#   wavelength (method=1) and its y axis is the angle between
#   (position - sample_pos) and beam_dir;
# - MultiScat counters score the per-particle scattering count, Split
#   scales the weight by 1/split and clones the track, RotatingObj scores
#   the comoving energy E0 + 0.5*m*(omega*rho)^2 of the rotating frame.
#
# The Launcher is a process-global singleton (one world per process), so
# every simulation test relies on the pytest --forked run mode. All sim
# bodies measure in the 10-60 ms range with 2000 primaries; they are
# marked medium per the conftest tier table (real simulations).

import math

import numpy as np
import pytest

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.scorer import (
    DepositionHelper,
    DirectSqHelper,
    DirectSqwHelper,
    ESpectrumHelper,
    MultiScatCounter,
    PSDHelper,
    TOFHelper,
    VolFluenceHelper,
    WlSpectrumHelper,
)

# --- shared physics constants (mirrored from PTUnitSystem.hh / PTMath.icc)

WL0 = 1.83                                             # beam wavelength [Aa]
E0 = 0.081804209605330899 / WL0**2                     # ekin [eV]
C_MM = 2.99792458e11                                   # c [mm/s]
M_EVC2 = 1.00866491588 * 931494095.17 / C_MM**2        # m_n [eV/(mm/s)^2]
V0 = math.sqrt(2 * E0 / M_EVC2)                        # beam speed [mm/s]
K0 = 2 * math.pi / WL0                                 # beam wavenumber [1/Aa]

NPRIM = 2000                                           # primaries per sim
SEED = 20261011

# geometry of the straight-through worlds: gun on the z axis, plate centred
# at z=141 built from half-lengths -> entry face z=139, exit face z=143
PLATE_ZC = 141.0
Z_ENTRY = 139.0
Z_EXIT = 143.0
THICK = Z_EXIT - Z_ENTRY

# 50-degree calibration beam used by the Q/angle family
THETA = math.radians(50.0)
ST, CT = math.sin(THETA), math.cos(THETA)
PATH_ANG = Z_ENTRY / CT                    # gun -> entry face path length
Q_ELASTIC = K0 * math.sqrt(2 - 2 * CT)     # 2 k0 sin(theta/2)
DIST_MS = 1000.0                           # fake moderator-sample distance
EKIN_STATIC = 0.5 * M_EVC2 * (V0 * (DIST_MS + PATH_ANG) / PATH_ANG) ** 2
Q_STATIC = K0 * math.sqrt(EKIN_STATIC / E0) * math.sqrt(2 - 2 * CT)
WL_STATIC = math.sqrt(0.081804209605330899 / EKIN_STATIC)


def _bin_linear(val, xmin, xmax, nbins):
    """Linear bin index of val, mirroring Hist1D/Hist2D::fill."""
    return int(math.floor((val - xmin) * nbins / (xmax - xmin)))


def _bin_log(val, xmin, xmax, nbins):
    """Logarithmic bin index of val, mirroring Hist1D::fill(linear=false)."""
    return int(math.floor((math.log10(val) - math.log10(xmin)) * nbins
                          / (math.log10(xmax) - math.log10(xmin))))


class _PencilGun(PythonGun):
    """Batch of identical monoenergetic neutrons flying along +z."""

    def __init__(self, vectorized=500, pos=(0., 0., 0.), direction=(0., 0., 1.)):
        super().__init__(vectorized=vectorized)
        self._pos = pos
        self._dir = direction
        self.pdata['ekin'] = E0
        self.pdata['pos'] = pos
        self.pdata['dir'] = direction
        self.pdata['t'] = 0.0

    def sampleEnergy(self, num):
        self.pdata['ekin'] = E0

    def sampleWeight(self, num):
        self.pdata['w'] = 1.0

    def sampleTime(self, num):
        self.pdata['t'] = 0.0

    def samplePosition(self, num):
        self.pdata['pos'] = self._pos

    def sampleDirection(self, num):
        self.pdata['dir'] = self._dir


def _straight_world():
    """World box + vacuum plate whose faces are at z=139/143."""
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(100, 100, 400), matCfg='vacuum.ncmat')
    plate = Volume("plate", Box(10, 10, 2), matCfg='vacuum.ncmat')
    return sim, world, plate


def _angled_world():
    """World box + wide vacuum plate for the 50-degree beam.

    The plate must span the impact point x = 139*tan(50deg) = 165.7 mm.
    """
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(500, 500, 400), matCfg='vacuum.ncmat')
    plate = Volume("plate", Box(200, 200, 2), matCfg='vacuum.ncmat')
    return sim, world, plate


def _single_bin(hist):
    """Assert the histogram received fills in exactly one bin; return
    (bin index, weight of that bin, total hit count)."""
    w = hist.getWeight()
    nz = np.nonzero(w.ravel())[0]
    assert nz.size == 1, f'expected a single filled bin, got {nz}'
    hit = hist.getHit()
    assert np.count_nonzero(hit) == 1
    return int(nz[0]), float(w.ravel()[nz[0]]), float(hit.sum())


# ---------------------------------------------------------------------------
# 1D helpers on the straight-through vacuum plate
# ---------------------------------------------------------------------------

@pytest.mark.medium
def test_tof_entry_lands_in_analytic_bin():
    # t = L/v with L = 139 mm (entry face) and v = sqrt(2E/m); the TOF
    # range is 40 ms over 4000 bins (10 us each) -> bin 6
    sim, world, plate = _straight_world()
    TOFHelper('tof', min=0., max=40e-3, numbin=4000, ptstate='ENTRY').make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('tof')
    t_pred = Z_ENTRY / V0
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(t_pred, 0., 40e-3, 4000) == 6
    assert wbin == hits == NPRIM
    assert h.getTotalWeight() == pytest.approx(NPRIM, rel=1e-12)
    assert h.getUnderflow() == 0 and h.getOverflow() == 0


@pytest.mark.medium
def test_wlspectrum_linear_monochromatic_bin():
    # the scored wavelength is ekin2wl(E0) = 1.83 Aa up to float noise
    sim, world, plate = _straight_world()
    WlSpectrumHelper('wl_lin', min=0.5, max=5, numbin=45,
                     ptstate='ENTRY', log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('wl_lin')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(WL0, 0.5, 5, 45) == 13
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_wlspectrum_log_binning_bin():
    # default binning of WlSpectrumHelper is logarithmic: 90 bins over
    # [0.5, 5] is exactly 90 bins/decade, 1.83 Aa -> bin 50
    sim, world, plate = _straight_world()
    helper = WlSpectrumHelper('wl_log', min=0.5, max=5, numbin=90,
                              ptstate='ENTRY')
    assert helper.log is True
    helper.make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('wl_log')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_log(WL0, 0.5, 5, 90) == 50
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_espectrum_linear_entry_bin():
    sim, world, plate = _straight_world()
    ESpectrumHelper('espec', min=0.01, max=0.05, numbin=40,
                    ptstate='ENTRY', log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('espec')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(E0, 0.01, 0.05, 40) == 14
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_espectrum_energy_transfer_is_zero_in_vacuum():
    # scoreTransfer fills EKin0 - EKin; nothing changes the energy in
    # vacuum, so all N transfers are exactly 0 -> bin 5 of the
    # deliberately asymmetric [-0.0055, 0.0445] range (0 sits mid-bin)
    sim, world, plate = _straight_world()
    ESpectrumHelper('etr', min=-0.0055, max=0.0445, numbin=50,
                    ptstate='EXIT', energyTransfer=True, log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('etr')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(0.0, -0.0055, 0.0445, 50) == 5
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_volfluence_track_length_integral_exact():
    # VolFluence weights each PEA_PRE fill with step/V, so a beam of N
    # particles traversing the plate thickness L in a volume V integrates
    # to exactly N*L/V = 2000*4/1600 = 5, independent of the binning; the
    # x axis is the energy, one bin for a monoenergetic beam
    sim, world, plate = _straight_world()
    VolFluenceHelper('vf_lin', min=0.01, max=0.05, numbin=40,
                     log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('vf_lin')
    assert h.getTotalWeight() == pytest.approx(NPRIM * THICK / 1600.0, rel=1e-6)
    assert h.getTotalWeight() == pytest.approx(5.0, rel=1e-6)
    assert h.getTotalHit() == NPRIM           # exactly one score per particle
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(E0, 0.01, 0.05, 40) == 14
    assert wbin == pytest.approx(5.0, rel=1e-6)


@pytest.mark.medium
def test_volfluence_log_binning_same_integral():
    # default VolFluenceHelper binning is logarithmic; the N*L/V identity
    # must not depend on the binning shape
    sim, world, plate = _straight_world()
    VolFluenceHelper('vf_log', min=0.01, max=0.05, numbin=40).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('vf_log')
    assert h.getTotalWeight() == pytest.approx(NPRIM * THICK / 1600.0, rel=1e-6)
    idx, _, _ = _single_bin(h)
    assert idx == _bin_log(E0, 0.01, 0.05, 40) == 22


@pytest.mark.medium
def test_deposition_is_zero_in_vacuum():
    # no production physics process registers an energy deposition, so
    # every EXIT fill scores exactly 0 -> bin 5 of [-0.0055, 0.0445]
    sim, world, plate = _straight_world()
    DepositionHelper('dep', min=-0.0055, max=0.0445, numbin=50, pdg=2112,
                     ptstate='EXIT', log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('dep')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(0.0, -0.0055, 0.0445, 50) == 5
    assert wbin == hits == NPRIM


# ---------------------------------------------------------------------------
# PSD: 2D binning, projection types and the local/global frame switch.
# The gun sits at (3, 5, 0) so that x and y are discriminable; the plate
# Box(60, 60, 2) is placed at (30, 0, 141), i.e. the entry point is
# global (3, 5, 139) and local (-27, 5, -2). Bins are 10 mm wide on both
# axes of every scorer here.
# ---------------------------------------------------------------------------

def _psd_world():
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(200, 200, 400), matCfg='vacuum.ncmat')
    plate = Volume("plate", Box(60, 60, 2), matCfg='vacuum.ncmat')
    world.placeChild('pv_plate', plate, Transformation3D(30, 0, PLATE_ZC))
    return sim, world, plate


@pytest.mark.medium
def test_psd_xy_local_vs_global_frame():
    sim, world, plate = _psd_world()
    PSDHelper('psd_loc', xmin=-60, xmax=60, xnumbin=12,
              ymin=-60, ymax=60, ynumbin=12,
              ptstate='ENTRY', psdtype='XY', isGlobal=False).make(plate)
    PSDHelper('psd_glb', xmin=-60, xmax=60, xnumbin=12,
              ymin=-60, ymax=60, ynumbin=12,
              ptstate='ENTRY', psdtype='XY', isGlobal=True).make(plate)
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, pos=(3., 5., 0.)), NPRIM)

    hw = sim.gatherHistData('psd_loc')
    assert hw.getWeight().shape == (12, 12)     # (xnumbin, ynumbin)
    w = hw.getWeight()
    nz = np.argwhere(w)
    assert len(nz) == 1
    ix, iy = int(nz[0][0]), int(nz[0][1])
    # local entry position (-27, 5) -> bins (3, 6)
    assert (ix, iy) == (_bin_linear(-27., -60, 60, 12),
                        _bin_linear(5., -60, 60, 12)) == (3, 6)
    assert w[ix, iy] == hw.getTotalHit() == NPRIM

    hg = sim.gatherHistData('psd_glb')
    w = hg.getWeight()
    nz = np.argwhere(w)
    assert len(nz) == 1
    ix, iy = int(nz[0][0]), int(nz[0][1])
    # global entry position (3, 5) -> bins (6, 6): the +30 mm placement
    # offset must show up only when isGlobal is set
    assert (ix, iy) == (_bin_linear(3., -60, 60, 12),
                        _bin_linear(5., -60, 60, 12)) == (6, 6)
    assert w[ix, iy] == hg.getTotalHit() == NPRIM


@pytest.mark.medium
def test_psd_xz_and_yz_projection_axes():
    # XZ fills (x, z) and YZ fills (y, z) into the (x-axis, y-axis) of the
    # 2D histogram; the local entry point is (-27, 5, -2)
    sim, world, plate = _psd_world()
    PSDHelper('psd_xz', xmin=-60, xmax=60, xnumbin=12,
              ymin=-60, ymax=60, ynumbin=12,
              ptstate='ENTRY', psdtype='XZ', isGlobal=False).make(plate)
    PSDHelper('psd_yz', xmin=-60, xmax=60, xnumbin=12,
              ymin=-60, ymax=60, ynumbin=12,
              ptstate='ENTRY', psdtype='YZ', isGlobal=False).make(plate)
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, pos=(3., 5., 0.)), NPRIM)

    h = sim.gatherHistData('psd_xz')
    w = h.getWeight()
    nz = np.argwhere(w)
    assert len(nz) == 1
    # XZ: x=-27 -> ix 3, z=-2 -> iy 5
    assert (int(nz[0][0]), int(nz[0][1])) == (_bin_linear(-27., -60, 60, 12),
                                              _bin_linear(-2., -60, 60, 12)) == (3, 5)
    assert w[nz[0][0], nz[0][1]] == h.getTotalHit() == NPRIM

    h = sim.gatherHistData('psd_yz')
    w = h.getWeight()
    nz = np.argwhere(w)
    assert len(nz) == 1
    # YZ: y=5 -> ix 6, z=-2 -> iy 5 (a swapped x/y fill would land elsewhere)
    assert (int(nz[0][0]), int(nz[0][1])) == (_bin_linear(5., -60, 60, 12),
                                              _bin_linear(-2., -60, 60, 12)) == (6, 5)
    assert w[nz[0][0], nz[0][1]] == h.getTotalHit() == NPRIM


@pytest.mark.medium
def test_vacuum_plate_entry_exit_absorb_bookkeeping():
    # conservation of the tracing-state bookkeeping: every particle that
    # ENTERS a volume must later EXIT it or be ABSORBED in it
    sim, world, plate = _straight_world()
    WlSpectrumHelper('p_entry', min=0.5, max=5, numbin=45,
                     ptstate='ENTRY', log=False).make(plate)
    WlSpectrumHelper('p_exit', min=0.5, max=5, numbin=45,
                     ptstate='EXIT', log=False).make(plate)
    WlSpectrumHelper('p_abs', min=0.5, max=5, numbin=45,
                     ptstate='ABSORB', log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    entry = sim.gatherHistData('p_entry').getTotalWeight()
    exitw = sim.gatherHistData('p_exit').getTotalWeight()
    absorbw = sim.gatherHistData('p_abs').getTotalWeight()
    assert entry == NPRIM
    assert absorbw == 0                       # vacuum cannot absorb
    assert exitw == entry                     # exit + absorb == entered


@pytest.mark.medium
def test_b4c_plate_exit_plus_absorb_equals_entry():
    # same identity through a real absorbing material: a 0.1 mm B4C plate
    # absorbs most of a 1.83 Aa beam but lets a measurable fraction through
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(100, 100, 400), matCfg='vacuum.ncmat')
    plate = Volume("plate", Box(10, 10, 0.05), matCfg='B4C.ncmat')
    WlSpectrumHelper('b_entry', min=0.5, max=5, numbin=45,
                     ptstate='ENTRY', log=False).make(plate)
    WlSpectrumHelper('b_exit', min=0.5, max=5, numbin=45,
                     ptstate='EXIT', log=False).make(plate)
    WlSpectrumHelper('b_abs', min=0.5, max=5, numbin=45,
                     ptstate='ABSORB', log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    entry = sim.gatherHistData('b_entry').getTotalWeight()
    exitw = sim.gatherHistData('b_exit').getTotalWeight()
    absorbw = sim.gatherHistData('b_abs').getTotalHit()
    assert entry == NPRIM
    assert exitw + absorbw == entry           # exact bookkeeping identity
    assert 0 < exitw < NPRIM                  # both channels populated
    assert 0 < absorbw < NPRIM


# ---------------------------------------------------------------------------
# Q/angle family on the 50-degree beam
# ---------------------------------------------------------------------------

@pytest.mark.medium
def test_directsq_method0_elastic_q_and_weight():
    # method 0: Q = k0*sqrt(1 + r - 2 mu sqrt(r)) with r = Eout/Ein = 1
    # (vacuum) and mu = cos(50 deg) taken from (position - samplePos)
    # projected on refDir; each fill carries weight 1/Q so the histogram
    # total is exactly N/Q
    sim, world, plate = _angled_world()
    DirectSqHelper('dsq0', qmin=0.5, qmax=5.0, numbin=45,
                   mod_smp_dist=DIST_MS, refDir=(0., 0., 1.),
                   samplePos=(0., 0., 0.), ptstate='ENTRY',
                   method=0, log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, direction=(ST, 0., CT)), NPRIM)

    h = sim.gatherHistData('dsq0')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(Q_ELASTIC, 0.5, 5.0, 45) == 24
    assert wbin == pytest.approx(NPRIM / Q_ELASTIC, rel=1e-6)
    assert hits == NPRIM


@pytest.mark.medium
def test_directsq_method1_static_approximation_q():
    # method 1 reconstructs the energy from v = (dist + |pos-samplePos|)/t,
    # i.e. as if the flight had started DIST_MS upstream, and fills the
    # elastic Q of that energy: Q = k(E')*sqrt(2 - 2 mu)
    sim, world, plate = _angled_world()
    DirectSqHelper('dsq1', qmin=0.5, qmax=30.0, numbin=59,
                   mod_smp_dist=DIST_MS, refDir=(0., 0., 1.),
                   samplePos=(0., 0., 0.), ptstate='ENTRY',
                   method=1, log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, direction=(ST, 0., CT)), NPRIM)

    h = sim.gatherHistData('dsq1')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(Q_STATIC, 0.5, 30.0, 59) == 31
    assert wbin == pytest.approx(NPRIM / Q_STATIC, rel=1e-4)
    assert hits == NPRIM


@pytest.mark.medium
def test_directsq_zero_q_straight_through_not_counted():
    # a particle that never changes direction has Q = 0 and is skipped by
    # the `if(qt)` guard instead of dividing by zero: the histogram must
    # stay completely empty (no fills, no under/overflow)
    sim, world, plate = _angled_world()
    DirectSqHelper('dsq_z', qmin=0.5, qmax=5.0, numbin=45,
                   mod_smp_dist=DIST_MS, refDir=(0., 0., 1.),
                   samplePos=(0., 0., 0.), ptstate='ENTRY',
                   method=0, log=False).make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('dsq_z')
    assert h.getTotalWeight() == 0
    assert h.getTotalHit() == 0
    assert h.getUnderflow() == 0 and h.getOverflow() == 0


@pytest.mark.medium
def test_angular_cfg_in_degree_bin():
    # ScorerAngular compares the flight direction with beam_dir; the
    # 50-degree beam lands in bin 40 of [10, 170] with 160 bins
    sim, world, plate = _angled_world()
    plate.addScorer("Scorer=Angular;name=ang_deg;beam_dir=0,0,1;min=10;"
                    "max=170;numbin=160;ptstate=ENTRY;inDegree=yes;linear=yes")
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, direction=(ST, 0., CT)), NPRIM)

    h = sim.gatherHistData('ang_deg')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(50., 10., 170., 160) == 40
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_angular_cfg_cosine_mode_bin():
    # inDegree=no scores mu = cos(angle) instead: cos(50 deg) -> bin 164
    # of [-1, 1] with 200 bins
    sim, world, plate = _angled_world()
    plate.addScorer("Scorer=Angular;name=ang_mu;beam_dir=0,0,1;min=-1;"
                    "max=1;numbin=200;ptstate=ENTRY;inDegree=no;linear=yes")
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, direction=(ST, 0., CT)), NPRIM)

    h = sim.gatherHistData('ang_mu')
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(CT, -1., 1., 200) == 164
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_wlangle_method0_wavelength_angle_cell():
    # WlAngle (2D, cfg string only): x = ekin2wl(EKin0) = 1.83, y = the
    # angle between (position - sample_pos) and beam_dir = 50 deg
    sim, world, plate = _angled_world()
    plate.addScorer("Scorer=WlAngle;name=wla0;sample_pos=0,0,0;beam_dir=0,0,1;"
                    "dist=1000;ptstate=ENTRY;wl_min=0.5;wl_max=5;numbin_wl=45;"
                    "angle_min=0;angle_max=180;numbin_angle=6;method=0")
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, direction=(ST, 0., CT)), NPRIM)

    h = sim.gatherHistData('wla0')
    assert h.getWeight().shape == (45, 6)     # (numbin_wl, numbin_angle)
    w = h.getWeight()
    nz = np.argwhere(w)
    assert len(nz) == 1
    ix, iy = int(nz[0][0]), int(nz[0][1])
    assert (ix, iy) == (_bin_linear(WL0, 0.5, 5, 45),
                        _bin_linear(50., 0., 180., 6)) == (13, 1)
    assert w[ix, iy] == h.getTotalHit() == NPRIM


@pytest.mark.medium
def test_wlangle_method1_static_wavelength_cell():
    # method=1 derives the wavelength from the static-approximation speed
    # v = (dist + |pos-samplePos|)/t = V0*(dist + L)/L, i.e. the speed is
    # inflated by (dist + L)/L so wl = WL0*L/(dist + L) with L the true
    # path length: 1.83*216.25/(1000 + 216.25) = 0.3254 Aa
    sim, world, plate = _angled_world()
    plate.addScorer("Scorer=WlAngle;name=wla1;sample_pos=0,0,0;beam_dir=0,0,1;"
                    "dist=1000;ptstate=ENTRY;wl_min=0.1;wl_max=2;numbin_wl=38;"
                    "angle_min=0;angle_max=180;numbin_angle=6;method=1")
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, direction=(ST, 0., CT)), NPRIM)

    h = sim.gatherHistData('wla1')
    w = h.getWeight()
    nz = np.argwhere(w)
    assert len(nz) == 1
    ix, iy = int(nz[0][0]), int(nz[0][1])
    assert (ix, iy) == (_bin_linear(WL_STATIC, 0.1, 2, 38),
                        _bin_linear(50., 0., 180., 6)) == (4, 1)
    assert w[ix, iy] == h.getTotalHit() == NPRIM


@pytest.mark.medium
def test_directsqw_axes_order_and_cell():
    # DirectSqw 2D: x axis is Q (num_qbin bins), y axis is the energy
    # transfer mean_ekin - ekin (num_ebin bins). Geometry: gun plays the
    # moderator at z=-140, sample_position at the origin, plate faces at
    # z=-2/+2. mod_smp_dist=240 deliberately exceeds the real L1=140, so
    # the L1-subtracted time is negative, the reconstructed ekin is
    # E0/(102/2)^2 = E0/2601 and the (Q, E) cell is computable in closed
    # form; the asymmetric shape (30, 100) also pins the axis order.
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(100, 100, 400), matCfg='vacuum.ncmat')
    plate = Volume("plate", Box(10, 10, 2), matCfg='vacuum.ncmat')
    DirectSqwHelper('sqw', mod_smp_dist=240.0, mean_ekin=E0,
                    mean_incident_dir=(0., 0., 1.), sample_position=(0., 0., 0.),
                    qmin=0.5, qmax=9.5, num_qbin=30,
                    ekinmin=-0.005, ekinmax=0.045, num_ebin=100,
                    pdg=2112, ptstate='ENTRY').make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, 0))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500, pos=(0., 0., -140.)), NPRIM)

    h = sim.gatherHistData('sqw')
    w = h.getWeight()
    assert w.shape == (30, 100)               # x = Q (num_qbin), y = E (num_ebin)
    # scored point (0,0,-2), sample_position origin: flight_dist = 2,
    # time = (138-240)/v0 < 0, mu = -1 (point behind the sample)
    ekin = 0.5 * M_EVC2 * (2.0 / ((138.0 - 240.0) / V0)) ** 2
    q = K0 * (1.0 + math.sqrt(ekin / E0))     # mu = -1 collapses the root
    etransfer = E0 - ekin
    nz = np.argwhere(w)
    assert len(nz) == 1
    ix, iy = int(nz[0][0]), int(nz[0][1])
    assert (ix, iy) == (_bin_linear(q, 0.5, 9.5, 30),
                        _bin_linear(etransfer, -0.005, 0.045, 100)) == (10, 58)
    # DirectSqw fills plain weights (no 1/Q factor, unlike DeltaMomentum)
    assert w[ix, iy] == h.getTotalHit() == NPRIM
    # Sign pin: the omega axis follows omega = E_initial - E_final, i.e.
    # POSITIVE omega means the neutron LOST energy (downscatter) - see the
    # C++ fill m_mean_ekin - ekin in PTScorerDirectSqw.cc and the DirectSqwHelper
    # docstring. The reconstructed ekin above is E0/2601 < E0, so this
    # downscattered event must land above omega = 0.
    assert ekin < E0
    assert etransfer > 0.
    assert h.ycenter[iy] > 0.


# ---------------------------------------------------------------------------
# MultiScat family
# ---------------------------------------------------------------------------

@pytest.mark.medium
def test_multiscat_counter_counts_zero_scatter_tracks():
    # MultiScatCounter (helper) is hardwired to [-2.5, 100.5] with 103
    # unit-width bins; a vacuum track scores count 0 -> bin index 2
    sim, world, plate = _straight_world()
    MultiScatCounter('msc').make(plate)
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('msc')
    assert h.getXMin() == pytest.approx(-2.5)
    assert h.getXMax() == pytest.approx(100.5)
    assert h.getDataSize() == 103
    w = h.getWeight()
    assert np.count_nonzero(w) == 1
    assert w[2] == h.getTotalHit() == NPRIM   # bin 2 <-> count 0
    assert h.getTotalWeight() == NPRIM


@pytest.mark.medium
def test_multiscat_cfg_string_zero_scatter_bin():
    # the cfg-string variant places count 0 into bin 0 of [-0.5, 5.5]
    sim, world, plate = _straight_world()
    plate.addScorer("Scorer=MultiScat;name=msc_cfg;min=0;max=5;linear=yes")
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('msc_cfg')
    assert h.getXMin() == pytest.approx(-0.5)
    assert h.getXMax() == pytest.approx(5.5)
    assert h.getDataSize() == 6               # numBin = max - min + 1
    w = h.getWeight()
    assert np.count_nonzero(w) == 1
    assert w[0] == h.getTotalHit() == NPRIM


@pytest.mark.medium
def test_scatter_counter_filter_reads_uninitialised_count_on_same_volume():
    # addScatterCounter wiring: ENTRY scorers on the SAME volume as the
    # counter fire before the counter has scored that particle, so the
    # per-particle count is still the "no information" value -1 and only
    # scatterNumberRequired=-1 sees the particles
    sim, world, plate = _straight_world()
    msc = MultiScatCounter('msc')
    msc.make(plate)
    made = {}
    for nm, req in (('f_m1', -1), ('f_0', 0), ('f_1', 1)):
        h = ESpectrumHelper(nm, min=0.01, max=0.05, numbin=40,
                            ptstate='ENTRY', log=False)
        h.make(plate)
        h.addScatterCounter(msc, req)
        made[nm] = h
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    assert sim.gatherHistData('f_m1').getTotalHit() == NPRIM
    assert sim.gatherHistData('f_0').getTotalHit() == 0
    assert sim.gatherHistData('f_1').getTotalHit() == 0


@pytest.mark.medium
def test_scatter_counter_filter_downstream_documented_semantics():
    # with the counter on an upstream volume the documented semantics
    # hold at the downstream ENTRY: required=0 keeps every (unscattered)
    # particle, required=1 and -1 keep none
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(100, 100, 500), matCfg='vacuum.ncmat')
    plate1 = Volume("plate1", Box(10, 10, 2), matCfg='vacuum.ncmat')
    msc = MultiScatCounter('msc')
    msc.make(plate1)
    world.placeChild('pv_plate1', plate1, Transformation3D(0, 0, PLATE_ZC))
    plate2 = Volume("plate2", Box(10, 10, 2), matCfg='vacuum.ncmat')
    for nm, req in (('d_0', 0), ('d_1', 1), ('d_m1', -1)):
        h = ESpectrumHelper(nm, min=0.01, max=0.05, numbin=40,
                            ptstate='ENTRY', log=False)
        h.make(plate2)
        h.addScatterCounter(msc, req)
    world.placeChild('pv_plate2', plate2, Transformation3D(0, 0, 161))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    assert sim.gatherHistData('d_0').getTotalHit() == NPRIM
    assert sim.gatherHistData('d_1').getTotalHit() == 0
    assert sim.gatherHistData('d_m1').getTotalHit() == 0


# ---------------------------------------------------------------------------
# Split and RotatingObj
# ---------------------------------------------------------------------------

@pytest.mark.medium
def test_split_multiplies_tracks_and_divides_weight():
    # ScorerSplit (cfg string): at ENTRY it records the incoming weight
    # once (log bin of w=1 over [1e-10, 1e2]), then scales the track to
    # w/split and clones it split-1 times. The ENTRY scorer sharing the
    # plate sees only the original track at w/3; the downstream plate is
    # entered by all 3 tracks: hit = 3N with total weight N (weight is
    # conserved exactly).
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(100, 100, 500), matCfg='vacuum.ncmat')
    plate1 = Volume("plate1", Box(10, 10, 2), matCfg='vacuum.ncmat')
    plate1.addScorer("Scorer=Split;name=splitter;split=3")
    WlSpectrumHelper('same_plate', min=0.5, max=5, numbin=45,
                     ptstate='ENTRY', log=False).make(plate1)
    world.placeChild('pv_plate1', plate1, Transformation3D(0, 0, PLATE_ZC))
    plate2 = Volume("plate2", Box(10, 10, 2), matCfg='vacuum.ncmat')
    WlSpectrumHelper('downstream', min=0.5, max=5, numbin=45,
                     ptstate='ENTRY', log=False).make(plate2)
    world.placeChild('pv_plate2', plate2, Transformation3D(0, 0, 161))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    # the splitter histogram itself: one fill of w=1 per primary
    hs = sim.gatherHistData('splitter')
    idx, wbin, hits = _single_bin(hs)
    assert idx == _bin_log(1.0, 1e-10, 1e2, 1200) == 1000
    assert wbin == hits == NPRIM

    # same-plate ENTRY scorer registered after the splitter: w = N/3
    h1 = sim.gatherHistData('same_plate')
    idx, wbin, hits = _single_bin(h1)
    assert idx == _bin_linear(WL0, 0.5, 5, 45) == 13
    assert wbin == pytest.approx(NPRIM / 3.0, rel=1e-9)
    assert hits == NPRIM

    # downstream: 3N entries carrying the conserved total weight N
    h2 = sim.gatherHistData('downstream')
    idx, wbin, hits = _single_bin(h2)
    assert idx == 13
    assert hits == 3 * NPRIM
    assert wbin == h2.getTotalWeight() == pytest.approx(NPRIM, rel=1e-9)


@pytest.mark.medium
def test_split_one_is_identity():
    # split=1 skips the weight scaling and the cloning entirely
    sim = Prompt(seed=SEED)
    world = Volume("world", Box(100, 100, 500), matCfg='vacuum.ncmat')
    plate1 = Volume("plate1", Box(10, 10, 2), matCfg='vacuum.ncmat')
    plate1.addScorer("Scorer=Split;name=splitter1;split=1")
    world.placeChild('pv_plate1', plate1, Transformation3D(0, 0, PLATE_ZC))
    plate2 = Volume("plate2", Box(10, 10, 2), matCfg='vacuum.ncmat')
    WlSpectrumHelper('after1', min=0.5, max=5, numbin=45,
                     ptstate='ENTRY', log=False).make(plate2)
    world.placeChild('pv_plate2', plate2, Transformation3D(0, 0, 161))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    h = sim.gatherHistData('after1')
    idx, wbin, hits = _single_bin(h)
    assert idx == 13
    assert wbin == hits == NPRIM


@pytest.mark.medium
def test_rotatingobj_effective_energy_bin():
    # ScorerRotatingObj (cfg string, PEA_POST) fills the comoving kinetic
    # energy E_lab + 0.5*m*(omega*rho)^2 into a hardwired [0, 1] eV / 100
    # bin histogram, with omega = 2*pi*rot_fre and rho = the distance of
    # the scored point from the rotation axis (143 mm at the exit face,
    # v_lab perpendicular to v_rot for this geometry). rot_fre=1853 puts
    # the rotation contribution at 0.0145 eV, i.e. bin 3 - one bin above
    # the f=0 result (bin 2); an omega=f slip would stay in bin 2, so the
    # pin discriminates the 2*pi factor at one-bin resolution.
    sim, world, plate = _straight_world()
    plate.addScorer("Scorer=RotatingObj;name=rot;rotation_axis=0,1,0;"
                    "point_on_axis=0,0,0;rot_fre=1853")
    world.placeChild('pv_plate', plate, Transformation3D(0, 0, PLATE_ZC))
    sim.setWorld(world)
    sim.simulate(_PencilGun(vectorized=500), NPRIM)

    omega = 2 * math.pi * 1853.0
    ecom = E0 + 0.5 * M_EVC2 * (Z_EXIT * omega) ** 2
    h = sim.gatherHistData('rot')
    assert h.getXMin() == 0.0 and h.getXMax() == pytest.approx(1.0)
    idx, wbin, hits = _single_bin(h)
    assert idx == _bin_linear(ecom, 0.0, 1.0, 100) == 3
    assert wbin == hits == NPRIM              # one score per primary


# ---------------------------------------------------------------------------
# fast, transport-free checks of the cfg-string-only scorers
# ---------------------------------------------------------------------------

def test_cfg_only_scorers_register_without_world():
    # Angular, WlAngle, MultiScat, RotatingObj and Split have no helper
    # class; adding their cfg strings to a standalone Volume must parse
    # them immediately and register them under their name key (the same
    # registration path the simulations above score through)
    from Cinema.Prompt.geo import Volume as VolumeCls

    vol = VolumeCls("cfgreg", Box(10, 10, 2), matCfg='vacuum.ncmat')
    cfgs = {
        'ang_reg': ("Scorer=Angular;name=ang_reg;beam_dir=0,0,1;min=10;max=170;"
                    "numbin=160;ptstate=ENTRY;inDegree=yes;linear=yes"),
        'wla_reg': ("Scorer=WlAngle;name=wla_reg;sample_pos=0,0,0;beam_dir=0,0,1;"
                    "dist=1000;ptstate=ENTRY;wl_min=0.5;wl_max=5;numbin_wl=45;"
                    "angle_min=0;angle_max=180;numbin_angle=6;method=0"),
        'msc_reg': "Scorer=MultiScat;name=msc_reg;min=0;max=5;linear=yes",
        'rot_reg': ("Scorer=RotatingObj;name=rot_reg;rotation_axis=0,1,0;"
                    "point_on_axis=0,0,0;rot_fre=50"),
        'split_reg': "Scorer=Split;name=split_reg;split=3",
    }
    for cfg in cfgs.values():
        vol.addScorer(cfg)
    assert set(VolumeCls.scorer_dict) >= set(cfgs)


def test_multiscat_counter_class_defaults():
    # the helper hardwires its binning so that integer scatter counts n
    # map to bin index n + 2 (unit-width bins starting at -2.5)
    msc = MultiScatCounter()
    assert msc.name == 'ScatterCounter'
    assert msc.min == pytest.approx(-2.5)
    assert msc.max == pytest.approx(100.5)
    assert msc.numbin == 103
    assert msc.ptstate == 'PEA_POST'
    assert msc.ptsNum == 6
    assert _bin_linear(0, msc.min, msc.max, msc.numbin) == 2
    assert _bin_linear(1, msc.min, msc.max, msc.numbin) == 3
