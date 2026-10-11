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
// Second solids coverage file; extends test_solids.cc with the gaps named in
// the coverage plan:
//   * Polycone with a genuine multi-z profile: capacity vs the exact
//     trapezoid-of-revolution decomposition, SafetyToIn/Out at mid-z,
//   * GenTrap (Arb8) vertex windings: CW/CCW acceptance, twisted
//     construction, the opposite-winding and crossing-segment error paths
//     (printf-based, captured via fd 1 redirection), degenerate inputs
//     (triangle, collinear quad, dz=1e-9, dz=0),
//   * Box/Tube/Cone inside/outside classification on dense 3D probe grids
//     vs analytic implicit functions (exact bool == bool checks),
//   * Transformation3D composition: A*B applied to points/directions vs
//     manually chained transforms, plus hand-derived absolute pins,
//   * boolean Capacity MC estimate within 5 sigma of the analytic volume
//     for a sphere-minus-box subtraction.
//
// All wrapper arguments follow the conventions documented in test_solids.cc
// (radians, half lengths, real (startphi, deltaphi) order for pt_Tube_new).

#include "../doctest.h"

#include "PTVecGeom.hh"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <sstream>
#include <string>
#include <unistd.h>
#include <vector>

#include "VecGeom/base/Transformation3D.h"
#include "VecGeom/base/Vector3D.h"
#include "VecGeom/volumes/LogicalVolume.h"
#include "VecGeom/volumes/PlacedVolume.h"
#include "VecGeom/volumes/UnplacedGenTrap.h"

namespace vg = VECGEOM_NAMESPACE;

namespace {

using V3 = vg::Vector3D<double>;

vg::LogicalVolume *makeVolume(const char *name, void *unplaced)
{
  return static_cast<vg::LogicalVolume *>(pt_Volume_new(name, unplaced));
}

double solidCapacity(vg::LogicalVolume *lv) { return pt_Volume_capacity(lv); }

// Build an Arb8 (UnplacedGenTrap) from bottom/top vertex ring arrays. Each
// entry is passed to pt_ArbTrapezoid_new as a double[2] vertex.
void *makeArb8(const double *bx, const double *by, const double *tx, const double *ty, double halfHeight)
{
  double v[8][2] = {{bx[0], by[0]}, {bx[1], by[1]}, {bx[2], by[2]}, {bx[3], by[3]},
                    {tx[0], ty[0]}, {tx[1], ty[1]}, {tx[2], ty[2]}, {tx[3], ty[3]}};
  return pt_ArbTrapezoid_new(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], halfHeight);
}

// Shoelace area of a 4-vertex ring (used for the independent Simpson volume).
double quadArea(const double *x, const double *y)
{
  double s = 0.0;
  for (int i = 0; i < 4; ++i) {
    int j = (i + 1) % 4;
    s += x[i] * y[j] - x[j] * y[i];
  }
  return std::fabs(s) / 2.0;
}

// Capture everything written to C stdout (fd 1, printf) and std::cout during
// fn(). The GenTrap error paths report through printf, so capturing fd 1 is
// the only way to assert on them.
template <typename F> std::string captureStdout(F fn)
{
  std::cout.flush();
  fflush(stdout);
  std::ostringstream cbuf;
  std::streambuf *oldBuf = std::cout.rdbuf(cbuf.rdbuf());
  int saved = dup(fileno(stdout));
  int pipefd[2];
  pipe(pipefd);
  dup2(pipefd[1], fileno(stdout));
  close(pipefd[1]);
  fn();
  std::cout.flush();
  fflush(stdout);
  dup2(saved, fileno(stdout));
  close(saved);
  std::cout.rdbuf(oldBuf);
  std::string out = cbuf.str();
  char buf[4096];
  ssize_t n;
  while ((n = read(pipefd[0], buf, sizeof buf)) > 0) out.append(buf, n);
  close(pipefd[0]);
  return out;
}

// Exact analytic inside test for the phi-segmented tube used below:
// rmin < r < rmax, |z| < hz, startphi < phi < startphi + deltaphi.
bool tubeAnalytic(double x, double y, double z, double rmin, double rmax, double hz, double sphi, double dphi,
                  double margin)
{
  double r  = std::hypot(x, y);
  double a  = std::atan2(y, x);
  if (a < 0) a += 2.0 * M_PI;
  double da = a - sphi;
  while (da > 2.0 * M_PI) da -= 2.0 * M_PI;
  while (da < 0) da += 2.0 * M_PI;
  return r > rmin + margin && r < rmax - margin && std::fabs(z) < hz - margin && da > margin && da < dphi - margin;
}

} // namespace

