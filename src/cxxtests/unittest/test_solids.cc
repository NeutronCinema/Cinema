////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    //
//                                                                            //
//  Copyright 2021-2026 Cinema developers                                     //
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
//
// Per-solid unit tests. Each TEST_CASE builds one solid through the exact
// pt_*_new C API wrappers that python solid.py uses (src/cxx/Python/libsrc/
// PTVecGeom.cc), wraps it in a LogicalVolume via pt_Volume_new, places it with
// LogicalVolume::Place() and then checks:
//   * analytic Capacity() against the closed-form volume,
//   * Contains() on fixed inside/outside point sets,
//   * one DistanceToOut() sanity per solid.
//
// All angles passed to the wrappers are RADIANS (python converts with
// deg2rad before calling). All dx/dy/dz follow the ROOT/Geant4 convention
// (HALF lengths).
//
// NOTE on pt_Tube_new: PTVecGeom.hh declares the last two parameters as
// "..., double deltaphi, double startphi", but the implementation
// (PTVecGeom.cc) passes them straight into UnplacedTube(rmin, rmax, z, sphi,
// dphi), i.e. the real argument order is (rmin, rmax, z, startphi, deltaphi).
// python solid.py passes phiStart, phiDelta in that order. The segmented-tube
// case below pins the REAL order.
//
// NOTE on boolean Capacity(): UnplacedBooleanVolume::Capacity() is NOT
// analytic - it lazily runs EstimateCapacity(1000000), a random MC estimate
// over the global RNG. It is therefore neither deterministic nor exact, so
// the boolean cases below assert Contains()/DistanceToOut() only.

#include "../doctest.h"

#include "PTVecGeom.hh"

#include <cmath>
#include <cstddef>
#include <vector>

#include "VecGeom/base/Vector3D.h"
#include "VecGeom/base/Transformation3D.h"
#include "VecGeom/volumes/LogicalVolume.h"
#include "VecGeom/volumes/PlacedVolume.h"

namespace vg = VECGEOM_NAMESPACE;

namespace {

// Wrap an unplaced solid in a LogicalVolume through the production C wrapper.
// The returned LogicalVolume* is what pt_Volume_capacity/pt_Volume_id take.
vg::LogicalVolume *makeVolume(const char *name, void *unplaced)
{
  return static_cast<vg::LogicalVolume *>(pt_Volume_new(name, unplaced));
}

// Capacity through the production C wrapper (LogicalVolume -> unplaced solid).
double solidCapacity(vg::LogicalVolume *lv) { return pt_Volume_capacity(lv); }

vg::Vector3D<double> V(double x, double y, double z) { return vg::Vector3D<double>(x, y, z); }

} // namespace

////////////////////////////////////////////////////////////////////////////////
// (1) Box
TEST_CASE("solid.Box")
{
  vg::LogicalVolume *lv = makeVolume("box", pt_Box_new(2.0, 3.0, 4.0)); // box 4 x 6 x 8
  vg::VPlacedVolume *vol = lv->Place();

  // Closed form volume 2hx * 2hy * 2hz:
  CHECK(solidCapacity(lv) == doctest::Approx(2.0 * 2.0 * 2.0 * 3.0 * 2.0 * 4.0));

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(1.9, 0.0, 0.0))); // face-eps inside
  CHECK(vol->Contains(V(0.0, 2.9, 0.0)));
  CHECK(vol->Contains(V(0.0, 0.0, 3.9)));
  CHECK_FALSE(vol->Contains(V(2.1, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 3.1, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 4.1)));

  // From the center along +x the exit is at x = hx:
  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(2.0));
}

////////////////////////////////////////////////////////////////////////////////
// (2) Orb
TEST_CASE("solid.Orb")
{
  vg::LogicalVolume *lv = makeVolume("orb", pt_Orb_new(2.5));
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(4.0 * M_PI / 3.0 * 2.5 * 2.5 * 2.5));

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(2.4, 0.0, 0.0)));       // r - eps
  CHECK(vol->Contains(V(1.0, 1.0, 1.0)));       // r = sqrt(3) ~ 1.73
  CHECK_FALSE(vol->Contains(V(2.6, 0.0, 0.0))); // r + eps
  CHECK_FALSE(vol->Contains(V(1.5, 1.5, 1.5))); // r ~ 2.60

  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(2.5));
}

