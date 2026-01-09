#include "PTVecGeom.hh"
#include "PromptCore.hh"

#include "VecGeom/management/GeoManager.h"
#include "VecGeom/volumes/UnplacedBox.h"
#include "VecGeom/volumes/UnplacedSphere.h"
#include "VecGeom/volumes/UnplacedTube.h"
#include "VecGeom/volumes/UnplacedTrapezoid.h"
#include "VecGeom/volumes/UnplacedPolyhedron.h"
#include "VecGeom/volumes/UnplacedGenTrap.h"
#include "VecGeom/volumes/UnplacedCone.h"
#include "VecGeom/volumes/UnplacedCutTube.h"
#include "VecGeom/volumes/UnplacedHype.h"
#include "VecGeom/volumes/UnplacedOrb.h"
#include "VecGeom/volumes/UnplacedParaboloid.h"
#include "VecGeom/volumes/UnplacedPolycone.h"
#include "VecGeom/volumes/UnplacedTet.h"
#include "VecGeom/volumes/UnplacedEllipsoid.h"
#include "VecGeom/volumes/UnplacedBooleanVolume.h"

#include "VecGeom/volumes/UnplacedVolume.h"
#include "VecGeom/volumes/SpecializedTessellated.h"
#include "VecGeom/volumes/UnplacedTessellated.h"
#include "VecGeom/volumes/MultiUnion.h"

#include "VecGeom/management/BVHManager.h"
#include "VecGeom/management/GeoManager.h"

#include "VecGeom/navigation/VNavigator.h"
#include "VecGeom/navigation/GlobalLocator.h"
#include "VecGeom/navigation/NewSimpleNavigator.h"
#include "VecGeom/navigation/SimpleABBoxNavigator.h"
#include "VecGeom/navigation/HybridNavigator2.h"
#include "VecGeom/navigation/BVHNavigatorV.h"


namespace vg = VECGEOM_NAMESPACE;


void pt_initNavigators(bool use_bvh_navigator)
{
  if (use_bvh_navigator)
    vg::BVHManager::Init();

  for (auto &lvol : vg::GeoManager::Instance().GetLogicalVolumesMap()) {
    auto ndaughters = lvol.second->GetDaughtersp()->size();

    if (ndaughters <= 2) {
      lvol.second->SetNavigator(vg::NewSimpleNavigator<>::Instance());
    } else if (ndaughters <= 10) {
      if (use_bvh_navigator) {
        lvol.second->SetNavigator(vg::BVHNavigatorV<>::Instance());
      } else {
        lvol.second->SetNavigator(vg::SimpleABBoxNavigator<>::Instance());
      }
    } else { // ndaughters > 10
      if (use_bvh_navigator) {
        lvol.second->SetNavigator(vg::BVHNavigatorV<>::Instance());
      } else {
        lvol.second->SetNavigator(vg::HybridNavigator<>::Instance());
        vg::HybridManager2::Instance().InitStructure((lvol.second));
      }
    }
  }
}


void pt_setWorld(void* logicalWorld)
{
    vg::GeoManager::Instance().SetWorld(static_cast<vg::LogicalVolume *>(logicalWorld)->Place());
    vg::GeoManager::Instance().CloseGeometry();
    pt_initNavigators(true);
}

//   Box *worldUnplaced      = new UnplacedBox(10, 10, 10)
void* pt_Box_new(double hx, double hy, double hz)
{
    return static_cast<void *>(new vg::UnplacedBox(hx, hy, hz));
}

// Orb
void *pt_Orb_new(double r)
{
    return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedOrb>(r));
}


void* pt_Tube_new(double rmin, double rmax, double z, double startphi, double deltaphi)
{
    return static_cast<void *>(new vg::SUnplacedTube<>(rmin, rmax, z, startphi, deltaphi));
}

void* pt_Sphere_new(double rmin, double rmax, double startphi, double deltaphi , double starttheta, double deltatheta)
{
  return static_cast<void *>(new vg::UnplacedSphere(rmin, rmax, startphi, deltaphi , starttheta, deltatheta));
}

//Trapezoid
void* pt_Trapezoid_new(double x1, double x2, double y1, double y2, double z)
{
    return static_cast<void *>(new vg::UnplacedTrapezoid(x1, x2, y1, y2, z));
}

// General_Trapezoid
void* pt_GenTrapezoid_new(double dz, double theta, double phi, double dy1, double dx1, 
                    double dx2, double Alpha1, double dy2, double dx3, double dx4, double Alpha2)
{
    return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedTrapezoid>(
                       dz,  theta,  phi,  dy1,  dx1, 
                     dx2,  Alpha1,  dy2,  dx3,  dx4,  Alpha2));
  }



