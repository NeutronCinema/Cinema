"""Tests for the additive parameter-table API on Prompt/solid.py.

Covers the refactor's additive surface and its two pinned bug fixes:

- params()/reconstruction round trip over every constructible solid:
  ``type(s)(**s.params())`` must rebuild a solid of the same type and the
  same capacity (exact for primitives; the three boolean solids and the
  tessellated solid have Monte-Carlo-estimated capacities, so they get loose
  tolerances -- see test_solid_capacity.py's header for the cost analysis).
- eval-able repr over a representative subset.
- bounds() sanity for Box/Sphere/Tube plus a capacity-containment sweep.
- the Ellipsoid cut-plane comparison fix: the former chained comparison
  ``zBottomCut >= self.zTopCut != 0`` is rewritten as two explicit checks
  with identical semantics (zero top cut still disables both cuts).
- constructor signatures and error-message anchors that the refactor
  promised to keep unchanged.

Capacities are read through the raw logical-volume probe (no physics
config), as in test_solid_validation.py / test_solid_capacity.py.
"""

import inspect
import warnings

import numpy as np
import pytest

from Cinema.Prompt.solid import (ArbTrapezoid, Box, Cone, CutTube, Ellipsoid,
                                 GenTrapezoid, HypebolicTube, HyperbolicTube,
                                 Orb, Paraboloid, PolyCone, Polyhedron,
                                 SolidIntersection, SolidSubtraction,
                                 SolidUnion, Sphere, Tessellated, Tetrahedron,
                                 Trapezoid, Tube, _Unset)
from Cinema.Prompt.geo import Transformation3D, _pt_Volume_new, _pt_Volume_capacity


def _capacity(solid):
    """Capacity in mm^3 via the raw logical-volume probe (no physics config)."""
    probe = _pt_Volume_new(b'cinema_pytest_params_api_probe', solid.cobj)
    return float(_pt_Volume_capacity(probe))


def _box_corners(sx, sy):
    """8 corners of a rectangular Arb8 footprint (bottom face then top face)."""
    sq = [(sx, sy), (-sx, sy), (-sx, -sy), (sx, -sy)]
    return [np.asarray(c, dtype=np.float64) for c in sq + sq]


def _tetra_polydata():
    """A minimal 4-face pyvista PolyData (no skip needed: pyvista is a hard
    dependency of the visualization layer and present in the test env)."""
    pyvista = pytest.importorskip("pyvista")
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1.]], dtype=np.float64)
    faces = np.array([3, 0, 1, 2, 3, 0, 1, 3, 3, 0, 2, 3, 3, 1, 2, 3])
    return pyvista.PolyData(points, faces)


# One representative construction per constructible solid. 17 solids can be
# built (everything except the base Solid, the raising CutTube and the
# deprecated HypebolicTube alias); all of them are covered.
def _all_solid_cases():
    polydata = _tetra_polydata()
    return [
        (Box, lambda: Box(5.0, 3.0, 2.0)),
        (Tube, lambda: Tube(1.0, 2.0, 5.0, 0, 90)),
        (Sphere, lambda: Sphere(1.0, 2.0, 0, 90, 0, 45)),
        (Trapezoid, lambda: Trapezoid(2.0, 4.0, 3.0, 6.0, 5.0)),
        (Polyhedron, lambda: Polyhedron([0., 5., 10.], [1., 2., 1.], [3., 4., 3.])),
        (Tessellated, lambda: Tessellated(polydata)),
        (ArbTrapezoid, lambda: ArbTrapezoid(*_box_corners(1.0, 1.0), 5.0)),
        (Cone, lambda: Cone(3.0, 1.0, 10.0, 1.0, 0.5, 0, 90)),
        (HyperbolicTube, lambda: HyperbolicTube(5.0, 40.0, 45.0, 10.0)),
        (Orb, lambda: Orb(5.0)),
        (Paraboloid, lambda: Paraboloid(1.0, 3.0, 5.0)),
        (PolyCone, lambda: PolyCone([0, 2, 4, 6], [1, 1.5, 2, 1.5], [3, 3.5, 4, 3.5], 0, 90)),
        (Tetrahedron, lambda: Tetrahedron([0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1])),
        (GenTrapezoid, lambda: GenTrapezoid(5.0, 0.1, 0.2, 3.0, 4.0, 5.0, 0.3, 3.5, 4.5, 6.0, 0.4)),
        (Ellipsoid, lambda: Ellipsoid(3.0, 2.0, 4.0, -2.0, 2.0)),
        (SolidUnion, lambda: SolidUnion(Box(2, 2, 2), Orb(1.0))),
        (SolidIntersection, lambda: SolidIntersection(Box(2, 2, 2), Orb(1.0))),
        (SolidSubtraction, lambda: SolidSubtraction(Box(4, 4, 4), Orb(1.0),
                                                    Transformation3D(z=1.0))),
    ]


