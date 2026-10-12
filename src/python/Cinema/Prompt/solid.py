################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################
"""
A Solid is a 3D geometry with shape and size.

This module provides a comprehensive set of geometric solid classes that wrap
C++ geometric primitives from the VecGeom library for Monte Carlo simulations.

Every solid is built through one declarative parameter table: a class declares
its parameters (kind, default, deprecated aliases) as ``Param`` entries and the
``Solid`` base runs the shared validate-then-build pipeline. Construction
failures raise ``ValueError``/``TypeError`` naming the offending parameter.

Additive introspection API on every solid:

    params()   canonical constructor keyword arguments (round-trip guarantee:
               ``type(s)(**s.params())`` rebuilds an equivalent solid)
    bounds()   conservative local-frame axis-aligned bounding box in mm
    repr(s)    eval-able reconstruction (except Tessellated, whose mesh
               buffers are not printable; use params() there)

Ownership: the C++ GeoManager keeps every shape alive for the process
lifetime; solids deliberately define no ``__del__`` (the Python object is only
a handle, and the C++ side is cleaned up with the GeoManager).

Classes:
    Solid - Base class for all geometric solids
    SolidIntersection - Boolean intersection of two solids
    SolidUnion - Boolean union of two solids
    SolidSubtraction - Boolean subtraction of two solids
    Box - Rectangular parallelepiped
    Tube - Cylindrical tube
    Sphere - Spherical shell
    Trapezoid - Trapezoidal prism
    Polyhedron - Polyhedral solid defined by z-planes
    Tessellated - Solid from polygonal mesh data
    ArbTrapezoid - Arbitrary trapezoid from 8 corner points
    Cone - Conical frustum with optional inner radii
    CutTube - Cut tube (not implemented, always raises)
    HyperbolicTube - Hyperbolic tube with stereo angles
    Orb - Perfect sphere
    Paraboloid - Parabolic solid
    PolyCone - Polyconical solid defined by z-planes
    Tetrahedron - Tetrahedral solid from 4 vertices
    GenTrapezoid - Generalized trapezoid with complex parameters
    Ellipsoid - Ellipsoidal solid with optional cuts
"""

import numpy as np
from ..Interface import *
from typing import Any, Callable, Union
import warnings
from dataclasses import dataclass
from .geo import Transformation3D