////////////////////////////////////////////////////////////////////////////////
// (1) Polycone with a genuine 3-section profile: cone / bored tube / bored
//     frustum. The meridian cross-section of each section is a trapezoid; the
//     exact volume of its solid of revolution is
//     pi*h/3*(R1^2+R1*R2+R2^2) - pi*h/3*(r1^2+r1*r2+r2^2)
//     (radii are linear in z inside a section, so the integral is exact).
TEST_CASE("solids2.PolyconeMultiZVolume")
{
  // Non-const arrays: the C wrapper takes double* planes.
  double zP[4]   = {-4.0, -1.0, 2.0, 5.0};
  double rIn[4]  = {0.0, 0.0, 1.0, 1.0};
  double rOut[4] = {1.0, 3.0, 3.0, 2.0};
  vg::LogicalVolume *lv = makeVolume("pc2", pt_Polycone_new(0.0, 2.0 * M_PI, 4, zP, rIn, rOut));
  vg::VPlacedVolume *vol = lv->Place();

  double decomposed = 0.0;
  for (int i = 0; i < 3; ++i) {
    double h = zP[i + 1] - zP[i];
    decomposed += M_PI * h / 3.0 *
                  (rOut[i] * rOut[i] + rOut[i] * rOut[i + 1] + rOut[i + 1] * rOut[i + 1]);
    decomposed -= M_PI * h / 3.0 * (rIn[i] * rIn[i] + rIn[i] * rIn[i + 1] + rIn[i + 1] * rIn[i + 1]);
  }
  // 13*pi + 26*pi + 16*pi = 55*pi: anchor the decomposition itself.
  CHECK(decomposed == doctest::Approx(55.0 * M_PI).epsilon(1e-12));
  CHECK(solidCapacity(lv) == doctest::Approx(decomposed).epsilon(1e-12));

  // Section 1 (cone R 1->3 on z in [-4,-1]; rmax(-2.5) = 2):
  CHECK(vol->Contains(V3(1.9, 0.0, -2.5)));
  CHECK_FALSE(vol->Contains(V3(2.1, 0.0, -2.5)));
  // Section 2 (outer cylinder r=3, inner cone r 0->1; rmin(0.5) = 0.5):
  CHECK(vol->Contains(V3(0.6, 0.0, 0.5)));
  CHECK_FALSE(vol->Contains(V3(0.4, 0.0, 0.5))); // inside the bore
  CHECK(vol->Contains(V3(2.9, 0.0, 0.5)));
  CHECK_FALSE(vol->Contains(V3(3.1, 0.0, 0.5)));
  // Section 3 (bore r=1, outer cone R 3->2; rmax(3.5) = 2.5):
  CHECK(vol->Contains(V3(1.5, 0.0, 3.5)));
  CHECK(vol->Contains(V3(2.4, 0.0, 3.5)));
  CHECK_FALSE(vol->Contains(V3(2.6, 0.0, 3.5)));
  CHECK_FALSE(vol->Contains(V3(0.0, 0.0, 3.5))); // axis is inside the bore here
  // Axial bounds:
  CHECK_FALSE(vol->Contains(V3(0.0, 0.0, 5.1)));
  CHECK_FALSE(vol->Contains(V3(0.0, 0.0, -4.1)));
}

////////////////////////////////////////////////////////////////////////////////
// (2) Polycone SafetyToIn/Out at mid-z heights. Each pin is the minimum
//     distance to the analytic surface set (z planes, outer walls, bore),
//     except where noted: the cone-based kernel tracks only a subset of
//     surfaces in some configurations and those limitations are pinned as
//     observed behaviour of this VecGeom.
TEST_CASE("solids2.PolyconeSafetyMidZ")
{
  double zP[4]   = {-4.0, -1.0, 2.0, 5.0};
  double rIn[4]  = {0.0, 0.0, 1.0, 1.0};
  double rOut[4] = {1.0, 3.0, 3.0, 2.0};
  vg::LogicalVolume *lv = makeVolume("pc3", pt_Polycone_new(0.0, 2.0 * M_PI, 4, zP, rIn, rOut));
  vg::VPlacedVolume *vol = lv->Place();

  // Axis point at mid height of section 1: nearest surfaces are the z planes
  // at 1.5; the slant wall is farther (6/sqrt(13) ~ 1.664).
  CHECK(vol->SafetyToOut(V3(0.0, 0.0, -2.5)) == doctest::Approx(1.5));
  // Mid-height of the solid outer-cylinder section (z=0.5, rIn=0 here):
  // the r=3 wall is the only nearby surface, so both pins are exact.
  CHECK(vol->SafetyToOut(V3(2.5, 0.0, 0.5)) == doctest::Approx(0.5));
  CHECK(vol->SafetyToOut(V3(2.0, 0.0, 0.5)) == doctest::Approx(1.0));
  // Interior of section 3: bore wall at 0.5 (true minimum; z planes 1.5).
  CHECK(vol->SafetyToOut(V3(1.5, 0.0, 3.5)) == doctest::Approx(0.5));

  // Outside points:
  CHECK(vol->SafetyToIn(V3(3.7, 0.0, 0.5)) == doctest::Approx(0.7));  // outer cylinder wall
  CHECK(vol->SafetyToIn(V3(0.0, 0.0, 3.5)) == doctest::Approx(1.0));  // axis inside the bore
  CHECK(vol->SafetyToIn(V3(0.0, 0.0, -4.5)) == doctest::Approx(0.5)); // below the full bottom disk
  CHECK(vol->SafetyToIn(V3(1.5, 0.0, 5.5)) == doctest::Approx(0.5));  // above the top annulus
  // Axis point above the bore: the kernel returns the radial bore distance
  // (1.0) although the true nearest surface is the top rim (sqrt(1.25) ~
  // 1.118) - conservative under-estimate, pinned as-is.
  CHECK(vol->SafetyToIn(V3(0.0, 0.0, 5.5)) == doctest::Approx(1.0));
}