////////////////////////////////////////////////////////////////////////////////
// (3) Tube, full 2*pi and phi-segmented
TEST_CASE("solid.Tube")
{
  // Full tube: rmin=1, rmax=3, half z=5, startphi=0, deltaphi=2pi.
  // The real wrapper argument order is (rmin, rmax, z, startphi, deltaphi);
  // PTVecGeom.hh misleadingly names the 4th/5th params deltaphi/startphi.
  vg::LogicalVolume *lv = makeVolume("tube_full", pt_Tube_new(1.0, 3.0, 5.0, 0.0, 2.0 * M_PI));
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(M_PI * (9.0 - 1.0) * 10.0)); // pi*(rmax^2-rmin^2)*2z

  CHECK(vol->Contains(V(2.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(2.0, 0.0, 4.9)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 0.0))); // radial hole: r=0 < rmin
  CHECK_FALSE(vol->Contains(V(0.5, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(3.5, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 5.5)));

  CHECK(vol->DistanceToOut(V(2.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(1.0));

  // Phi-segment [0, pi]: this call pins the real (startphi, deltaphi) order.
  vg::LogicalVolume *lv2 = makeVolume("tube_seg", pt_Tube_new(1.0, 3.0, 5.0, 0.0, M_PI));
  vg::VPlacedVolume *vol2 = lv2->Place();

  CHECK(vol2->Contains(V(1.2, 1.2, 0.0)));         // phi = pi/4
  CHECK(vol2->Contains(V(-1.2, 1.2, 0.0)));        // phi = 3pi/4
  CHECK_FALSE(vol2->Contains(V(-1.2, -1.2, 0.0))); // phi = 5pi/4
  CHECK_FALSE(vol2->Contains(V(1.2, -1.2, 0.0)));  // phi = -pi/4
  CHECK_FALSE(vol2->Contains(V(0.0, 0.0, 5.5)));   // axial bound unchanged
}

////////////////////////////////////////////////////////////////////////////////
// (4) Sphere, full shell and theta-segmented
TEST_CASE("solid.Sphere")
{
  // Wrapper order: (rmin, rmax, startphi, deltaphi, starttheta, deltatheta),
  // radians. Full shell r in [0.5, 2]:
  vg::LogicalVolume *lv = makeVolume("sphere_full", pt_Sphere_new(0.5, 2.0, 0.0, 2.0 * M_PI, 0.0, M_PI));
  vg::VPlacedVolume *vol = lv->Place();

  double dV = 4.0 * M_PI / 3.0 * (8.0 - 0.125); // 4/3 pi (rmax^3 - rmin^3)
  CHECK(solidCapacity(lv) == doctest::Approx(dV));

  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 0.0))); // the origin sits in the rmin hole
  CHECK_FALSE(vol->Contains(V(0.3, 0.0, 0.0))); // r = 0.3 < rmin
  CHECK(vol->Contains(V(0.7, 0.0, 0.0)));       // r = 0.7, just above rmin
  CHECK(vol->Contains(V(0.3, 0.0, 0.9)));       // r ~ 0.949
  CHECK(vol->Contains(V(1.5, 0.0, 0.0)));       // r = 1.5
  CHECK_FALSE(vol->Contains(V(2.1, 0.0, 0.0))); // r > rmax
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 2.1)));

  // From an interior point radially out the exit is at r = rmax: 2 - 1.5:
  CHECK(vol->DistanceToOut(V(1.5, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(0.5));

  // Theta segment [0, pi/2]: upper hemisphere shell.
  vg::LogicalVolume *lv2 = makeVolume("sphere_theta", pt_Sphere_new(0.5, 2.0, 0.0, 2.0 * M_PI, 0.0, M_PI / 2.0));
  vg::VPlacedVolume *vol2 = lv2->Place();

  double dV2 = 2.0 * M_PI / 3.0 * (8.0 - 0.125) * (std::cos(0.0) - std::cos(M_PI / 2.0));
  CHECK(solidCapacity(lv2) == doctest::Approx(dV2));

  CHECK(vol2->Contains(V(0.3, 0.0, 0.9)));        // theta ~ 0.32 < pi/2
  CHECK_FALSE(vol2->Contains(V(0.3, 0.0, -0.9))); // theta ~ pi - 0.32
}

////////////////////////////////////////////////////////////////////////////////
// (5) Trapezoid (Trd-like 5-argument constructor)
TEST_CASE("solid.Trapezoid")
{
  // Box-degenerate parameters: x1=x2, y1=y2 -> box 4 x 6 x 8 (half dims 2,3,4).
  vg::LogicalVolume *lv = makeVolume("trap_box", pt_Trapezoid_new(2.0, 2.0, 3.0, 3.0, 4.0));
  vg::VPlacedVolume *vol = lv->Place();
  CHECK(solidCapacity(lv) == doctest::Approx(4.0 * 6.0 * 8.0));
  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(1.9, 2.9, 3.9)));
  CHECK_FALSE(vol->Contains(V(2.1, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 4.1)));
  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(2.0));

  // Genuine Trd2: x/y half widths 1->2 over half z 3. The exact volume of a
  // Trd2 is (4/3)*dz*(2*x1*y1 + x1*y2 + x2*y1 + 2*x2*y2) with half dims:
  double exact = 4.0 / 3.0 * 3.0 * (2.0 * 1.0 * 1.0 + 1.0 * 2.0 + 2.0 * 1.0 + 2.0 * 2.0 * 2.0); // = 56
  vg::LogicalVolume *lv2 = makeVolume("trap_trd2", pt_Trapezoid_new(1.0, 2.0, 1.0, 2.0, 3.0));
  vg::VPlacedVolume *vol2 = lv2->Place();
  CHECK(solidCapacity(lv2) == doctest::Approx(exact));

  CHECK(vol2->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol2->Contains(V(1.4, 1.4, 0.0))); // half widths at z=0 are 1.5
  CHECK_FALSE(vol2->Contains(V(1.6, 0.0, 0.0)));
  CHECK_FALSE(vol2->Contains(V(0.0, 0.0, 3.1)));
  CHECK(vol2->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(1.5));
}

