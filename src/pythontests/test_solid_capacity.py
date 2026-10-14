"""Analytic capacity anchors for the Prompt solid classes (solid.py).

Capacity is read through the internal low-level probe
``_pt_Volume_new(b'name', solid.cobj)`` + ``_pt_Volume_capacity`` -- the same
binding geo.py's daughter-overlap scan uses. Wrapping each solid in a full
``Volume`` would configure the default (dilute) material and build an NCrystal
physics model in every forked test (~60 ms each, see the survey notes); the raw
probe keeps every case here at sub-millisecond level except the three VecGeom
boolean solids, whose capacity is Monte-Carlo estimated (~50 ms) and therefore
checked against loose tolerances.

All closed forms are mm^3; solid dimensions are mm and angular parameters deg.
"""

import numpy as np
import pytest

from Cinema.Prompt.solid import (ArbTrapezoid, Box, Cone, Ellipsoid, GenTrapezoid,
                                 Orb, Paraboloid, PolyCone, Polyhedron, Sphere,
                                 SolidSubtraction, SolidUnion, Trapezoid, Tube)
from Cinema.Prompt.geo import Transformation3D, _pt_Volume_new, _pt_Volume_capacity


def _capacity(solid):
    """Capacity in mm^3 via the raw logical-volume probe (no physics config)."""
    probe = _pt_Volume_new(b'cinema_pytest_capacity_probe', solid.cobj)
    return float(_pt_Volume_capacity(probe))


def _box_corners(sx, sy):
    """8 corners of a rectangular Arb8 footprint (bottom face then top face)."""
    sq = [(sx, sy), (-sx, sy), (-sx, -sy), (sx, -sy)]
    return [np.asarray(c, dtype=np.float64) for c in sq + sq]


def test_box_capacity():
    # full box from half-edges: (2hx)(2hy)(2hz)
    assert _capacity(Box(5.0, 3.0, 2.0)) == pytest.approx(8 * 5 * 3 * 2)


def test_orb_capacity():
    assert _capacity(Orb(5.0)) == pytest.approx(4 / 3 * np.pi * 5.0 ** 3)


def test_tube_capacity():
    # full annular cylinder: pi (rmax^2 - rmin^2) (2z)
    assert _capacity(Tube(1.0, 2.0, 5.0)) == pytest.approx(np.pi * (4 - 1) * 10)


def test_quarter_tube_is_quarter_of_full():
    full = _capacity(Tube(1.0, 2.0, 5.0))
    assert _capacity(Tube(1.0, 2.0, 5.0, 0, 90)) == pytest.approx(full * 90 / 360)


def test_sphere_shell_capacity():
    assert _capacity(Sphere(1.0, 2.0)) == pytest.approx(4 / 3 * np.pi * (8 - 1))


def test_sphere_theta_segment_follows_cosine_law():
    # polar cap theta in [0, 45] deg holds a (1 - cos45)/(1 - cos180) fraction
    # of the shell -- the (1-cos) solid-angle law, NOT 45/180
    full = _capacity(Sphere(1.0, 2.0))
    seg = _capacity(Sphere(1.0, 2.0, 0, 360, 0, 45))
    assert seg == pytest.approx(2 / 3 * np.pi * (8 - 1) * (1 - np.cos(np.deg2rad(45))))
    assert seg == pytest.approx(full * (1 - np.cos(np.deg2rad(45))) / 2)


def test_cone_frustum_capacity_pins_half_height():
    # frustum V = pi*h/3 (R^2 + R r + r^2) with h = 2z: the ctor argument z is
    # the HALF height even though the Cone docstring calls it "Height"
    assert _capacity(Cone(3.0, 1.0, 10.0)) == \
        pytest.approx(2 * np.pi * 10.0 / 3 * (9 + 3 + 1))


def test_ellipsoid_full_capacity():
    assert _capacity(Ellipsoid(3.0, 2.0, 4.0)) == pytest.approx(4 / 3 * np.pi * 3 * 2 * 4)


def _ellipsoid_slice_cap(a, b, c, zb, zt):
    # closed form for pi*a*b*[z - z^3/(3 c^2)] between two cut planes
    f = lambda z: z - z ** 3 / (3 * c ** 2)
    return np.pi * a * b * (f(zt) - f(zb))


def test_ellipsoid_cut_planes_capacity():
    assert _capacity(Ellipsoid(3.0, 2.0, 4.0, -2.0, 2.0)) == \
        pytest.approx(_ellipsoid_slice_cap(3, 2, 4, -2, 2))