# C extension function imports for all solid types
_pt_Box_new = importFunc('pt_Box_new', type_voidp, [type_dbl, type_dbl, type_dbl])
_pt_Box_delete = importFunc('pt_Box_delete', None, [type_voidp] )
_pt_Tube_new = importFunc('pt_Tube_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl] )
_pt_Trapezoid_new = importFunc('pt_Trapezoid_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl] )
_pt_GenTrapezoid_new = importFunc('pt_GenTrapezoid_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl,type_dbl,type_dbl,type_dbl,type_dbl,type_dbl] )
_pt_Sphere_new = importFunc('pt_Sphere_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl] )
_pt_Polyhedron_new = importFunc('pt_Polyhedron_new', type_voidp, [type_dbl, type_dbl, type_int, type_int, type_npdbl1d, type_npdbl1d, type_npdbl1d] )
_pt_ArbTrapezoid_new = importFunc('pt_ArbTrapezoid_new', type_voidp, [type_npdbl1d, type_npdbl1d, type_npdbl1d, type_npdbl1d, type_npdbl1d, type_npdbl1d, type_npdbl1d, type_npdbl1d, type_dbl])
_pt_Cone_new = importFunc('pt_Cone_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl])
# pt_CutTube_new was bound here but its only caller always raised
# NotImplementedError before reaching it; the dead binding is dropped.
_pt_HypeTube_new = importFunc('pt_HypeTube_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl] )
_pt_Orb_new = importFunc('pt_Orb_new', type_voidp, [type_dbl])
_pt_Paraboloid_new = importFunc('pt_Paraboloid_new', type_voidp, [type_dbl, type_dbl, type_dbl])
_pt_Polycone_new = importFunc('pt_Polycone_new', type_voidp, [type_dbl, type_dbl, type_int, type_npdbl1d, type_npdbl1d, type_npdbl1d])
_pt_Tet_new = importFunc('pt_Tet_new', type_voidp, [type_npdbl1d, type_npdbl1d, type_npdbl1d, type_npdbl1d])
_pt_Ellipsoid_new = importFunc('pt_Ellipsoid_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl])

# Tessellated solid function
_pt_Tessellated_new = importFunc('pt_Tessellated_new', type_voidp, [type_sizet, type_npint641d, type_npdbl2d] )

# Boolean operation functions
_pt_solid_intersection = importFunc('pt_solid_intersection', type_voidp, [type_voidp, type_voidp, type_voidp])
_pt_solid_union = importFunc('pt_solid_union', type_voidp, [type_voidp, type_voidp, type_voidp])
_pt_solid_subtraction = importFunc('pt_solid_subtraction', type_voidp, [type_voidp, type_voidp, type_voidp])

# Sentinel used as the constructor-visible default of a parameter whose value
# is folded from a deprecated alias keyword (e.g. Tube(phiDelta_deg=_Unset,
# **{'deltaphi': ...})). Also marks "the caller did not provide this
# parameter" inside the binding pipeline, so an alias colliding with an
# explicitly passed canonical parameter can be rejected instead of silently
# overriding it.
_Unset = object()

# Sentinel marking a table parameter with no default: leaving it unbound is a
# missing-argument error (replaces GenTrapezoid's hand-rolled missing list).
_REQUIRED = object()

# Largest tilt/stereo angle (deg) accepted by GenTrapezoid/HyperbolicTube.
_RIGHT_ANGLE_DEG = 90


@dataclass(frozen=True)
class Param:
    """One entry of a solid's declarative parameter table.

    Attributes:
        name: canonical parameter name; also the attribute name the value is
            stored under, and the key used by ``Solid.params()``.
        kind: one of "length" (mm, rejects negatives), "angle_deg" (deg,
            converted to rad for the bridge), "count" (integral, rejects
            negatives and non-integers), "array" (converted to a C-contiguous
            float64 array), or "raw" (stored and passed through untouched).
        default: value used when the caller omits the parameter; the
            ``_REQUIRED`` sentinel marks a mandatory argument.
        allow_zero: length/count parameters accept zero when True (all
            historical solids admit zero, e.g. Tube rmin=0 is a solid
            cylinder); False additionally requires strictly positive.
        max_deg: optional angular-extent guard for "angle_deg" parameters;
            the single home of the historical ">360 deg" checks.
        abs_extent: if True (default) the extent guard tests ``abs(value)``;
            Cone sets False, preserving its historical asymmetric check.
        length: for "array" parameters, the required number of elements.
    """
    name: str
    kind: str
    default: Any = _REQUIRED
    allow_zero: bool = True
    max_deg: float | None = None
    abs_extent: bool = True
    length: int | None = None


def _repr_value(v):
    """Format one bound parameter for eval-able repr output."""
    if isinstance(v, np.ndarray):
        return repr(v.tolist())
    if isinstance(v, (float, np.floating)):
        return repr(float(v))
    if isinstance(v, (int, np.integer)):
        return repr(int(v))
    return repr(v)


class Solid:
    """
    Base class for all geometric solids.

    A concrete solid declares a ``_params`` tuple of :class:`Param` entries
    and the single ctypes ``_bridge`` call; ``__init__`` hands its locals to
    :meth:`_construct`, which runs the shared pipeline:

        1. ``_bind``          fold deprecated alias keywords, apply defaults,
                              collect values (missing mandatory parameters are
                              listed together in one TypeError)
        2. ``_validate``      per-kind fail-fast checks; every message names
                              the offending parameter
        3. attribute storage  every parameter is stored under its canonical
                              name (uniform access, e.g. Box.hx)
        4. ``_post_validate`` per-class relational hook (rmin<=rmax, cut
                              planes, ...)
        5. ``_build``         the single ctypes call; deg->rad conversion is
                              applied here, once, driven by the table

    Every solid additionally provides ``params()``, ``bounds()`` and an
    eval-able ``repr()`` (see the module docstring).

    Ownership: the C++ GeoManager owns the shape for the process lifetime;
    solids intentionally define no ``__del__``.
    """

    _params: tuple[Param, ...] = ()
    # deprecated keyword spelling -> canonical parameter name
    _legacy_aliases: dict[str, str] = {}
    _bridge: Callable | None = None
    # parameter names in the bridge argument order; defaults to _params order
    _bridge_args: tuple[str, ...] | None = None

    # ------------------------------------------------------------ pipeline

    def _construct(self, frame, kwargs=None):
        """Run the shared validate-then-build pipeline.

        Args:
            frame: the constructor's ``locals()`` (minus self/kwargs), giving
                the canonical parameters as passed positionally or by keyword
            kwargs: the constructor's ``**kwargs`` catch-all, scanned for
                deprecated alias spellings
        """
        values = self._bind(frame or {}, kwargs or {})
        self._validate(values)
        for name, v in values.items():
            setattr(self, name, v)
        self._values = dict(values)
        self._post_validate(values)
        self.cobj = self._build(values)
        return self

    def _bind(self, frame, kwargs):
        """Fold deprecated aliases and bind the parameter values.

        Raises ValueError when both spellings of one parameter are given,
        TypeError on leftover unknown keywords, and one TypeError listing all
        missing mandatory parameters.
        """
        cls = type(self)
        for old, new in cls._legacy_aliases.items():
            if old not in kwargs:
                continue
            if frame.get(new, _Unset) is not _Unset:
                raise ValueError(f"pass either '{new}' or its deprecated alias '{old}', not both")
            warnings.warn(f"keyword '{old}' is deprecated, use '{new}' instead",
                          DeprecationWarning, stacklevel=4)
            frame[new] = kwargs.pop(old)
        if kwargs:
            raise TypeError(f"unexpected keyword argument(s): {', '.join(sorted(kwargs))}")
        values, missing = {}, []
        for p in cls._params:
            v = frame.get(p.name, _Unset)
            if v is _Unset:
                v = p.default
            if v is _REQUIRED:
                missing.append(p.name)
                continue
            values[p.name] = v
        if missing:
            raise TypeError(f"missing required positional argument(s): {', '.join(missing)}")
        return values

    def _validate(self, values):
        """Per-kind validation; every message names the offending parameter."""
        cls = type(self).__name__
        for p in type(self)._params:
            v = values[p.name]
            if p.kind == 'length':
                if v < 0:
                    raise ValueError(f"{cls}.{p.name}: Negative value {v} (must be >= 0)")
                if not p.allow_zero and v == 0:
                    raise ValueError(f"{cls}.{p.name} must be > 0, got {v}")
            elif p.kind == 'count':
                try:
                    iv = int(v)
                except (TypeError, ValueError):
                    raise ValueError(f"{cls}.{p.name} must be an integer, got {v!r}") from None
                if iv != v:
                    raise ValueError(f"{cls}.{p.name} must be an integer, got {v}")
                if iv < 0:
                    raise ValueError(f"{cls}.{p.name}: Negative value {v} (must be >= 0)")
                values[p.name] = iv
            elif p.kind == 'angle_deg':
                if p.max_deg is not None:
                    extent = abs(v) if p.abs_extent else v
                    if extent > p.max_deg:
                        raise ValueError(f"{cls}.{p.name} ({v}) > {p.max_deg}. ill-defined angular extent")
            elif p.kind == 'array':
                values[p.name] = self._check_array(cls, p.name, v, p.length)
            # kind == 'raw': stored and passed through untouched

    def _post_validate(self, values):
        """Per-class relational hook; default no-op. Runs after the per-kind
        checks and after the values are stored as attributes, so it may use
        ``self.<name>``."""

    def _build(self, values):
        """The single ctypes call of the class; deg->rad conversion for
        "angle_deg" parameters happens here, driven by the table."""
        bridge = type(self)._bridge
        if bridge is None:
            raise NotImplementedError(f"{type(self).__name__} declares no bridge")
        pmap = {p.name: p for p in type(self)._params}
        order = type(self)._bridge_args if type(self)._bridge_args is not None else pmap.keys()
        args = []
        for name in order:
            p, v = pmap[name], values[name]
            if p.kind == 'angle_deg':
                args.append(np.deg2rad(v))
            elif p.kind == 'count':
                args.append(int(v))
            else:
                args.append(v)
        return bridge(*args)

    # ------------------------------------------------------ shared checks

    @staticmethod
    def _check_array(cls_name, name, v, length=None):
        """Convert user input to a C-contiguous float64 array, checking the
        element count and finiteness; the message names the parameter."""
        try:
            arr = np.ascontiguousarray(v, dtype=np.float64)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{cls_name}.{name} could not be converted to a "
                             f"float array: {e}") from None
        if arr.ndim == 0:
            raise ValueError(f"{cls_name}.{name} must be an array, got a scalar")
        if length is not None and arr.shape[0] != length:
            raise ValueError(f"{cls_name}.{name} must have {length} elements, got {arr.shape[0]}")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{cls_name}.{name} contains non-finite value(s); "
                             "all elements must be finite")
        return arr

    def _check_order(self, name_min, name_max):
        """Enforce name_min <= name_max for two stored parameters. The
        historical 'min (x) > max (y)' wording is kept (tests pin it)."""
        mn, mx = getattr(self, name_min), getattr(self, name_max)
        if mn > mx:
            raise ValueError(f"{type(self).__name__}: {name_min}/{name_max}: min ({mn}) > max ({mx})")

    # ------------------------------------------------- introspection API

    def params(self):
        """Return the bound parameter values as a dict of canonical
        constructor keyword arguments. Arrays are copied. Round-trip
        guarantee: ``type(s)(**s.params())`` rebuilds an equivalent solid."""
        return {name: (v.copy() if isinstance(v, np.ndarray) else v)
                for name, v in self._values.items()}

    def bounds(self):
        """Return ``(lo, hi)``, the conservative local-frame axis-aligned
        bounding box of the solid in mm. Conservative means it may
        over-estimate (e.g. angular cuts are not exploited) but never
        under-estimates the solid's extent."""
        raise NotImplementedError(f"{type(self).__name__} does not implement bounds()")

    def __repr__(self):
        inner = ', '.join(f"{name}={_repr_value(v)}" for name, v in self.params().items())
        return f"{type(self).__name__}({inner})"

    # -------------------------------------- legacy single-solid helpers

    def _sanityCheckPositive(self, *args: Union[float, int, np.ndarray]):
        """
        Legacy helper: reject negative values.

        Zero passes (despite an older docstring claiming otherwise, the code
        always admitted zero); the table-driven pipeline supersedes this
        helper, which is kept for backward compatibility.

        Raises:
            ValueError: If any parameter is negative
        """
        for arg in args:
            if isinstance(arg, np.ndarray):
                if np.any(arg < 0):
                    raise ValueError("Negative value found in array")
            else:
                if arg < 0:
                    raise ValueError(f"Negative value: {arg}")

    def _sanityCheckRelation(self, min, max):
        """
        Legacy helper: ensure min <= max for two scalar parameters.

        Raises:
            ValueError: If min > max
        """
        if min > max:
            raise ValueError(f"min ({min}) > max ({max})")

    def _arrayCheck(self, p):
        """
        Convert input array to a C-compatible numpy array.

        Args:
            p: List or numpy array to convert

        Returns:
            C-contiguous numpy array of type double
        """
        return np.ascontiguousarray(p, dtype=np.double)

    def _box_bounds(self, hx, hy, hz):
        """Axis-aligned box helper shared by the bounds() implementations."""
        lo = np.array([-hx, -hy, -hz], dtype=np.float64)
        hi = np.array([hx, hy, hz], dtype=np.float64)
        return lo, hi


class _BooleanBase(Solid):
    """Shared implementation of the three boolean solids. Each subclass is a
    shell supplying its bridge; children are fail-fast type-checked (a wrong
    type previously crossed the bridge as a garbage pointer)."""

    _op_bridge: Callable | None = None

    def __init__(self, left, right, right_transf3d = Transformation3D()):
        if not isinstance(left, Solid):
            raise TypeError(f"{type(self).__name__}.left must be a Solid, got {type(left).__name__}")
        if not isinstance(right, Solid):
            raise TypeError(f"{type(self).__name__}.right must be a Solid, got {type(right).__name__}")
        if not isinstance(right_transf3d, Transformation3D):
            raise TypeError(f"{type(self).__name__}.right_transf3d must be a Transformation3D, "
                            f"got {type(right_transf3d).__name__}")
        self.left = left
        self.right = right
        self.right_transf3d = right_transf3d
        self.cobj = type(self)._op_bridge(left.cobj, right.cobj, right_transf3d.cobj)

    def params(self):
        return {'left': self.left, 'right': self.right, 'right_transf3d': self.right_transf3d}

    def bounds(self):
        # conservative union of the child boxes; the right child is placed
        # through the relative transformation
        lo, hi = self.left.bounds()
        rlo, rhi = self.right.bounds()
        corners = np.array([[x, y, z] for x in (rlo[0], rhi[0])
                            for y in (rlo[1], rhi[1]) for z in (rlo[2], rhi[2])],
                           dtype=np.float64)
        moved = np.ascontiguousarray(self.right_transf3d.transform(corners))
        return np.minimum(lo, moved.min(axis=0)), np.maximum(hi, moved.max(axis=0))

    def __repr__(self):
        t = self.right_transf3d
        x, y, z = (float(c) for c in t.getTranslation())
        rx, ry, rz = (float(c) for c in t.euler_xyz)
        transf = (f"Transformation3D.from_euler_xyz({x!r}, {y!r}, {z!r}, "
                  f"{rx!r}, {ry!r}, {rz!r})")
        return (f"{type(self).__name__}(left={self.left!r}, right={self.right!r}, "
                f"right_transf3d={transf})")


class SolidIntersection(_BooleanBase):
    """
    Boolean intersection of two solids.

    Creates the geometric intersection (logical AND) of two solids.

    Args:
        left: First solid object
        right: Second solid object
        right_transf3d: Transformation for the second solid

    Example:
        >>> intersection = SolidIntersection(box1, sphere1, transform)
    """

    _op_bridge = staticmethod(_pt_solid_intersection)

    def __init__(self, left, right, right_transf3d = Transformation3D()):
        super().__init__(left, right, right_transf3d)

class SolidUnion(_BooleanBase):
    """
    Boolean union of two solids.

    Creates the geometric union (logical OR) of two solids.

    Args:
        left: First solid object
        right: Second solid object
        right_transf3d: Transformation for the second solid

    Example:
        >>> union = SolidUnion(cylinder1, box1, transform)
    """

    _op_bridge = staticmethod(_pt_solid_union)

    def __init__(self, left, right, right_transf3d = Transformation3D()):
        super().__init__(left, right, right_transf3d)

class SolidSubtraction(_BooleanBase):
    """
    Boolean subtraction of two solids.

    Subtracts the second solid from the first solid.

    Args:
        left: First solid object
        right: Second solid object
        right_transf3d: Transformation for the second solid

    Example:
        >>> subtraction = SolidSubtraction(sphere1, box1, transform)
    """

    _op_bridge = staticmethod(_pt_solid_subtraction)

    def __init__(self, left, right, right_transf3d = Transformation3D()):
        super().__init__(left, right, right_transf3d)

class Box(Solid):
    """
    Rectangular parallelepiped (box) solid.

    Args:
        hx: Half-length in x-direction. In unit mm.
        hy: Half-length in y-direction. In unit mm.
        hz: Half-length in z-direction. In unit mm.

    Example:
        >>> box = Box(5.0, 3.0, 2.0)  # 10x6x4 mm box
    """

    _params = (
        Param('hx', 'length'),
        Param('hy', 'length'),
        Param('hz', 'length'),
    )
    _bridge = staticmethod(_pt_Box_new)

    def __init__(self, hx, hy, hz):
        self._construct(locals())

    def bounds(self):
        return self._box_bounds(self.hx, self.hy, self.hz)

class Tube(Solid):
    """
    Cylindrical tube.

    Creates a tube with inner and outer radius, height, and angular limits.

    Args:
        rmin: Inner radius. In unit mm.
        rmax: Outer radius. In unit mm.
        z: Half-height. In unit mm.
        phiStart_deg: Starting angle in deg (default: 0)
        phiDelta_deg: Angular extent in deg (default: 360)

    Example:
        >>> tube = Tube(1.0, 2.0, 5.0)  # Full tube
        >>> tube_segment = Tube(1.0, 2.0, 5.0, 0, 90)  # Quarter tube

    The legacy spellings startphi/deltaphi are accepted as deprecated
    keyword aliases of phiStart_deg/phiDelta_deg.
    """

    _params = (
        Param('rmin', 'length'),
        Param('rmax', 'length'),
        Param('z', 'length'),
        Param('phiStart_deg', 'angle_deg', default=0),
        Param('phiDelta_deg', 'angle_deg', default=360, max_deg=360),
    )
    _legacy_aliases = {'startphi': 'phiStart_deg', 'deltaphi': 'phiDelta_deg'}
    _bridge = staticmethod(_pt_Tube_new)

    def __init__(self, rmin, rmax, z, phiStart_deg = _Unset, phiDelta_deg = _Unset, **kwargs):
        self._construct(locals(), kwargs)

    def _post_validate(self, values):
        self._check_order('rmin', 'rmax')

    def bounds(self):
        # full circle: a phi-cut tube can still reach the full radius
        return self._box_bounds(self.rmax, self.rmax, self.z)

class Sphere(Solid):
    """
    Spherical shell.

    Creates a spherical shell with inner and outer radii and angular limits.

    Args:
        rmin: Inner radius. In unit mm.
        rmax: Outer radius. In unit mm.
        phiStart_deg: Starting azimuthal angle in deg (default: 0)
        phiDelta_deg: Azimuthal extent in deg (default: 360)
        thetaStart_deg: Starting polar angle in deg (default: 0)
        thetaDelta_deg: Polar extent in deg (default: 180)

    Example:
        >>> sphere = Sphere(1.0, 2.0)  # Full sphere
        >>> sphere_segment = Sphere(1.0, 2.0, 0, 90, 0, 45)

    The legacy spellings startphi/deltaphi/starttheta/deltatheta are accepted
    as deprecated keyword aliases of the phiStart_deg/phiDelta_deg and
    thetaStart_deg/thetaDelta_deg pairs.
    """

    _params = (
        Param('rmin', 'length'),
        Param('rmax', 'length'),
        Param('phiStart_deg', 'angle_deg', default=0),
        Param('phiDelta_deg', 'angle_deg', default=360, max_deg=360),
        Param('thetaStart_deg', 'angle_deg', default=0),
        Param('thetaDelta_deg', 'angle_deg', default=180, max_deg=180),
    )
    _legacy_aliases = {'startphi': 'phiStart_deg', 'deltaphi': 'phiDelta_deg',
                       'starttheta': 'thetaStart_deg', 'deltatheta': 'thetaDelta_deg'}
    _bridge = staticmethod(_pt_Sphere_new)

    def __init__(self, rmin, rmax, phiStart_deg = _Unset, phiDelta_deg = _Unset, thetaStart_deg = _Unset, thetaDelta_deg = _Unset, **kwargs):
        self._construct(locals(), kwargs)

    def _post_validate(self, values):
        self._check_order('rmin', 'rmax')

    def bounds(self):
        # conservative: theta/phi cuts are not exploited
        return self._box_bounds(self.rmax, self.rmax, self.rmax)

class Trapezoid(Solid):
    """
    Trapezoidal prism solid.

    Creates a trapezoidal shape with specified dimensions.
    In unit mm.

    Args:
        x1: First x-dimension
        x2: Second x-dimension
        y1: First y-dimension
        y2: Second y-dimension
        z: Half-height

    Example:
        >>> trapezoid = Trapezoid(2.0, 4.0, 3.0, 6.0, 5.0)
    """

    _params = (
        Param('x1', 'length'),
        Param('x2', 'length'),
        Param('y1', 'length'),
        Param('y2', 'length'),
        Param('z', 'length'),
    )
    _bridge = staticmethod(_pt_Trapezoid_new)

    def __init__(self, x1, x2, y1, y2, z):
        self._construct(locals())

    def bounds(self):
        return self._box_bounds(max(self.x1, self.x2), max(self.y1, self.y2), self.z)

class Polyhedron(Solid):
    """
    Polyhedral solid defined by multiple z-planes.

    Creates a polyhedron from cross-sectional definitions at different z-positions.
    In unit mm.

    Args:
        zPlanes: Array of z-positions for cross-sections
        rMin: Array of minimum radii at each z-plane
        rMax: Array of maximum radii at each z-plane
        sideCount: Number of sides (default: 6 for hexagonal prism)
        phiStart_deg: Starting angle in deg (default: 0)
        phiDelta_deg: Angular extent in deg (default: 360)

    Example:
        >>> z = [0, 5, 10]
        >>> rmin = [1, 2, 1]
        >>> rmax = [3, 4, 3]
        >>> poly = Polyhedron(z, rmin, rmax)
    """

    _params = (
        Param('zPlanes', 'array'),
        Param('rMin', 'array'),
        Param('rMax', 'array'),
        Param('sideCount', 'count', default=6),
        Param('phiStart_deg', 'angle_deg', default=0),
        Param('phiDelta_deg', 'angle_deg', default=360, max_deg=360),
    )
    _bridge = staticmethod(_pt_Polyhedron_new)

    def __init__(self, zPlanes, rMin, rMax, sideCount = 6, phiStart_deg = 0, phiDelta_deg = 360):
        self._construct(locals())

    def _post_validate(self, values):
        # mismatched plane arrays are user input errors: ValueError, matching
        # the error style of the other solids (was RuntimeError)
        nz, na, nb = len(self.zPlanes), len(self.rMin), len(self.rMax)
        if nz != na or nz != nb:
            raise ValueError(f"Polyhedron: zPlanes, rMin, rMax must have same length "
                             f"(got {nz}, {na}, {nb})")
        for i in range(nz):
            for nm, v in (('rMin', self.rMin[i]), ('rMax', self.rMax[i])):
                if v < 0:
                    raise ValueError(f"Polyhedron.{nm}[{i}]: Negative value {v} (must be >= 0)")
            if self.rMin[i] > self.rMax[i]:
                raise ValueError(f"Polyhedron: rMin/rMax at plane {i}: "
                                 f"min ({self.rMin[i]}) > max ({self.rMax[i]})")

    def _build(self, values):
        # plane count is derived from the arrays; angles arrive in rad
        return _pt_Polyhedron_new(np.deg2rad(self.phiStart_deg), np.deg2rad(self.phiDelta_deg),
                                  self.sideCount, len(self.zPlanes),
                                  self.zPlanes, self.rMin, self.rMax)

    def bounds(self):
        zmin, zmax = float(np.min(self.zPlanes)), float(np.max(self.zPlanes))
        r = float(np.max(self.rMax))
        # full circle: a phi-cut solid can still reach the full radius
        lo = np.array([-r, -r, zmin], dtype=np.float64)
        hi = np.array([r, r, zmax], dtype=np.float64)
        return lo, hi

class Tessellated(Solid):
    """
    Solid defined by polygonal mesh data.

    Creates a solid from pyvista PolyData mesh. Requires pyvista library.

    Args:
        polydata: pyvista PolyData object containing mesh
        tranMat: Optional transformation (Transformation3D) applied to the
            mesh points

    repr() is informational only (mesh buffers are not printable); rebuild
    via ``type(s)(**s.params())`` instead.
    """

    _params = (
        Param('polydata', 'raw'),
        Param('tranMat', 'raw', default=None),
    )

    def __init__(self, polydata, tranMat = None):
        self._construct(locals())

    def _points(self):
        """Mesh points as built into the solid (tranMat applied)."""
        pts = np.ascontiguousarray(self.polydata.points, dtype=np.float64)
        if self.tranMat is not None:
            pts = self.tranMat.transform(pts)
        return pts

    def _post_validate(self, values):
        try:
            import pyvista
        except ImportError:
            raise ImportError("pyvista is required to construct a Tessellated "
                              "solid (polydata must be a pyvista PolyData mesh)") from None
        if not isinstance(self.polydata, pyvista.core.pointset.PolyData):
            raise RuntimeError('Tessellated solid only supports pyvista.core.pointset.PolyData')
        if self.tranMat is not None and not isinstance(self.tranMat, Transformation3D):
            raise TypeError(f"Tessellated.tranMat must be a Transformation3D or None, "
                            f"got {type(self.tranMat).__name__}")
        points = self._points()
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"Tessellated: mesh points must have shape (N, 3), got {points.shape}")
        if not np.all(np.isfinite(points)):
            raise ValueError("Tessellated: mesh points contain non-finite value(s); "
                             "all coordinates must be finite")
        faces = np.asarray(self.polydata.faces)
        if faces.ndim != 1 or faces.size == 0 or not np.issubdtype(faces.dtype, np.integer):
            raise ValueError("Tessellated: polydata.faces must be a non-empty 1-D "
                             "integer array in packed format")
        if self.polydata.n_faces_strict > 100:
            warnings.warn(f"Tessellated solid is initiallised by "
                          f"{self.polydata.n_faces_strict} faces.", stacklevel=3)

    def _build(self, values):
        faces = np.ascontiguousarray(self.polydata.faces, dtype=np.int64)
        return _pt_Tessellated_new(faces.shape[0], faces, self._points())

    def bounds(self):
        pts = self._points()
        return pts.min(axis=0), pts.max(axis=0)

    def __repr__(self):
        return (f"Tessellated(polydata={type(self.polydata).__name__}"
                f"({self.polydata.n_points} points, {self.polydata.n_faces_strict} faces), "
                f"tranMat={self.tranMat!r})")

class ArbTrapezoid(Solid):
    """
    Arbitrary trapezoid defined by 8 corner points.

    Creates a complex trapezoidal shape from 8 corner coordinates.

    Args:
        xy1 to xy8: 8 corner points as (x, y) pairs
        halfz: Half-height of the trapezoid

    Example:
        >>> corners = [np.array([x, y]) for x,y in [...]]
        >>> arb_trap = ArbTrapezoid(*corners, 5.0)
    """

    _params = (
        Param('xy1', 'array', length=2),
        Param('xy2', 'array', length=2),
        Param('xy3', 'array', length=2),
        Param('xy4', 'array', length=2),
        Param('xy5', 'array', length=2),
        Param('xy6', 'array', length=2),
        Param('xy7', 'array', length=2),
        Param('xy8', 'array', length=2),
        Param('halfz', 'length'),
    )
    _bridge = staticmethod(_pt_ArbTrapezoid_new)

    def __init__(self, xy1, xy2, xy3, xy4, xy5, xy6, xy7, xy8, halfz):
        self._construct(locals())

    def bounds(self):
        pts = np.stack([getattr(self, f'xy{i}') for i in range(1, 9)])
        lo = np.array([pts[:, 0].min(), pts[:, 1].min(), -self.halfz], dtype=np.float64)
        hi = np.array([pts[:, 0].max(), pts[:, 1].max(), self.halfz], dtype=np.float64)
        return lo, hi

class Cone(Solid):
    """
    Conical frustum.

    Creates a conical shape with bottom and top radii and optional hollow sections.

    Args:
        rmaxBot: Maximum radius at bottom
        rmaxTop: Maximum radius at top
        z: Height
        rminBot: Minimum radius at bottom (default: 0)
        rminTop: Minimum radius at top (default: 0)
        phiStart_deg: Starting angle in deg (default: 0)
        phiDelta_deg: Angular extent in deg (default: 360)

    Example:
        >>> cone = Cone(3.0, 1.0, 10.0)  # Solid cone
        >>> hollow_cone = Cone(3.0, 1.0, 10.0, 1.0, 0.5)  # Hollow cone

    The legacy spellings startPhi/deltaPhi are accepted as deprecated
    keyword aliases of phiStart_deg/phiDelta_deg.
    """

    _params = (
        Param('rmaxBot', 'length'),
        Param('rmaxTop', 'length'),
        Param('z', 'length'),
        Param('rminBot', 'length', default=0),
        Param('rminTop', 'length', default=0),
        Param('phiStart_deg', 'angle_deg', default=0),
        # abs_extent=False preserves the historical (drifted) Cone check that
        # only rejects positive extents above 360 deg; flagged for the user
        Param('phiDelta_deg', 'angle_deg', default=360, max_deg=360, abs_extent=False),
    )
    _legacy_aliases = {'startPhi': 'phiStart_deg', 'deltaPhi': 'phiDelta_deg'}
    _bridge = staticmethod(_pt_Cone_new)
    _bridge_args = ('rminBot', 'rmaxBot', 'rminTop', 'rmaxTop', 'z',
                    'phiStart_deg', 'phiDelta_deg')

    def __init__(self, rmaxBot, rmaxTop, z, rminBot = 0, rminTop = 0, phiStart_deg = _Unset, phiDelta_deg = _Unset, **kwargs) -> None:
        self._construct(locals(), kwargs)

    def _post_validate(self, values):
        self._check_order('rminBot', 'rmaxBot')
        self._check_order('rminTop', 'rmaxTop')

    def bounds(self):
        r = max(self.rmaxBot, self.rmaxTop)
        return self._box_bounds(r, r, self.z)


class CutTube(Solid):
    """
    Cut tube (cylindrical tube with non-parallel end planes).

    Not implemented: construction always raises NotImplementedError (the
    transport tracing point is not handled for this shape yet; see the issue
    tracker). The signature is kept so callers can be written against the
    final API; use Tube for the common cylindrical case.
    """

    def __init__(self, rmax, halfHeight, botNormal, topNormal, rmin = 0, phiStart_deg = 0, phiDelta_deg = 360) -> None:
        raise NotImplementedError("CutTube got problems, See issue!")
        # TODO:fix tracing point location problem

class HyperbolicTube(Solid):
    """
    Hyperbolic tube with stereo angles.

    Creates a hyperbolic tube shape with specified stereo angles.

    Args:
        rmax: Outer radius. In unit mm.
        inst: Inner stereo angle. In unit deg.
        outst: Outer stereo angle. In unit deg.
        halfHeight: Half-height. In unit mm.
        rmin: Inner radius. In unit mm. (default: 0)

    Methods:
        stereoAngleCheck: Validates stereo angles (in deg) are < 90 deg

    Example:
        >>> hype_tube = HyperbolicTube(5.0, 0.1, 0.2, 10.0)
    """

    _params = (
        Param('rmax', 'length'),
        Param('inst', 'angle_deg'),
        Param('outst', 'angle_deg'),
        Param('halfHeight', 'length'),
        Param('rmin', 'length', default=0),
    )
    _bridge = staticmethod(_pt_HypeTube_new)
    _bridge_args = ('rmin', 'rmax', 'inst', 'outst', 'halfHeight')

    def __init__(self, rmax, inst, outst, halfHeight, rmin = 0):
        self._construct(locals())

    def _post_validate(self, values):
        cls = type(self).__name__
        # the stereo angles are degree-based and must be non-negative
        for nm in ('inst', 'outst'):
            v = getattr(self, nm)
            if v < 0:
                raise ValueError(f"{cls}.{nm}: Negative value {v} (must be >= 0)")
        self._check_order('rmin', 'rmax')
        self.stereoAngleCheck(self.inst, self.outst)

    def stereoAngleCheck(self, *args):
        # input (and therefore the message) is in deg, matching the ctor args
        for p in args:
            if p > _RIGHT_ANGLE_DEG:
                raise ValueError(f"Too strong stereo angle {p}! Please check! "
                                 f"Must be in unit deg and less than {_RIGHT_ANGLE_DEG} deg.")

    def bounds(self):
        # hyperbolic profile (G4Hype convention): the surface radius grows
        # with |z| as sqrt(r^2 + z^2 tan^2(stereo)), so the end faces are the
        # widest points; using the larger stereo angle is conservative
        tan_stereo = abs(np.tan(np.deg2rad(max(self.inst, self.outst))))
        r_end = np.hypot(self.rmax, self.halfHeight * tan_stereo)
        return self._box_bounds(r_end, r_end, self.halfHeight)

class HypebolicTube(HyperbolicTube):
    """
    Deprecated misspelled alias of HyperbolicTube.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn("HypebolicTube is a misspelling and deprecated, use HyperbolicTube instead", DeprecationWarning, stacklevel=2)
        super().__init__(*args, **kwargs)

class Orb(Solid):
    """
    Perfect sphere solid.

    Creates a simple sphere with uniform radius.

    Orb(r) covers the same region as Sphere(0, r) but is a distinct C++
    kernel type; both are kept working.

    Args:
        r: Radius of the sphere. In unit mm.

    Example:
        >>> sphere = Orb(5.0)  # Sphere with radius 5
    """

    _params = (
        Param('r', 'length'),
    )
    _bridge = staticmethod(_pt_Orb_new)

    def __init__(self, r):
        self._construct(locals())

    def bounds(self):
        return self._box_bounds(self.r, self.r, self.r)

class Paraboloid(Solid):
    """
    Parabolic solid.

    Creates a paraboloid shape.

    Args:
        rbot: Radius at bottom. In unit mm.
        rtop: Radius at top. In unit mm.
        halfHeight: Half-height. In unit mm.

    Raises:
        ValueError: If rbot >= rtop. The vendored transport kernel is written
            for rhi > rlo; inverted radii make DistanceToOut/DistanceToIn
            return garbage (negative/infinite), and equal radii are not a
            defined shape (the profile parabola through two equal-radius
            circles is not unique), so both are rejected loudly.

    Example:
        >>> paraboloid = Paraboloid(1.0, 3.0, 5.0)
    """

    _params = (
        Param('rbot', 'length'),
        Param('rtop', 'length'),
        Param('halfHeight', 'length'),
    )
    _bridge = staticmethod(_pt_Paraboloid_new)

    def __init__(self, rbot, rtop, halfHeight):
        self._construct(locals())

    def _post_validate(self, values):
        if self.rbot >= self.rtop:
            raise ValueError(f"Paraboloid requires rbot < rtop, got rbot={self.rbot}, rtop={self.rtop}")

    def bounds(self):
        r = max(self.rbot, self.rtop)
        return self._box_bounds(r, r, self.halfHeight)

class PolyCone(Solid):
    """
    Polyconical solid defined by multiple z-planes.

    Creates a complex conical shape with multiple cross-sectional definitions.

    Args:
        vec_z: Array of z-positions. In unit mm.
        vec_rmin: Array of minimum radii. In unit mm.
        vec_rmax: Array of maximum radii. In unit mm.
        phiStart_deg: Starting angle in deg (default: 0)
        phiDelta_deg: Angular extent in deg (default: 360)

    Methods:
        sizeConsistencyCheck: Validates array sizes match
        monotonicCheck: Ensures z-positions are monotonic

    Example:
        >>> z = [0, 2, 4, 6]
        >>> rmin = [1, 1.5, 2, 1.5]
        >>> rmax = [3, 3.5, 4, 3.5]
        >>> polycone = PolyCone(z, rmin, rmax)

    The legacy spellings sphi/dphi are accepted as deprecated keyword aliases
    of phiStart_deg/phiDelta_deg.
    """

    _params = (
        Param('vec_z', 'array'),
        Param('vec_rmin', 'array'),
        Param('vec_rmax', 'array'),
        Param('phiStart_deg', 'angle_deg', default=0),
        Param('phiDelta_deg', 'angle_deg', default=360, max_deg=360),
    )
    _legacy_aliases = {'sphi': 'phiStart_deg', 'dphi': 'phiDelta_deg'}
    _bridge = staticmethod(_pt_Polycone_new)

    def __init__(self, vec_z, vec_rmin, vec_rmax, phiStart_deg = _Unset, phiDelta_deg = _Unset, **kwargs):
        self._construct(locals(), kwargs)

    def sizeConsistencyCheck(self, *arg):
        vec_size = len(arg[0])
        if any([len(p) != vec_size for p in arg]):
            raise ValueError("Input vector size for planes not consistent!")

    def monotonicCheck(self, *arg : np.ndarray):
        for p in arg:
            if not ((p == np.sort(p)).all() or (p == np.sort(p)[::-1]).all()):
                raise ValueError(f"Plane location inputs should be monotonic! {p}")

    def _post_validate(self, values):
        self.sizeConsistencyCheck(self.vec_z, self.vec_rmin, self.vec_rmax)
        for i, (mmin, mmax) in enumerate(zip(self.vec_rmin, self.vec_rmax)):
            if mmin > mmax:
                raise ValueError(f"PolyCone: rmin/rmax at plane {i}: min ({mmin}) > max ({mmax})")
        self.monotonicCheck(self.vec_z)

    def _build(self, values):
        # plane count is derived from the arrays; angles arrive in rad
        return _pt_Polycone_new(np.deg2rad(self.phiStart_deg), np.deg2rad(self.phiDelta_deg),
                                len(self.vec_z), self.vec_z, self.vec_rmin, self.vec_rmax)

    def bounds(self):
        zmin, zmax = float(np.min(self.vec_z)), float(np.max(self.vec_z))
        r = float(np.max(self.vec_rmax))
        # full circle: a phi-cut solid can still reach the full radius
        lo = np.array([-r, -r, zmin], dtype=np.float64)
        hi = np.array([r, r, zmax], dtype=np.float64)
        return lo, hi

class Tetrahedron(Solid):
    """
    Tetrahedral solid from four vertices.

    Args:
        p1 to p4: Vertex coordinates as (x, y, z) arrays. In unit mm.
    """

    _params = (
        Param('p1', 'array', length=3),
        Param('p2', 'array', length=3),
        Param('p3', 'array', length=3),
        Param('p4', 'array', length=3),
    )
    _bridge = staticmethod(_pt_Tet_new)

    def __init__(self, p1, p2, p3, p4) -> None:
        self._construct(locals())

    def _arrayCheck(self, *args):
        # kept as-is for backward compatibility: this historical *args
        # override shadows the base single-array helper (flagged quirk, the
        # pipeline itself uses Solid._check_array)
        ps = []
        for p in args:
            ps.append(super()._arrayCheck(p))
        return ps

    def bounds(self):
        pts = np.stack([self.p1, self.p2, self.p3, self.p4])
        return pts.min(axis=0), pts.max(axis=0)


class GenTrapezoid(Solid):
    """
    Generalized trapezoid with complex parameters (Geant4 G4Trap style).

    All lengths in unit mm, all angles in unit deg.

    Args:
        dz: Half-height
        theta, phi: Polar/azimuthal tilt of the axis (0 <= angle <= 90)
        dy1, dx1, dx2, alpha1: First end-face half-dimensions and tilt
        dy2, dx3, dx4, alpha2: Second end-face half-dimensions and tilt

    The tilt angles must be non-negative: negative tilts (allowed by
    Geant4's G4Trap) are not implemented and rejected loudly.

    Example:
        >>> gen_trap = GenTrapezoid(5.0, 0.1, 0.2, 3.0, 4.0, 5.0, 0.3, 3.5, 4.5, 6.0, 0.4)

    The legacy spellings Alpha1/Alpha2 are accepted as deprecated keyword
    aliases of alpha1/alpha2.
    """

    _params = (
        Param('dz', 'length'),
        Param('theta', 'angle_deg'),
        Param('phi', 'angle_deg'),
        Param('dy1', 'length'),
        Param('dx1', 'length'),
        Param('dx2', 'length'),
        Param('alpha1', 'angle_deg'),
        Param('dy2', 'length'),
        Param('dx3', 'length'),
        Param('dx4', 'length'),
        Param('alpha2', 'angle_deg'),
    )
    _legacy_aliases = {'Alpha1': 'alpha1', 'Alpha2': 'alpha2'}
    _bridge = staticmethod(_pt_GenTrapezoid_new)

    def __init__(self, dz, theta, phi, dy1, dx1, dx2, alpha1 = _Unset, dy2 = _Unset, dx3 = _Unset, dx4 = _Unset, alpha2 = _Unset, **kwargs):
        self._construct(locals(), kwargs)

    def _post_validate(self, values):
        cls = type(self).__name__
        # dz..dx2 are lengths already checked by the table; the four angles
        # need the non-negative and <= right-angle restrictions
        for nm in ('theta', 'phi', 'alpha1', 'alpha2'):
            v = getattr(self, nm)
            if v < 0:
                raise ValueError(f"{cls}.{nm}: Negative value {v} (must be >= 0; "
                                 "negative tilts (G4Trap) are not implemented)")
            if v > _RIGHT_ANGLE_DEG:
                raise ValueError(f"{cls}.{nm}: min ({v}) > max ({_RIGHT_ANGLE_DEG})")

    def bounds(self):
        # conservative box: axis tilt widens x/y by dz*tan(tilt), and the
        # end-face tilts (alpha) widen x by up to dy*tan(alpha)
        dx_max = max(self.dx1, self.dx2, self.dx3, self.dx4)
        dy_max = max(self.dy1, self.dy2)
        x_slack = (abs(self.dz) * np.tan(np.deg2rad(self.theta))
                   + abs(self.dy1) * np.tan(np.deg2rad(self.alpha1))
                   + abs(self.dy2) * np.tan(np.deg2rad(self.alpha2)))
        y_slack = abs(self.dz) * np.tan(np.deg2rad(self.phi))
        return self._box_bounds(dx_max + x_slack, dy_max + y_slack, abs(self.dz))

class Ellipsoid(Solid):
    """
    Ellipsoidal solid with optional cuts.

    Creates an ellipsoid with specified semi-axes and optional cut planes.

    Args:
        dx: Semi-axis in x-direction
        dy: Semi-axis in y-direction
        dz: Semi-axis in z-direction
        zBottomCut: Bottom cut plane (default: 0)
        zTopCut: Top cut plane (default: 0)

    Cut-plane rule: with the default zTopCut = 0 the kernel treats both cut
    planes as unset and builds the full ellipsoid (a zero top cut disables
    both cuts). When cuts are active, they must lie strictly inside the
    ellipsoid (|cut| < dz) and ordered (zBottomCut < zTopCut).

    Methods:
        checkParams: Validates cut plane positions

    Example:
        >>> ellipsoid = Ellipsoid(3.0, 2.0, 4.0)  # Full ellipsoid
        >>> cut_ellipsoid = Ellipsoid(3.0, 2.0, 4.0, -2.0, 2.0)  # Cut ellipsoid
    """

    _params = (
        Param('dx', 'length'),
        Param('dy', 'length'),
        Param('dz', 'length'),
        # cut planes legitimately go negative: no sign validation ('raw')
        Param('zBottomCut', 'raw', default=0),
        Param('zTopCut', 'raw', default=0),
    )
    _bridge = staticmethod(_pt_Ellipsoid_new)

    def __init__(self, dx, dy, dz, zBottomCut = 0, zTopCut = 0):
        self._construct(locals())

    def checkParams(self):
        """Validate the cut planes; see the class docstring for the rule.

        The ordering clause is written as two explicit checks: the former
        ``zBottomCut >= self.zTopCut != 0`` chained comparison encoded the
        same logic but read like an accidental comparison chain.
        """
        if (self.zBottomCut >= self.dz or self.zTopCut <= -self.dz
                or (self.zTopCut != 0 and self.zBottomCut >= self.zTopCut)):
            raise ValueError(f"Wrong cut planes. Please check! zBottomCut = {self.zBottomCut}; zTopCut = {self.zTopCut}")

    def checkParamaters(self):
        """Deprecated misspelled alias of :meth:`checkParams`."""
        warnings.warn("Ellipsoid.checkParamaters is deprecated, use checkParams instead",
                      DeprecationWarning, stacklevel=2)
        return self.checkParams()

    def _post_validate(self, values):
        self.checkParams()

    def bounds(self):
        zlo, zhi = -self.dz, self.dz
        if self.zTopCut != 0:  # cuts active (zero top cut disables both)
            zlo, zhi = max(zlo, self.zBottomCut), min(zhi, self.zTopCut)
        return np.array([-self.dx, -self.dy, zlo], dtype=np.float64), \
               np.array([self.dx, self.dy, zhi], dtype=np.float64)
