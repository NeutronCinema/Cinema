"""Per-solid constructor validation tests for Prompt/solid.py.

The guard code is pure Python (sub-ms per case); the positive paths additionally
build a C++ solid (~10 us). Each test has a single assertion focus. Two known
gaps are documented as xfail (the guard should reject the input but currently
does not), and one -- Polyhedron sideCount=0, which builds a degenerate solid
with capacity 0 instead of raising -- is skipped with evidence.
"""

import numpy as np
import pytest

from Cinema.Prompt.solid import (ArbTrapezoid, Box, Cone, CutTube, Ellipsoid,
                                 GenTrapezoid, HyperbolicTube, Orb, Paraboloid,
                                 PolyCone, Polyhedron, Sphere, Tube)
from Cinema.Prompt.geo import _pt_Volume_new, _pt_Volume_capacity


def _capacity(solid):
    """Capacity in mm^3 via the raw logical-volume probe (no physics config)."""
    probe = _pt_Volume_new(b'cinema_pytest_validation_probe', solid.cobj)
    return float(_pt_Volume_capacity(probe))


def _box_corners(sx, sy):
    """8 corners of a rectangular Arb8 footprint (bottom face then top face)."""
    sq = [(sx, sy), (-sx, sy), (-sx, -sy), (sx, -sy)]
    return [np.asarray(c, dtype=np.float64) for c in sq + sq]


# ---------------------------------------------------------------- Box / Tube

def test_box_negative_halfx_raises():
    with pytest.raises(ValueError, match="Negative value"):
        Box(-1.0, 1.0, 1.0)


def test_tube_negative_rmin_raises():
    with pytest.raises(ValueError, match="Negative value"):
        Tube(-1.0, 2.0, 5.0)


def test_tube_rmin_greater_than_rmax_raises():
    with pytest.raises(ValueError, match=r"min \(2\.0\) > max \(1\.0\)"):
        Tube(2.0, 1.0, 5.0)


def test_tube_phi_delta_over_360_raises():
    with pytest.raises(ValueError, match="360"):
        Tube(1.0, 2.0, 5.0, 0, 400)


def test_tube_rmin_zero_is_allowed():
    # _sanityCheckPositive admits zero; rmin=0 means a solid cylinder
    tube = Tube(0.0, 2.0, 5.0)
    assert _capacity(tube) == pytest.approx(np.pi * 4 * 10)


# -------------------------------------------------------------------- Sphere

def test_sphere_negative_rmax_raises():
    with pytest.raises(ValueError, match="Negative value"):
        Sphere(1.0, -2.0)


def test_sphere_rmin_greater_than_rmax_raises():
    with pytest.raises(ValueError, match=r"min \(2\.0\) > max \(1\.0\)"):
        Sphere(2.0, 1.0)


def test_sphere_theta_delta_over_180_raises():
    with pytest.raises(ValueError, match="180"):
        Sphere(1.0, 2.0, 0, 360, 0, 200)


def test_sphere_phi_delta_over_360_raises():
    with pytest.raises(ValueError, match="360"):
        Sphere(1.0, 2.0, 0, 400)


# ---------------------------------------------------------------------- Cone

def test_cone_rmin_bot_greater_than_rmax_bot_raises():
    with pytest.raises(ValueError, match=r"min \(4\.0\) > max \(3\.0\)"):
        Cone(3.0, 1.0, 10.0, 4.0, 0.5)


def test_cone_phi_delta_over_360_raises():
    with pytest.raises(ValueError, match="360"):
        Cone(3.0, 1.0, 10.0, 1.0, 0.5, 0, 400)


@pytest.mark.xfail(
    reason="solid.py Cone checks only 'phiDelta_deg > 360' without abs(), unlike "
           "Tube/Sphere, so negative deltaPhi slips through today",
    strict=False)
def test_cone_negative_phi_delta_rejected():
    with pytest.raises(ValueError, match="360"):
        Cone(3.0, 1.0, 10.0, 1.0, 0.5, 0, -400)


# ------------------------------------------------------------------ PolyCone

def test_polycone_size_mismatch_raises():
    with pytest.raises(ValueError, match="not consistent"):
        PolyCone([0, 2], [1.0], [3.0, 3.0])


def test_polycone_nonmonotonic_z_raises():
    with pytest.raises(ValueError, match="monotonic"):
        PolyCone(np.array([0.0, 4.0, 2.0]),
                 np.array([1.0, 1.0, 1.0]),
                 np.array([3.0, 3.0, 3.0]))


def test_polycone_rmin_greater_than_rmax_at_plane_raises():
    with pytest.raises(ValueError, match=r"min \(2\.0\) > max \(1\.0\)"):
        PolyCone(np.array([0.0, 2.0]), np.array([2.0, 2.0]), np.array([3.0, 1.0]))


# ---------------------------------------------------------------- Polyhedron

