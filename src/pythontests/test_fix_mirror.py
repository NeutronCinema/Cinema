# Regression tests for the Mirror surface process fixes:
#
# 1. the C++ factory default of the m parameter is 1 (was silently 0, i.e.
#    mirror off, for 'physics=Mirror' without an explicit m= key);
# 2. a low-reflectivity (Russian roulette loser) hit used to fly on through
#    the mirror wall with weight 1, and since the McStas reflectivity factor
#    evaluates to -0.0 above the cutoff every such hit transmitted: a mirror
#    wall acted as a window. Now the reflectivity is clamped at zero and the
#    roulette loser is absorbed.
#
# Each test runs its own simulation (the Launcher state is process global,
# the pytest run uses --forked), with a parallel beam hitting the front face
# of a Mirror wall head on:
# - above cutoff (1 A neutrons, Q = 4*pi/lambda >> Qc) every neutron must be
#   absorbed exactly at the wall: the absorption scorer counts N hits and the
#   detectors on both sides stay empty (before the fix all N leaked through);
# - below cutoff (600 A ultracold neutrons, Q = 0.0209 < Qc = 0.0219) every
#   neutron must still reflect with the full R0 = 0.99 weighting: the wall
#   absorption count stays zero and the detector behind the gun catches all
#   N reflected neutrons.
import numpy as np
import pytest

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box
from Cinema.Prompt.scorer import WlSpectrumHelper

NUM_BEAM = 500
# head-on momentum transfer of a neutron is Q = 4*pi/lambda [Aa^-1], the
# mirror critical momentum is m*Qc = 0.0219 Aa^-1
GUN_CFG = ("gun=UniModeratorGun;src_w=2;src_h=2;src_z=-90;"
           "slit_w=2;slit_h=2;slit_z=1e99;mean_wl={};range_wl=1e-6")


def _makeMirrorWorld():
    """World with a Mirror wall at z=+50, a transmission detector behind it,
    a reflection detector behind the gun and an ABSORB scorer on the wall."""
    world = Volume("world", Box(20, 20, 100), matCfg='vacuum.ncmat')

    slab = Volume("slab", Box(10, 10, 0.05), matCfg='vacuum.ncmat',
                  surfaceCfg='physics=Mirror')
    world.placeChild("slab", slab, Transformation3D(0, 0, 50))
    WlSpectrumHelper("mabs", min=0.1, max=10, numbin=10,
                     ptstate='ABSORB').make(slab)

    trans = Volume("trans", Box(10, 10, 1), matCfg='vacuum.ncmat')
    WlSpectrumHelper("transwl", min=0.1, max=10, numbin=10,
                     ptstate='ENTRY').make(trans)
    world.placeChild("trans", trans, Transformation3D(0, 0, 80))

    # behind the gun (src_z=-90), so only reflected neutrons ever cross it
    back = Volume("back", Box(10, 10, 1), matCfg='vacuum.ncmat')
    WlSpectrumHelper("backwl", min=100, max=1000, numbin=10,
                     ptstate='ENTRY').make(back)
    world.placeChild("back", back, Transformation3D(0, 0, -95))

    return world


@pytest.mark.medium
def test_mirror_wall_absorbs_above_cutoff():
    sim = Prompt(seed=4096)
    sim.setWorld(_makeMirrorWorld())
    sim.simulate(GUN_CFG.format(1.0), NUM_BEAM)

    absorbed = sim.gatherHistData('mabs')
    np.testing.assert_allclose(absorbed.getHit().sum(), NUM_BEAM)
    np.testing.assert_allclose(absorbed.getTotalWeight(), NUM_BEAM, rtol=1e-12)

    # nothing passes the wall any more (it used to be a window) and nothing
    # reflects above the cutoff either
    assert sim.gatherHistData('transwl').getHit().sum() == 0
    assert sim.gatherHistData('backwl').getHit().sum() == 0


@pytest.mark.medium
def test_mirror_wall_reflects_below_cutoff():
    sim = Prompt(seed=4096)
    sim.setWorld(_makeMirrorWorld())
    sim.simulate(GUN_CFG.format(600.0), NUM_BEAM)

    # no absorption at the wall below the cutoff, no transmission either
    assert sim.gatherHistData('mabs').getHit().sum() == 0
    assert sim.gatherHistData('transwl').getHit().sum() == 0

    reflected = sim.gatherHistData('backwl')
    np.testing.assert_allclose(reflected.getHit().sum(), NUM_BEAM)
    # every reflection carries the full R0 = 0.99 weight
    np.testing.assert_allclose(reflected.getTotalWeight(),
                               NUM_BEAM * 0.99, rtol=1e-12)