////////////////////////////////////////////////////////////////////////////////
// (3) GenTrap accepts both vertex windings: the struct auto-reverts a
//     counter-clockwise ring to clockwise. Both orders must give identical
//     capacity and containment.
TEST_CASE("solids2.GenTrapWindingBothOrders")
{
  // Same square, once clockwise (negative shoelace) and once counter-clockwise.
  const double cw[4]  = {1.0, 1.0, -1.0, -1.0};
  const double cwy[4] = {1.0, -1.0, -1.0, 1.0};
  const double ccw[4]  = {1.0, -1.0, -1.0, 1.0};
  const double ccwy[4] = {1.0, 1.0, -1.0, -1.0};

  vg::LogicalVolume *lvCW  = makeVolume("gt_cw", makeArb8(cw, cwy, cw, cwy, 1.0));
  vg::LogicalVolume *lvCCW = makeVolume("gt_ccw", makeArb8(ccw, ccwy, ccw, ccwy, 1.0));

  CHECK(solidCapacity(lvCW) == doctest::Approx(8.0));
  CHECK(solidCapacity(lvCCW) == doctest::Approx(8.0));

  vg::VPlacedVolume *volCW  = lvCW->Place();
  vg::VPlacedVolume *volCCW = lvCCW->Place();
  for (const V3 &p : std::vector<V3>{V3(0.0, 0.0, 0.0), V3(0.9, -0.9, 0.9), V3(-0.9, 0.9, -0.9)}) {
    CHECK(volCW->Contains(p));
    CHECK(volCCW->Contains(p));
  }
  for (const V3 &p : std::vector<V3>{V3(1.1, 0.0, 0.0), V3(0.0, 0.0, 1.1)}) {
    CHECK_FALSE(volCW->Contains(p));
    CHECK_FALSE(volCCW->Contains(p));
  }
}

////////////////////////////////////////////////////////////////////////////////
// (4) Twisted GenTrap: the top ring rotated by -45 deg about z keeps the
//     winding but makes all four lateral faces non-planar, so IsPlanar()
//     flips and the volume follows the exact prismatoid (Simpson) rule
//     V = 2dz/6*(A_bottom + 4*A_middle + A_top), with the middle ring the
//     vertex-wise average. The area of the linearly interpolated ring is
//     quadratic in the interpolation parameter, which makes Simpson exact.
TEST_CASE("solids2.GenTrapTwistedPlanarity")
{
  const double sq[4]  = {1.0, 1.0, -1.0, -1.0};
  const double sqy[4] = {1.0, -1.0, -1.0, 1.0};
  // Bottom corner 0 (1,1) rotated by -45 deg lands at (sqrt(2), 0), etc.
  const double tw[4]  = {std::sqrt(2.0), 0.0, -std::sqrt(2.0), 0.0};
  const double twy[4] = {0.0, -std::sqrt(2.0), 0.0, std::sqrt(2.0)};

  auto *unTwist = static_cast<vg::UnplacedGenTrap *>(makeArb8(sq, sqy, tw, twy, 1.0));
  auto *unPlain = static_cast<vg::UnplacedGenTrap *>(makeArb8(sq, sqy, sq, sqy, 1.0));
  CHECK_FALSE(unTwist->IsPlanar());
  CHECK(unPlain->IsPlanar());

  // Independent closed form via Simpson's rule on the interpolated ring area.
  double mx[4], my[4];
  for (int i = 0; i < 4; ++i) {
    mx[i] = 0.5 * (sq[i] + tw[i]);
    my[i] = 0.5 * (sqy[i] + twy[i]);
  }
  double aBot = quadArea(sq, sqy), aMid = quadArea(mx, my), aTop = quadArea(tw, twy);
  double simpson = (2.0 * 1.0 / 6.0) * (aBot + 4.0 * aMid + aTop);
  CHECK(aBot == doctest::Approx(4.0));
  CHECK(aTop == doctest::Approx(4.0));

  vg::LogicalVolume *lv  = makeVolume("gt_twist", unTwist);
  vg::VPlacedVolume *vol = lv->Place();
  CHECK(solidCapacity(lv) == doctest::Approx(simpson).epsilon(1e-10));

  // Containment follows the interpolated ring exactly: at z=0 the local
  // polygon is the midpoint quad, whose edge m3->m0 rejects (0.9,0.9) while
  // the center stays inside.
  CHECK(vol->Contains(V3(0.0, 0.0, 0.0)));
  CHECK_FALSE(vol->Contains(V3(0.9, 0.9, 0.0)));
  CHECK_FALSE(vol->Contains(V3(0.8, 0.8, 0.0)));
  CHECK_FALSE(vol->Contains(V3(0.9, -0.9, 0.0)));
  // Near the bottom the ring is close to the unit square:
  CHECK(vol->Contains(V3(0.9, 0.9, -0.9)));
  // Near the top the ring approaches the -45-deg-rotated square, whose edge
  // x+y = 1.3435 rejects the diagonal point:
  CHECK_FALSE(vol->Contains(V3(0.9, 0.9, 0.9)));
  CHECK_FALSE(vol->Contains(V3(1.3, 0.0, 0.0)));
}