_CASE_IDS = [cls.__name__ for cls, _ in _all_solid_cases()]
_MC_ESTIMATED = {'SolidUnion', 'SolidIntersection', 'SolidSubtraction', 'Tessellated'}


@pytest.mark.parametrize("cls,factory", _all_solid_cases(), ids=_CASE_IDS)
def test_params_round_trip(cls, factory):
    """params() must carry everything needed to rebuild an equal solid."""
    solid = factory()
    rebuilt = type(solid)(**solid.params())
    assert type(rebuilt) is cls
    rtol = 5e-2 if cls.__name__ in _MC_ESTIMATED else 1e-12
    assert _capacity(rebuilt) == pytest.approx(_capacity(solid), rel=rtol)


def test_params_returns_copies_of_arrays():
    # mutating the returned dict must not corrupt the solid's stored values
    cone = PolyCone([0., 2.], [1., 1.], [3., 3.])
    p = cone.params()
    p['vec_z'][0] = 99.0
    assert cone.vec_z[0] == 0.0


# ---------------------------------------------------------------- repr round trip

def _eval_namespace():
    ns = {cls.__name__: cls for cls, _ in _all_solid_cases()}
    ns['Transformation3D'] = Transformation3D
    ns['np'] = np
    return ns


@pytest.mark.parametrize("cls,factory", _all_solid_cases(), ids=_CASE_IDS)
def test_repr_round_trip(cls, factory):
    """eval(repr(s)) must rebuild an equal solid for every solid whose repr
    is eval-able (all primitives and the boolean shells; Tessellated is
    explicitly informational-only and skipped)."""
    if cls is Tessellated:
        pytest.skip("Tessellated repr is informational only (mesh buffers)")
    solid = factory()
    rebuilt = eval(repr(solid), _eval_namespace())  # repr is repo-owned content
    assert type(rebuilt) is cls
    rtol = 5e-2 if cls.__name__ in _MC_ESTIMATED else 1e-12
    assert _capacity(rebuilt) == pytest.approx(_capacity(solid), rel=rtol)


def test_boolean_repr_round_trips_through_a_real_transform():
    # the right child is placed through a translated frame; the repr embeds
    # the frame as Transformation3D.from_euler_xyz(...)
    s = SolidSubtraction(Box(4, 4, 4), Orb(1.5), Transformation3D(z=1.0))
    rebuilt = eval(repr(s), _eval_namespace())
    assert _capacity(rebuilt) == pytest.approx(_capacity(s), rel=5e-2)


# ------------------------------------------------------------------- bounds

def test_box_bounds_exact():
    lo, hi = Box(5.0, 3.0, 2.0).bounds()
    assert np.allclose(lo, [-5, -3, -2])
    assert np.allclose(hi, [5, 3, 2])


def test_sphere_bounds_is_outer_radius_box():
    lo, hi = Sphere(1.0, 2.0, 0, 90, 0, 45).bounds()
    # conservative: angular cuts are not exploited
    assert np.allclose(lo, [-2, -2, -2])
    assert np.allclose(hi, [2, 2, 2])


def test_tube_bounds_covers_half_height():
    lo, hi = Tube(1.0, 2.0, 5.0).bounds()
    assert np.allclose(lo, [-2, -2, -5])
    assert np.allclose(hi, [2, 2, 5])


