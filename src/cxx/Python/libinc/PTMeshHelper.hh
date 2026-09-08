#ifndef Prompt_MeshHelper_hh
#define Prompt_MeshHelper_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  you may not use this file except in compliance with the License.          //
//  You may obtain a copy of the License at                                   //
//                                                                            //
//      http://www.apache.org/licenses/LICENSE-2.0                            //
//                                                                            //
//  Unless required by applicable law or agreed to in writing, software       //
//  distributed under the License is distributed on an "AS IS" BASIS,         //
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  //
//  See the License for the specific language governing permissions and       //
//  limitations under the License.                                            //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

#include "PromptCore.hh"

#ifdef __cplusplus
extern "C" {
#endif

enum BooleanOp_t {
  Union = 1,
  Subtraction = 2,
  Intersection = 3,
};

//  Transformation3D 
void* pt_Transformation3D_new(void *consttrfm3Dobj);
void* pt_Transformation3D_newfromID(int volid);
void* pt_Transformation3D_newfromdata(double x, double y, double z,
                              double phi, double theta, double psi,
                              double sx, double sy, double sz);
void pt_Transformation3D_delete(void *trfm3Dobj);
void pt_Transformation3D_multiple(void *trfm3Dobj1, void *trfm3Dobj2);
void pt_Transformation3D_transform(void *trfm3Dobj1, size_t numPt, double *in, double *out);
const char* pt_Transformation3D_print(void *trfm3Dobj);

void pt_Transformlation3D_setRotation(void *trfm3Dobj1, double r0, double r1, double r2, double r3,
                                      double r4, double r5, double r6, double r7, double r8);
void pt_Transformlation3D_setTranslation(void *obj, double x, double y, double z);

size_t pt_countFullTreeNode();
size_t pt_getPhysicalVolID_ByNodeID(size_t nodeID);

const char* pt_getPhysicalVolumeName(size_t pvolID);
const char* pt_getMeshName(size_t pvolID);
void pt_getLogVolumeInfo(size_t pvolID, char* cp);
const char* pt_getLogicalVolumeMaterialName(size_t pvolID);
const char* pt_getLogicalVolumeSurfaceProcessName(size_t pvolID);
void pt_meshInfo(size_t pvolID, size_t nSegments, size_t &npoints, size_t &nPlolygen, size_t &faceSize,
                  int &leftvolID, int &rightvolID, size_t &boolOp);
void pt_generatePointCloud(size_t pvolID, size_t nPoint, double *points, double *normals);
void pt_getMesh(size_t nodeID, size_t nSegments, float *points, size_t *NumPolygonPoints, size_t *faces, size_t pvolID);
void pt_printMesh();

// solid -> mesh extraction from a bare Solid (its own cobj), no
// GeoTree/world required. Unlike pt_getMesh above (GeoTree based, global
// frame, float), these output the solid's LOCAL frame in double precision,
// as required by UnplacedTessellated::Close (1e-9 mm vertex dedup).
// Two-phase protocol: query the sizes, allocate on the python side, then fill.
//   status 0 = ok, 1 = CreateMesh3D not implemented for this solid
//   (boolean solids return nullptr -> mesh on the pyvista/trimesh side instead),
//   2 = empty mesh.
// faces is the flat VTK layout [n, i1..in, ...]; faceSize counts n as well.
int pt_solid_meshInfo(void* unplaced, size_t nSegments,
                      size_t* npoints, size_t* npolygons, size_t* faceSize);
int pt_solid_getMesh(void* unplaced, size_t nSegments,
                     double* points, size_t* faces);
// Analytic capacity of a bare solid, mm^3 (works without a world/Volume).
double pt_solid_capacity(void* unplaced);

// Unpack a boolean solid so python can mesh its operands on the pyvista side:
//   status 0 = it is a boolean (outputs filled), 1 = not a boolean solid.
// left/right receive the operand VUnplacedVolume*, left_trans/right_trans
// their placement vg::Transformation3D* (members of the placed operand
// volumes, which live as long as the solid; pt_solid_* never deletes them).
// op uses the BooleanOp_t codes above (Union=1, Subtraction=2,
// Intersection=3); the left operand sits at identity by construction
// (pt_solid_* and the GDML loader both Place() it bare).
int pt_solid_boolInfo(void* unplaced, unsigned* op,
                      void** left, void** left_trans,
                      void** right, void** right_trans);

// Apply the INVERSE of a vg::Transformation3D to a point batch
// (local->master direction - what baking a placement into mesh points
// needs; Transformation3D::Transform is master->local, see
// SolidMesh::TransformVertices for the VecGeom-internal precedent).
void pt_Transformation3D_inverseTransform(void* trfm, size_t numPt,
                                          double* in, double* out);

#ifdef __cplusplus
}
#endif
#endif
