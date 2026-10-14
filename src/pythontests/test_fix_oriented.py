#!/usr/bin/env python3
# Regression test for the oriented-crystal sampling frame (ModelCollection.
# pickAndSample): the cross-section path converts the incident direction into
# the placed volume's local (crystal) frame for oriented models, but the
# sampling path passed the global direction, so xs and sampling saw different
# incident directions and oriented crystals scattered into wrong angles.
#
# Fingerprint (scaled down from the audit's version): a monoenergetic beam
# through an oriented Ge slab at three settings that are equivalent in the
# crystal frame:
#   A: identity crystal, beam along +z
#   B: crystal rotated by 60 deg about y, beam along +z
#      (crystal-frame beam = R^-1 z, with R the placement rotation)
#   C: identity crystal, beam along R^-1 z
# B and C present the SAME beam to the crystal, so with a fixed seed their
# local-frame trajectories run in lockstep and their crystal-frame outgoing
# directions must agree exactly. Before the fix, B sampled with the global
# direction and disagreed with C by O(1). A uses a different beam-to-crystal
# geometry (off the (111) Bragg condition chosen for B/C) and must differ.

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as scipyRot
from scipy.stats import ks_2samp

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.gun import SimpleThermalGun
from Cinema.Prompt.solid import Box

# oriented Ge: (111) planes perpendicular to the crystal z axis, (1,-1,0)
# planes perpendicular to the crystal x axis
GE_CFG = ('Ge_sg227.ncmat;mos=2deg;'
          'dir1=@crys_hkl:1,1,1@lab:0,0,1;dir2=@crys_hkl:1,-1,0@lab:1,0,0')

SEED = 20260101
NEV = 30000
ROTY_DEG = 60.0
WAVELENGTH = 3.2664  # [Aa]; d111 = a/√3 puts B/C exactly on the (111) Bragg
                     # condition for a beam 60 deg off the plane normal

_RY = scipyRot.from_euler('xyz', [0, ROTY_DEG, 0], degrees=True).as_matrix()
_U = _RY.T @ np.array([0., 0., 1.])  # crystal-frame beam direction of B


class _SlabSim(Prompt):
    """Ge slab (20x20x4 mm) at the origin, optionally rotated about y."""

    def __init__(self, seed, rotdeg):
        super().__init__(seed)
        self._rotdeg = rotdeg

    def makeWorld(self):
        world = Volume('world', Box(240, 240, 320), 'void.ncmat')
        slab = Volume('slab', Box(20, 20, 4), matCfg=GE_CFG)
        if self._rotdeg:
            tf = Transformation3D.from_euler_xyz(0, 0, 0, 0, self._rotdeg, 0)
            # the reference rotation below must be the placement rotation
            assert np.allclose(tf.getRotMatrix(), _RY, atol=1e-12)
        else:
            tf = Transformation3D(0., 0., 0.)
        world.placeChild('slab', slab, tf)
        self.setWorld(world)


def _outgoingCrystalFrameDirs(config):
    """Simulate NEV neutrons through the slab, return the outgoing directions
    in the crystal (local) frame of the slab, one row per event."""
    if config == 'A':    # identity crystal, beam along +z
        rotdeg = 0.
        gunpos, gundir = np.array([0., 0., -100.]), np.array([0., 0., 1.])
    elif config == 'B':  # rotated crystal, beam along +z
        rotdeg = ROTY_DEG
        gunpos, gundir = _RY @ (-100. * _U), np.array([0., 0., 1.])
    else:                # C: identity crystal, beam along U
        rotdeg = 0.
        gunpos, gundir = -100. * _U, _U

    sim = _SlabSim(SEED, rotdeg)
    sim.makeWorld()
    gun = SimpleThermalGun()
    gun.setWavelength(WAVELENGTH)
    gun.setPosition(gunpos)
    gun.setDirection(gundir)

    sim.l.setGun(gun.cfg)
    dirs = np.empty((NEV, 3))
    for i in range(NEV):
        # recordTrj keeps the per-event position polyline; the last
        # non-degenerate segment is the final flight direction (the world is
        # void, so it equals the slab exit direction)
        sim.l.go(1, recordTrj=True, timer=False, save2Disk=False)
        trj = sim.l.getTrajectory()
        j = len(trj) - 2
        while j >= 0 and np.array_equal(trj[j], trj[-1]):
            j -= 1
        d = trj[-1] - trj[j]
        dirs[i] = d / np.linalg.norm(d)
    sim.clear()

    # rotate back into the crystal frame
    if config == 'B':
        dirs = (_RY.T @ dirs.T).T
    return dirs


@pytest.mark.slow  # real simulations (~2 s body): excluded from the pre-push hook, runs in cimbuild -ttt
def test_oriented_sampling_agrees_in_crystal_frame():
    dirsA = _outgoingCrystalFrameDirs('A')
    dirsB = _outgoingCrystalFrameDirs('B')
    dirsC = _outgoingCrystalFrameDirs('C')

    beamA = np.array([0., 0., 1.])
    cosA = dirsA @ beamA
    cosB = dirsB @ _U

    # the setup must actually scatter, otherwise the comparison is vacuous
    assert np.mean(cosB < np.cos(np.deg2rad(5.))) > 0.02

    # B vs C: identical crystal-frame physics, fixed seed -> lockstep; before
    # the frame fix this distance was O(0.5). A KS on the cosines would be
    # dominated by the unscattered tie block, so compare event by event.
    bcMeanDist = float(np.linalg.norm(dirsB.mean(0) - dirsC.mean(0)))
    assert bcMeanDist < 1e-9
    assert float(np.abs(dirsB - dirsC).max()) < 1e-9

    # B vs A: different beam-to-crystal geometry must scatter differently
    assert float(np.linalg.norm(dirsB.mean(0) - dirsA.mean(0))) > 0.1
    assert float(ks_2samp(cosA, cosB).statistic) > 0.1