void pt_Box_delete(void* obj)
{
    delete static_cast<vg::UnplacedBox *>(obj);
}


void *pt_Polyhedron_new(double phiStart, double phiDelta, const int sideCount, const int zPlaneCount,
                     double *zPlanes, double *rMin, double *rMax)
{
    return static_cast<void *>(new vg::UnplacedPolyhedron(phiStart, phiDelta,  sideCount, 
                          zPlaneCount, zPlanes, rMin, rMax));
}

void *pt_Tessellated_new(size_t faces_length, size_t* faces, double *points)
{
    vg::UnplacedTessellated *tsl = new vg::UnplacedTessellated ();

    size_t i = 0;

    while (i < faces_length) {
        size_t n_points = faces[i];

          if (n_points == 3) {
            size_t idx1 = faces[i + 1];
            size_t idx2 = faces[i + 2];
            size_t idx3 = faces[i + 3];

            const vg::Vector3D<double>* p1 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx1 * 3]);
            const vg::Vector3D<double>* p2 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx2 * 3]);
            const vg::Vector3D<double>* p3 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx3 * 3]);

            tsl->AddTriangularFacet(*p1, *p2, *p3);
        } else if (n_points == 4) {
            size_t idx1 = faces[i + 1];
            size_t idx2 = faces[i + 2];
            size_t idx3 = faces[i + 3];
            size_t idx4 = faces[i + 4];

            const vg::Vector3D<double>* p1 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx1 * 3]);
            const vg::Vector3D<double>* p2 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx2 * 3]);
            const vg::Vector3D<double>* p3 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx3 * 3]);
            const vg::Vector3D<double>* p4 = reinterpret_cast<const vg::Vector3D<double>*>(&points[idx4 * 3]);

            tsl->AddQuadrilateralFacet(*p1, *p2, *p3, *p4);
        }
        i += n_points + 1;
    }
    tsl->Close();

    return static_cast<void *>(tsl);
}

void *pt_ArbTrapezoid_new(double (*v11), double (*v12), double (*v13), double (*v14), 
                        double (*v21), double (*v22), double (*v23), double (*v24),
                        double halfHeight)
{
    std::vector<double> verticesx;
    verticesx.push_back(v11[0]);
    verticesx.push_back(v12[0]);
    verticesx.push_back(v13[0]);
    verticesx.push_back(v14[0]);
    verticesx.push_back(v21[0]);
    verticesx.push_back(v22[0]);
    verticesx.push_back(v23[0]);
    verticesx.push_back(v24[0]);
    std::vector<double> verticesy;
    verticesy.push_back(v11[1]);
    verticesy.push_back(v12[1]);
    verticesy.push_back(v13[1]);
    verticesy.push_back(v14[1]);
    verticesy.push_back(v21[1]);
    verticesy.push_back(v22[1]);
    verticesy.push_back(v23[1]);
    verticesy.push_back(v24[1]);
    return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedGenTrap>(verticesx.data(), verticesy.data(), halfHeight));
}

// Cone
void *pt_Cone_new(double rmin1, double rmax1, double rmin2, double rmax2, double dz, double phimin,
               double deltaphi)
{
    return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedCone>(rmin1, rmax1, rmin2, rmax2, dz, phimin,
              deltaphi));
}

// CutTube
void *pt_CutTube_new(double rmin, double rmax, double halfHeight, double sphi, double dphi, 
                  double (*botNormal), double (*topNormal))
{
    return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedCutTube>(rmin, rmax, halfHeight, sphi, dphi, botNormal[0],
                           botNormal[1], botNormal[2], topNormal[0], topNormal[1], topNormal[2]));
}

// Hyperbolic_tube
void *pt_HypeTube_new(double rmin, double rmax, double inst, double outst, double halfHeight)
{
  return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedHype>(
    rmin, rmax, inst, outst, halfHeight));
}

// Paraboloid
void *pt_Paraboloid_new(double rbot, double rtop, double halfHeight)
{
  return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedParaboloid>(
                      rbot, rtop, halfHeight));
}

// Polycone
void *pt_Polycone_new(double sphi, double dphi, int planeNum, double (*z), double (*rmin), double (*rmax))
{
  return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedPolycone>(
                      sphi, dphi, planeNum, z, rmin, rmax));
}

// Tet
void *pt_Tet_new(double (*p1), double (*p2), double (*p3), double (*p4))
{
  return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedTet>(
                      p1, p2, p3, p4));
}

