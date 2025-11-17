################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2022 Prompt developers                                     ##
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

from typing import Union

from scipy.spatial.transform import Rotation as scipyRot
from ..Interface import *
from .Mesh import _pt_Transformation3D_transform
from copy import deepcopy
from .scorer import Scorer

__all__ = ['Volume', 'Transformation3D']


#Volume
_pt_Volume_new = importFunc('pt_Volume_new', type_voidp, [type_cstr, type_voidp])
_pt_Volume_delete = importFunc('pt_Volume_delete', None, [type_voidp] )
_pt_Volume_placeChild = importFunc('pt_Volume_placeChild', None, [type_voidp, type_cstr, type_voidp, type_voidp, type_int])

_pt_Volume_id = importFunc('pt_Volume_id', type_uint, [type_voidp])
_pt_Volume_capacity = importFunc('pt_Volume_capacity', type_dbl, [type_voidp])

_pt_Transformation3D_newfromdata = importFunc('pt_Transformation3D_newfromdata', type_voidp, [type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl])
_pt_Transformation3D_delete = importFunc('pt_Transformation3D_delete', None, [type_voidp] )
_pt_Transformlation3D_setRotation  = importFunc('pt_Transformlation3D_setRotation', None, [type_voidp, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl, type_dbl] )
_pt_Transformlation3D_setTranslation  = importFunc('pt_Transformlation3D_setTranslation', None, [type_voidp, type_dbl, type_dbl, type_dbl] )


#resource manager 
_pt_ResourceManager_addNewVolume = importFunc('pt_ResourceManager_addNewVolume', None, [type_uint])
_pt_ResourceManager_addScorer = importFunc('pt_ResourceManager_addScorer', None, [type_uint, type_cstr, type_voidp])
_pt_ResourceManager_addSurface = importFunc('pt_ResourceManager_addSurface', None, [type_uint, type_cstr])
_pt_ResourceManager_cfgVolPhysics = importFunc('pt_ResourceManager_cfgVolPhysics', None, [type_uint, type_cstr])