////////////////////////////////////////////////////////////////////////////////
// (6) GenTrapezoid (G4Trap/TGeoTrap 11-parameter constructor)
TEST_CASE("solid.GenTrapezoid")
{
  // theta = phi = alpha = 0 must reduce to a plain box 8 x 6 x 4.
  // Wrapper order (Geant4 convention):
  // (dz, theta, phi, dy1, dx1, dx2, alpha1, dy2, dx3, dx4, alpha2).
  vg::LogicalVolume *lv =
      makeVolume("gentrap_box", pt_GenTrapezoid_new(2.0, 0.0, 0.0, 3.0, 4.0, 4.0, 0.0, 3.0, 4.0, 4.0, 0.0));
  vg::VPlacedVolume *vol = lv->Place();
  CHECK(solidCapacity(lv) == doctest::Approx(8.0 * 2.0 * 4.0 * 3.0)); // 2dz*2dx*2dy = 192

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(3.9, 2.9, 1.9)));
  CHECK_FALSE(vol->Contains(V(4.1, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 3.1, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 2.1)));
  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(4.0));

  // Slanted variant (the Arb8 lineage). Nonzero alpha shears the side faces:
  // the x half width interpolates linearly from 4 at z=-dz to 3 at z=+dz, so
  // at z=0 it is 3.5.
  double alpha = std::atan(0.2);
  vg::LogicalVolume *lv2 =
      makeVolume("gentrap_slant", pt_GenTrapezoid_new(2.0, 0.0, 0.0, 3.0, 4.0, 4.0, alpha, 3.0, 3.0, 3.0, alpha));
  vg::VPlacedVolume *vol2 = lv2->Place();
  // dz*((dx1+dx2+dx3+dx4)*(dy1+dy2) + (dx4+dx3-dx2-dx1)*(dy2-dy1)/3) - the
  // Geant4 cubic formula, which is the exact prismatoid volume here:
  double exact = 2.0 * ((4.0 + 4.0 + 3.0 + 3.0) * (3.0 + 3.0)); // = 168
  CHECK(solidCapacity(lv2) == doctest::Approx(exact));

  CHECK(vol2->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol2->Contains(V(2.5, 0.0, 0.0)));
  CHECK_FALSE(vol2->Contains(V(3.8, 0.0, 0.0)));
  CHECK_FALSE(vol2->Contains(V(0.0, 3.1, 0.0)));
  CHECK_FALSE(vol2->Contains(V(0.0, 0.0, 2.1)));
}