////////////////////////////////////////////////////////////////////////////////
// (5) Opposite winding (top ring reversed w.r.t. bottom): GenTrapStruct
//     prints the "opposite clockwise" ERROR to C stdout and abandons
//     initialization (the bool return is ignored by the constructor, so the
//     observable post-state is the zero-initialized vertex arrays: planar
//     flag untouched, capacity exactly 0).
TEST_CASE("solids2.GenTrapOppositeWindingError")
{
  const double cw[4]  = {1.0, 1.0, -1.0, -1.0};
  const double cwy[4] = {1.0, -1.0, -1.0, 1.0};
  // Same square but reversed ring order -> positive shoelace.
  const double rev[4]  = {1.0, -1.0, -1.0, 1.0};
  const double revy[4] = {1.0, 1.0, -1.0, -1.0};

  std::string msg;
  vg::LogicalVolume *lv = nullptr;
  void *raw             = nullptr;
  msg = captureStdout([&] {
    raw = makeArb8(cw, cwy, rev, revy, 1.0);
    lv  = makeVolume("gt_badwind", raw);
  });
  CHECK(msg.find("ERROR: Unplaced generic trap defined with opposite clockwise") != std::string::npos);

  auto *un = static_cast<vg::UnplacedGenTrap *>(raw);
  CHECK(un->IsPlanar()); // twist detection never ran on the error path
  CHECK(solidCapacity(lv) == 0.0);
}

////////////////////////////////////////////////////////////////////////////////
// (6) Self-crossing ("bowtie") bottom ring: the crossing-segment check is the
//     fatal error path here, not the convexity check.
TEST_CASE("solids2.GenTrapCrossingSegmentsError")
{
  const double bow[4]  = {-1.0, 1.0, 1.0, -1.0};
  const double bowy[4] = {-1.0, 1.0, -1.0, 1.0};

  std::string msg = captureStdout([&] {
    makeArb8(bow, bowy, bow, bowy, 1.0);
  });
  CHECK(msg.find("ERROR: Unplaced generic trap defined with crossing opposite segments") != std::string::npos);
  CHECK(msg.find("not convex") == std::string::npos);
}

////////////////////////////////////////////////////////////////////////////////
// (7) Triangle degenerate Arb8 (two coincident vertices per ring, CW ring so
//     no reversion print): supported cleanly, capacity is the exact prism
//     volume area*2dz = 1*3 = 3.
TEST_CASE("solids2.GenTrapTriangleDegenerate")
{
  // Ring (0,0) (0,1) (2,0) (0,0): v3 == v0 closes the triangle clockwise.
  const double bx[4] = {0.0, 0.0, 2.0, 0.0};
  const double by[4] = {0.0, 1.0, 0.0, 0.0};

  auto *un = static_cast<vg::UnplacedGenTrap *>(makeArb8(bx, by, bx, by, 1.5));
  CHECK(un->IsPlanar());
  vg::LogicalVolume *lv  = makeVolume("gt_tri2", un);
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == doctest::Approx(3.0).epsilon(1e-12));

  // Hypotenuse x/2 + y = 1 at every z in [-1.5, 1.5]:
  CHECK(vol->Contains(V3(0.5, 0.3, 0.0)));
  CHECK(vol->Contains(V3(1.5, 0.1, 0.0)));    // 0.85 < 1
  CHECK_FALSE(vol->Contains(V3(1.8, 0.15, 0.0))); // 1.05 > 1
  CHECK(vol->Contains(V3(0.5, 0.3, -1.4)));
  CHECK_FALSE(vol->Contains(V3(0.5, 0.3, 1.6)));
}

