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

#include "PTMeshHelper.hh"
#include "PTGeoTree.hh"
#include "PTGeoLoader.hh"

#include <VecGeom/base/Config.h>
#include <VecGeom/volumes/SolidMesh.h>
#include <VecGeom/management/GeoManager.h>
#include <VecGeom/gdml/Middleware.h>
#include <VecGeom/gdml/Frontend.h>

#include <VecGeom/base/Transformation3D.h>
#include "VecGeom/base/Vector3D.h"
#include <VecGeom/volumes/UnplacedBooleanVolume.h>
#include <VecGeom/volumes/BooleanStruct.h>

void* pt_Transformation3D_new(void *consttrfm3Dobj)
{
  auto p = static_cast<const vecgeom::Transformation3D*> (consttrfm3Dobj) ;
  return static_cast<void *>(new vecgeom::Transformation3D(*p));
}

void* pt_Transformation3D_newfromID(int id)
{
  auto &geoManager = vecgeom::GeoManager::Instance();
  // const vgdml::VPlacedVolume
  auto *vol = geoManager.Convert(id);

  auto p = new vecgeom::Transformation3D();
  *p = vol->GetTransformation()->Inverse();
  return static_cast<void *>(p);
}

void* pt_Transformation3D_newfromdata(double x, double y, double z,
                              double phi, double theta, double psi,  
                              double sx, double sy, double sz)
{
  auto obj = new vecgeom::Transformation3D(x, y, z, phi, theta, psi, sx, sy, sz);
  return static_cast<void *>(obj);    
}   


void pt_Transformlation3D_setRotation(void *obj, double r0, double r1, double r2, double r3,
                                      double r4, double r5, double r6, double r7, double r8)
{
  
  static_cast<vecgeom::Transformation3D *>(obj)->SetRotation(r0,r1,r2,r3,r4,r5,r6,r7,r8);
  static_cast<vecgeom::Transformation3D *>(obj)->SetProperties(); // update the internal flags 
}

void pt_Transformlation3D_setTranslation(void *obj, double x, double y, double z)
{
  
  static_cast<vecgeom::Transformation3D *>(obj)->SetTranslation(x,y,z);
  static_cast<vecgeom::Transformation3D *>(obj)->SetProperties(); // update the internal flags 
}


void pt_Transformation3D_delete(void *trfm3Dobj)
{
  delete static_cast<vecgeom::Transformation3D *>(trfm3Dobj);
}

void pt_Transformation3D_multiple(void *trfm3Dobj1, void *trfm3Dobj2)
{
   auto obj1 = static_cast<vecgeom::Transformation3D *>(trfm3Dobj1);
   auto obj2 = static_cast<vecgeom::Transformation3D *>(trfm3Dobj2);
   obj1->MultiplyFromRight(*obj2);
}

void pt_Transformation3D_transform(void *obj, size_t numPt, double *in, double *out)
{
  auto mat = static_cast<vecgeom::Transformation3D *>(obj);
  for(size_t i=0;i<numPt;i++)
  {
    // vecgeom::Vector3D<Precision> vert(in[i*3], in[i*3+1], in[i*3+2]);
    auto vert = *reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(in+i*3);
    // auto vertTransformed = reinterpret_cast<vecgeom::Vector3D<vecgeom::Precision>*>(out+i*3);
    auto vertTransformed = mat->Transform(vert);
    *(out + i*3) = vertTransformed.x();
    *(out + i*3 + 1) = vertTransformed.y();
    *(out + i*3 + 2) = vertTransformed.z();
  }
}

const char* pt_Transformation3D_print(void *trfm3Dobj)
{
  std::ostringstream a;
  static_cast<vecgeom::Transformation3D *>(trfm3Dobj)->Print(a);
  std::string str;
  a << str;
  return str.c_str();
}

size_t pt_countFullTreeNode()
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  return tree.getNumNodes(Prompt::GeoTree::FULL);
}

size_t pt_getPhysicalVolID_ByNodeID(size_t nodeID)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[nodeID];
  return node->physical;
}

void pt_generatePointCloud(size_t pvolID, size_t nPoint, double *points, double *normals)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[pvolID];
  const auto &tMatrix = tree.m_fllTreeMatrix[pvolID];

  auto &geoManager = vecgeom::GeoManager::Instance();
  // const vgdml::VPlacedVolume
  auto *vol = geoManager.Convert(node->physical);

  for(size_t i=0;i<nPoint;i++)
  {
    auto p = vol->GetUnplacedVolume()->SamplePointOnSurface();
    auto ap = tMatrix.Transform(p);
    *(points++) = ap.x();
    *(points++) = ap.y();
    *(points++) = ap.z();

    vecgeom::Vector3D<Precision> norm;
    vol->GetUnplacedVolume()->Normal(p, norm);
    auto an = tMatrix.TransformDirection(norm);
    *(normals++) = an.x();
    *(normals++) = an.y();
    *(normals++) = an.z();
  }
}