////////////////////////////////////////////////////////////////////////////////
// (7) ArbTrapezoid (GenTrap from 8 xy vertices)
TEST_CASE("solid.ArbTrapezoid")
{
  // Unit cube: 4 lower + 4 upper vertices, half height 0.5. GenTrapStruct
  // re-orients the vertex winding on its own, so either ordering works.
  double v11[2] = {-0.5, -0.5}, v12[2] = {0.5, -0.5}, v13[2] = {0.5, 0.5}, v14[2] = {-0.5, 0.5};
  double v21[2] = {-0.5, -0.5}, v22[2] = {0.5, -0.5}, v23[2] = {0.5, 0.5}, v24[2] = {-0.5, 0.5};
  vg::LogicalVolume *lv = makeVolume("arb8_cube", pt_ArbTrapezoid_new(v11, v12, v13, v14, v21, v22, v23, v24, 0.5));
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(1.0));

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(0.4, 0.4, 0.4)));
  CHECK(vol->Contains(V(0.49, -0.49, -0.49)));
  CHECK_FALSE(vol->Contains(V(0.6, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 0.6)));
  CHECK_FALSE(vol->Contains(V(1.0, 1.0, 1.0)));

  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(0.5));
}

////////////////////////////////////////////////////////////////////////////////
// (8) Cone
TEST_CASE("solid.Cone")
{
  // Wrapper order: (rmin1, rmax1, rmin2, rmax2, dz, phimin, deltaphi).
  // Frustum rmax 2 -> 4 over half z 3, solid (rmin=0), full phi:
  vg::LogicalVolume *lv = makeVolume("cone_frustum", pt_Cone_new(0.0, 2.0, 0.0, 4.0, 3.0, 0.0, 2.0 * M_PI));
  vg::VPlacedVolume *vol = lv->Place();

  double h = 6.0; // full height
  CHECK(solidCapacity(lv) == doctest::Approx(M_PI * h / 3.0 * (4.0 + 16.0 + 8.0))); // pi*h/3*(R1^2+R1R2+R2^2)

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(2.5, 0.0, 0.0))); // radius at z=0 is 3
  CHECK(vol->Contains(V(1.5, 0.0, 2.9))); // radius at z=2.9 ~ 3.97
  CHECK_FALSE(vol->Contains(V(3.5, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 3.1)));

  // From the origin radially out at z=0 the exit is at r(z=0) = 3:
  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(3.0));

  // Apex case: rmax1 = 0 collapses the -z face to a point.
  vg::LogicalVolume *lv2 = makeVolume("cone_apex", pt_Cone_new(0.0, 0.0, 0.0, 4.0, 3.0, 0.0, 2.0 * M_PI));
  vg::VPlacedVolume *vol2 = lv2->Place();
  // VecGeom bumps rmax1 by kConeTolerance=1e-7; volume stays pi*h/3*R2^2 to
  // far better than the default doctest tolerance:
  CHECK(solidCapacity(lv2) == doctest::Approx(M_PI * h / 3.0 * 16.0));

  CHECK(vol2->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol2->Contains(V(1.9, 0.0, 0.0))); // radius at z=0 is 2
  CHECK_FALSE(vol2->Contains(V(2.1, 0.0, 0.0)));
  CHECK_FALSE(vol2->Contains(V(0.0, 0.0, -3.1))); // below the apex
}

////////////////////////////////////////////////////////////////////////////////
// (9) HypeTube with zero stereo angle (Hype exoneration target)
TEST_CASE("solid.HypeTube")
{
  // Wrapper order: (rmin, rmax, innerStereo, outerStereo, halfHeight), stereo
  // in radians. stereo=0 degenerates the hyperbolas to cylinders, so the
  // solid must be identical to Tube(rmin, rmax, halfHeight, 0, 2pi).
  vg::LogicalVolume *lv = makeVolume("hype0", pt_HypeTube_new(1.0, 3.0, 0.0, 0.0, 5.0));
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(M_PI * (9.0 - 1.0) * 10.0));

  CHECK(vol->Contains(V(2.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(2.0, 0.0, 4.9)));
  CHECK(vol->Contains(V(1.5, 1.0, 0.0)));       // r = sqrt(3.25) ~ 1.80
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 0.0))); // r=0 < rmin
  CHECK_FALSE(vol->Contains(V(0.5, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(3.5, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 5.5)));

  CHECK(vol->DistanceToOut(V(2.0, 0.0, 0.0), V(1.0, 0.0, 0.0)) == doctest::Approx(1.0));
}