////////////////////////////////////////////////////////////////////////////////
// (8) Collinear zero-area quad (four distinct vertices on one line):
//     constructs without error, capacity is exactly 0, and only points on
//     the degenerate medial segment test as inside (boundary tolerance).
TEST_CASE("solids2.GenTrapCollinearFlatQuad")
{
  const double xs[4] = {-1.0, -0.3, 0.4, 1.0};
  const double ys[4] = {0.0, 0.0, 0.0, 0.0};

  auto *un = static_cast<vg::UnplacedGenTrap *>(makeArb8(xs, ys, xs, ys, 1.0));
  CHECK(un->IsPlanar());
  vg::LogicalVolume *lv  = makeVolume("gt_flat2", un);
  vg::VPlacedVolume *vol = lv->Place();

  CHECK(solidCapacity(lv) == 0.0);

  CHECK(vol->Contains(V3(0.0, 0.0, 0.0)));     // on the segment
  CHECK(vol->Contains(V3(0.0, 0.0, -0.5)));    // on the segment
  CHECK_FALSE(vol->Contains(V3(0.0, 0.5, 0.0))); // off the segment
  CHECK_FALSE(vol->Contains(V3(0.0, -0.5, 0.5)));
}

////////////////////////////////////////////////////////////////////////////////
// (9) Ultra-thin GenTrap (dz = 1e-9): the capacity stays exact
//     (area * 2dz = 8e-9) and z classification remains exact, but the
//     degenerate lateral kernel no longer discriminates xy (any xy point at
//     |z| < dz tests inside) - pinned as observed behaviour.
TEST_CASE("solids2.GenTrapUltraThin")
{
  const double sq[4]  = {1.0, 1.0, -1.0, -1.0};
  const double sqy[4] = {1.0, -1.0, -1.0, 1.0};

  vg::LogicalVolume *lv  = makeVolume("gt_thin2", makeArb8(sq, sqy, sq, sqy, 1e-9));
  vg::VPlacedVolume *vol = lv->Place();

  // doctest's default comparison carries an absolute floor (~1e-5); scale(0.)
  // restores a pure relative comparison for this 1e-9-scale volume.
  CHECK(solidCapacity(lv) == doctest::Approx(8e-9).scale(0.).epsilon(1e-9));

  CHECK(vol->Contains(V3(0.0, 0.0, 0.0)));
  CHECK(vol->Contains(V3(0.0, 0.0, 5e-10)));  // inside |z| < 1e-9
  CHECK(vol->Contains(V3(0.0, 0.0, -5e-10)));
  CHECK_FALSE(vol->Contains(V3(0.0, 0.0, 5e-9)));  // 4e-9 above the top face
  CHECK_FALSE(vol->Contains(V3(0.0, 0.0, -5e-9)));
  // xy degeneracy of the kernel: a point far outside the unit square at
  // z = 0 is still reported inside.
  CHECK(vol->Contains(V3(5.0, 5.0, 0.0)));
}

////////////////////////////////////////////////////////////////////////////////
// (10) dz = 0 is rejected with a clean std::runtime_error.
TEST_CASE("solids2.GenTrapZeroHalfHeightThrows")
{
  const double sq[4]  = {1.0, 1.0, -1.0, -1.0};
  const double sqy[4] = {1.0, -1.0, -1.0, 1.0};
  CHECK_THROWS_AS(makeArb8(sq, sqy, sq, sqy, 0.0), std::runtime_error);
}

////////////////////////////////////////////////////////////////////////////////
// (11) Box: dense 3D probe grid classified by the analytic implicit function.
//      Probes sit at least 0.04 away from every face, so the comparison is an
//      exact bool == bool with no tolerance dependence.
TEST_CASE("solids2.GridBoxImplicit")
{
  const double hx = 1.3, hy = 0.7, hz = 1.1, d = 0.06;
  vg::LogicalVolume *lv  = makeVolume("box2", pt_Box_new(hx, hy, hz));
  vg::VPlacedVolume *vol = lv->Place();

  const double xs[7] = {-hx - d, -hx + d, -hx / 2, 0.0, hx / 2, hx - d, hx + d};
  const double ys[7] = {-hy - d, -hy + d, -hy / 2, 0.0, hy / 2, hy - d, hy + d};
  const double zs[7] = {-hz - d, -hz + d, -hz / 2, 0.0, hz / 2, hz - d, hz + d};

  int inside = 0;
  for (double x : xs)
    for (double y : ys)
      for (double z : zs) {
        bool expect = std::fabs(x) < hx && std::fabs(y) < hy && std::fabs(z) < hz;
        bool got    = vol->Contains(V3(x, y, z));
        if (got) inside++;
        CHECK_MESSAGE(got == expect, "box probe (" << x << "," << y << "," << z << ") got " << got << " expect "
                                                   << expect);
      }
  CHECK(inside == 125); // 5^3 strictly interior grid nodes
}

