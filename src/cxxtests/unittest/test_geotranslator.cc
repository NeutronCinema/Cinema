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

#include "../doctest.h"

#include "PTGeoTranslator.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

namespace {

// Component-wise vector comparison with an absolute tolerance. Used instead of
// bare doctest::Approx since Approx(0.) with an epsilon would require exact
// equality (its tolerance scales with the expected magnitude).
void checkVecNear(const pt::Vector& v, const pt::Vector& expect, double tol)
{
  CHECK(std::fabs(v.x() - expect.x()) <= tol);
  CHECK(std::fabs(v.y() - expect.y()) <= tol);
  CHECK(std::fabs(v.z() - expect.z()) <= tol);
}

// A fixed spread of probe points, including the origin, axis points and
// off-axis octant points.
std::vector<pt::Vector> probePoints()
{
  return { pt::Vector(0., 0., 0.),   pt::Vector(1., 0., 0.),
           pt::Vector(0., 1., 0.),   pt::Vector(0., 0., 1.),
           pt::Vector(1., 2., 3.),   pt::Vector(-4., 0.5, -0.25),
           pt::Vector(10., -20., 30.) };
}

// Unit directions pointing into every octant.
std::vector<pt::Vector> probeDirections()
{
  std::vector<pt::Vector> dirs;
  for (int sx = -1; sx <= 1; sx += 2)
    for (int sy = -1; sy <= 1; sy += 2)
      for (int sz = -1; sz <= 1; sz += 2)
        dirs.push_back(pt::Vector(sx, sy, sz).unit());
  dirs.push_back(pt::Vector(0., 0., 1.));
  dirs.push_back(pt::Vector(1., 0., 0.));
  return dirs;
}

constexpr double g_tol = 1e-12;

} // namespace

TEST_CASE("geotranslator_default_is_the_identity_map")
{
  pt::GeoTranslator trans;

  for (const auto& p : probePoints()) {
    checkVecNear(trans.global2Local(p), p, g_tol);
    checkVecNear(trans.local2Global(p), p, g_tol);
    // both round trip directions are the identity as well:
    checkVecNear(trans.global2Local(trans.local2Global(p)), p, g_tol);
    checkVecNear(trans.local2Global(trans.global2Local(p)), p, g_tol);
  }

  for (const auto& d : probeDirections()) {
    checkVecNear(trans.global2Local_direction(d), d, g_tol);
    checkVecNear(trans.local2Global_direction(d), d, g_tol);
  }
}

TEST_CASE("geotranslator_direction_transforms_ignore_translation")
{
  pt::GeoTranslator trans;
  const pt::Vector shift(10., -20., 30.);
  trans.getTransformMatrix().SetTranslation(shift.x(), shift.y(), shift.z());

  // directions only ever see the rotation part (identity here), never the
  // translation - not even the offset from the origin:
  for (const auto& d : probeDirections()) {
    checkVecNear(trans.global2Local_direction(d), d, g_tol);
    checkVecNear(trans.local2Global_direction(d), d, g_tol);
  }

  // sanity: the same transform does move points, so the check above can not
  // pass vacuously:
  checkVecNear(trans.global2Local(pt::Vector(0., 0., 0.)), shift, g_tol);
}

TEST_CASE("geotranslator_pure_translation_shifts_by_the_offset")
{
  pt::GeoTranslator trans;
  const pt::Vector shift(10., -20., 30.);
  trans.getTransformMatrix().SetTranslation(shift.x(), shift.y(), shift.z());

  const pt::Vector origin(0., 0., 0.);
  checkVecNear(trans.global2Local(origin), shift, g_tol);
  checkVecNear(trans.local2Global(shift), origin, g_tol);

  for (const auto& p : probePoints()) {
    checkVecNear(trans.global2Local(p), p + shift, g_tol);
    checkVecNear(trans.local2Global(p), p - shift, g_tol);
    // both round trips return the input exactly (up to rounding):
    checkVecNear(trans.global2Local(trans.local2Global(p)), p, g_tol);
    checkVecNear(trans.local2Global(trans.global2Local(p)), p, g_tol);
  }
}