////////////////////////////////////////////////////////////////////////////////
// (10) Paraboloid
TEST_CASE("solid.Paraboloid")
{
  // Degenerate radii rbot=rtop: ParaboloidStruct computes fA = 2dz/(rhi^2-rlo^2)
  // (division by zero), so only the CAPACITY (which uses rlo/rhi directly:
  // V = pi*dz*(rlo^2+rhi^2)) is pinned here; containment on this shape is
  // exercised by the non-degenerate instance below instead.
  vg::LogicalVolume *lvDeg = makeVolume("paraboloid_deg", pt_Paraboloid_new(2.0, 2.0, 3.0));
  CHECK(solidCapacity(lvDeg) == doctest::Approx(M_PI * 3.0 * (4.0 + 4.0))); // = cylinder 2*pi*4*3

  // Non-degenerate: rlo=1 at z=-3, rhi=2 at z=+3. r(z)^2 is linear in z, so
  // V = pi*dz*(rlo^2 + rhi^2) holds exactly for any radii:
  vg::LogicalVolume *lv = makeVolume("paraboloid", pt_Paraboloid_new(1.0, 2.0, 3.0));
  vg::VPlacedVolume *vol = lv->Place();
  CHECK(solidCapacity(lv) == doctest::Approx(M_PI * 3.0 * (1.0 + 4.0))); // 15*pi

  // r^2(0) = 2.5 -> r(0) ~ 1.581:
  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(0.5, 0.0, 0.0)));
  CHECK(vol->Contains(V(0.0, 0.0, 2.9)));
  CHECK(vol->Contains(V(1.9, 0.0, 2.9))); // surface radius at z=2.9 ~ 1.99
  CHECK_FALSE(vol->Contains(V(1.7, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 3.1)));

  // Down the axis the exit is the flat -z cap at z=-3:
  // NOTE: DistanceToOut is only trustworthy for rlo < rhi; with rlo > rhi the
  // kernel returns negative garbage for interior points (observed -5 and
  // -1.58 from the origin), so the sane orientation is pinned here.
  CHECK(vol->DistanceToOut(V(0.0, 0.0, 0.0), V(0.0, 0.0, -1.0)) == doctest::Approx(3.0));
}

////////////////////////////////////////////////////////////////////////////////
// (11) Polycone
TEST_CASE("solid.Polycone")
{
  // Wrapper order: (sphi, dphi, planeNum, z[], rmin[], rmax[]). Two z-planes
  // with rmin=0 is exactly a cone frustum: R 2->4 over z in [-3,3], full phi.
  double z[2] = {-3.0, 3.0}, rmin[2] = {0.0, 0.0}, rmax[2] = {2.0, 4.0};
  vg::LogicalVolume *lv = makeVolume("polycone", pt_Polycone_new(0.0, 2.0 * M_PI, 2, z, rmin, rmax));
  vg::VPlacedVolume *vol = lv->Place();

  double h = 6.0;
  CHECK(solidCapacity(lv) == doctest::Approx(M_PI * h / 3.0 * (4.0 + 16.0 + 8.0))); // 56*pi

  CHECK(vol->Contains(V(0.5, 0.0, 0.0)));
  CHECK(vol->Contains(V(1.0, 0.0, 2.9)));       // rmax(2.9) ~ 3.93
  CHECK_FALSE(vol->Contains(V(4.5, 0.0, 0.0))); // rmax(0) = 3
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 3.1)));
  CHECK_FALSE(vol->Contains(V(0.5, 0.0, -3.1)));

  // Up the axis the exit is the +z plane (band check: section-based kernel):
  double d = vol->DistanceToOut(V(1.0, 0.0, 0.0), V(0.0, 0.0, 1.0));
  CHECK(d > 2.9);
  CHECK(d < 3.1);
}