////////////////////////////////////////////////////////////////////////////////
// (12) Tube with phi segment [0, 3pi/4]: dense (r, phi, z) grid vs the
//      analytic cylinder + half-plane classification.
TEST_CASE("solids2.GridTubePhiSegment")
{
  const double rmin = 1.0, rmax = 3.0, hz = 2.0, sphi = 0.0, dphi = 3.0 * M_PI / 4.0, d = 0.06;
  vg::LogicalVolume *lv  = makeVolume("tube2", pt_Tube_new(rmin, rmax, hz, sphi, dphi));
  vg::VPlacedVolume *vol = lv->Place();

  const double rs[7]   = {rmin - d, rmin + d, 1.5, 2.0, 2.5, rmax - d, rmax + d};
  const double phis[6] = {-d, d, M_PI / 2, dphi - d, dphi + d, 3.0 * M_PI / 2};
  const double zs[7]   = {-hz - d, -hz + d, -1.0, 0.0, 1.0, hz - d, hz + d};

  int inside = 0, total = 0;
  for (double r : rs)
    for (double a : phis)
      for (double z : zs) {
        double x = r * std::cos(a), y = r * std::sin(a);
        bool expect = tubeAnalytic(x, y, z, rmin, rmax, hz, sphi, dphi, d / 2.0);
        bool got    = vol->Contains(V3(x, y, z));
        total++;
        if (got) inside++;
        CHECK_MESSAGE(got == expect, "tube probe r=" << r << " phi=" << a << " z=" << z << " got " << got << " expect "
                                                     << expect);
      }
  CHECK(total == 294);
  CHECK(inside == 75); // 5 interior radii x 3 interior phis x 5 interior z rows
}

////////////////////////////////////////////////////////////////////////////////
// (13) Solid cone frustum (R 2 -> 4 over z in [-3,3]): grid vs rmax(z) = 3 +
//      z/3 implicit function, including rows beyond both z faces.
TEST_CASE("solids2.GridConeFrustum")
{
  const double dz = 3.0, d = 0.05;
  vg::LogicalVolume *lv  = makeVolume("cone2", pt_Cone_new(0.0, 2.0, 0.0, 4.0, dz, 0.0, 2.0 * M_PI));
  vg::VPlacedVolume *vol = lv->Place();
  CHECK(solidCapacity(lv) == doctest::Approx(M_PI * 6.0 / 3.0 * (4.0 + 8.0 + 16.0)).epsilon(1e-12));

  const double zRows[7] = {-dz - d, -dz + d, -1.5, 0.0, 1.5, dz - d, dz + d};
  const double phis[3]  = {0.2, 1.5, 3.0};
  int inside = 0;
  for (double z : zRows) {
    double zc   = std::max(-dz + 2 * d, std::min(dz - 2 * d, z)); // reference for probe radii
    double rmax = 3.0 + zc / 3.0;
    const double rs[4] = {d, rmax / 2, rmax - d, rmax + d};
    for (double r : rs)
      for (double a : phis) {
        double x = r * std::cos(a), y = r * std::sin(a);
        bool expect = std::fabs(z) < dz && r > 0.0 && r < 3.0 + z / 3.0;
        bool got = vol->Contains(V3(x, y, z));
        if (got) inside++;
        CHECK_MESSAGE(got == expect, "cone probe r=" << r << " phi=" << a << " z=" << z << " got " << got << " expect "
                                                     << expect);
      }
  }
  CHECK(inside == 45); // 5 interior z rows x 3 interior radii x 3 phis
}