def test_polyhedron_array_length_mismatch_raises():
    with pytest.raises(RuntimeError, match="same length"):
        Polyhedron(np.array([0.0, 5.0]), np.array([1.0]), np.array([2.0, 2.0]))


@pytest.mark.xfail(
    reason="Polyhedron passes raw lists to the ctypes ndpointer binding (no "
           "_arrayCheck, unlike PolyCone), so its own docstring example with "
           "plain lists [0,5,10]/[1,2,1]/[3,4,3] raises ctypes.ArgumentError",
    strict=False)
def test_polyhedron_plain_list_input_matches_docstring():
    # the class docstring example must be executable as written
    poly = Polyhedron([0., 5., 10.], [1., 2., 1.], [3., 4., 3.])
    assert poly.cobj


@pytest.mark.skip(
    reason="survey expected Polyhedron(sideCount=0) to raise, but it does not: "
           "sideCount=0 passes _sanityCheckPositive (zero is allowed) and VecGeom "
           "builds a degenerate solid with capacity 0.0, printing 'could not find "
           "three non degenerated points'. Validation gap, evidence probed "
           "2026-10-10; owner decision needed before pinning a contract")
def test_polyhedron_zero_side_count_raises():
    Polyhedron(np.array([0.0, 10.0]), np.array([0.0, 0.0]), np.array([2.0, 2.0]), 0)


# ------------------------------------------------- Orb / Paraboloid / Arb8

def test_orb_negative_radius_raises():
    with pytest.raises(ValueError, match="Negative value"):
        Orb(-1.0)


def test_paraboloid_negative_halfheight_raises():
    with pytest.raises(ValueError, match="Negative value"):
        Paraboloid(3.0, 1.0, -5.0)


def test_paraboloid_inverted_raises():
    # the vendored kernel is written for rhi > rlo (dd = 1/(rhi^2 - rlo^2)):
    # probed 2026-10-10, inverted radii make DistanceToOut return negative
    # garbage for interior points (e.g. -2.35) -- a silent wall leak -- and
    # equal radii diverge it (3e30), because dd divides by zero and the
    # profile parabola through two equal-radius circles is not even unique
    # (unlike Cone, where rmin == rmax is the well-defined cylinder limit)
    with pytest.raises(ValueError, match=r"requires rbot < rtop, got rbot=3\.0, rtop=1\.0"):
        Paraboloid(3.0, 1.0, 5.0)
    with pytest.raises(ValueError, match=r"requires rbot < rtop, got rbot=2\.0, rtop=2\.0"):
        Paraboloid(2.0, 2.0, 4.0)


def test_arbtrapezoid_negative_halfz_raises():
    with pytest.raises(ValueError, match="Negative value"):
        ArbTrapezoid(*_box_corners(1.0, 1.0), -5.0)


# ------------------------------------------------------------- GenTrapezoid

def test_gentrapezoid_theta_over_90_raises():
    with pytest.raises(ValueError, match=r"min \(95\.0\) > max \(90\)"):
        GenTrapezoid(5.0, 95.0, 0.0, 2.0, 1.0, 1.0, 0.0, 2.0, 1.0, 1.0, 0.0)


def test_gentrapezoid_negative_alpha_raises():
    with pytest.raises(ValueError, match="Negative value"):
        GenTrapezoid(5.0, 0.0, 0.0, 2.0, 1.0, 1.0, -1.0, 2.0, 1.0, 1.0, 0.0)


# ----------------------------------------------------------------- Ellipsoid

def test_ellipsoid_degenerate_cuts_raise():
    # bottom == top (and equal nonzero cuts in general) are ill-defined
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 2.0, 2.0)
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 1.0, 1.0)


def test_ellipsoid_zero_topcut_disables_both_cuts():
    # pins the chained-compare semantics of checkParamaters: zBottomCut >=
    # zTopCut != 0 is False when zTopCut == 0, so (3.1, 0) is accepted and the
    # capacity comes out identical to the uncut ellipsoid
    cut = Ellipsoid(3.0, 2.0, 4.0, 3.1, 0.0)
    uncut = Ellipsoid(3.0, 2.0, 4.0)
    assert _capacity(cut) == pytest.approx(_capacity(uncut), rel=1e-12)
    assert _capacity(cut) == pytest.approx(4 / 3 * np.pi * 24, rel=1e-12)


def test_ellipsoid_inverted_cuts_raise():
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 1.0, -1.0)


# ------------------------------------------------- CutTube / HyperbolicTube

def test_cuttube_not_implemented():
    with pytest.raises(NotImplementedError):
        CutTube(2.0, 5.0, [0.0, 0.0, 1.0], [0.0, 0.0, 1.0])


def test_hyperbolictube_stereo_angle_boundary():
    # the check is strictly '> 90': exactly 90 deg constructs, beyond it raises
    HyperbolicTube(5.0, 90.0, 90.0, 10.0)
    with pytest.raises(ValueError, match="90"):
        HyperbolicTube(5.0, 90.01, 45.0, 10.0)
