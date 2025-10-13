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

_pt_Transformation3D_new = importFunc('pt_Transformation3D_new', type_voidp, [type_voidp])
_pt_Transformation3D_newfromID = importFunc('pt_Transformation3D_newfromID', type_voidp, [type_uint])
_pt_Transformation3D_delete = importFunc('pt_Transformation3D_delete', None, [type_voidp])
_pt_Transformation3D_multiple = importFunc('pt_Transformation3D_multiple', None, [type_voidp, type_voidp])
_pt_Transformation3D_transform = importFunc('pt_Transformation3D_transform', None, [type_voidp, type_sizet, type_npdbl2d, type_npdbl2d])
_pt_Transformation3D_print = importFunc('pt_Transformation3D_print', ctypes.c_char_p, [type_voidp])



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
_pt_printMesh = importFunc("pt_printMesh", type_voidp, [])
_pt_meshInfo = importFunc("pt_meshInfo", None,  [type_sizet, type_sizet, type_sizetp, type_sizetp, type_sizetp])
_pt_getMesh = importFunc("pt_getMesh", None,  [type_sizet, type_sizet, type_npsbl2d, type_npszt1d, type_npszt1d])
_pt_getMeshName = importFunc("pt_getMeshName", type_cstr,  [type_sizet])
_pt_getLogVolumeInfo = importFunc("pt_getLogVolumeInfo", None, [type_sizet, type_cstr])
_pt_generatePointCloud = importFunc("pt_generatePointCloud", None,  [type_sizet, type_sizet, type_npdbl2d, type_npdbl2d])
_pt_getLogicalVolumeMaterialName = importFunc("pt_getLogicalVolumeMaterialName", type_cstr, [type_sizet])

class Mesh():
    def __init__(self):
        self.nMax=self.countFullTreeNode()
        self.n = 0


    def countFullTreeNode(self):
        return _pt_countFullTreeNode()


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

    def meshInfo(self, nSegments=10):
        npoints = type_sizet()
        nPlolygen = type_sizet()
        faceSize = type_sizet()
        npoints.value = 0
        nPlolygen.value = 0
        faceSize.value = 0
        _pt_meshInfo(self.n, nSegments, ctypes.byref(npoints), ctypes.byref(nPlolygen), ctypes.byref(faceSize))
        return self.getMeshName(), npoints.value, nPlolygen.value, faceSize.value

    def getMesh(self, nSegments=10):
        try:
            import pyvista as pv
        except:
            raise ImportError("pyvista is required to visualize.")

        name, npoints, nPlolygen, faceSize = self.meshInfo(nSegments)
        # The point cloud mode
        if npoints==0: 
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
            return name, mesh
        # The mesh mode
        else:
            vert = np.zeros([npoints, 3], dtype=np.float32)
            NumPolygonPoints = np.zeros(nPlolygen, dtype=type_sizet)
            facesVec = np.zeros(faceSize+nPlolygen, dtype=type_sizet)
            _pt_getMesh(self.n, nSegments, vert, NumPolygonPoints, facesVec)
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