def test_ellipsoid_bounds_respect_active_cuts():
    full = Ellipsoid(3.0, 2.0, 4.0)
    lo, hi = full.bounds()
    assert np.allclose(lo, [-3, -2, -4]) and np.allclose(hi, [3, 2, 4])
    cut = Ellipsoid(3.0, 2.0, 4.0, -2.0, 2.0)
    lo, hi = cut.bounds()
    assert np.allclose(lo, [-3, -2, -2]) and np.allclose(hi, [3, 2, 2])


@pytest.mark.parametrize("cls,factory", _all_solid_cases(), ids=_CASE_IDS)
def test_bounds_contain_the_solid(cls, factory):
    """bounds() must never under-estimate: the bounding-box volume must hold
    the solid's capacity (loose slack where the capacity is MC-estimated)."""
    solid = factory()
    lo, hi = solid.bounds()
    assert lo.shape == (3,) and hi.shape == (3,)
    assert np.all(lo <= hi)
    slack = 0.95 if cls.__name__ in _MC_ESTIMATED else 1.0 - 1e-12
    assert np.prod(hi - lo) >= _capacity(solid) * slack


# --------------------------------------------------- Ellipsoid comparison fix

def test_ellipsoid_defaults_still_construct():
    # a naive rewrite of the old chained comparison as
    # "zBottomCut >= zTopCut" alone would reject the (0, 0) defaults
    e = Ellipsoid(3.0, 2.0, 4.0)
    assert _capacity(e) == pytest.approx(4 / 3 * np.pi * 24, rel=1e-12)


def test_ellipsoid_zero_topcut_disables_both_cuts():
    # the intended two checks are "cuts inverted" AND "cuts active":
    # zTopCut == 0 means the kernel ignores both planes, so (3.1, 0) is
    # accepted and builds the uncut ellipsoid -- the semantics the former
    # chained comparison encoded accidentally, now explicit and pinned
    cut = Ellipsoid(3.0, 2.0, 4.0, 3.1, 0.0)
    uncut = Ellipsoid(3.0, 2.0, 4.0)
    assert _capacity(cut) == pytest.approx(_capacity(uncut), rel=1e-12)


def test_ellipsoid_inverted_active_cuts_raise():
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 1.0, -1.0)
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 2.0, 2.0)


def test_ellipsoid_bottom_cut_beyond_surface_raises_even_when_uncut():
    # the first clause (|cut| < dz) is independent of the cut-active flag:
    # same rejection as before the refactor
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 5.0, 0.0)
    with pytest.raises(ValueError, match="Wrong cut planes"):
        Ellipsoid(3.0, 2.0, 4.0, 0.0, -5.0)


def test_ellipsoid_checkparamaters_misspelled_alias_deprecated():
    with pytest.warns(DeprecationWarning, match="checkParams"):
        Ellipsoid(3.0, 2.0, 4.0).checkParamaters()


# ------------------------------------------------- pinned error-style fixes

def test_polyhedron_length_mismatch_raises_valueerror():
    # was RuntimeError; user input errors are ValueError across the module
    with pytest.raises(ValueError, match="same length"):
        Polyhedron(np.array([0.0, 5.0]), np.array([1.0]), np.array([2.0, 2.0]))


def test_polyhedron_sidecount_must_be_integral():
    # new integrality check: int(sideCount) used to truncate silently
    with pytest.raises(ValueError, match="sideCount"):
        Polyhedron(np.array([0.0, 10.0]), np.array([0.0, 0.0]), np.array([2.0, 2.0]), 6.5)


def test_boolean_solids_type_check_children():
    # a wrong type used to cross the bridge as a garbage pointer
    with pytest.raises(TypeError, match="left must be a Solid"):
        SolidUnion(42, Orb(1.0))
    with pytest.raises(TypeError, match="right must be a Solid"):
        SolidUnion(Box(1, 1, 1), None)
    with pytest.raises(TypeError, match="right_transf3d"):
        SolidUnion(Box(1, 1, 1), Orb(1.0), "not a frame")