def test_ellipsoid_thin_slice_capacity():
    assert _capacity(Ellipsoid(3.0, 2.0, 4.0, -0.5, 0.5)) == \
        pytest.approx(_ellipsoid_slice_cap(3, 2, 4, -0.5, 0.5))


def test_trapezoid_boxlike_capacity():
    # with x1==x2 and y1==y2 the prism degenerates to a box
    assert _capacity(Trapezoid(2.0, 2.0, 3.0, 3.0, 5.0)) == \
        pytest.approx((2 + 2) * (3 + 3) * 2 * 5)


def test_paraboloid_capacity_315():
    # convention confirmed on four parameter sets: V = pi z (rbot^2 + rtop^2)
    # with z the halfHeight argument
    assert _capacity(Paraboloid(1.0, 3.0, 5.0)) == pytest.approx(np.pi * 5 * (9 + 1))


def test_paraboloid_capacity_234():
    # the old (2,2,4) case pinned the same formula but rbot == rtop is rejected
    # by the constructor now (out of the kernel's rhi > rlo contract), so the
    # equality degenerate was replaced by a valid ordered pair
    assert _capacity(Paraboloid(2.0, 3.0, 4.0)) == pytest.approx(np.pi * 4 * (4 + 9))


def test_polycone_straight_profile_is_tube():
    # two z-planes with constant radii must reproduce the equivalent Tube
    poly = PolyCone(np.array([-5.0, 5.0]), np.array([1.0, 1.0]), np.array([2.0, 2.0]))
    assert _capacity(poly) == pytest.approx(_capacity(Tube(1.0, 2.0, 5.0)))


def test_arbtrapezoid_box_corners_capacity():
    # rectangular footprint +-1 in x/y, halfz=5 -> same box as Box(1, 1, 5)
    arb = ArbTrapezoid(*_box_corners(1.0, 1.0), 5.0)
    assert _capacity(arb) == pytest.approx(_capacity(Box(1.0, 1.0, 5.0)))
    assert _capacity(arb) == pytest.approx(40.0)


def test_gentrapezoid_zero_angles_is_box():
    # all angular parameters 0 degenerates GenTrapezoid into a plain box
    gen = GenTrapezoid(5.0, 0.0, 0.0, 2.0, 1.0, 1.0, 0.0, 2.0, 1.0, 1.0, 0.0)
    assert _capacity(gen) == pytest.approx(_capacity(Box(1.0, 2.0, 5.0)))
    assert _capacity(gen) == pytest.approx(80.0)


def test_polyhedron_hexagonal_prism_capacity():
    # regular n-gon prism with apothem a: area = n tan(pi/n) a^2; for n=6 that
    # is 2*sqrt(3) a^2.  rMax/rMin act as apothems (not circumradii).
    h = 10.0
    solid0 = Polyhedron(np.array([0.0, h]), np.array([0.0, 0.0]), np.array([2.0, 2.0]))
    solid1 = Polyhedron(np.array([0.0, h]), np.array([1.0, 1.0]), np.array([2.0, 2.0]))
    cap0 = _capacity(solid0)
    cap1 = _capacity(solid1)
    assert cap0 == pytest.approx(2 * np.sqrt(3) * 4 * h)          # solid hexagon
    assert cap1 == pytest.approx(2 * np.sqrt(3) * (4 - 1) * h)    # hexagonal tube
    # shrinking the inner radius everywhere can only grow the capacity
    assert cap0 > cap1


@pytest.mark.medium
def test_solid_union_coincident_boxes_capacity():
    # union of two identical coincident boxes is one box: VecGeom estimates
    # boolean capacity by sampling, hence the loose 1% tolerance
    union = SolidUnion(Box(2.0, 2.0, 2.0), Box(2.0, 2.0, 2.0))
    assert _capacity(union) == pytest.approx(64.0, rel=1e-2)


@pytest.mark.medium
def test_solid_union_shifted_boxes_capacity():
    # two 4^3 boxes shifted 2 mm along x overlap in a 2x4x4 slab:
    # 64 + 64 - 32 = 96
    shift = Transformation3D(2.0, 0.0, 0.0)
    union = SolidUnion(Box(2.0, 2.0, 2.0), Box(2.0, 2.0, 2.0), shift)
    assert _capacity(union) == pytest.approx(96.0, rel=1e-2)


@pytest.mark.medium
def test_solid_subtraction_center_cube_capacity():
    # 4^3 cube with a centered 2^3 cube removed
    sub = SolidSubtraction(Box(2.0, 2.0, 2.0), Box(1.0, 1.0, 1.0))
    assert _capacity(sub) == pytest.approx(56.0, rel=1e-2)
