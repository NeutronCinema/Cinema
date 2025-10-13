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
import numpy as np
from ..Interface import *
from typing import Union

#box
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


#Tessellated
_pt_Tessellated_new = importFunc('pt_Tessellated_new', type_voidp, [type_sizet, type_npint641d, type_npdbl2d] )

#boolean operation
_pt_solid_intersection = importFunc('pt_solid_intersection', type_voidp, [type_voidp, type_voidp, type_voidp])
_pt_solid_union = importFunc('pt_solid_union', type_voidp, [type_voidp, type_voidp, type_voidp])
_pt_solid_subtraction = importFunc('pt_solid_subtraction', type_voidp, [type_voidp, type_voidp, type_voidp])



class Solid:
    def __init__(self) -> None:
        pass

    def sanityCheckPositive(self, *args: Union[float, int, np.ndarray]):
        for p in args:
            if isinstance(p, np.ndarray):
                if any(p < 0):
                    raise ValueError(
                        f"Invalid input! Each element of {p} should be positive value or zero!")
            elif p < 0:
                raise ValueError(f"Invalid input! {p} should be positive value or zero!")
            
    def sanityCheckRelation(self, min, max):
        if min > max:
            raise ValueError(f"Invalid inputs! rmin ({min}) should less than or equal rmax ({max}))!")

    def arrayCheck(self, p):
        """
        If a pointer points to an array, its elements can be read and written using standard subscript and slice accesses
        Ref: https://docs.python.org/3/library/ctypes.html#ctypes._Pointer
        """
        if isinstance(p, list):
            p = np.array(p)
        p_c = p.astype(np.double)
        return p_c

class SolidIntersection(Solid):
    def __init__(self, left : Solid, right: Solid, right_transf3d):
       self.cobj =  _pt_solid_intersection(left.cobj, right.cobj, right_transf3d.cobj)

class SolidUnion(Solid):
    def __init__(self, left : Solid, right: Solid, right_transf3d):
       self.cobj =  _pt_solid_union(left.cobj, right.cobj, right_transf3d.cobj)

class SolidSubtraction(Solid):
    def __init__(self, left : Solid, right: Solid, right_transf3d):
       self.cobj =  _pt_solid_subtraction(left.cobj, right.cobj, right_transf3d.cobj)


# _pt_solid_union = importFunc('pt_solid_union', type_voidp, [type_voidp, type_voidp, type_voidp])
# _pt_solid_subtraction = importFunc('pt_solid_subtraction', type_voidp, [type_voidp, type_voidp, type_voidp])


class Box(Solid):
    def __init__(self, hx, hy, hz):
        self.sanityCheckPositive(hx, hy, hz)
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
    def __init__(self, rmin, rmax, z, startphi = 0, deltaphi = 360):
        self.sanityCheckPositive(rmin, rmax, z, deltaphi)
        self.cobj = _pt_Tube_new(rmin, rmax, z, np.deg2rad(startphi), np.deg2rad(deltaphi))

class Sphere(Solid):
    def __init__(self, rmin, rmax, startphi=0., deltaphi=2*np.pi, starttheta=0., deltatheta=np.pi):
        self.sanityCheckPositive(rmin, rmax, deltaphi, deltatheta)
        self.cobj = _pt_Sphere_new(rmin, rmax, startphi, deltaphi, starttheta, deltatheta)

class Trapezoid(Solid):
    def __init__(self, x1, x2, y1, y2, z) -> None:
        self.sanityCheckPositive(x1, x2, y1, y2, z)
        self.cobj = _pt_Trapezoid_new(x1, x2, y1, y2, z)

class Polyhedron(Solid):
    def __init__(self, zPlanes, rMin, rMax, sideCount=6,
                 phiStart_deg=0, phiDelta_deg=360) -> None:
        self.sanityCheckPositive(zPlanes, rMin, rMax, sideCount,phiDelta_deg)
        zp, rmin, rmax = np.array(zPlanes), np.array(rMin), np.array(rMax)
        if zp.size!=rmin.size or rmin.size!=rmax.size:
            raise RuntimeError('the sizes of zPlanes, rMin and rMax are not equal')    
        
        self.cobj = _pt_Polyhedron_new(np.deg2rad(phiStart_deg), np.deg2rad(phiDelta_deg), int(sideCount), int(zp.size), 
                 zp, rmin, rmax)

class Tessellated(Solid): #this one is not working
    def __init__(self, polydata, tranMat=None) -> None:
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
    def __init__(self, xy1 : np.ndarray, xy2 : np.ndarray, xy3 : np.ndarray, xy4 : np.ndarray,
                 xy5 : np.ndarray, xy6 : np.ndarray, xy7 : np.ndarray, xy8 : np.ndarray, halfz) -> None:
        self.sanityCheckPositive(halfz)
        # if not xy1.flags['C_CONTIGUOUS']:         TODO: solid or not when ndarray is not contiguous?
            # xy1 = np.ascontiguousarray(xy1, dtype=xy1.dtype)
        # xy1 = ctypes.cast(xy1.ctypes.data, type_dblp)
        vectors = (xy1, xy2, xy3, xy4, xy5, xy6, xy7, xy8)
        p_vecs = []
        for vec in vectors:
            p_vecs.append(self.arrayCheck(vec))
        self.cobj = _pt_ArbTrapezoid_new(p_vecs[0], p_vecs[1], p_vecs[2], p_vecs[3], p_vecs[4], p_vecs[5], p_vecs[6], p_vecs[7], halfz)

        # self.cobj = _pt_ArbTrapezoid_new( xy1, xy2, xy3, xy4, xy5, xy6, xy7, xy8, halfz)

