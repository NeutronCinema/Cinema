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

const char* pt_getMeshName(size_t pvolID);
void pt_getLogVolumeInfo(size_t pvolID, char* cp);
const char* pt_getLogicalVolumeMaterialName(size_t pvolID);
void pt_meshInfo(size_t pvolID, size_t nSegments, size_t &npoints, size_t &nPlolygen, size_t &faceSize,
                  int &leftvolID, int &rightvolID, size_t &boolOp);
void pt_generatePointCloud(size_t pvolID, size_t nPoint, double *points, double *normals);
void pt_getMesh(size_t nodeID, size_t nSegments, float *points, size_t *NumPolygonPoints, size_t *faces, size_t pvolID);
void pt_printMesh();

#ifdef __cplusplus
}
#endif
#endif