////////////////////////////////////////////////////////////////////////////////
// (14) Annular phi-segmented cone (rmin 1->2, rmax 2->4, phi in [0,pi]): grid
//      vs the double implicit cone, probing both radial walls.
TEST_CASE("solids2.GridConeAnnularPhiSegment")
{
  const double dz = 3.0, d = 0.05;
  vg::LogicalVolume *lv  = makeVolume("cone3", pt_Cone_new(1.0, 2.0, 2.0, 4.0, dz, 0.0, M_PI));
  vg::VPlacedVolume *vol = lv->Place();
  // Wedge factor dphi/2pi = 1/2 applies to both the outer and inner frusta:
  // full annulus 42*pi, phi half-segment 21*pi.
  CHECK(solidCapacity(lv) ==
        doctest::Approx((M_PI * 6.0 / 3.0 * (4.0 + 8.0 + 16.0) - M_PI * 6.0 / 3.0 * (1.0 + 2.0 + 4.0)) *
                        (M_PI / (2.0 * M_PI)))
            .epsilon(1e-12));

  const double zRows[7] = {-dz - d, -dz + d, -1.5, 0.0, 1.5, dz - d, dz + d};
  const double phis[6]  = {-d, d, M_PI / 2, M_PI - d, M_PI + d, 3.0 * M_PI / 2};
  int inside = 0;
  for (double z : zRows) {
    double zc    = std::max(-dz + 2 * d, std::min(dz - 2 * d, z));
    double rmin  = 1.0 + (zc + dz) / 6.0;
    double rmax  = 2.0 + 2.0 * (zc + dz) / 6.0;
    const double rs[5] = {rmin - d, rmin + d, 0.5 * (rmin + rmax), rmax - d, rmax + d};
    for (double r : rs)
      for (double a : phis) {
        double x = r * std::cos(a), y = r * std::sin(a);
        bool expect = false;
        if (std::fabs(z) < dz) {
          double rTmin = 1.0 + (z + dz) / 6.0;
          double rTmax = 2.0 + 2.0 * (z + dz) / 6.0;
          double aa    = std::atan2(y, x);
          if (aa < 0) aa += 2.0 * M_PI;
          expect = r > rTmin && r < rTmax && aa > 0.0 && aa < M_PI;
        }
        bool got = vol->Contains(V3(x, y, z));
        if (got) inside++;
        CHECK_MESSAGE(got == expect, "annular cone probe r=" << r << " phi=" << a << " z=" << z << " got " << got
                                                             << " expect " << expect);
      }
  }
  CHECK(inside == 45);
}

////////////////////////////////////////////////////////////////////////////////
// (15) Transformation3D composition: (A*B).Transform must equal the manual
//      chain A.Transform(B.Transform(.)) for points and directions, with
//      hand-derived absolute pins. A: translate(3,-2,5) + matrix mapping
//      e_x->e_y, e_y->-e_x; B: translate(1,1,-4) + matrix mapping
//      e_y->e_z, e_z->-e_y. The 9 rotation components are given in the
//      (rxx, ryx, rzx, rxy, ryy, rzy, rxz, ryz, rzz) order of SetRotation.
TEST_CASE("solids2.TransformComposition")
{
  const double rz[9] = {0, 1, 0, -1, 0, 0, 0, 0, 1};
  const double rx[9] = {1, 0, 0, 0, 0, 1, 0, -1, 0};
  vg::Transformation3D ta(3.0, -2.0, 5.0, rz[0], rz[1], rz[2], rz[3], rz[4], rz[5], rz[6], rz[7], rz[8]);
  vg::Transformation3D tb(1.0, 1.0, -4.0, rx[0], rx[1], rx[2], rx[3], rx[4], rx[5], rx[6], rx[7], rx[8]);

  // Absolute convention pin: local = R*(p - t) with the matrices above.
  V3 pa = ta.Transform(V3(5.0, 1.0, 7.0));
  CHECK(pa.x() == doctest::Approx(-3.0));
  CHECK(pa.y() == doctest::Approx(2.0));
  CHECK(pa.z() == doctest::Approx(2.0));

  const V3 p(0.7, -1.3, 2.2);
  V3 composed  = (ta * tb).Transform(p);
  V3 chained   = ta.Transform(tb.Transform(p));
  // Hand derivation: B gives (-0.3,-6.2,-2.3); A gives (4.2,-3.3,-7.3).
  CHECK(composed.x() == doctest::Approx(4.2).epsilon(1e-10));
  CHECK(composed.y() == doctest::Approx(-3.3).epsilon(1e-10));
  CHECK(composed.z() == doctest::Approx(-7.3).epsilon(1e-10));
  CHECK((composed - chained).Mag() < 1e-12);

  // Directions: rotation only, translations must not leak in. Hand: B maps
  // (1,2,3) -> (1,-3,2); A maps that to (3,1,2).
  V3 dComp = (ta * tb).TransformDirection(V3(1.0, 2.0, 3.0));
  CHECK(dComp.x() == doctest::Approx(3.0).epsilon(1e-12));
  CHECK(dComp.y() == doctest::Approx(1.0).epsilon(1e-12));
  CHECK(dComp.z() == doctest::Approx(2.0).epsilon(1e-12));
  V3 dChain = ta.TransformDirection(tb.TransformDirection(V3(1.0, 2.0, 3.0)));
  CHECK((dComp - dChain).Mag() < 1e-12);

  // Order matters: the reversed product gives (-1.7,-1.2,-3.3) here.
  V3 wrong = (tb * ta).Transform(p);
  CHECK(wrong.x() == doctest::Approx(-1.7).epsilon(1e-10));
  CHECK(wrong.y() == doctest::Approx(-1.2).epsilon(1e-10));
  CHECK(wrong.z() == doctest::Approx(-3.3).epsilon(1e-10));

  // Round trip through the inverse:
  V3 back = (ta * tb).InverseTransform(composed);
  CHECK((back - p).Mag() < 1e-9);
}

