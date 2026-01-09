################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2024 Prompt developers                                     ##
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
    HypebolicTube - Hyperbolic tube with stereo angles
    Orb - Perfect sphere
    Paraboloid - Parabolic solid
    PolyCone - Polyconical solid defined by z-planes
    Tetrahedron - Tetrahedral solid from 4 vertices
    GenTrapezoid - Generalized trapezoid with complex parameters
    Ellipsoid - Ellipsoidal solid with optional cuts
"""

import numpy as np
from ..Interface import *
from typing import Union
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
_pt_CutTube_new = importFunc('pt_CutTube_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_npdbl1d, type_npdbl1d])
_pt_HypeTube_new = importFunc('pt_HypeTube_new', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl])
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

class Solid:
    """
    Base class for all geometric solids.
    
    Provides common validation methods and serves as the foundation for
    all specific geometric shapes
    
    """

    def _sanityCheckPositive(self, *args: Union[float, int, np.ndarray]):
        """
        Validate that all input parameters are positive numbers or zero.
        
        Args:
            *args: Variable number of numeric values or numpy arrays
            
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
        Ensure min <= max relationship for geometric parameters.
        
        Args:
            min: Minimum value
            max: Maximum value
            
        Raises:
            ValueError: If min > max
        """
        if min > max:
            raise ValueError(f"min ({min}) > max ({max})")
        
    def _arrayCheck(self, p):
        """
        Convert input arrays to C-compatible numpy arrays.
        
        Args:
            p: List or numpy array to convert
            
        Returns:
            C-contiguous numpy array of type double
        """
        return np.ascontiguousarray(p, dtype=np.double)

class SolidIntersection(Solid):
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
    
    def __init__(self, left, right, right_transf3d = Transformation3D()):
        self.cobj = _pt_solid_intersection(left.cobj, right.cobj, right_transf3d.cobj)

class SolidUnion(Solid):
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
    
    def __init__(self, left, right, right_transf3d = Transformation3D()):
        self.cobj = _pt_solid_union(left.cobj, right.cobj, right_transf3d.cobj)

class SolidSubtraction(Solid):
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
    
    def __init__(self, left, right, right_transf3d = Transformation3D()):
        self.cobj = _pt_solid_subtraction(left.cobj, right.cobj, right_transf3d.cobj)

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
    
    def __init__(self, hx, hy, hz):
        self._sanityCheckPositive(hx, hy, hz)
        self.cobj = _pt_Box_new(hx, hy, hz)
        self.hx = hx
        self.hy = hy
        self.hz = hz

    # the memory should be managed by the Volume. 
    # fixme: double check if it is release at the very end
    def __del__(self):
        # _pt_Box_delete(self.cobj)
        pass

class Tube(Solid):
    """
    Cylindrical tube.
    
    Creates a tube with inner and outer radius, height, and angular limits.
    
    Args:
        rmin: Inner radius. In unit mm.
        rmax: Outer radius. In unit mm.
        z: Half-height. In unit mm.
        startphi: Starting angle in deg (default: 0)
        deltaphi: Angular extent in deg (default: 360)
        
    Example:
        >>> tube = Tube(1.0, 2.0, 5.0)  # Full tube
        >>> tube_segment = Tube(1.0, 2.0, 5.0, 0, np.deg2rad(90))  # Quarter tube
    """
    
    def __init__(self, rmin, rmax, z, startphi = 0, deltaphi = 360):
        self._sanityCheckPositive(rmin, rmax, z)
        self._sanityCheckRelation(rmin, rmax)
        if abs(deltaphi) > 360:
            raise ValueError(f"deltaphi ({deltaphi}) > 360. ill-defined angular extent")
        self.cobj = _pt_Tube_new(rmin, rmax, z, np.deg2rad(startphi), np.deg2rad(deltaphi))

class Sphere(Solid):
    """
    Spherical shell.
    
    Creates a spherical shell with inner and outer radii and angular limits.
    
    Args:
        rmin: Inner radius. In unit mm.
        rmax: Outer radius. In unit mm.
        startphi: Starting azimuthal angle in deg (default: 0)
        deltaphi: Azimuthal extent in deg (default: 360)
        starttheta: Starting polar angle in deg (default: 0)
        deltatheta: Polar extent in deg (default: 180)
        
    Example:
        >>> sphere = Sphere(1.0, 2.0)  # Full sphere
        >>> sphere_segment = Sphere(1.0, 2.0, 0, 90, 0, 45)
    """
    
    def __init__(self, rmin, rmax, startphi = 0, deltaphi = 360, starttheta = 0, deltatheta = 180):
        self._sanityCheckPositive(rmin, rmax)
        self._sanityCheckRelation(rmin, rmax)
        if abs(deltaphi) > 360:
            raise ValueError(f"deltaphi ({deltaphi}) > 360. ill-defined angular extent")
        if abs(deltatheta) > 180:
            raise ValueError(f"deltatheta ({deltatheta}) > 180. ill-defined angular extent")
        self.cobj = _pt_Sphere_new(rmin, rmax, np.deg2rad(startphi), np.deg2rad(deltaphi), np.deg2rad(starttheta), np.deg2rad(deltatheta))

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
    
    def __init__(self, x1, x2, y1, y2, z):
        self._sanityCheckPositive(x1, x2, y1, y2, z)
        self.cobj = _pt_Trapezoid_new(x1, x2, y1, y2, z)

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
    
    def __init__(self, zPlanes, rMin, rMax, sideCount = 6, phiStart_deg = 0, phiDelta_deg = 360):
        if len(zPlanes) != len(rMin) or len(zPlanes) != len(rMax):
            raise RuntimeError("zPlanes, rMin, rMax must have same length")
        
        self._sanityCheckPositive(sideCount)
        for i in np.arange(len(zPlanes)):
            self._sanityCheckPositive(rMin[i], rMax[i])
            self._sanityCheckRelation(rMin[i], rMax[i])
        if abs(phiDelta_deg) > 360:
            raise ValueError(f"phiDelta_deg ({phiDelta_deg}) > 360. ill-defined angular extent")
        self.cobj = _pt_Polyhedron_new(np.deg2rad(phiStart_deg), np.deg2rad(phiDelta_deg), int(sideCount), int(len(zPlanes)), 
                 zPlanes, rMin, rMax)

class Tessellated(Solid):
    """
    Solid defined by polygonal mesh data.
    
    Creates a solid from pyvista PolyData mesh. Requires pyvista library.
    
    Args:
        polydata: pyvista PolyData object containing mesh
        tranMat: Optional transformation matrix

    """
    
    def __init__(self, polydata, tranMat = None):
        try:
            import pyvista
        except:
            raise ImportError("pyvista is required to visualize.")
        super().__init__()
        if not isinstance(polydata, pyvista.core.pointset.PolyData):
            raise RuntimeError('Tessellated solid only supports pyvista.core.pointset.PolyData')
        points = polydata.points.astype(float)
        faces = polydata.faces
        if tranMat is not None:
            points=tranMat.transform(points)
        if polydata.n_faces_strict > 100:
            print(f'Warning: Tessellated solid is initiallised by {polydata.n_faces_strict} faces.')
        self.cobj = _pt_Tessellated_new(faces.shape[0], faces, points)

class ArbTrapezoid(Solid):
    """
    Arbitrary trapezoid defined by 8 corner points.
    
    Creates a complex trapezoidal shape from 8 corner coordinates.
    
    Args:
        xy1 to xy8: 8 corner points as numpy arrays
        halfz: Half-height of the trapezoid
        
    Example:
        >>> corners = [np.array([x, y]) for x,y in [...]]
        >>> arb_trap = ArbTrapezoid(*corners, 5.0)
    """
    
    def __init__(self, xy1, xy2, xy3, xy4, xy5, xy6, xy7, xy8, halfz):
        vec = [xy1, xy2, xy3, xy4, xy5, xy6, xy7, xy8]
        v = self._arrayCheck(vec)
        self._sanityCheckPositive(halfz)
        
        self.cobj = _pt_ArbTrapezoid_new(*v, halfz)

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
        startPhi: Starting angle in degrees (default: 0)
        deltaPhi: Angular extent in degrees (default: 360)
        
    Example:
        >>> cone = Cone(3.0, 1.0, 10.0)  # Solid cone
        >>> hollow_cone = Cone(3.0, 1.0, 10.0, 1.0, 0.5)  # Hollow cone
    """
    
    def __init__(self, rmaxBot, rmaxTop, z, rminBot = 0, rminTop = 0, startPhi = 0, deltaPhi = 360) -> None:
        self._sanityCheckPositive(rmaxBot, rmaxTop, z, rminBot, rminTop)
        self._sanityCheckRelation(rminBot, rmaxBot)
        self._sanityCheckRelation(rminTop, rmaxTop)
        if deltaPhi > 360:
            raise ValueError(f"deltaPhi ({deltaPhi}) > 360. ill-defined angular extent")
        self.cobj = _pt_Cone_new(rminBot, rmaxBot, rminTop, rmaxTop, z, np.deg2rad(startPhi), np.deg2rad(deltaPhi))
       

