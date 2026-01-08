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

from ..Interface import *
from enum import Enum
import sys

try:
    import pyvista as pv
except:
    raise ImportError("pyvista is required to visualize.")

_pt_Transformation3D_new = importFunc('pt_Transformation3D_new', type_voidp, [type_voidp])
_pt_Transformation3D_newfromID = importFunc('pt_Transformation3D_newfromID', type_voidp, [type_uint])
_pt_Transformation3D_delete = importFunc('pt_Transformation3D_delete', None, [type_voidp])
_pt_Transformation3D_multiple = importFunc('pt_Transformation3D_multiple', None, [type_voidp, type_voidp])
_pt_Transformation3D_transform = importFunc('pt_Transformation3D_transform', None, [type_voidp, type_sizet, type_npdbl2d, type_npdbl2d])
_pt_Transformation3D_print = importFunc('pt_Transformation3D_print', ctypes.c_char_p, [type_voidp])

def generateVolumetricMesh(mesh : pv.PolyData) -> pv.PolyData:
    try:
        from tetgen import TetGen
    except Exception as e:
        print(e)
        print("tetgen is required. Use 'pip install tetgen' to install. ")
        sys.exit(1)

    mesh.triangulate(inplace=True)
    tet = TetGen(mesh)
    tet.make_manifold()
    tet.tetrahedralize(quality=False)
    mesh = tet.mesh
    return mesh

class MeshHelper(object):
    def __init__(self, id):
        self.cobj = _pt_Transformation3D_newfromID(id)
        print(f'Created Transfromation {self.print()}') #fixme

    def __del__(self):
        _pt_Transformation3D_delete(self.cobj)

    def multiple(self, cobjmatrix):
        _pt_Transformation3D_multiple(self.cobj, cobjmatrix)

    def tansform(self, input):
        out = np.zeros_like(input, dtype=float)
        _pt_Transformation3D_transform(self.cobj, input.shape[0], input, out)
        return out

    def print(self):
        return _pt_Transformation3D_print(self.cobj).decode('utf-8')

_pt_countFullTreeNode = importFunc('pt_countFullTreeNode', type_sizet, [])
_pt_getPhysicalVolID_ByNodeID = importFunc('pt_getPhysicalVolID_ByNodeID', type_sizet, [type_sizet])
_pt_printMesh = importFunc("pt_printMesh", type_voidp, [])
_pt_meshInfo = importFunc("pt_meshInfo", None,  [type_sizet, type_sizet, type_sizetp, type_sizetp, type_sizetp, type_intp, type_intp, type_sizetp])
_pt_getMesh = importFunc("pt_getMesh", None,  [type_sizet, type_sizet, type_npsbl2d, type_npszt1d, type_npszt1d, type_sizet])
_pt_getMeshName = importFunc("pt_getMeshName", type_cstr,  [type_sizet])
_pt_getLogVolumeInfo = importFunc("pt_getLogVolumeInfo", None, [type_sizet, type_cstr])
_pt_generatePointCloud = importFunc("pt_generatePointCloud", None,  [type_sizet, type_sizet, type_npdbl2d, type_npdbl2d])
_pt_getLogicalVolumeMaterialName = importFunc("pt_getLogicalVolumeMaterialName", type_cstr, [type_sizet])

class MeshBoolOpr(Enum):
    Union = 1,
    Subtraction = 2,
    Intersection = 3,