////////////////////////////////////////////////////////////////////////////////
// (16) operator*= accumulation, the identity shortcut and the Euler-angle
//      constructor (which takes DEGREES).
TEST_CASE("solids2.TransformOperatorTimesEquals")
{
  const double rz[9] = {0, 1, 0, -1, 0, 0, 0, 0, 1};
  const double rx[9] = {1, 0, 0, 0, 0, 1, 0, -1, 0};
  vg::Transformation3D tb(1.0, 1.0, -4.0, rx[0], rx[1], rx[2], rx[3], rx[4], rx[5], rx[6], rx[7], rx[8]);

  // acc = [translate(0.5) + rz90] accumulated with tb: chaining gives
  // B(2,3,4) = (1,-8,2), then translate-rotate gives (8, 0.5, 2).
  vg::Transformation3D acc(0.5, 0.0, 0.0, rz[0], rz[1], rz[2], rz[3], rz[4], rz[5], rz[6], rz[7], rz[8]);
  acc *= tb;
  V3 p = acc.Transform(V3(2.0, 3.0, 4.0));
  CHECK(p.x() == doctest::Approx(8.0).epsilon(1e-10));
  CHECK(p.y() == doctest::Approx(0.5).epsilon(1e-10));
  CHECK(p.z() == doctest::Approx(2.0).epsilon(1e-10));

  // Composing with the identity is a no-op (fast path returns a copy).
  vg::Transformation3D ta(3.0, -2.0, 5.0, rz[0], rz[1], rz[2], rz[3], rz[4], rz[5], rz[6], rz[7], rz[8]);
  vg::Transformation3D ident;
  CHECK((ta * ident).ApproxEqual(ta, 1e-12));
  CHECK((ident * ta).ApproxEqual(ta, 1e-12));

  // Euler constructor: angles in degrees; theta=90 maps (0,0,1)->(0,1,0) and
  // leaves (1,0,0) fixed.
  vg::Transformation3D te(0.0, 0.0, 0.0, 0.0, 90.0, 0.0);
  V3 q1 = te.Transform(V3(0.0, 0.0, 1.0));
  V3 q2 = te.Transform(V3(1.0, 0.0, 0.0));
  CHECK(q1.x() == doctest::Approx(0.0).epsilon(1e-12));
  CHECK(q1.y() == doctest::Approx(1.0));
  CHECK(q1.z() == doctest::Approx(0.0).epsilon(1e-12)); // cos(90 deg) leaves ~6e-17
  CHECK(q2.x() == doctest::Approx(1.0));
  CHECK(q2.y() == doctest::Approx(0.0).epsilon(1e-12));
  CHECK(q2.z() == doctest::Approx(0.0).epsilon(1e-12));
}

////////////////////////////////////////////////////////////////////////////////
// (17) Boolean subtraction capacity: UnplacedBooleanVolume::Capacity() runs a
//      one-shot MC estimate with N = 1e6 uniform samples over the left
//      solid's bounding box ([0.5*(upper+lower) +- 0.5*(upper-lower)], i.e.
//      the [-3,3]^3 sphere box, ref volume 8*3*3*3 = 216). The estimator is
//      binomial, so sigma = Vbox*sqrt(p*(1-p)/N) with p = V/Vbox, and the
//      estimate must agree with the analytic 36*pi - 8 within 5 sigma.
TEST_CASE("solids2.BooleanCapacitySphereMinusBox")
{
  void *sphere = pt_Sphere_new(0.0, 3.0, 0.0, 2.0 * M_PI, 0.0, M_PI);
  void *box    = pt_Box_new(1.0, 1.0, 1.0);
  vg::Transformation3D ident; // must outlive the boolean volume

  vg::LogicalVolume *lv  = makeVolume("sph_box", pt_solid_subtraction(sphere, box, &ident));
  double analytic        = 4.0 * M_PI / 3.0 * 27.0 - 8.0; // 36*pi - 8
  double vbox            = 8.0 * 3.0 * 3.0 * 3.0;
  double p               = analytic / vbox;
  double sigma           = vbox * std::sqrt(p * (1.0 - p) / 1000000.0);
  double estimated       = solidCapacity(lv);

  CHECK(sigma == doctest::Approx(0.10796).epsilon(1e-4));
  CHECK(std::fabs(estimated - analytic) < 5.0 * sigma);
}
