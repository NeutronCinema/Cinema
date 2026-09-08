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
Geometry meshes: Solid -> pyvista PolyData, and back to transport.

Two related paths:

* :class:`Mesh` walks the GeoTree of a built world (visualisation ABI,
  float32, global frame); boolean volumes are combined there via the
  static engine :meth:`BoolSolidMeshHandlerMixin.boolean`.
* The transport-grade path lives ON the Solids themselves:
  :class:`BoolSolidMeshHandlerMixin` is mixed into ``solid.Solid`` and
  provides ``solid.to_polydata()`` (``CreateMesh3D`` in the solid's LOCAL
  frame, double precision; boolean solids automatically unpack into their
  operand solids with the ``Transformation3D`` placements applied - the
  modeling entry stays Solid throughout), ``solid.capacity()``,
  ``solid.to_tessellated()`` (one-stop clean + Tessellated, ready for a
  Volume), ``solid.roundtrip_report()``, plus the static engine and mesh
  conditioning (:meth:`BoolSolidMeshHandlerMixin.boolean`,
  ``clean_for_tessellated``, ``structured_cylinder``).  Division of
  labour: VecGeom owns geometric truth and transport, pyvista owns mesh
  generation/processing/QC (doc/plan/06-mesh-transport.md).
"""

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
_pt_getPhysicalVolumeName = importFunc("pt_getPhysicalVolumeName", type_cstr,  [type_sizet])
_pt_getLogVolumeInfo = importFunc("pt_getLogVolumeInfo", None, [type_sizet, type_cstr])
_pt_generatePointCloud = importFunc("pt_generatePointCloud", None,  [type_sizet, type_sizet, type_npdbl2d, type_npdbl2d])
_pt_getLogicalVolumeMaterialName = importFunc("pt_getLogicalVolumeMaterialName", type_cstr, [type_sizet])

class MeshBoolOpr(Enum):
    Union = 1,
    Subtraction = 2,
    Intersection = 3,

# The single op-code -> engine-name map: pt_meshInfo's boolOp (visualisation)
# and pt_solid_boolInfo's op (transport) share the VecGeom BooleanOp_t coding
# (Union=1, Subtraction=2 -> 'difference', Intersection=3).
_BOOL_OP_NAMES = {MeshBoolOpr.Union.value[0]: 'union',
                  MeshBoolOpr.Subtraction.value[0]: 'difference',
                  MeshBoolOpr.Intersection.value[0]: 'intersection'}

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

    def getPhysicalVolumeName(self):
        return _pt_getPhysicalVolumeName(self.n).decode('utf-8')

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
        return self.getPhysicalVolumeName(), npoints.value, nPlolygen.value, faceSize.value, leftvolID.value, rightvolID.value, boolOp.value

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

                    opname = _BOOL_OP_NAMES.get(boolOp)
                    if opname is None:
                        raise ValueError(f"Unknown boolean operation: {boolOp}")
                    mesh = BoolSolidMeshHandlerMixin.boolean(
                        BoolSolidMeshHandlerMixin._weld(lmesh),
                        BoolSolidMeshHandlerMixin._weld(rmesh), opname)
                except Exception as e: # fall back to point cloud mode
                    print(f"Error: meshing the boolean operation via trimesh/manifold3d failed.")
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


# ---------------------------------------------------------------------------
# Solid-level mesh & boolean handling: BoolSolidMeshHandlerMixin merges the
# former MeshBoolWrapper (mesh x mesh boolean engine) and SolidMeshHandler
# (solid -> mesh extraction) and is mixed into Cinema Solids (solid.py), so
# every Solid carries the whole chain.  C++ side: the pt_solid_* /
# inverseTransform bindings declared in PTMeshHelper.hh.
# ---------------------------------------------------------------------------

# Vertex-weld tolerance [mm]: matches VecGeom's own dedup tolerance in
# UnplacedTessellated::Close, so what welds here also dedups there.
_WELD_MM = 1e-9

_BOOL_HINT = ("VecGeom does not implement CreateMesh3D for this solid and it "
              "is not a boolean volume either, so it cannot be meshed. "
              "Boolean solids (SolidUnion/SolidSubtraction/SolidIntersection, "
              "optionally positioning the right operand with a "
              "Transformation3D) are meshed automatically by the Solid "
              "boolean-mesh fallback (Solid.to_polydata).")


class BoolSolidMeshHandlerMixin:
    """Mesh & boolean handling for Cinema Solids (mixed into ``solid.Solid``).

    Merged from the former ``MeshBoolWrapper`` (the mesh x mesh boolean
    engine) and ``SolidMeshHandler`` (the solid -> mesh extraction), so a
    boolean Solid is meshed straight from the Solid API:

    * instance methods (``self`` is a Solid): :meth:`to_polydata` (local-frame
      double surface mesh; boolean solids unpack into their operand solids
      with the ``Transformation3D`` placements applied - nested booleans
      expand recursively), :meth:`capacity`, :meth:`to_tessellated`,
      :meth:`roundtrip_report`;
    * statics, usable without a Solid instance: :meth:`boolean` (the
      trimesh/manifold3d engine - also the backend of :meth:`Mesh.getMesh`),
      :meth:`_weld`, :meth:`clean_for_tessellated`,
      :meth:`structured_cylinder`.

    Defines NO ``__init__`` - construction stays with the host class.
    """

    # --- ctypes bindings (PTMeshHelper.hh); _voidpp must precede _boolInfo,
    #     the argtypes list is evaluated at class-body execution time ---
    _meshInfo = importFunc('pt_solid_meshInfo', type_int,
                           [type_voidp, type_sizet,
                            type_sizetp, type_sizetp, type_sizetp])
    _getMesh = importFunc('pt_solid_getMesh', type_int,
                          [type_voidp, type_sizet,
                           type_npdbl1d, type_npszt1d])
    _capacity = importFunc('pt_solid_capacity', type_dbl, [type_voidp])
    _voidpp = ctypes.POINTER(ctypes.c_void_p)
    _boolInfo = importFunc('pt_solid_boolInfo', type_int,
                           [type_voidp, type_uintp,
                            _voidpp, _voidpp, _voidpp, _voidpp])
    _inverseTransform = importFunc('pt_Transformation3D_inverseTransform',
                                   None,
                                   [type_voidp, type_sizet,
                                    type_npdbl2d, type_npdbl2d])

    # ------------------------------------------------------------------
    # public transport API (self is a Solid instance)
    # ------------------------------------------------------------------
    def to_polydata(self, n_segments: int = 30) -> pv.PolyData:
        """Surface mesh of the Solid in its LOCAL frame (double precision).

        ``CreateMesh3D(identity, n_segments)`` on the bare unplaced volume -
        unlike the GeoTree-based :meth:`Mesh.getMesh` it needs no world.
        n_segments conventions vary per shape (Box ignores it, Tube
        subdivides phi only, Sphere uses it for both theta and phi).
        Boolean solids (no CreateMesh3D in VecGeom) fall back automatically:
        the operand solids are unpacked with their ``Transformation3D``
        placements applied and combined with trimesh/manifold3d (optional
        dependency).
        """
        return self._mesh_from_unplaced(self.cobj, n_segments)

    def capacity(self) -> float:
        """Analytic capacity of the solid in mm^3 (no world/Volume needed).

        Note: for boolean solids this is a cached 1e6-sample Monte-Carlo
        estimate (``UnplacedBooleanVolume::Capacity``), not an exact value.
        """
        return self._capacity(self.cobj)

    def to_tessellated(self, n_segments: int = 30):
        """One-stop solid -> mesh -> clean -> Tessellated, ready for a Volume."""
        # deferred import: Mesh must not import solid at module level
        from .solid import Tessellated
        return Tessellated(self.clean_for_tessellated(self.to_polydata(n_segments)))

    def roundtrip_report(self, n_segments: int = 30) -> dict:
        """Fidelity report of the mesh roundtrip for the solid.

        Keys: ``n_segments``, ``npoints``, ``nfacets``, ``n_open_edges``,
        ``capacity_csg`` (analytic), ``capacity_mesh`` (VecGeom surface
        integral over the tessellation), ``capacity_polydata`` (pyvista's own
        volume - independent implementation, must agree with
        ``capacity_mesh``), ``ratio`` = ``capacity_mesh / capacity_csg``.
        Sweep ``n_segments`` to get the fidelity-vs-facet-count curve for
        performance budgeting.  For boolean solids ``capacity_csg``/``ratio``
        are only indicative (Monte-Carlo capacity, see :meth:`capacity`).
        """
        # deferred import: Mesh must not import solid at module level
        from .solid import Tessellated
        mesh = self.clean_for_tessellated(self.to_polydata(n_segments))
        tess = Tessellated(mesh)
        cap_csg = self.capacity()
        cap_mesh = tess.capacity()
        return {'n_segments': n_segments,
                'npoints': mesh.n_points,
                'nfacets': mesh.n_faces_strict,
                'n_open_edges': mesh.n_open_edges,
                'capacity_csg': cap_csg,
                'capacity_mesh': cap_mesh,
                'capacity_polydata': float(mesh.volume),
                'ratio': cap_mesh / cap_csg}

    # ------------------------------------------------------------------
    # solid -> mesh internals
    # ------------------------------------------------------------------
    def _mesh_from_unplaced(self, cobj, n_segments: int) -> pv.PolyData:
        """Two-phase CreateMesh3D extraction on a bare VUnplacedVolume handle.

        Boolean solids (CreateMesh3D -> nullptr) fall back to
        :meth:`_bool_mesh`.
        """
        npoints = ctypes.c_size_t(0)
        npolygons = ctypes.c_size_t(0)
        facesize = ctypes.c_size_t(0)
        status = self._meshInfo(cobj, n_segments, ctypes.byref(npoints),
                                ctypes.byref(npolygons), ctypes.byref(facesize))
        if status == 1:
            return self._bool_mesh(cobj, n_segments)
        if status == 2:
            raise ValueError('CreateMesh3D returned an empty mesh')
        if status != 0:
            raise RuntimeError(f'pt_solid_meshInfo failed with status {status}')

        points = np.empty(npoints.value * 3, dtype=np.float64)
        faces = np.empty(facesize.value, dtype=np.uint64)
        status = self._getMesh(cobj, n_segments, points, faces)
        if status != 0:
            raise RuntimeError(f'pt_solid_getMesh failed with status {status}')

        return pv.PolyData(points.reshape(-1, 3), faces.astype(np.int64))

    def _bool_mesh(self, cobj, n_segments: int) -> pv.PolyData:
        """Mesh a boolean solid from its bare ``VUnplacedVolume`` handle.

        Unpacks the operand solids and their placements
        (``pt_solid_boolInfo``), meshes each operand (recursively - nested
        booleans expand), applies the operand placements and combines the
        meshes with the boolean engine.  Returns the resulting PolyData in
        the boolean solid's local frame, ready for
        :meth:`clean_for_tessellated`.

        Raises
        ------
        ValueError
            If the handle is not a boolean volume.
        """
        op = ctypes.c_uint(0)
        left = ctypes.c_void_p()
        left_trans = ctypes.c_void_p()
        right = ctypes.c_void_p()
        right_trans = ctypes.c_void_p()
        status = self._boolInfo(cobj, ctypes.byref(op), ctypes.byref(left),
                                ctypes.byref(left_trans), ctypes.byref(right),
                                ctypes.byref(right_trans))
        if status != 0:
            raise ValueError(_BOOL_HINT)
        lmesh = self._apply_placement(
            self._mesh_from_unplaced(left.value, n_segments), left_trans.value)
        rmesh = self._apply_placement(
            self._mesh_from_unplaced(right.value, n_segments), right_trans.value)
        # BooleanOp_t (PTMeshHelper.hh), same coding as the viz boolOp
        opname = _BOOL_OP_NAMES.get(op.value)
        if opname is None:
            raise ValueError(f'unknown boolean operation code: {op.value}')
        return self.boolean(self._weld(lmesh), self._weld(rmesh), opname)

    @staticmethod
    def _apply_placement(mesh, trans_cobj):
        """Apply an operand's vg::Transformation3D placement to mesh points.

        Baking a placement into operand-local points is a local->master
        mapping, i.e. the INVERSE of what Transformation3D::Transform does
        (master->local) - exactly the direction VecGeom's own
        SolidMesh::TransformVertices uses for placed volumes.  The handles
        point into the placed operand volumes, which live as long as the
        solid, so no keep-alive is needed.  An identity placement (the left
        operand by construction) reproduces the points bit-for-bit.
        """
        points = np.ascontiguousarray(mesh.points, dtype=np.float64)
        out = np.empty_like(points)
        BoolSolidMeshHandlerMixin._inverseTransform(trans_cobj, points.shape[0],
                                                    points, out)
        return pv.PolyData(out, mesh.faces)

    # ------------------------------------------------------------------
    # mesh x mesh boolean engine (also the backend of Mesh.getMesh)
    # ------------------------------------------------------------------
    @staticmethod
    def _weld(mesh) -> pv.PolyData:
        """Triangulate + weld at a scale-adaptive absolute tolerance.

        Operands coming from the visualisation ABI are float32, where
        coincident vertices (seams/poles) differ by ~1e-6 relative; without
        this weld the manifold engine rejects the operand
        ("Not all meshes are volumes!").
        """
        mesh = mesh.triangulate()
        lo = np.asarray(mesh.bounds[0::2])
        hi = np.asarray(mesh.bounds[1::2])
        tol = max(1e-9, float(np.linalg.norm(hi - lo)) * 1e-6)
        return mesh.clean(tolerance=tol, absolute=True)

    @staticmethod
    def boolean(mesh_a: pv.PolyData, mesh_b: pv.PolyData,
                operation: str = 'difference') -> pv.PolyData:
        """Boolean combination of two closed PolyData meshes (the engine).

        Boolean MESH fallback for CSG solids (VecGeom keeps the analytic
        truth; this only approximates it as a mesh).  Operands are
        triangulated and welded at ``_WELD_MM`` absolute tolerance first:
        meshes whose coincident vertices carry distinct indices (pyvista
        primitives' cap rings, VecGeom seam/pole points) are rejected by
        the manifold engine ("Not all meshes are volumes!").  The result
        should still go through :meth:`clean_for_tessellated`.

        pyvista's native boolean filters are deliberately not used: they
        wrap VTK filters that are unreliable for non-trivial inputs
        (pyvista issue #8632).  The engine needs
        ``pip install trimesh manifold3d``.
        """
        try:
            import trimesh
        except ImportError:
            raise ImportError('mesh booleans need trimesh and manifold3d: '
                              'pip install trimesh manifold3d') from None

        def to_tm(mesh):
            mesh = mesh.triangulate().clean(tolerance=_WELD_MM, absolute=True)
            return trimesh.Trimesh(vertices=mesh.points,
                                   faces=mesh.faces.reshape(-1, 4)[:, 1:],
                                   process=False)

        if operation not in ('difference', 'union', 'intersection'):
            raise ValueError(f"operation must be difference/union/intersection, got '{operation}'")

        operands = {}
        for name, mesh in (('mesh_a', mesh_a), ('mesh_b', mesh_b)):
            tm = to_tm(mesh)
            if not tm.is_volume:
                raise ValueError(f'{name} is not a closed volume '
                                 f'(watertight={tm.is_watertight}, '
                                 f'winding_consistent={tm.is_winding_consistent}); '
                                 'repair it on the pyvista side first '
                                 '(clean_for_tessellated)')
            operands[name] = tm
        result = getattr(operands['mesh_a'], operation)(operands['mesh_b'])

        faces = np.hstack(np.column_stack([np.full(len(result.faces), 3), result.faces]))
        vertices = np.asarray(result.vertices, dtype=np.float64)
        return pv.PolyData(vertices, faces.astype(np.int64))

    # ------------------------------------------------------------------
    # mesh conditioning / direct construction
    # ------------------------------------------------------------------
    @staticmethod
    def clean_for_tessellated(mesh: pv.PolyData, min_edge_ratio: float = 1e-6,
                              weld_tolerance: float = _WELD_MM) -> pv.PolyData:
        """Prepare a PolyData for transport as a Tessellated solid.

        Pipeline: triangulate (the C++ binding silently drops faces with >4
        vertices) -> weld coincident vertices with an ABSOLUTE tolerance (the
        default exact merge misses VecGeom seam/pole points, which coincide to
        ~1e-15 but carry distinct indices) -> collapse edges shorter than
        ``min_edge_ratio * bbox diagonal`` (boolean-engine slivers; the surface
        stays closed, unlike deleting the sliver facets) -> assert watertight
        (``n_open_edges == 0``), the contract VecGeom's closed-surface volume
        definition relies on.

        ``weld_tolerance`` is in mm; 1e-9 matches VecGeom's own vertex-dedup
        tolerance in ``UnplacedTessellated::Close``, so what welds here also
        dedups there.

        Raises
        ------
        ValueError
            If the cleaned mesh is not watertight.
        """
        mesh = mesh.triangulate().clean(tolerance=weld_tolerance, absolute=True)
        if mesh.n_cells == 0:
            raise ValueError('empty mesh')

        points = mesh.points
        tris = mesh.faces.reshape(-1, 4)[:, 1:]  # all triangles after triangulate
        lo = np.asarray(mesh.bounds[0::2])
        hi = np.asarray(mesh.bounds[1::2])
        tol = max(float(np.linalg.norm(hi - lo)), 1.0) * min_edge_ratio

        points, tris = BoolSolidMeshHandlerMixin._collapse_short_edges(points, tris, tol)
        faces = np.hstack(np.column_stack([np.full(tris.shape[0], 3), tris]))
        mesh = pv.PolyData(points, faces.astype(np.int64))

        n_open = mesh.n_open_edges
        if n_open:
            raise ValueError(f'mesh is not watertight: {n_open} open edges remain '
                             f'({mesh.n_faces_strict} faces). Fix the mesh on the '
                             'pyvista side before transport.')
        return mesh

    @staticmethod
    def _collapse_short_edges(points, tris, tol):
        """Merge triangle-mesh vertices closer than ``tol`` (edge collapse).

        Boolean-engine output carries sliver triangles whose short edges survive
        pyvista's absolute-tolerance weld; simply deleting those facets opens
        the surface.  Collapsing the short edges instead keeps it closed: the
        boundary is unchanged, only re-triangulated.  Groups of vertices chained
        by short edges are merged via connected components, each group taking
        its members' mean position; the triangles that collapse onto a repeated
        vertex (the degenerate ones) are dropped.
        """
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components

        edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
        lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
        close = edges[lengths < tol]
        if not len(close):
            return points, tris
        graph = coo_matrix((np.ones(len(close)), (close[:, 0], close[:, 1])),
                           shape=(len(points), len(points)))
        _, labels = connected_components(graph, directed=False)
        counts = np.bincount(labels)
        sums = np.zeros((counts.size, 3))
        np.add.at(sums, labels, points)
        points = sums / counts[:, None]
        tris = labels[tris]
        distinct = ((tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2])
                    & (tris[:, 0] != tris[:, 2]))
        return points, tris[distinct]

    @staticmethod
    def _face_sizes(mesh) -> np.ndarray:
        """Per-face vertex counts of a PolyData with arbitrary polygon faces."""
        flat = np.asarray(mesh.faces)
        sizes = []
        i = 0
        while i < flat.size:
            sizes.append(int(flat[i]))
            i += int(flat[i]) + 1
        return np.asarray(sizes, dtype=np.int64)

    @staticmethod
    def structured_cylinder(r: float, h: float, ntheta: int, nz: int,
                            thetas=None) -> pv.PolyData:
        """Watertight structured cylinder mesh built from ONE shared point array.

        Topological sharing makes coincident vertices bitwise identical, which
        sidesteps both pyvista's tolerance welding and VecGeom's 1e-9 dedup.
        ``thetas`` (radians, endpoint=False convention) allows a non-uniform phi
        grid for local refinement - something VecGeom's uniform-phi
        CreateMesh3D cannot do.  ``r``/``h`` in mm (full height).
        """
        if thetas is None:
            thetas = np.linspace(0., 2. * np.pi, ntheta, endpoint=False)
        else:
            thetas = np.asarray(thetas, dtype=np.float64)
            ntheta = len(thetas)
        zz = np.linspace(-h / 2., h / 2., nz + 1)

        points = np.empty(((nz + 1) * ntheta + 2, 3), dtype=np.float64)
        ring = np.column_stack([r * np.cos(thetas), r * np.sin(thetas)])
        for j, z in enumerate(zz):
            points[j * ntheta:(j + 1) * ntheta, :2] = ring
            points[j * ntheta:(j + 1) * ntheta, 2] = z
        ctr_bottom = (nz + 1) * ntheta
        ctr_top = ctr_bottom + 1
        points[ctr_bottom] = [0., 0., zz[0]]
        points[ctr_top] = [0., 0., zz[-1]]

        def idx(i, j):
            return (i % ntheta) + j * ntheta

        faces = []
        for j in range(nz):  # side quads, outward normal
            for i in range(ntheta):
                faces += [4, idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)]
        for j, ctr, flip in ((0, ctr_bottom, True), (nz, ctr_top, False)):  # fan caps
            for i in range(ntheta):
                a, b = (i + 1, i) if flip else (i, i + 1)
                faces += [3, ctr, idx(a, j), idx(b, j)]

        return pv.PolyData(points, np.asarray(faces, dtype=np.int64))