class Cone(Solid):
    def __init__(self, rmaxBot, rmaxTop, z, rminBot = 0, rminTop = 0, startPhi = 0, deltaPhi = 360) -> None:
        self.sanityCheckPositive(rmaxBot, rmaxTop, z, rminBot, rminTop, deltaPhi)
        self.sanityCheckRelation(rminBot, rmaxBot)
        self.sanityCheckRelation(rminTop, rmaxTop)
        self.cobj = _pt_Cone_new(rminBot, rmaxBot, rminTop, rmaxTop, z, np.deg2rad(startPhi), np.deg2rad(deltaPhi))
       

class CutTube(Solid):
    def __init__(self, rmax, halfHeight, botNormal, topNormal, rmin = 0, sphi = 0, dphi = 360) -> None:
        raise NotImplementedError("CutTube got problems, See issue!")
        # TODO:fix tracing point location problem
        # super().__init__()
        # self.sanityCheckPositive(rmin, rmax, halfHeight, dphi)
        # botN = self.arrayCheck(botNormal)
        # topN = self.arrayCheck(topNormal)
        # self.sanityCheck(rmin, rmax)
        # self.cobj = _pt_CutTube_new(rmin, rmax, halfHeight, np.deg2rad(sphi), np.deg2rad(dphi), botN, topN)
        
class HypebolicTube(Solid):
    def __init__(self, rmax, inst, outst, halfHeight, rmin = 0) -> None:
        super().__init__()
        self.sanityCheckPositive(rmin, rmax, inst, outst, halfHeight)
        self.sanityCheckRelation(rmin, rmax)
        self.stereoAngleCheck(inst, outst)
        self.cobj = _pt_HypeTube_new(rmin, rmax, inst, outst, halfHeight)

    def stereoAngleCheck(self, *args):
        for p in args:
            if p > np.pi / 2:
                raise ValueError(f"Too strong stereo angle {p}! Please check! Must be in unit rad. Less than pi/2 suggested!")
            

class Orb(Solid):
    def __init__(self, r) -> None:
        super().__init__()
        self.sanityCheckPositive(r)
        self.cobj = _pt_Orb_new(r)


class Paraboloid(Solid):
    def __init__(self, rbot, rtop, halfHeight) -> None:
        super().__init__()
        self.sanityCheckPositive(rbot, rtop, halfHeight)
        self.cobj = _pt_Paraboloid_new(rbot, rtop, halfHeight)


class PolyCone(Solid):
    def __init__(self, vec_z : np.ndarray, vec_rmin : np.ndarray, vec_rmax : np.ndarray, sphi = 0, dphi = 360) -> None:
        super().__init__()
        self.sanityCheckPositive(sphi, dphi, vec_rmin, vec_rmax)
        self.sizeConsistencyCheck(vec_z, vec_rmin, vec_rmax)
        self.sanityCheckRelation(vec_rmin, vec_rmax)
        self.monotonicCheck(vec_z)
        planeNum = len(vec_z)
        pot_z = self.arrayCheck(vec_z)
        pot_rmin = self.arrayCheck(vec_rmin)
        pot_rmax = self.arrayCheck(vec_rmax)
        self.cobj = _pt_Polycone_new(np.deg2rad(sphi), np.deg2rad(dphi), planeNum, pot_z, pot_rmin, pot_rmax)

    def sizeConsistencyCheck(self, *arg):
        vec_size = len(arg[0])
        if any([len(p) != vec_size for p in arg]):
            raise ValueError("Input vector size for planes not consistent!")
        
    def sanityCheckRelation(self, min : np.ndarray, max : np.ndarray):
        for mmin, mmax in zip(min, max):
            super().sanityCheckRelation(mmin, mmax)

    def monotonicCheck(self, *arg : np.ndarray):
        for p in arg:
            if not ((p == np.sort(p)).all() or (p == np.sort(p)[::-1]).all()):
                raise ValueError(f"Plane location inputs should be monotonic! {p}")
            

class Tetrahedron(Solid):
    def __init__(self, p1, p2, p3, p4) -> None:
        super().__init__()
        ps = self.arrayCheck(p1, p2, p3, p4)
        self.cobj = _pt_Tet_new(ps[0], ps[1], ps[2], ps[3])
    
    def arrayCheck(self, *args):
        ps = []
        for p in args:
            ps.append(super().arrayCheck(p))
        return ps


class GenTrapezoid(Solid):
    def __init__(self, dz, theta, phi, dy1, dx1, dx2, Alpha1, dy2, dx3, dx4, Alpha2) -> None:
        super().__init__()
        self.sanityCheckPositive(dz, theta, phi, dy1, dx1, dx2, Alpha1, dy2, dx3, dx4, Alpha2)
        self.sanityCheckRelation(theta, 90)
        self.sanityCheckRelation(phi, 90)
        self.sanityCheckRelation(Alpha1, 90)
        self.sanityCheckRelation(Alpha2, 90)
        self.cobj = _pt_GenTrapezoid_new(dz, np.deg2rad(theta), np.deg2rad(phi), dy1, dx1, dx2, np.deg2rad(Alpha1), dy2, dx3, dx4, np.deg2rad(Alpha2))

class Ellipsoid(Solid):
    def __init__(self, dx, dy, dz, zBottomCut = 0, zTopCut = 0) -> None:
        super().__init__()
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