// Ellipsoid
void *pt_Ellipsoid_new(double dx, double dy, double dz, double zBottomCut, double zTopCut)
{
  return static_cast<void *> (vg::GeoManager::MakeInstance<vg::UnplacedEllipsoid>(
    dx, dy, dz, zBottomCut, zTopCut));
}


// Volume 
void* pt_Volume_new(const char* name, void *unplacedVolume)
{
    auto logVol = new vg::LogicalVolume(name, static_cast<vg::VUnplacedVolume *>(unplacedVolume));
    auto p = static_cast<void *>(logVol);
    // const std::map<unsigned int, vg::LogicalVolume *> & vmap  = vg::GeoManager::Instance().GetLogicalVolumesMap();
    // for(auto it=vmap.begin(); it!=vmap.end(); ++it)
    // {
    std::cout << "pt_Volume_new " << logVol->GetName() << ", vol id " << logVol->id() << std::endl; 
    // }
    std::cout << "\n";
    return p;
}

void pt_Volume_delete(void* obj)
{
    delete static_cast<vg::LogicalVolume *>(obj);
}

void pt_Volume_placeChild(void* obj, const char* name, void *volume,
                                    void *transformation, int group)
{
    auto transf = static_cast<const vg::Transformation3D *>(transformation);
    auto vol = static_cast<vg::LogicalVolume *>(volume);
    auto constplaced = static_cast<vg::LogicalVolume *>(obj)->PlaceDaughter(name, vol, transf);
    vg::VPlacedVolume* placed = const_cast<vg::VPlacedVolume *>(constplaced);;

    if(group)
    {
        placed->SetCopyNo(group);
    }
    std::cout << name << " Group ID " << placed->GetCopyNo() << std::endl;
}

unsigned pt_Volume_id(void* obj)
{
    return static_cast<vg::LogicalVolume *>(obj)->id();
}

double pt_Volume_capacity(void *obj)
{
  return static_cast<vg::LogicalVolume *>(obj)->GetUnplacedVolume()->Capacity();
}

// obj_left and obj_right are unplaced
// return an unplaced as well
void* pt_solid_intersection(void* obj_left, void* obj_right, void* obj_right_transf)
{
  auto solid1 = static_cast<vg::VUnplacedVolume *>(obj_left);
  auto lbox1 = new vg::LogicalVolume("solid_left", solid1);
  auto pbox1 = lbox1->Place();

  auto solid2 = static_cast<vg::VUnplacedVolume *>(obj_right);
  auto lbox2 = new vg::LogicalVolume("solid_right", solid2);
  auto transf = static_cast<const vg::Transformation3D *>(obj_right_transf);
  auto pbox2 = lbox2->Place(transf);

  return static_cast<void *> (new vg::UnplacedBooleanVolume<vg::kIntersection> (vg::kIntersection, pbox1, pbox2));
}

void* pt_solid_union(void* obj_left, void* obj_right, void* obj_right_transf)
{
  auto solid1 = static_cast<vg::VUnplacedVolume *>(obj_left);
  auto lbox1 = new vg::LogicalVolume("solid_left", solid1);
  auto pbox1 = lbox1->Place();

  auto solid2 = static_cast<vg::VUnplacedVolume *>(obj_right);
  auto lbox2 = new vg::LogicalVolume("solid_right", solid2);
  auto transf = static_cast<const vg::Transformation3D *>(obj_right_transf);
  auto pbox2 = lbox2->Place(transf);

// enum BooleanOperation { kUnion, kIntersection, kSubtraction };
  return static_cast<void *> (new vg::UnplacedBooleanVolume<vg::kUnion> (vg::kUnion, pbox1, pbox2));
}

void* pt_solid_subtraction(void* obj_left, void* obj_right, void* obj_right_transf)
{
  auto solid1 = static_cast<vg::VUnplacedVolume *>(obj_left);
  auto lbox1 = new vg::LogicalVolume("solid_left", solid1);
  auto pbox1 = lbox1->Place();

  auto solid2 = static_cast<vg::VUnplacedVolume *>(obj_right);
  auto lbox2 = new vg::LogicalVolume("solid_right", solid2);
  auto transf = static_cast<const vg::Transformation3D *>(obj_right_transf);
  auto pbox2 = lbox2->Place(transf);

// enum BooleanOperation { kUnion, kIntersection, kSubtraction };
  return static_cast<void *> (new vg::UnplacedBooleanVolume<vg::kSubtraction> (vg::kSubtraction, pbox1, pbox2));
}


// unsigned pt_LogicalVolume_copyid(void* obj)
// {
//     return static_cast<vg::LogicalVolume *>(obj)->GetCopyNo()();
// }