class Mesh():
    def __init__(self):
        self.nMax=self.countFullTreeNode()
        self.n = 0


    def countFullTreeNode(self):
        return _pt_countFullTreeNode()
    
    def getPhysicalVolID(self):
        return _pt_getPhysicalVolID_ByNodeID(self.n)
        
    def printMesh(self):
        _pt_printMesh()

    def getMeshName(self):
        return _pt_getMeshName(self.n).decode('utf-8')

    def getMaterialName(self):
        # print(_pt_getLogicalVolumeMaterialName(self.n).decode('utf-8'))
        return _pt_getLogicalVolumeMaterialName(self.n).decode('utf-8')

    def getLogVolumeInfo(self):
        info = ctypes.create_string_buffer(2000) #fixme
        _pt_getLogVolumeInfo(self.n, info)
        return info.value.decode('utf-8')

    def meshInfo(self, nSegments=10, pvolID = None):
        npoints = type_sizet()
        nPlolygen = type_sizet()
        faceSize = type_sizet()
        leftvolID = ctypes.c_int()
        rightvolID = ctypes.c_int()
        boolOp = type_sizet()
        
        npoints.value = 0
        nPlolygen.value = 0
        faceSize.value = 0
        leftvolID.value = -1
        rightvolID.value = -1
        boolOp.value = 0

        _pt_meshInfo(pvolID, nSegments, ctypes.byref(npoints), ctypes.byref(nPlolygen), 
                     ctypes.byref(faceSize), ctypes.byref(leftvolID), ctypes.byref(rightvolID), ctypes.byref(boolOp))
        return self.getMeshName(), npoints.value, nPlolygen.value, faceSize.value, leftvolID.value, rightvolID.value, boolOp.value

    def getMesh(self, nSegments=30, byPointCloud=False, pvolID = None) -> tuple[str, pv.PolyData]:
        """Get a mesh of volume. Multiple approaches to handle different cases:
        1. If the volume is handled by VecGeom, it will return a mesh object.
        2. If the volume is not handled by VecGeom, in this case might probably be a boolean operation:
        2.1 If byPointCloud is True, a mesh will be generated by sampling on surfaces and then PointCloud method.
        2.2 If byPointCloud is False, a mesh will be handled by PyVista by triangulation.

        Args:
            nSegments (int, optional): Number of segments to divide the volume. Defaults to 10.
            byPointCloud (bool, optional): Whether to generate by PointCloud method. Defaults to False.

        Returns:
            tuple: A tuple containing the mesh name and the mesh object.
        """
        def meshByPointCloud(npoints):
            npoints = nSegments*100
            points = np.zeros([npoints, 3])
            norm = np.zeros_like(points)
            _pt_generatePointCloud(self.n, npoints, points, norm)
            point_cloud = pv.PolyData(points)
            # Add normals to the point cloud
            point_cloud.point_data['Normals'] = norm
            # Use reconstruct_surface with normals
            # Note: You can specify additional parameters such as `tolerance`, or `clean` as required.
            mesh = point_cloud.reconstruct_surface()
            return mesh

        if pvolID is None:
            pvolID = self.getPhysicalVolID()

        name, npoints, nPlolygen, faceSize, leftvolID, rightvolID, boolOp = self.meshInfo(nSegments, pvolID)

        if npoints==0 and boolOp!=0: # 3D mesh not created by VecGeom, intended to handle geometry boolean operation
            if not byPointCloud:
                try:
                    _, lmesh = self.getMesh(nSegments, pvolID=leftvolID)
                    _, rmesh = self.getMesh(nSegments, pvolID=rightvolID)

                    lmesh = VtkBoolWrapper(lmesh)
                    rmesh = VtkBoolWrapper(rmesh)

                    if boolOp == MeshBoolOpr.Union.value[0]:
                        mesh = lmesh | rmesh
                    elif boolOp == MeshBoolOpr.Intersection.value[0]:
                        mesh = lmesh & rmesh
                    elif boolOp == MeshBoolOpr.Subtraction.value[0]:
                        mesh = lmesh - rmesh
                    else:
                        raise ValueError(f"Unknown boolean operation: {boolOp}")
                except Exception as e: # fall back to point cloud mode
                    print(f"Error: Meshing boolean operation via `vtkbool` is highly experimental. May be a rerun can solve it.")
                    print(f"Mesh realized in point cloud mode.")
                    print(e)
                    mesh = meshByPointCloud(npoints)
                finally:
                    return name, mesh
            else:
                mesh = meshByPointCloud(npoints)
                return name, mesh
        # The mesh mode
        else:
            vert = np.zeros([npoints, 3], dtype=np.float32)
            NumPolygonPoints = np.zeros(nPlolygen, dtype=type_sizet)
            facesVec = np.zeros(faceSize+nPlolygen, dtype=type_sizet)
            _pt_getMesh(self.n, nSegments, vert, NumPolygonPoints, facesVec, pvolID)

            return name, pv.PolyData(vert, facesVec)

    def __iter__(self):
        self.n = -1
        return self

    def __next__(self):
        if self.n < self.nMax-1:
            self.n += 1
            return self
        else:
            raise StopIteration

class VtkBoolWrapper:
    
    def __init__(self, mesh):
        self.mesh = mesh
        
    def __or__(self, other):
        return self._boolean_operation(other, 'union')
    
    def __and__(self, other):
        return self._boolean_operation(other, 'intersection')
    
    def __sub__(self, other):
        return self._boolean_operation(other, 'difference')
    
    def _boolean_operation(self, other, operation):
        from vtkbool.vtkBool import vtkPolyDataBooleanFilter
        
        other_mesh = other.mesh if hasattr(other, 'mesh') else other
        boolean_filter = vtkPolyDataBooleanFilter()
        
        if operation == 'union':
            boolean_filter.SetOperModeToUnion()
        elif operation == 'intersection':
            boolean_filter.SetOperModeToIntersection()
        elif operation == 'difference':
            boolean_filter.SetOperModeToDifference()
        else:
            raise ValueError(f"Unknown boolean operation: {operation}")
        
        boolean_filter.SetInputData(0, self.mesh)
        boolean_filter.SetInputData(1, other_mesh)
        boolean_filter.Update()
        
        result = boolean_filter.GetOutput()
        mesh = pv.wrap(result)
        return mesh