class CutTube(Solid):
    def __init__(self, rmax, halfHeight, botNormal, topNormal, rmin = 0, sphi = 0, dphi = 360) -> None:
        raise NotImplementedError("CutTube got problems, See issue!")
        # TODO:fix tracing point location problem
        # super().__init__()
        # self._sanityCheckPositive(rmin, rmax, halfHeight, dphi)
        # botN = self._arrayCheck(botNormal)
        # topN = self._arrayCheck(topNormal)
        # self.sanityCheck(rmin, rmax)
        # self.cobj = _pt_CutTube_new(rmin, rmax, halfHeight, np.deg2rad(sphi), np.deg2rad(dphi), botN, topN)
        
class HypebolicTube(Solid):
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
        stereoAngleCheck: Validates stereo angles < π/2
        
    Example:
        >>> hype_tube = HypebolicTube(5.0, 0.1, 0.2, 10.0)
    """
    
    def __init__(self, rmax, inst, outst, halfHeight, rmin = 0):
        self._sanityCheckPositive(rmin, rmax, inst, outst, halfHeight)
        self._sanityCheckRelation(rmin, rmax)
        inst, outst = np.deg2rad(inst), np.deg2rad(outst)
        self.stereoAngleCheck(inst, outst)
        self.cobj = _pt_HypeTube_new(rmin, rmax, inst, outst, halfHeight)

    def stereoAngleCheck(self, *args):
        for p in args:
            if p > np.pi / 2:
                raise ValueError(f"Too strong stereo angle {p}! Please check! Must be in unit rad. Less than pi/2 suggested!")

class Orb(Solid):
    """
    Perfect sphere solid.
    
    Creates a simple sphere with uniform radius.
    
    Args:
        r: Radius of the sphere. In unit mm.
        
    Example:
        >>> sphere = Orb(5.0)  # Sphere with radius 5
    """
    
    def __init__(self, r):
        self._sanityCheckPositive(r)
        self.cobj = _pt_Orb_new(r)

class Paraboloid(Solid):
    """
    Parabolic solid.
    
    Creates a paraboloid shape.
    
    Args:
        rbot: Radius at bottom. In unit mm.
        rtop: Radius at top. In unit mm.
        halfHeight: Half-height. In unit mm.
        
    Example:
        >>> paraboloid = Paraboloid(3.0, 1.0, 5.0)
    """
    
    def __init__(self, rbot, rtop, halfHeight):
        self._sanityCheckPositive(rbot, rtop, halfHeight)
        self.cobj = _pt_Paraboloid_new(rbot, rtop, halfHeight)

class PolyCone(Solid):
    """
    Polyconical solid defined by multiple z-planes.
    
    Creates a complex conical shape with multiple cross-sectional definitions.
    
    Args:
        vec_z: Array of z-positions. In unit mm.
        vec_rmin: Array of minimum radii. In unit mm.
        vec_rmax: Array of maximum radii. In unit mm.  
        sphi: Starting angle in degrees (default: 0)
        dphi: Angular extent in degrees (default: 360)
        
    Methods:
        sizeConsistencyCheck: Validates array sizes match
        monotonicCheck: Ensures z-positions are monotonic
        
    Example:
        >>> z = [0, 2, 4, 6]
        >>> rmin = [1, 1.5, 2, 1.5]
        >>> rmax = [3, 3.5, 4, 3.5]
        >>> polycone = PolyCone(z, rmin, rmax)
    """
    
    def __init__(self, vec_z, vec_rmin, vec_rmax, sphi = 0, dphi = 360):
        self.sizeConsistencyCheck(vec_z, vec_rmin, vec_rmax)
        self._sanityCheckRelation(vec_rmin, vec_rmax)
        self.monotonicCheck(vec_z)
        planeNum = len(vec_z)
        pot_z = self._arrayCheck(vec_z)
        pot_rmin = self._arrayCheck(vec_rmin)
        pot_rmax = self._arrayCheck(vec_rmax)
        self.cobj = _pt_Polycone_new(np.deg2rad(sphi), np.deg2rad(dphi), planeNum, pot_z, pot_rmin, pot_rmax)

    def sizeConsistencyCheck(self, *arg):
        vec_size = len(arg[0])
        if any([len(p) != vec_size for p in arg]):
            raise ValueError("Input vector size for planes not consistent!")
        
    def _sanityCheckRelation(self, min : np.ndarray, max : np.ndarray):
        for mmin, mmax in zip(min, max):
            super()._sanityCheckRelation(mmin, mmax)

    def monotonicCheck(self, *arg : np.ndarray):
        for p in arg:
            if not ((p == np.sort(p)).all() or (p == np.sort(p)[::-1]).all()):
                raise ValueError(f"Plane location inputs should be monotonic! {p}")
            

class Tetrahedron(Solid):
    def __init__(self, p1, p2, p3, p4) -> None:
        super().__init__()
        ps = self._arrayCheck(p1, p2, p3, p4)
        self.cobj = _pt_Tet_new(ps[0], ps[1], ps[2], ps[3])
    
    def _arrayCheck(self, *args):
        ps = []
        for p in args:
            ps.append(super()._arrayCheck(p))
        return ps


class GenTrapezoid(Solid):
    """
    Generalized trapezoid with complex parameters.
    
    Creates a trapezoid with multiple dimensional and angular parameters.
    
    Args:
        dz: Half-height
        theta, phi: Angular parameters
        dy1, dx1, dx2, Alpha1: First set of dimensions and angles
        dy2, dx3, dx4, Alpha2: Second set of dimensions and angles
        
    Example:
        >>> gen_trap = GenTrapezoid(5.0, 0.1, 0.2, 3.0, 4.0, 5.0, 0.3, 3.5, 4.5, 6.0, 0.4)
    """
    
    def __init__(self, dz, theta, phi, dy1, dx1, dx2, Alpha1, dy2, dx3, dx4, Alpha2):
        self._sanityCheckPositive(dz, theta, phi, dy1, dx1, dx2, Alpha1, dy2, dx3, dx4, Alpha2)
        self._sanityCheckRelation(theta, 90)
        self._sanityCheckRelation(phi, 90)
        self._sanityCheckRelation(Alpha1, 90)
        self._sanityCheckRelation(Alpha2, 90)
        self.cobj = _pt_GenTrapezoid_new(dz, np.deg2rad(theta), np.deg2rad(phi), dy1, dx1, dx2, np.deg2rad(Alpha1), dy2, dx3, dx4, np.deg2rad(Alpha2))

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
        
    Methods:
        checkParamaters: Validates cut plane positions
        
    Example:
        >>> ellipsoid = Ellipsoid(3.0, 2.0, 4.0)  # Full ellipsoid
        >>> cut_ellipsoid = Ellipsoid(3.0, 2.0, 4.0, -2.0, 2.0)  # Cut ellipsoid
    """
    
    def __init__(self, dx, dy, dz, zBottomCut = 0, zTopCut = 0):
        self._sanityCheckPositive(dx, dy, dz)
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.zBottomCut = zBottomCut
        self.zTopCut = zTopCut
        self.checkParamaters()
        self.cobj = _pt_Ellipsoid_new(dx, dy, dz, zBottomCut, zTopCut)

    def checkParamaters(self):
        if self.zBottomCut >= self.dz or self.zTopCut <= - self.dz or self.zBottomCut >= self.zTopCut != 0:
            raise ValueError(f"Wrong cut planes. Please check! zBottomCut = {self.zBottomCut}; zTopCut = {self.zTopCut}")