def test_shared_validation_names_the_parameter():
    # the point of the param-table refactor: actionable error messages
    with pytest.raises(ValueError, match=r"Box\.hx: Negative value -1"):
        Box(-1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match=r"Tube\.phiDelta_deg \(400\) > 360"):
        Tube(1.0, 2.0, 5.0, 0, 400)


# ------------------------------------------------- frozen constructor surface

def test_constructor_signatures_unchanged():
    expected = {
        Box: ['self', 'hx', 'hy', 'hz'],
        Tube: ['self', 'rmin', 'rmax', 'z', 'phiStart_deg', 'phiDelta_deg', 'kwargs'],
        Sphere: ['self', 'rmin', 'rmax', 'phiStart_deg', 'phiDelta_deg',
                 'thetaStart_deg', 'thetaDelta_deg', 'kwargs'],
        Trapezoid: ['self', 'x1', 'x2', 'y1', 'y2', 'z'],
        Polyhedron: ['self', 'zPlanes', 'rMin', 'rMax', 'sideCount', 'phiStart_deg', 'phiDelta_deg'],
        Tessellated: ['self', 'polydata', 'tranMat'],
        ArbTrapezoid: ['self'] + [f'xy{i}' for i in range(1, 9)] + ['halfz'],
        Cone: ['self', 'rmaxBot', 'rmaxTop', 'z', 'rminBot', 'rminTop',
               'phiStart_deg', 'phiDelta_deg', 'kwargs'],
        CutTube: ['self', 'rmax', 'halfHeight', 'botNormal', 'topNormal',
                  'rmin', 'phiStart_deg', 'phiDelta_deg'],
        HyperbolicTube: ['self', 'rmax', 'inst', 'outst', 'halfHeight', 'rmin'],
        HypebolicTube: ['self', 'args', 'kwargs'],
        Orb: ['self', 'r'],
        Paraboloid: ['self', 'rbot', 'rtop', 'halfHeight'],
        PolyCone: ['self', 'vec_z', 'vec_rmin', 'vec_rmax', 'phiStart_deg', 'phiDelta_deg', 'kwargs'],
        Tetrahedron: ['self', 'p1', 'p2', 'p3', 'p4'],
        GenTrapezoid: ['self', 'dz', 'theta', 'phi', 'dy1', 'dx1', 'dx2',
                       'alpha1', 'dy2', 'dx3', 'dx4', 'alpha2', 'kwargs'],
        Ellipsoid: ['self', 'dx', 'dy', 'dz', 'zBottomCut', 'zTopCut'],
    }
    for cls, names in expected.items():
        assert list(inspect.signature(cls.__init__).parameters) == names, cls.__name__


def test_sentinel_and_numeric_defaults_unchanged():
    sig = inspect.signature(Tube.__init__).parameters
    assert sig['phiStart_deg'].default is _Unset  # fold sentinel, not a value
    assert inspect.signature(Cone.__init__).parameters['rminBot'].default == 0
    assert inspect.signature(Polyhedron.__init__).parameters['sideCount'].default == 6
    assert inspect.signature(HyperbolicTube.__init__).parameters['rmin'].default == 0
    assert inspect.signature(Ellipsoid.__init__).parameters['zTopCut'].default == 0
    assert inspect.signature(Tessellated.__init__).parameters['tranMat'].default is None


def test_cuttube_still_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        CutTube(2.0, 5.0, [0.0, 0.0, 1.0], [0.0, 0.0, 1.0])


def test_uniform_attribute_storage():
    # every solid now stores its parameters under the canonical names
    # (previously only Box/Ellipsoid did; scorer.makePSD hasattr-probes hx)
    t = Tube(1.0, 2.0, 5.0, 0, 90)
    assert (t.rmin, t.rmax, t.z, t.phiStart_deg, t.phiDelta_deg) == (1.0, 2.0, 5.0, 0, 90)
    g = GenTrapezoid(5.0, 0.1, 0.2, 3.0, 4.0, 5.0, 0.3, 3.5, 4.5, 6.0, 0.4)
    assert (g.dz, g.alpha2) == (5.0, 0.4)
    assert Box(1, 2, 3).hx == 1