void pt_meshInfo(size_t pvolID, size_t nSegments, size_t &npoints, size_t &nPlolygen, size_t &faceSize,
                  int &leftvolID, int &rightvolID, size_t &boolOp)
{
  leftvolID = -1;
  rightvolID = -1;
  boolOp = 0;

  auto &geoManager = vecgeom::GeoManager::Instance();

  // const vgdml::VPlacedVolume
  auto *vol = geoManager.Convert(pvolID);
  auto volName = vol->GetName();

  auto unplacedVol = vol->GetUnplacedVolume();
  if(unplacedVol)
  {
    using namespace vecgeom;
    if(auto unionVol = dynamic_cast<UnplacedBooleanVolume<kUnion> const *>(unplacedVol)) 
    {
      boolOp = Union;
      leftvolID = unionVol->GetLeft()->id();
      rightvolID = unionVol->GetRight()->id();
    }
    if(auto unionVol = dynamic_cast<UnplacedBooleanVolume<kSubtraction> const *>(unplacedVol)) 
    {
      boolOp = Subtraction;
      leftvolID = unionVol->GetLeft()->id();
      rightvolID = unionVol->GetRight()->id();
    }
    if(auto unionVol = dynamic_cast<UnplacedBooleanVolume<kIntersection> const *>(unplacedVol)) 
    {
      boolOp = Intersection;
      leftvolID = unionVol->GetLeft()->id();
      rightvolID = unionVol->GetRight()->id();
    }
  }
  else
   PROMPT_THROW2(BadInput, "No unplaced volume found for physical volume ID: " << pvolID);
   
  // Utils3D::USolidMesh
  auto *mesh = vol->CreateMesh3D(nSegments);
  if(!mesh)
  {
    npoints=0;
    nPlolygen=0;
    faceSize=0;
    return;
  }

  nPlolygen = mesh->GetPolygons().size();
  npoints = 0;
  for(const auto &apolygon: mesh->GetPolygons())
  {
    if(!npoints)
      npoints = apolygon.fVert.size();
    faceSize += apolygon.fInd.size();
  }
}

const char* pt_getMeshName(size_t pvolID)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[pvolID];
  auto &geoManager = vecgeom::GeoManager::Instance();
  // const vgdml::VPlacedVolume
  return geoManager.Convert(node->physical)->GetLogicalVolume()->GetName();
}

const char* pt_getPhysicalVolumeName(size_t pvolID)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[pvolID];
  auto &geoManager = vecgeom::GeoManager::Instance();
  // const vgdml::VPlacedVolume
  return geoManager.Convert(node->physical)->GetName();
}

const char* pt_getLogicalVolumeMaterialName(size_t pvolID)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[pvolID];
  auto &resman = Prompt::Singleton<Prompt::ResourceManager>::getInstance();
  std::cout << resman.getLogicalVolumeMaterialName(node->logical) << std::endl;
  return resman.getLogicalVolumeMaterialName(node->logical);
}

void pt_getLogVolumeInfo(size_t pvolID, char* cp)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[pvolID];
  auto &resman = Prompt::Singleton<Prompt::ResourceManager>::getInstance();
  std::string info = "Material : ";
  info += resman.getLogicalVolumeMaterialName(node->logical);

  auto scorinfo = resman.getLogicalVolumeScorerName(node->logical);
  if(!scorinfo.empty())
  {
    info += "\n Associated scorer: ";
    info += scorinfo;
  }
  sprintf (cp, "%s ", info.c_str());
}

//size of points: 3*n
//size of faces: n
//size of NumPolygonPoints: m
void pt_getMesh(size_t nodeID, size_t nSegments, float *points, size_t *NumPolygonPoints, size_t *faces, size_t pvolID)
{
  auto tree = Prompt::Singleton<Prompt::GeoTree>::getInstance();
  const auto node = tree.m_fullTreeNode[nodeID];
  // std::cout << "Handling node:" << node->physical << " pvolID:" << pvolID << std::endl;
  const auto &tMatrix = tree.m_fllTreeMatrix[nodeID];

  auto &geoManager = vecgeom::GeoManager::Instance();

  // const vgdml::VPlacedVolume
  auto *vol = geoManager.Convert(pvolID);
  
  vecgeom::Transformation3D matrix;
  // handling physical volumes that do not belong to the node, 
  // eg. boolean operation where the individual basic physical volumes not in the tree
  if(node->physical != pvolID) 
  {
    auto botTrans = vol->GetTransformation();
    matrix = *botTrans;
  }
  auto *mesh = vol->GetUnplacedVolume()->CreateMesh3D(matrix, nSegments);

  if(mesh->GetPolygons().empty())
    PROMPT_THROW(BadInput, "empty mesh");

  // auto = Utils3D::vector_t<Utils3D::Polygon> const
  auto &polygens = mesh->GetPolygons();
  for(const auto &poly: polygens)
  {
    for(const auto &vert: poly.fVert)
    {
      auto vertTransformed = tMatrix.Transform(vert);
      *(points++)=vertTransformed[0];
      *(points++)=vertTransformed[1];
      *(points++)=vertTransformed[2];
    }
   break;
   }

  for(const auto &apolygon: polygens)
  {
    *(NumPolygonPoints++) = apolygon.fN;
    *(faces++)  = apolygon.fN;

    for(auto vt : apolygon.fInd )
    {
      *(faces++) = vt;
      // std::cout << vt << std::endl;
    }
  }
}

void pt_printMesh()
{
  std::vector<vecgeom::VPlacedVolume *> v1;
  vecgeom::GeoManager::Instance().getAllPlacedVolumes(v1);
  for (auto &plvol : v1)
  {
    std::cerr << "placedVol=" << plvol << ", name=" << plvol->GetName()
              << ". type name " << typeid(plvol).name()
              << ". Number of solids " << plvol->GetDaughters().size()
              << ", " << vecgeom::GeoManager::Instance().GetWorld() << ">\n";

    // Utils3D::USolidMesh
    auto *mesh = plvol->CreateMesh3D(10);
    if(mesh)
    {
      for(const auto &v: mesh->GetPolygons())
      {
        std::cout << v << std::endl;
      }
    }
  }
}