////////////////////////////////////////////////////////////////////////////////
// (12) Polyhedron
TEST_CASE("solid.Polyhedron")
{
  // Wrapper order: (phiStart, phiDelta, sideCount, zPlaneCount, zPlanes[],
  // rMin[], rMax[]), angles in radians. A 4-sided full-phi prism over z in
  // [-1,1]. PROBED VecGeom convention: rMax=2 is the facet (apothem)
  // distance, the first VERTEX sits at phiStart, and the vertices are at
  // rmax/cos(pi/sideCount) = 2*sqrt(2). With phiStart=pi/4 the facet planes
  // are the axis-normal planes |x|=|y|=rmax. Regular n-gon area with
  // apothem a is n*a^2*tan(pi/n): 4*4*1 = 16, volume 16*2 = 32.
  double zp[2] = {-1.0, 1.0}, rmin[2] = {0.0, 0.0}, rmax[2] = {2.0, 2.0};
  vg::LogicalVolume *lv = makeVolume("polyhedron", pt_Polyhedron_new(M_PI / 4.0, 2.0 * M_PI, 4, 2, zp, rmin, rmax));
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(4.0 * 4.0 * 1.0 * 2.0)); // n*a^2*tan(pi/n)*h = 32

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(1.9, 0.0, 0.0)));       // inside the |x|=2 facet
  CHECK(vol->Contains(V(0.0, 1.9, 0.0)));
  CHECK(vol->Contains(V(1.4, 1.4, 0.9)));       // vertex at 2*sqrt(2) ~ 2.83
  CHECK_FALSE(vol->Contains(V(2.1, 0.0, 0.0))); // beyond the |x|=2 facet
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 1.1)));

  double d = vol->DistanceToOut(V(0.0, 0.0, 0.0), V(0.0, 0.0, 1.0));
  CHECK(d > 0.9);
  CHECK(d < 1.1);
}

////////////////////////////////////////////////////////////////////////////////
// (13) Tet
TEST_CASE("solid.Tet")
{
  // Wrapper order: (p1, p2, p3, p4), each a double[3] vertex.
  double p1[3] = {0.0, 0.0, 0.0};
  double p2[3] = {2.0, 0.0, 0.0};
  double p3[3] = {0.0, 2.0, 0.0};
  double p4[3] = {0.0, 0.0, 2.0};
  vg::LogicalVolume *lv = makeVolume("tet", pt_Tet_new(p1, p2, p3, p4));
  vg::VPlacedVolume *vol = lv->Place();

  // |det(p2-p1, p3-p1, p4-p1)| / 6 = 8/6:
  CHECK(solidCapacity(lv) == doctest::Approx(8.0 / 6.0));

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));       // a vertex
  CHECK(vol->Contains(V(0.5, 0.5, 0.5)));       // centroid, x+y+z = 1.5 < 2
  CHECK(vol->Contains(V(1.0, 0.4, 0.4)));       // positive barycentric coords
  CHECK_FALSE(vol->Contains(V(1.0, 1.0, 1.0))); // x+y+z = 3 > 2
  CHECK_FALSE(vol->Contains(V(2.1, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.5, 0.5, -0.5)));

  // From the centroid along -z the exit is the z=0 facet, 0.5 below:
  CHECK(vol->DistanceToOut(V(0.5, 0.5, 0.5), V(0.0, 0.0, -1.0)) == doctest::Approx(0.5));
}

////////////////////////////////////////////////////////////////////////////////
// (14) Ellipsoid
TEST_CASE("solid.Ellipsoid")
{
  // Wrapper order: (dx, dy, dz, zBottomCut, zTopCut) - SEMI-axes; cuts of 0
  // mean "no cut" (the getters then report -dz/+dz).
  vg::LogicalVolume *lv = makeVolume("ellipsoid", pt_Ellipsoid_new(2.0, 3.0, 5.0, 0.0, 0.0));
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(4.0 * M_PI / 3.0 * 2.0 * 3.0 * 5.0)); // 40*pi

  CHECK(vol->Contains(V(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V(1.9, 0.0, 0.0)));
  CHECK(vol->Contains(V(0.0, 2.9, 0.0)));
  CHECK(vol->Contains(V(0.0, 0.0, 4.9)));
  CHECK_FALSE(vol->Contains(V(2.1, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 5.1)));

  // The kernel approximates the distance near the surface -> band check:
  double d = vol->DistanceToOut(V(0.0, 0.0, 0.0), V(1.0, 0.0, 0.0));
  CHECK(d > 1.9);
  CHECK(d < 2.1);

  // Z-cut at +-2.5: the removed volume is
  // pi*ab/3*[(1+z1/c)^2*(2c-z1) + (1-z2/c)^2*(2c+z2)] = 2*pi*0.25*12.5*2
  // = 12.5*pi, leaving 40*pi - 12.5*pi = 27.5*pi:
  vg::LogicalVolume *lvCut = makeVolume("ellipsoid_cut", pt_Ellipsoid_new(2.0, 3.0, 5.0, -2.5, 2.5));
  vg::VPlacedVolume *volCut = lvCut->Place();
  CHECK(solidCapacity(lvCut) == doctest::Approx(40.0 * M_PI - 12.5 * M_PI));

  CHECK(volCut->Contains(V(0.0, 0.0, 2.4)));
  CHECK_FALSE(volCut->Contains(V(0.0, 0.0, 2.6)));
  CHECK_FALSE(volCut->Contains(V(0.0, 0.0, -2.6)));
}