TEST_CASE("geotranslator_90deg_z_rotation_maps_components_as_expected")
{
  pt::GeoTranslator trans;
  // SetRotation takes the nine matrix elements column by column:
  // (rxx,ryx,rzx, rxy,ryy,rzy, rxz,ryz,rzz), i.e. the first three args are
  // the first column (rxx,ryx,rzx) of the stored matrix. This call stores
  // M = [[0,-1,0],[1,0,0],[0,0,1]], the CCW +90deg z rotation matrix.
  trans.getTransformMatrix().SetRotation(0., 1., 0., -1., 0., 0., 0., 0., 1.);

  const pt::Vector ex(1., 0., 0.);
  const pt::Vector ey(0., 1., 0.);

  // local2Global applies M (maps x onto +y), global2Local applies M^T
  // (maps x onto -y). No translation is involved.
  checkVecNear(trans.local2Global(ex), pt::Vector(0., 1., 0.), g_tol);
  checkVecNear(trans.local2Global(ey), pt::Vector(-1., 0., 0.), g_tol);
  checkVecNear(trans.global2Local(ex), pt::Vector(0., -1., 0.), g_tol);
  checkVecNear(trans.global2Local(ey), pt::Vector(1., 0., 0.), g_tol);

  // direction transforms apply the same two matrices, translation-free:
  checkVecNear(trans.local2Global_direction(ex), pt::Vector(0., 1., 0.), g_tol);
  checkVecNear(trans.local2Global_direction(ey), pt::Vector(-1., 0., 0.), g_tol);
  checkVecNear(trans.global2Local_direction(ex), pt::Vector(0., -1., 0.), g_tol);
  checkVecNear(trans.global2Local_direction(ey), pt::Vector(1., 0., 0.), g_tol);

  // z stays untouched by a z rotation:
  const pt::Vector ez(0., 0., 1.);
  checkVecNear(trans.global2Local(ez), ez, g_tol);
  checkVecNear(trans.local2Global_direction(ez), ez, g_tol);

  // directions are still unit vectors after the transform:
  for (const auto& d : probeDirections()) {
    CHECK(std::fabs(trans.global2Local_direction(d).mag() - 1.0) <= g_tol);
    CHECK(std::fabs(trans.local2Global_direction(d).mag() - 1.0) <= g_tol);
  }
}

TEST_CASE("geotranslator_combined_rotation_and_translation_round_trips")
{
  pt::GeoTranslator trans;
  // rotation about z by +90deg via the axis-angle setter ...
  trans.getTransformMatrix().Set(vecgeom::Vector3D<double>(0., 0., 1.), 0.5 * M_PI);
  // ... composed with a translation:
  const pt::Vector shift(5., -3., 2.);
  trans.getTransformMatrix().SetTranslation(shift.x(), shift.y(), shift.z());

  // round trips stay exact for both point conventions:
  for (const auto& p : probePoints()) {
    checkVecNear(trans.global2Local(trans.local2Global(p)), p, g_tol);
    checkVecNear(trans.local2Global(trans.global2Local(p)), p, g_tol);
  }

  // direction transforms must equal the rotation-only action of the same
  // rotation (compare against a second translator carrying no translation):
  pt::GeoTranslator rotOnly;
  rotOnly.getTransformMatrix().Set(vecgeom::Vector3D<double>(0., 0., 1.), 0.5 * M_PI);
  for (const auto& d : probeDirections()) {
    checkVecNear(trans.global2Local_direction(d), rotOnly.global2Local_direction(d), g_tol);
    checkVecNear(trans.local2Global_direction(d), rotOnly.local2Global_direction(d), g_tol);
    CHECK(std::fabs(trans.global2Local_direction(d).mag() - 1.0) <= g_tol);
  }

  // explicit component spot check: global2Local(p) = shift + M^T*p with
  // M the +90deg z rotation matrix, i.e. M^T maps (1,2,3) onto (2,-1,3):
  const pt::Vector p(1., 2., 3.);
  checkVecNear(trans.global2Local(p), pt::Vector(5. + 2., -3. - 1., 2. + 3.), g_tol);
}
