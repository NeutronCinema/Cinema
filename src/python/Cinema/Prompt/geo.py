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

import warnings
from typing import Union

from scipy.spatial.transform import Rotation as scipyRot
from ..Interface import *
from .Mesh import _pt_Transformation3D_transform
from copy import deepcopy
from .scorer import Scorer
from .physics import _validateNccfgFiles, _validateMatCfg, wrapRawNccfg

__all__ = ['Volume', 'Transformation3D']


# C function imports for Volume class
_pt_Volume_new = importFunc('pt_Volume_new', type_voidp, [type_cstr, type_voidp])
_pt_Volume_delete = importFunc('pt_Volume_delete', None, [type_voidp] )
_pt_Volume_placeChild = importFunc('pt_Volume_placeChild', None, [type_voidp, type_cstr, type_voidp, type_voidp, type_int])

_pt_Volume_id = importFunc('pt_Volume_id', type_uint, [type_voidp])
_pt_Volume_capacity = importFunc('pt_Volume_capacity', type_dbl, [type_voidp])

# C function imports for Transformation3D class
_pt_Transformation3D_newfromdata = importFunc('pt_Transformation3D_newfromdata', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl])
_pt_Transformation3D_delete = importFunc('pt_Transformation3D_delete', None, [type_voidp] )
_pt_Transformlation3D_setRotation  = importFunc('pt_Transformlation3D_setRotation', None, [type_voidp, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl] )
_pt_Transformlation3D_setTranslation  = importFunc('pt_Transformlation3D_setTranslation', None, [type_voidp, type_dbl, type_dbl, type_dbl] )


# Resource manager C function imports
# addScorer/addSurface are bridged (int status + pt_last_error message,
# surfaced through raiseOnBridgeError) so a rejected cfg raises a normal
# RuntimeError instead of aborting the process at the ctypes boundary
_pt_ResourceManager_addNewVolume = importFunc('pt_ResourceManager_addNewVolume', None, [type_uint])
_pt_ResourceManager_addScorer = importFunc('pt_ResourceManager_addScorer', type_int, [type_uint, type_cstr, type_voidp])
_pt_ResourceManager_addSurface = importFunc('pt_ResourceManager_addSurface', type_int, [type_uint, type_cstr])
_pt_ResourceManager_cfgVolPhysics = importFunc('pt_ResourceManager_cfgVolPhysics', None, [type_uint, type_cstr])