////////////////////////////////////////////////////////////////////////////////
// (15) Tessellated (tetrahedron from 4 triangular facets)
TEST_CASE("solid.Tessellated")
{
  // Wrapper order: (faces_length, faces[], points[]) with faces a flat list
  // of [nVertices, idx1, ...] blocks and points a flat xyz array. Facet
  // vertices are ordered counter-clockwise seen from outside (outward
  // normals), as required by the tessellated Contains kernel.
  double pts[12]  = {0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0};
  size_t faces[16] = {3, 0, 2, 1, // z=0 face,   outward normal (0,0,-1)
                      3, 0, 1, 3, // y=0 face,   outward normal (0,-1,0)
                      3, 0, 3, 2, // x=0 face,   outward normal (-1,0,0)
                      3, 1, 2, 3}; // slant face, outward normal (1,1,1)/sqrt(3)
  vg::LogicalVolume *lv = makeVolume("tess_tet", pt_Tessellated_new(16, faces, pts));
  vg::VPlacedVolume *vol = lv->Place();

  // Divergence-theorem capacity over the closed facet set = |det|/6:
  CHECK(solidCapacity(lv) == doctest::Approx(1.0 / 6.0));

  CHECK(vol->Contains(V(0.25, 0.25, 0.25)));    // centroid
  CHECK(vol->Contains(V(0.2, 0.2, 0.2)));
  CHECK_FALSE(vol->Contains(V(0.4, 0.4, 0.4))); // sum = 1.2 > 1
  CHECK_FALSE(vol->Contains(V(1.0, 1.0, 1.0)));

  // From the centroid down the -z axis the exit is the z=0 facet at 0.25:
  double d = vol->DistanceToOut(V(0.25, 0.25, 0.25), V(0.0, 0.0, -1.0));
  CHECK(d > 0.2);
  CHECK(d < 0.3);
}

////////////////////////////////////////////////////////////////////////////////
// (16) Boolean subtraction: box minus concentric box = shell
TEST_CASE("solid.BooleanSubtraction")
{
  void *outer = pt_Box_new(5.0, 5.0, 5.0); // 10^3 = 1000
  void *inner = pt_Box_new(3.0, 3.0, 3.0); // 6^3 = 216
  vg::Transformation3D ident;              // must outlive the boolean volume

  vg::LogicalVolume *lv = makeVolume("shell", pt_solid_subtraction(outer, inner, &ident));
  vg::VPlacedVolume *vol = lv->Place();

  // Analytic shell volume is 1000 - 216 = 784, but the boolean Capacity() is
  // a 1e6-point MC estimate (non-deterministic), so it is not asserted here.
  CHECK(vol->Contains(V(4.0, 0.0, 0.0)));       // in outer, outside inner
  CHECK(vol->Contains(V(3.2, 0.0, 0.0)));
  CHECK(vol->Contains(V(0.0, 4.0, 4.0)));
  CHECK_FALSE(vol->Contains(V(0.0, 0.0, 0.0))); // hollow center
  CHECK_FALSE(vol->Contains(V(2.0, 0.0, 0.0))); // inside inner
  CHECK_FALSE(vol->Contains(V(5.5, 0.0, 0.0))); // outside outer

  double d = vol->DistanceToOut(V(4.0, 0.0, 0.0), V(1.0, 0.0, 0.0));
  CHECK(d > 0.9);
  CHECK(d < 1.1);
}