class Transformation3D:
        # Rotation follows ZXZ convention in vecgeom backend
        self.__cobj = _pt_Transformation3D_newfromdata(x, y, z, rot_z, rot_new_x, rot_new_z, 1, 1, 1)
        self.__sciRot = scipyRot.from_euler('ZXZ', [rot_z, rot_new_x, rot_new_z], degrees)
        self.__translation = np.array([x, y, z])

    @property
    def cobj(self):
        """Get C++ transformation object pointer.
        
        Returns:
            void*: Pointer to C++ transformation object
        """
        return self.__cobj

    @classmethod 
    def from_euler_xyz(cls, x=0., y=0., z=0., rx=0., ry=0., rz=0., degrees = True):
        obj = cls(x,y,z)
        sciRot = scipyRot.from_euler('xyz', [rx, ry, rz], degrees)
        obj.setSciRot(sciRot)
        return obj

    @classmethod
    def from_alignement(cls, x=0., y=0., z=0., rotated=None, original=None) :  # rotated, original are with shape (N, 3)
        if rotated or original is None:
            raise RuntimeError('Rotated and original should be provided')
        obj = cls(x,y,z)
        obj.setRotByAlignement(rotated, original)
        return obj

    @property
    def euler_xyz(self):
        return self.__sciRot.as_euler('xyz', True)

    def __deepcopy__(self, memo):
        copy = type(self)()
        memo[id(self)] = copy
        copy.cobj = _pt_Transformation3D_newfromdata(self.__translation[0], self.__translation[1], self.__translation[2], 
                                                     0, 0, 0, 1.,1.,1.)
        copy._Transformation3D__sciRot = scipyRot.from_matrix(self.__sciRot.as_matrix())
        copy.update_cpp_rot()
        copy._translation = self.__translation
        copy.sciRotMatrix = self.__sciRot.as_matrix()
        return copy

    def __del__(self):
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

    def update_cpp_rot(self):
        mat = self.__sciRot.as_matrix()
        # print(mat)
        _pt_Transformlation3D_setRotation(self.cobj, mat[0,0], mat[0,1], mat[0,2],
                                          mat[1,0], mat[1,1], mat[1,2],
                                          mat[2,0], mat[2,1], mat[2,2])
        
    def applyRotAxis(self, angle, axis, degrees=True):
        axis = np.array(axis)
        rot = scipyRot.from_rotvec(angle * axis/np.linalg.norm(axis), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotX(self, angle, degrees=True):
        rot = scipyRot.from_rotvec(angle * np.array([1,0,0.]), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotY(self, angle, degrees=True):
        rot = scipyRot.from_rotvec(angle * np.array([0,1,0.]), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotZ(self, angle, degrees=True):
        rot = scipyRot.from_rotvec(angle * np.array([0,0,1.]), degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self
    
    def applyRotxyz(self, rotx, roty, rotz, degrees=True):
        rot = scipyRot.from_euler('xyz', [rotx, roty, rotz], degrees=degrees)
        self.__sciRot *= rot
        self.update_cpp_rot()
        return self

    def applyTrans(self, refMatrix):
        mat = self.__sciRot.as_matrix().dot(refMatrix)
        self.__sciRot = scipyRot.from_matrix(self.__sciRot.as_matrix())
        _pt_Transformlation3D_setRotation(self.cobj, mat[0,0], mat[0,1], mat[0,2],
                                          mat[1,0], mat[1,1], mat[1,2],
                                          mat[2,0], mat[2,1], mat[2,2])

    def setRotByAlignement(self, rotated, original) :  # rotated, original are with shape (N, 3)
        if len(original)!= len(rotated) or len(original)!=2:
            raise RuntimeError('rotated and original should be contain 2 vectors')
        self.__sciRot, rssd = scipyRot.align_vectors(original, rotated)
        self.update_cpp_rot()
        return self

    def setSciRot(self, sciRot):
        self.__sciRot = deepcopy(sciRot)
        self.update_cpp_rot()
        return self
    
    def getRotMatrix(self):
        return self.__sciRot.as_matrix()
        
    def getTranslation(self):
        return self.__translation

    def getTransformationTo(self, other):
        return self.inv() * other

    #  a wrapper of scipy.spatial.transform.Rotation    
    def set_euler_ZXZ(self, rot_z=0., rot_new_x=0., rot_new_z=0., degrees = True):
        self.__sciRot = scipyRot.from_euler('ZXZ', [rot_z, rot_new_x, rot_new_z], degrees)
        self.update_cpp_rot()

    def transform(self, input):
        output = np.zeros_like(input)
        _pt_Transformation3D_transform(self.cobj, input.shape[0], input, output)
        return output
    
    def transform_py(self, input):
        return self.__sciRot.inv().apply(input)+ self.__sciRot.inv().apply(self.__translation)
        
class Volume:
    scorerDict = {}
    volume_list = []

    def __init__(self, volname, solid, matCfg=None, surfaceCfg=None):
        self.volname = volname
        # the type of self.solid is vecgeom::VUnplacedVolume 
        self.solid = solid
        self.child = []
        # the type of self.cobj is vecgeom::LogicalVolume
        self.cobj = _pt_Volume_new(volname.encode('utf-8'), solid.cobj)
        self.volid = self.getLogicalID(self.cobj)
        self.matCfg = matCfg
        self.surfaceCfg = surfaceCfg

        _pt_ResourceManager_addNewVolume(self.volid)
        
        if matCfg is None:
            self.setMaterial('freegas::H1/1e-26kgm3/H_is_1_H1') # set as the universe
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

    def setMaterial(self, cfg : str):
        _pt_ResourceManager_cfgVolPhysics(self.volid, cfg.encode('utf-8')) # set as the universe

    def addScorer(self, scorer : Union[Scorer, str], cppScorer=ctypes.c_voidp()):
        if isinstance(cppScorer, int):
            self.__class__.scorerDict[scorer.name] = scorer.name
            _pt_ResourceManager_addScorer(self.volid, scorer.name.encode('utf-8'), cppScorer) 
        else:
            import re
            if isinstance(scorer, str):
                nameList = scorer.split(';')
                name = [n for n in nameList if 'name' in n][0]
                name = re.search(r'=.*', name)
                name = re.sub(r'=', '', name.group()).strip()
                self.__class__.scorerDict[name] = scorer
                _pt_ResourceManager_addScorer(self.volid, scorer.encode('utf-8'), cppScorer) 
            else:
                cfg = scorer.cfg
                self.__class__.scorerDict[scorer.cfg_name] = cfg
                _pt_ResourceManager_addScorer(self.volid, cfg.encode('utf-8'), cppScorer) 

    def setSurface(self, cfg : str):
        _pt_ResourceManager_addSurface(self.volid, cfg.encode('utf-8')) 

    def placeChild(self, name, logVolume, transf=Transformation3D(0,0,0), scorerGroup=0):
        self.child.append(logVolume)
        _pt_Volume_placeChild(self.cobj, name.encode('utf-8'), logVolume.cobj, transf.cobj, scorerGroup)
        return self
    
    def placeArray(self, array, transf = None, marker = '', count = 0):
        if transf == None:
            transf = array.refFrame
        marker = f'{marker}{count}'
        for i_mem in array.members:
            if isinstance(array.element, Volume):
                transf_t = transf * i_mem.refFrame 
                # transf_t.sciRot = deepcopy(transf.sciRot)
                # transf_t.applyTrans(i_mem.refFrame.sciRotMatrix)
                self.placeChild(f'phyvol_{marker}_{array.element.volname}', array.element, transf_t)
            else:
                count = count + 1
                self.placeArray(array.element, transf * i_mem.refFrame, i_mem.marker, count = count)

    def getCapacity(self):
        """Get the capacity (or the volume of a solid, in other words) of the current Volume.

        Returns:
            capacity of volume(double)
        """
        return _pt_Volume_capacity(self.cobj)

    def getLogicalID(self, cobj=None):
        if cobj is None: # reutrn the ID of this volume
            return _pt_Volume_id(self.cobj)
        else:
            return _pt_Volume_id(cobj)