class Transformation3D:
    """
    Transformation in 3d-space of Volume, manipulating on Volume translation and rotation.
    Provided with methods for intrinsic (local coordinate) and extrinsic (global coordinate) rotation.
    
    Attributes:
        cobj (void*): Pointer to C++ transformation object
        __sciRot (scipyRot): Scipy rotation object for Python-side operations
        __translation (ndarray): Translation vector [x, y, z]
    """
    def __init__(self, 
                 x:float=0., y:float=0., z:float=0., 
                 rot_z:float=0., rot_new_x:float=0., rot_new_z:float=0., 
                 degrees=True):
        """
        Initialize transformation with translation and ZXZ Euler angles.
        Intrinsic rotation follows ZXZ convention.
        
        Args:
            x (float, optional): X translation. Default: 0.0
            y (float, optional): Y translation. Default: 0.0
            z (float, optional): Z translation. Default: 0.0
            rot_z (float, optional): First Z rotation angle. Default: 0.0
            rot_new_x (float, optional): X rotation angle. Default: 0.0
            rot_new_z (float, optional): Second Z rotation angle. Default: 0.0
            degrees (bool, optional): Whether angles are in degrees. Default: True

        Raises:
            TypeError: If any positional argument is not a number (e.g. a
                vector or None). To build a frame from a position vector,
                unpack it first: Transformation3D(*pos)
        """
        # validate/coerce before any ctypes call: a vector or None passed by
        # mistake used to surface as a raw ctypes.ArgumentError from the
        # binding, followed by a confusing __del__ traceback on the
        # half-initialized object
        try:
            x, y, z = float(x), float(y), float(z)
            rot_z, rot_new_x, rot_new_z = float(rot_z), float(rot_new_x), float(rot_new_z)
        except (TypeError, ValueError):
            raise TypeError(
                "Transformation3D expects 6 numbers "
                "(x, y, z, rot_z, rot_new_x, rot_new_z), got an argument of "
                f"type {type(x).__name__}. To build a frame from a position "
                "vector, unpack it first: Transformation3D(*pos)") from None
        # Rotation follows ZXZ convention in vecgeom backend
        self.cobj = _pt_Transformation3D_newfromdata(x, y, z, rot_z, rot_new_x, rot_new_z, 1, 1, 1)
        self.__sciRot = scipyRot.from_euler('ZXZ', [rot_z, rot_new_x, rot_new_z], degrees)
        self.__translation = np.array([x, y, z])
        # self.update_cpp_rot()


    @classmethod 
    def from_euler_xyz(cls, x=0., y=0., z=0., rx=0., ry=0., rz=0., degrees=True):
        """
        Create transformation from xyz Euler angles.
        Extrinsic rotation follows xyz convention.
        
        Args:
            x (float, optional): X translation. Default: 0.0
            y (float, optional): Y translation. Default: 0.0
            z (float, optional): Z translation. Default: 0.0
            rx (float, optional): X rotation angle. Default: 0.0
            ry (float, optional): Y rotation angle. Default: 0.0
            rz (float, optional): Z rotation angle. Default: 0.0
            degrees (bool, optional): Whether angles are in degrees. Default: True
            
        Returns:
            Transformation3D: New transformation object
        """
        obj = cls(x,y,z)
        sciRot = scipyRot.from_euler('xyz', [rx, ry, rz], degrees)
        obj.setSciRot(sciRot)
        return obj

    @classmethod
    def from_alignment(cls, x=0., y=0., z=0., rotated:np.ndarray=None, original:np.ndarray=None):
        """
        Create transformation by aligning vectors.

        The resulting rotation maps the original vectors onto the rotated
        vectors (R . original[i] == rotated[i]).

        Args:
            x (float, optional): X translation. Default: 0.0
            y (float, optional): Y translation. Default: 0.0
            z (float, optional): Z translation. Default: 0.0
            rotated (ndarray): Target vectors after rotation (Nx3)
            original (ndarray): Original vectors before rotation (Nx3)

        Returns:
            Transformation3D: New transformation object

        Raises:
            RuntimeError: If rotated or original vectors are not provided
        """
        # guard must test each argument separately: "if rotated or original
        # is None" is parsed as "(rotated) or (original is None)" and made
        # this constructor fail for every array input
        if rotated is None or original is None:
            raise RuntimeError('Both the rotated and original vectors must be provided')
        obj = cls(x,y,z)
        obj.setRotByAlignment(rotated, original)
        return obj

    @classmethod
    def from_alignement(cls, x=0., y=0., z=0., rotated:np.ndarray=None, original:np.ndarray=None):
        """Deprecated spelling of :meth:`from_alignment`."""
        warnings.warn("Transformation3D.from_alignement is deprecated, "
                      "use from_alignment instead.",
                      DeprecationWarning, stacklevel=2)
        return cls.from_alignment(x, y, z, rotated=rotated, original=original)

    @property
    def euler_xyz(self):
        """Get XYZ Euler angles extrinsic representation of rotation.
        
        Returns:
            ndarray: XYZ Euler angles in degrees
        """
        return self.__sciRot.as_euler('xyz', True)

    def __deepcopy__(self, memo):
        """Create a deep copy of the transformation.
        
        Args:
            memo: Memo dictionary for deepcopy
            
        Returns:
            Transformation3D: Deep copy of current object
        """
        copy = type(self)()
        memo[id(self)] = copy
        copy.cobj = _pt_Transformation3D_newfromdata(self.__translation[0], self.__translation[1], self.__translation[2],
                                                     0, 0, 0, 1.,1.,1.)
        copy._Transformation3D__sciRot = scipyRot.from_matrix(self.__sciRot.as_matrix())
        # the mangled attribute must be set explicitly: the copy used to get
        # the value in a non-mangled "_translation" attribute (aliasing the
        # source array), so the documented getTranslation() accessor reported
        # [0, 0, 0] on every deepcopied frame
        copy._Transformation3D__translation = self.__translation.copy()
        copy.update_cpp_rot()
        return copy

    def __del__(self):
        """Clean up C++ transformation object."""
        # guard against __del__ running on a never-initialized object (e.g.
        # when __init__ raised before assigning cobj)
        if hasattr(self, 'cobj'):
            _pt_Transformation3D_delete(self.cobj)
    
    # TODO: review the transformation operations
    # def __mul__(self, other):
    #     '''
    #     Transformation following another parent transformation.
    #     a dot B: a project in B, successive add up
    #     '''
    #     rot = self.getRotMatrix().dot(other.getRotMatrix())
    #     transl = self.translation + other.getTranslation().dot(self.getRotMatrix())
    #     transf = Transformation3D(transl[0], transl[1], transl[2])
    #     transf.sciRot = self.sciRot * other.sciRot
    #     transf.applyTrans(rot)
    #     return transf

    # def __mul__(self, other):
    #     rot = self.getRotMatrix().dot(other.getRotMatrix())
    #     transl = self.__translation + self.getRotMatrix().dot(other.getTranslation())
    #     transf = Transformation3D(transl[0], transl[1], transl[2])
    #     transf._Transformation3D__sciRot = self.__sciRot * other.sciRot
    #     transf.applyTrans(rot)
    #     return transf

    # def inv(self):
    #     inversion = type(self)(-self.__translation[0], -self.__translation[1], -self.__translation[2])
    #     inversion._Transformation3D__sciRot = self.__sciRot.inv()
    #     inversion.update_cpp_rot()
    #     return inversion

    def __mul__(self, other):
        """
        Compose two transformations: `other` is applied first, then self
        (parent frame composed with a child frame expressed in it).

        Args:
            other (Transformation3D): Transformation applied first

        Returns:
            Transformation3D: The composed transformation
        """
        rot = self.getRotMatrix().dot(other.getRotMatrix())
        transl = self.getTranslation() + self.getRotMatrix().dot(other.getTranslation())
        return type(self)(transl[0], transl[1], transl[2]).setSciRot(scipyRot.from_matrix(rot))

    def update_cpp_rot(self):
        """Push Python side roation to C++ side."""
        mat = self.__sciRot.as_matrix()
        _pt_Transformlation3D_setRotation(self.cobj, mat[0,0], mat[0,1], mat[0,2],
                                          mat[1,0], mat[1,1], mat[1,2],
                                          mat[2,0], mat[2,1], mat[2,2])
        
    def applyRotAxis(self, angle, axis, degrees=True):
        """
        Apply rotation around arbitrary axis.
        
        Args:
            angle (float): Rotation angle
            axis (array-like): Rotation axis vector
            degrees (bool, optional): Whether angle is in degrees. Default: True
            
        Returns:
            Transformation3D: Self for method chaining
        """
        axis = np.array(axis)
        rot = scipyRot.from_rotvec(angle * axis/np.linalg.norm(axis), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotX(self, angle, degrees=True):
        """
        Apply rotation around X axis.
        
        Args:
            angle (float): Rotation angle
            degrees (bool, optional): Whether angle is in degrees. Default: True
            
        Returns:
            Transformation3D: Self for method chaining
        """
        rot = scipyRot.from_rotvec(angle * np.array([1,0,0.]), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotY(self, angle, degrees=True):
        """
        Apply rotation around Y axis.
        
        Args:
            angle (float): Rotation angle
            degrees (bool, optional): Whether angle is in degrees. Default: True
            
        Returns:
            Transformation3D: Self for method chaining
        """
        rot = scipyRot.from_rotvec(angle * np.array([0,1,0.]), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotZ(self, angle, degrees=True):
        """
        Apply rotation around Z axis.
        
        Args:
            angle (float): Rotation angle
            degrees (bool, optional): Whether angle is in degrees. Default: True
            
        Returns:
            Transformation3D: Self for method chaining
        """
        rot = scipyRot.from_rotvec(angle * np.array([0,0,1.]), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotxyz(self, rotx, roty, rotz, degrees=True):
        """
        Apply extrinsic rotation using xyz Euler angles.
        
        Args:
            rotx (float): X rotation angle
            roty (float): Y rotation angle
            rotz (float): Z rotation angle
            degrees (bool, optional): Whether angles are in degrees. Default: True
            
        Returns:
            Transformation3D: Self for method chaining
        """
        rot = scipyRot.from_euler('xyz', [rotx, roty, rotz], degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self

    def applyRotbyMatrix(self, refMatrix):
        """
        Apply rotation by multiplying with reference matrix.

        Args:
            refMatrix (ndarray): 3x3 reference rotation matrix

        Returns:
            Transformation3D: Self for method chaining
        """
        # the new matrix (R_cur . refMatrix) must also update the Python
        # side: re-wrapping the OLD matrix here left __sciRot stale, so
        # C++/Python transforms diverged and deepcopy silently dropped
        # the applied rotation
        mat = self.__sciRot.as_matrix().dot(refMatrix)
        self.__sciRot = scipyRot.from_matrix(mat)
        _pt_Transformlation3D_setRotation(self.cobj, mat[0,0], mat[0,1], mat[0,2],
                                          mat[1,0], mat[1,1], mat[1,2],
                                          mat[2,0], mat[2,1], mat[2,2])
        return self

    def setRotByAlignment(self, rotated, original):
        """
        Set rotation so that it maps the original vectors onto the rotated
        vectors (R . original[i] == rotated[i], like
        scipyRot.align_vectors(rotated, original)).

        Args:
            rotated (ndarray): Target vectors after rotation (shape: Nx3)
            original (ndarray): Original vectors before rotation (shape: Nx3)

        Returns:
            Transformation3D: Self for method chaining

        Raises:
            RuntimeError: If vectors don't contain exactly 2 vectors
        """
        if len(original)!= len(rotated) or len(original)!=2:
            raise RuntimeError('rotated and original should be contain 2 vectors')
        # argument order matters: align_vectors(a, b) returns the rotation
        # with a.apply(b) == a, i.e. R maps original onto rotated; the old
        # align_vectors(original, rotated) stored the inverse rotation
        self.__sciRot, rssd = scipyRot.align_vectors(rotated, original)
        self.update_cpp_rot()
        return self

    def setRotByAlignement(self, rotated, original):
        """Deprecated spelling of :meth:`setRotByAlignment`."""
        warnings.warn("Transformation3D.setRotByAlignement is deprecated, "
                      "use setRotByAlignment instead.",
                      DeprecationWarning, stacklevel=2)
        return self.setRotByAlignment(rotated, original)

    def setSciRot(self, sciRot):
        """
        Set rotation from scipy rotation object.
        
        Args:
            sciRot (scipyRot): Scipy rotation object
            
        Returns:
            Transformation3D: Self for method chaining
        """
        self.__sciRot = deepcopy(sciRot)
        self.update_cpp_rot()
        return self
    
    def getRotMatrix(self):
        """Get 3x3 rotation matrix.
        
        Returns:
            ndarray: 3x3 rotation matrix
        """
        return self.__sciRot.as_matrix()
        
    def getTranslation(self):
        """Get translation vector.
        
        Returns:
            ndarray: Translation vector [x, y, z]
        """
        return self.__translation

    # TODO: review transformation operation
    # def getTransformationTo(self, other):
    #     """Get transformation from self to other transformation.
        
    #     Args:
    #         other (Transformation3D): Target transformation
            
    #     Returns:
    #         Transformation3D: Transformation from self to other
    #     """
    #     return self.inv() * other

    def set_euler_ZXZ(self, rot_z=0., rot_new_x=0., rot_new_z=0., degrees=True):
        """
        Set rotation using intrinsic ZXZ Euler angles.
        
        Args:
            rot_z (float, optional): First Z rotation angle. Default: 0.0
            rot_new_x (float, optional): X rotation angle. Default: 0.0
            rot_new_z (float, optional): Second Z rotation angle. Default: 0.0
            degrees (bool, optional): Whether angles are in degrees. Default: True
        """
        self.__sciRot = scipyRot.from_euler('ZXZ', [rot_z, rot_new_x, rot_new_z], degrees)
        self.update_cpp_rot()

    def transform(self, input):
        """
        Transform input points using C++ backend.
        
        Args:
            input (ndarray): Input points (shape: Nx3)
            
        Returns:
            ndarray: Transformed points (shape: Nx3)
        """
        output = np.zeros_like(input)
        _pt_Transformation3D_transform(self.cobj, input.shape[0], input, output)
        return output
    
    def transform_py(self, input):
        """
        Transform input points using Python implementation.

        Args:
            input (ndarray): Input points (shape: Nx3)

        Returns:
            ndarray: Transformed points (shape: Nx3)
        """
        # global -> local like the C++ transform(): R^-1 (p - t); the old
        # "+ R^-1 t" version disagreed with the C++ side for non-zero
        # translations
        return self.__sciRot.inv().apply(input - self.__translation)
        

# material configured for Volume(matCfg=None). This is NOT a vacuum: it is a
# dilute free gas (number density ~6 atoms/m^3, mean free path ~1e24 m, i.e.
# numerically indistinguishable from vacuum), kept for backwards
# compatibility instead of silently changing long-established geometries
_VOLUME_DEFAULT_MATCFG = 'freegas::H1/1e-26kgm3/H_is_1_H1'

# warn only once per process about the implicit default material
_defaultMatcfgWarned = False

# ---- daughter overlap scan (see Volume.placeChild/_checkDaughterOverlap) ---
# no new C++ binding is required: the exported boolean-solid helper builds
# the intersection of two placed solids, whose Monte-Carlo capacity is the
# overlap volume
_pt_solid_intersection = importFunc('pt_solid_intersection', type_voidp, [type_voidp, type_voidp, type_voidp])

# pairs farther apart than this multiple of the radii of their
# capacity-equivalent spheres are assumed disjoint without probing
_OVERLAP_SCAN_DIST_FACTOR = 50.
# boolean-capacity probes per parent volume (each costs a 1e6-point
# Monte-Carlo sample in VecGeom, ~tens of ms)
_OVERLAP_SCAN_MAX_PROBES = 200
# intersections below this volume (in mm^3) are Monte-Carlo noise
_OVERLAP_SCAN_MIN_OVERLAP = 1e-6
# a daughter is reported as (partly) outside its parent when more than this
# fraction of its volume lies outside (the 1e6-point boolean-capacity
# Monte-Carlo stays well below it for any non-sliver shape)
_CONTAIN_SCAN_NOISE_FRACTION = 0.01

# (solidA cobj, solidB cobj, relative rotation, relative translation) -> overlap
_overlapProbeCache = {}


def _equivalentSphereRadius(volume):
    """Radius of the sphere with the same capacity as the volume's solid."""
    try:
        cap = volume.getCapacity()
    except Exception:
        return 0.
    return (3. * max(float(cap), 0.) / (4. * np.pi)) ** (1. / 3.)


def _intersectionCapacity(solidA, solidB, transfA, transfB):
    """Overlap volume (mm^3) of two solids placed by transfA/transfB.

    Returns the Monte-Carlo capacity of solidA . (transfA^-1 transfB)(solidB),
    cached per solid pair and relative placement.
    """
    rotA, transA = transfA.getRotMatrix(), transfA.getTranslation()
    rotB, transB = transfB.getRotMatrix(), transfB.getTranslation()
    relRot = rotA.T.dot(rotB)
    relTrans = rotA.T.dot(transB - transA)
    key = (solidA, solidB, np.round(relRot, 9).tobytes(), np.round(relTrans, 9).tobytes())
    if key in _overlapProbeCache:
        return _overlapProbeCache[key]
    rel = Transformation3D(relTrans[0], relTrans[1], relTrans[2]).setSciRot(scipyRot.from_matrix(relRot))
    inter = _pt_solid_intersection(solidA, solidB, rel.cobj)
    # wrap the intersection in a throw-away logical volume to reach the
    # capacity binding; it stays registered in the GeoManager on purpose,
    # deleting it gives "deregistering ... while geometry is closed" noise
    # (the same reason Volume.__del__ is a no-op)
    probeLv = _pt_Volume_new(b'cinema_overlap_probe', inter)
    cap = float(_pt_Volume_capacity(probeLv))
    _overlapProbeCache[key] = cap
    return cap


class Volume:
    """
    A Volume consists of a geometry, material, surface physics and scorers.
    A geometry defines the shape and size.
    A material defines the bulk physics and potential variance reduction techniques.
    A surface physics defines the neutron optics model.
    The scorers defines how the neutron interactions are counted/scored.
        
        Class Attributes:
        scorer_dict (dict): Dictionary mapping scorer names to configurations
        volume_list (list): List of all created Volume instances
    """
    scorer_dict = {}
    volume_list = []

    def __init__(self, volname, solid, matCfg=None, surfaceCfg=None):
        """
        Initialize a volume with name, solid shape, and optional configurations.
        
        Args:
            volname (str): Name identifier for the volume
            solid: Solid shape object (vecgeom::VUnplacedVolume type)
            matCfg (str, optional): Material configuration string. Default: None,
                which applies the dilute default material (see
                _VOLUME_DEFAULT_MATCFG: not a true vacuum) and warns once
            surfaceCfg (str, optional): Surface configuration string. Default: None
        """
        self.volname = volname
        # self.solid is of type vecgeom::VUnplacedVolume
        self.solid = solid
        self.child = []  # List of child volumes
        # placed daughters (name, Volume, Transformation3D) for the overlap scan
        self._placed = []
        self._overlapProbeCount = 0
        # self.cobj is of type vecgeom::LogicalVolume
        self.cobj = _pt_Volume_new(volname.encode('utf-8'), solid.cobj)
        self.volid = self.getLogicalID(self.cobj)
        self.matCfg = matCfg
        self.surfaceCfg = surfaceCfg

        _pt_ResourceManager_addNewVolume(self.volid)

        if matCfg is None:
            global _defaultMatcfgWarned
            if not _defaultMatcfgWarned:
                warnings.warn(
                    f"Volume '{volname}' created without matCfg: applying the "
                    f"dilute default material '{_VOLUME_DEFAULT_MATCFG}' "
                    "(not a true vacuum). Pass an explicit matCfg (e.g. a "
                    "Material built on 'void.ncmat') to silence this warning.",
                    RuntimeWarning, stacklevel=2)
                _defaultMatcfgWarned = True
            self.setMaterial(_VOLUME_DEFAULT_MATCFG)
            # record the actually applied material so introspection matches
            # the configured physics
            self.matCfg = _VOLUME_DEFAULT_MATCFG
        else:
            if isinstance(matCfg, str):
                self.setMaterial(matCfg)
            else:
                self.setMaterial(matCfg.cfg)

        if surfaceCfg is not None:
            self.setSurface(surfaceCfg) 
        self.__class__.volume_list.append(self)

    def __del__(self):
        # the memory should be managed by the Volume. 
        # otherwise the code will give the warning message:
        #    ""deregistering an object from GeoManager while geometry is closed""
        # _pt_Volume_delete(self.cobj)
        pass

    def setMaterial(self, cfg: str):
        """
        Set bulk material for a volume.

        Args:
            cfg (str): Material configuration string. The canonical form is a
                `Material().cfg`-style string like
                `physics=ncrystal;nccfg='<ncrystal cfg>'`; raw NCrystal
                config strings containing parameters (e.g.
                `Al_sg225.ncmat;temp=300K`) are accepted with a warning and
                wrapped automatically, but only the canonical form carries
                the bias options (scatter_bias/abs_bias/absorp_in_weight).

        Note:
            Material cfg *content* errors are pre-validated in Python
            (_validateMatCfg) and raise a normal ValueError. Any error that
            still escapes into the C++ NCrystal layer crosses the extern "C"
            ctypes wrappers as a C++ exception, which cannot be caught from
            Python and aborts the whole process - that bridge itself cannot
            be fixed from Python.
        """
        # pre-validate to turn the most common failure modes (missing data
        # file, rejected cfg content) into normal exceptions instead of an
        # uncatchable process abort
        _validateMatCfg(cfg)
        cfg = wrapRawNccfg(cfg)
        _pt_ResourceManager_cfgVolPhysics(self.volid, cfg.encode('utf-8'))

    def _raiseIfScorerNameTaken(self, name: str):
        """Raise ValueError when a scorer name is already registered.

        A duplicate scorer name would silently alias to the first
        registration: both volumes would report the same histogram and the
        results could not be told apart. The registry is shared by all
        volumes, so a name must be unique across the whole world. This is the
        single contract enforcement point; the C++ ResourceManager only
        prints a warning when the same cfg is re-registered on one volume.
        """
        if name in self.__class__.scorer_dict:
            raise ValueError(
                f"a scorer named '{name}' is already registered (registering "
                f"volume '{self.volname}'); scorer names must be unique - "
                "give the scorer a different name instead of registering it "
                "twice")

    def addScorer(self, scorer: Union[Scorer, str], cppScorer=ctypes.c_voidp()):
        """
        Add a scorer to the volume.

        Args:
            scorer (Union[Scorer, str]): Scorer object or configuration string
            cppScorer (ctypes.c_voidp, optional): C++ scorer object pointer. Default: empty

        Raises:
            ValueError: A scorer with the same name is already registered,
                on this or any other volume of the world.
        """
        # The registry entry is written only AFTER the C++ bridge accepts the
        # cfg: a rejected registration must leave no ghost behind (a ghost
        # would fail a same-name retry with a false "already registered" and
        # send later gathers into an unregistered scorer).
        if isinstance(cppScorer, int):
            self._raiseIfScorerNameTaken(scorer.name)
            raiseOnBridgeError(_pt_ResourceManager_addScorer(self.volid, scorer.name.encode('utf-8'), cppScorer))
            self.__class__.scorer_dict[scorer.name] = scorer.name
        else:
            import re
            if isinstance(scorer, str):
                _validateNccfgFiles(scorer)
                nameList = scorer.split(';')
                name = [n for n in nameList if 'name' in n][0]
                name = re.search(r'=.*', name)
                name = re.sub(r'=', '', name.group()).strip()
                self._raiseIfScorerNameTaken(name)
                raiseOnBridgeError(_pt_ResourceManager_addScorer(self.volid, scorer.encode('utf-8'), cppScorer))
                self.__class__.scorer_dict[name] = scorer
            else:
                cfg = scorer.cfg
                _validateNccfgFiles(cfg)
                self._raiseIfScorerNameTaken(scorer.cfg_name)
                raiseOnBridgeError(_pt_ResourceManager_addScorer(self.volid, cfg.encode('utf-8'), cppScorer))
                self.__class__.scorer_dict[scorer.cfg_name] = cfg

    def setSurface(self, cfg: str):
        """
        Set surface physics for the volume.
        
        Args:
            cfg (str): Surface physics configuration string
        """
        _validateNccfgFiles(cfg)
        raiseOnBridgeError(_pt_ResourceManager_addSurface(self.volid, cfg.encode('utf-8')))

    def placeChild(self, name, logVolume, transf=None, scorerGroup=0, checkOverlap=True):
        """
        Place a child volume inside the current volume.

        Args:
            name (str): Name for the placed volume
            logVolume (Volume): Child volume to place
            transf (Transformation3D, optional): Transformation for placement. Default: identity
            scorerGroup (int, optional): Scorer group identifier. Default: 0
            checkOverlap (bool, optional): Run the best-effort assembly scan
                and warn on intersections between the already-placed daughter
                volumes (see _checkDaughterOverlap) and on daughters lying
                outside their parent (see _checkDaughterContainment).
                Default: True

        Returns:
            Volume: Self
        """
        if transf is None:
            # fresh identity per call: a shared default instance would be
            # mutated by the first applyRot* on any caller-held reference
            transf = Transformation3D()
        self.child.append(logVolume)
        if checkOverlap:
            try:
                self._checkDaughterOverlap(name, logVolume, transf)
                self._checkDaughterContainment(name, logVolume, transf)
            except Exception as exc:
                # the scan is diagnostic-only and must never break assembly
                warnings.warn(f"Assembly scan of volume '{self.volname}' was "
                              f"skipped ({exc.__class__.__name__}: {exc})",
                              RuntimeWarning, stacklevel=2)
        self._placed.append((name, logVolume, transf))
        _pt_Volume_placeChild(self.cobj, name.encode('utf-8'), logVolume.cobj, transf.cobj, scorerGroup)
        return self

    def _checkDaughterOverlap(self, name, logVolume, transf):
        """Warn when the new daughter intersects an already-placed daughter.

        The C++ build and the transport never diagnose overlapping daughters
        (they run silently with exit 0), so this is the only code-level
        diagnostic. The intersection volume of two solids is measured as the
        capacity of their boolean intersection (VecGeom estimates boolean
        capacities by Monte-Carlo sampling; a disjoint pair measures exactly
        0). The scan is best effort:

        - pairs whose placement origins are farther apart than
          _OVERLAP_SCAN_DIST_FACTOR radii of their capacity-equivalent
          spheres are assumed disjoint (only extreme sliver shapes could
          defeat this),
        - at most _OVERLAP_SCAN_MAX_PROBES probes run per parent volume,
        - results are cached per (solid pair, relative placement).
        """
        rNew = _equivalentSphereRadius(logVolume)
        for pname, pvol, ptransf in self._placed:
            rOld = _equivalentSphereRadius(pvol)
            dist = np.linalg.norm(transf.getTranslation() - ptransf.getTranslation())
            if dist > _OVERLAP_SCAN_DIST_FACTOR * (rNew + rOld):
                continue
            if self._overlapProbeCount >= _OVERLAP_SCAN_MAX_PROBES:
                warnings.warn(
                    f"Overlap scan of volume '{self.volname}' stopped after "
                    f"{self._overlapProbeCount} daughter pairs; very large "
                    "daughter arrays are not fully scanned. Use "
                    "placeChild(checkOverlap=False) to silence this.",
                    RuntimeWarning, stacklevel=3)
                # freeze the counter so the message fires only once
                self._overlapProbeCount = _OVERLAP_SCAN_MAX_PROBES + 1
                continue
            self._overlapProbeCount += 1
            overlap = _intersectionCapacity(pvol.solid.cobj, logVolume.solid.cobj,
                                            ptransf, transf)
            if overlap > _OVERLAP_SCAN_MIN_OVERLAP:
                warnings.warn(
                    f"Daughter volumes '{pname}' and '{name}' of volume "
                    f"'{self.volname}' overlap: estimated intersection "
                    f"volume {overlap:.3f} mm^3. Overlapping daughters have "
                    "an undefined transport order; adjust the placements.",
                    RuntimeWarning, stacklevel=3)

    def _checkDaughterContainment(self, name, logVolume, transf):
        """Warn when a part of the new daughter lies outside its parent.

        Like the sibling-overlap scan, the transport cannot diagnose this at
        run time: VecGeom silently tracks a daughter placed outside its
        parent, so neutrons get transported into the misplaced region and
        world ENTRY/EXIT scorers over-count. The check reuses the overlap
        machinery: the Monte-Carlo capacity of
        parent . (placed daughter) divided by the daughter capacity is the
        contained fraction, so one boolean-capacity probe measures the
        outside fraction directly. It is best effort (see the noise
        threshold _CONTAIN_SCAN_NOISE_FRACTION) and never raises.
        """
        capDaughter = float(logVolume.getCapacity())
        if capDaughter <= 0.:
            return
        # the parent solid lives in its own frame, i.e. at identity placement
        capInside = _intersectionCapacity(self.solid.cobj, logVolume.solid.cobj,
                                          Transformation3D(), transf)
        outsideFraction = 1. - capInside / capDaughter
        if outsideFraction > _CONTAIN_SCAN_NOISE_FRACTION:
            warnings.warn(
                f"Daughter volume '{name}' of volume '{self.volname}' lies "
                f"{max(outsideFraction, 0.) * 100:.1f}% outside its parent "
                "(Monte-Carlo volume estimate). Daughters outside their "
                "parent are silently transported into; adjust the placement.",
                RuntimeWarning, stacklevel=3)
    
    # TODO: need review, to place a collection of Volume
    # def placeArray(self, array, transf=None, marker='', count=0):
    #     """
    #     Place an array of volumes recursively.
        
    #     Args:
    #         array: Array structure containing volumes
    #         transf (Transformation3D, optional): Base transformation. Default: None
    #         marker (str, optional): Naming marker. Default: ''
    #         count (int, optional): Recursion counter. Default: 0
    #     """
    #     if transf == None:
    #         transf = array.refFrame
    #     marker = f'{marker}{count}'
    #     for i_mem in array.members:
    #         if isinstance(array.element, Volume):
    #             transf_t = transf * i_mem.refFrame 
    #             self.placeChild(f'phyvol_{marker}_{array.element.volname}', array.element, transf_t)
    #         else:
    #             count = count + 1
    #             self.placeArray(array.element, transf * i_mem.refFrame, i_mem.marker, count=count)

    def getCapacity(self):
        """Get the volumic capacity in mm^3 of the solid.
        
        Returns:
            float: Volume capacity in mm^3
        """
        return _pt_Volume_capacity(self.cobj)

    def getLogicalID(self, cobj=None):
        """Get logical volume ID.
        
        Args:
            cobj (void*, optional): C++ volume object. Default: None (use self.cobj)
            
        Returns:
            int: Logical volume identifier
        """
        if cobj is None:  # Return the ID of this volume
            return _pt_Volume_id(self.cobj)
        else:
            return _pt_Volume_id(cobj)