////////////////////////////////////////////////////////////////////////////////
// (17) Boolean intersection and union of two offset boxes
TEST_CASE("solid.BooleanIntersectionUnion")
{
  void *boxA = pt_Box_new(1.0, 1.0, 1.0); // A: x,y,z in [-1,1]
  void *boxB = pt_Box_new(1.0, 1.0, 1.0); // B shifted +1.5 in x: x in [0.5,2.5]
  vg::Transformation3D shiftB(1.5, 0.0, 0.0);

  // Overlap region: x in [0.5,1], volume 0.5*2*2 = 2.
  vg::LogicalVolume *lvI = makeVolume("inter", pt_solid_intersection(boxA, boxB, &shiftB));
  vg::VPlacedVolume *volI = lvI->Place();

  CHECK(volI->Contains(V(0.75, 0.0, 0.0)));
  CHECK(volI->Contains(V(0.6, 0.5, 0.5)));
  CHECK_FALSE(volI->Contains(V(0.0, 0.0, 0.0))); // in A only
  CHECK_FALSE(volI->Contains(V(2.0, 0.0, 0.0))); // in B only
  CHECK_FALSE(volI->Contains(V(0.4, 0.0, 0.0))); // left of the overlap

  double dI = volI->DistanceToOut(V(0.75, 0.0, 0.0), V(0.0, 0.0, 1.0));
  CHECK(dI > 0.9);
  CHECK(dI < 1.1);

  // Union covers both boxes (analytic volume 8 + 8 - 2 = 14, again not
  // asserted because boolean Capacity() is an MC estimate):
  vg::LogicalVolume *lvU = makeVolume("unio", pt_solid_union(boxA, boxB, &shiftB));
  vg::VPlacedVolume *volU = lvU->Place();

  CHECK(volU->Contains(V(0.0, 0.0, 0.0)));  // in A
  CHECK(volU->Contains(V(2.0, 0.0, 0.0)));  // in B
  CHECK(volU->Contains(V(0.75, 0.0, 0.0))); // in both
  CHECK_FALSE(volU->Contains(V(5.0, 0.0, 0.0)));
  CHECK_FALSE(volU->Contains(V(0.0, 0.0, 1.5))); // above both boxes

  // Along +y both boxes end at y=1, so the union exit is exactly 1:
  double dU = volU->DistanceToOut(V(0.0, 0.0, 0.0), V(0.0, 1.0, 0.0));
  CHECK(dU > 0.9);
  CHECK(dU < 1.1);
}

////////////////////////////////////////////////////////////////////////////////
// (18) pt_Volume_id uniqueness and pt_Volume_capacity passthrough
TEST_CASE("solid.VolumeIdAndCapacity")
{
  void *lvA = pt_Volume_new("vol_a", pt_Box_new(2.0, 3.0, 4.0));
  void *lvB = pt_Volume_new("vol_b", pt_Box_new(2.0, 3.0, 4.0)); // same shape, new LogicalVolume
  void *lvC = pt_Volume_new("vol_c", pt_Orb_new(1.0));

  unsigned idA = pt_Volume_id(lvA);
  unsigned idB = pt_Volume_id(lvB);
  unsigned idC = pt_Volume_id(lvC);

  // The passthrough must agree with LogicalVolume::id() itself:
  CHECK(idA == static_cast<vg::LogicalVolume *>(lvA)->id());

  // Every LogicalVolume gets a distinct id (this also holds across the other
  // cases in this binary, which create their volumes through the same API):
  CHECK(idA != idB);
  CHECK(idA != idC);
  CHECK(idB != idC);

  // Capacity passthrough hits the unplaced solid:
  CHECK(pt_Volume_capacity(lvA) == doctest::Approx(192.0)); // 4*6*8
  CHECK(pt_Volume_capacity(lvC) == doctest::Approx(4.0 * M_PI / 3.0));

  // Placement through the same wrapper keeps working:
  vg::VPlacedVolume *placed = static_cast<vg::LogicalVolume *>(lvA)->Place();
  REQUIRE(placed != nullptr);
  CHECK(placed->Contains(V(1.0, 1.0, 1.0)));
}
