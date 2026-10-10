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

#include <cmath>

#include "../doctest.h"

#include "PTDiskChopper.hh"
#include "PTUnitSystem.hh"

namespace pt = Prompt;

namespace {

// Generic (non axis-aligned) angles in degrees, used to place probe points
// safely away from any opening edge of the choppers below.
constexpr double g_baseAngleDeg = 7.3;
constexpr double g_angleStepDeg = 14.9;

double probeX(double radius, double angleDeg)
{
  return radius * std::sin(angleDeg * pt::const_deg2rad);
}

double probeY(double radius, double angleDeg)
{
  return radius * std::cos(angleDeg * pt::const_deg2rad);
}

} // namespace

TEST_CASE("test_diskchopper_ctor_opening_vs_slot_spacing")
{
  // Two slits -> 180 deg slot spacing: a 200 deg opening cannot fit.
  CHECK_THROWS_AS(pt::DiskChopper(200.0, 50.0, 0.0, 96.0, 2), pt::Error::CalcError);
  // Four slits -> 90 deg slot spacing: a 95 deg opening cannot fit.
  CHECK_THROWS_AS(pt::DiskChopper(95.0, 50.0, 0.0, 96.0, 4), pt::Error::CalcError);
  // An opening exactly equal to the slot spacing is accepted: the ctor
  // rejects only when the spacing is strictly smaller than the opening.
  CHECK_NOTHROW(pt::DiskChopper(180.0, 50.0, 0.0, 96.0, 2));
}

TEST_CASE("test_diskchopper_inside_radius_always_absorbed")
{
  const pt::DiskChopper chop(40.0, 50.0, 10.0, 96.0, 2);
  const double times[] = { 0.0, 1.0 / 96.0 / 3.0, -1.0 / (2.0 * 96.0), 3.7 / 96.0 };

  // 5 radii x 5 angles x 4 times = 100 points, all strictly inside the
  // disk radius: absorbed regardless of angle and time.
  for (double time : times) {
    for (int ir = 0; ir < 5; ++ir) {
      const double radius = 5.0 + 10.0 * ir; // 5..45 mm, all < 50 mm
      for (int ia = 0; ia < 5; ++ia) {
        const double ang = g_baseAngleDeg + g_angleStepDeg * ia;
        CHECK_FALSE(chop.canSurvive(probeX(radius, ang), probeY(radius, ang), time));
      }
    }
  }
}

TEST_CASE("test_diskchopper_outside_point_survives_at_some_time")
{
  const pt::DiskChopper chop(30.0, 50.0, 0.0, 96.0, 4);
  const double period = 1.0 / 96.0; // one full rotation

  // A generic point well outside the disk, at 37 deg from the +y axis.
  const double x = probeX(100.0, 37.0);
  const double y = probeY(100.0, 37.0);
  constexpr unsigned N = 2000;
  unsigned nSurvive = 0;
  for (unsigned i = 0; i < N; ++i) {
    if (chop.canSurvive(x, y, i * period / N))
      ++nSurvive;
  }
  // The opening passes the point during one rotation, but not always.
  CHECK(nSurvive > 0);
  CHECK(nSurvive < N);
  // The opening covers 30 deg of every 90 deg slit spacing, so close to
  // one third of the sampled phases should let the point through
  // (verified 664/2000 for this configuration; window is generous).
  CHECK(nSurvive > 500);
  CHECK(nSurvive < 850);
}

TEST_CASE("test_diskchopper_time_periodicity")
{
  const pt::DiskChopper chop(30.0, 50.0, 0.0, 96.0, 4);
  const double T = 1.0 / 96.0;

  // Base times are full rotations (t = k T), which keeps the opening-edge
  // angle in the well-defined non-negative regime.
  for (int it = 1; it <= 4; ++it) {
    const double time = it * T;
    for (int ia = 0; ia < 24; ++ia) {
      const double ang = g_baseAngleDeg + g_angleStepDeg * ia;
      const double x = probeX(80.0, ang);
      const double y = probeY(80.0, ang);
      const bool ref = chop.canSurvive(x, y, time);
      // Survival is periodic with the full rotation time 1/f.
      CHECK(chop.canSurvive(x, y, time + T) == ref);
      // ... and the n-slit pattern repeats n times per rotation.
      CHECK(chop.canSurvive(x, y, time + T / 4.0) == ref);
    }
  }
}

TEST_CASE("test_diskchopper_nfold_angular_symmetry")
{
  const pt::DiskChopper chop(30.0, 50.0, 0.0, 96.0, 4);
  const double T = 1.0 / 96.0;
  const double delta = 2.0 * M_PI / 4.0;

  // Rotating the probe point by one slit spacing (2pi/n) must not change
  // the survival, at any of the probed times.
  for (int it = 1; it <= 4; ++it) {
    const double time = it * T;
    for (int ia = 0; ia < 24; ++ia) {
      const double ang = g_baseAngleDeg + g_angleStepDeg * ia;
      const double x = probeX(80.0, ang);
      const double y = probeY(80.0, ang);
      const bool ref = chop.canSurvive(x, y, time);
      const double xr = x * std::cos(delta) - y * std::sin(delta);
      const double yr = x * std::sin(delta) + y * std::cos(delta);
      CHECK(chop.canSurvive(xr, yr, time) == ref);
    }
  }
}

TEST_CASE("test_diskchopper_pinned_point_table_t0_phase0")
{
  const pt::DiskChopper chop(40.0, 50.0, 0.0, 96.0, 2);

  // Reference booleans generated with an independent python
  // reimplementation of the fmod/atan2 bookkeeping. At t=0, phase=0 the
  // opening spans [-theta0/2, +theta0/2] and crosses the slot spacing
  // boundary; the probe points below stay clear of the wrapped sector,
  // so the table holds regardless of how that sector is credited.
  struct Entry
  {
    double x, y;
    bool survive;
  };
  static const Entry table[] = {
    { 0.0, 10.0, false },   // inside the disk radius
    { 30.0, 30.0, false },  // r = 42.4 mm < 50 mm
    { 10.0, 49.0, true },   // hitAngle 11.5 deg, opening is [0, 20] deg at t=0
    { 0.0, 60.0, true },    // hitAngle 0 deg
    { 10.418890660015819, 59.088465180732484, true },  // hitAngle 10 deg
    { 19.534089267429401, 56.731114535959009, true },  // hitAngle 19 deg
    { 21.502076972718015, 56.014825589832107, false }, // hitAngle 21 deg, past the edge
    { 29.999999999999996, 51.96152422706632, false },  // hitAngle 30 deg
    { 42.426406871192846, 42.426406871192853, false }, // hitAngle 45 deg
    { 59.990861709383474, 1.047144386237016, false },  // hitAngle 89 deg
    { -50.0, 20.0, false }, // hitAngle 291.8 -> 111.8 deg (mod 180)
    { 0.0, -60.0, true },   // hitAngle 180 -> 0 deg (mod 180)
  };
  for (const auto &e : table)
    CHECK(chop.canSurvive(e.x, e.y, 0.0) == e.survive);
}

TEST_CASE("test_diskchopper_negative_time_consistency")
{
  // The 60 deg phase keeps the opening-edge angle positive also for the
  // small negative times probed here.
  const pt::DiskChopper chop(30.0, 50.0, 60.0, 96.0, 4);
  const double T = 1.0 / 96.0;
  const double times[] = { -1e-6, -1e-5, -1e-4, -1e-3 };

  for (double time : times) {
    // The radial invariant holds for any sign of the time.
    CHECK_FALSE(chop.canSurvive(10.0, 20.0, time));
    CHECK_FALSE(chop.canSurvive(30.0, 30.0, time));
    // Shifting the time by one full rotation leaves survival unchanged.
    for (int ia = 0; ia < 24; ++ia) {
      const double ang = g_baseAngleDeg + g_angleStepDeg * ia;
      const double x = probeX(80.0, ang);
      const double y = probeY(80.0, ang);
      CHECK(chop.canSurvive(x, y, time + T) == chop.canSurvive(x, y, time));
    }
  }
}

TEST_CASE("test_diskchopper_zero_opening_edge_angles_only")
{
  const pt::DiskChopper chop(0.0, 50.0, 0.0, 96.0, 4);
  constexpr double r = 80.0;

  // With zero-width openings only the edge angles themselves
  // (hitAngle == phase == 0 mod the 90 deg slot spacing) can pass, and the
  // axis directions are the only points where that comparison is exact.
  CHECK(chop.canSurvive(0.0, r, 0.0));  // 0 deg
  CHECK(chop.canSurvive(r, 0.0, 0.0));  // 90 deg
  CHECK(chop.canSurvive(0.0, -r, 0.0)); // 180 deg
  CHECK(chop.canSurvive(-r, 0.0, 0.0)); // 270 deg

  // Everything strictly between the edge angles is absorbed.
  for (int ia = 0; ia < 24; ++ia) {
    const double ang = g_baseAngleDeg + g_angleStepDeg * ia;
    CHECK_FALSE(chop.canSurvive(probeX(r, ang), probeY(r, ang), 0.0));
  }
  // The radial invariant is unaffected by the opening width.
  CHECK_FALSE(chop.canSurvive(10.0, 10.0, 0.0));
}

TEST_CASE("test_diskchopper_opening_wrapped_across_zero_t0")
{
  // Single-slit phaseless chopper at T0: the opening spans
  // [-theta0/2, +theta0/2], i.e. it crosses the angular period boundary
  // and its wrapped part sits just below 2pi. The opening-edge angle is
  // negative before normalisation (C fmod keeps the dividend sign), and
  // the pre-fix code then absorbed neutrons inside that wrapped part.
  const pt::DiskChopper chop(20.0, 50.0, 0.0, 96.0, 1);
  constexpr double r = 80.0; // outside the disk radius

  // Audit case 1: inside the opening, non-wrapped side, passes.
  CHECK(chop.canSurvive(probeX(r, 5.0), probeY(r, 5.0), 0.0));
  // Audit case 2: inside the wrapped part of the opening (355 deg =
  // -5 deg); was wrongly absorbed before the edge normalisation.
  CHECK(chop.canSurvive(probeX(r, 355.0), probeY(r, 355.0), 0.0));
  // Audit case 3: just outside the wrapped edge (345 deg = -15 deg).
  CHECK_FALSE(chop.canSurvive(probeX(r, 345.0), probeY(r, 345.0), 0.0));
  // Deep inside the absorbing sector, far from every edge.
  CHECK_FALSE(chop.canSurvive(probeX(r, 175.0), probeY(r, 175.0), 0.0));
}

TEST_CASE("test_diskchopper_opening_wrap_early_source_time")
{
  // While t < (theta0/2 - phase)/omega the raw opening-edge angle stays
  // negative; at omega*t = 5 deg the normalised edge is 355 deg and the
  // opening is [355, 360) u [0, 15) deg.
  const pt::DiskChopper chop(20.0, 50.0, 0.0, 96.0, 1);
  constexpr double r = 80.0;
  const double tEdge = (5.0 * pt::const_deg2rad) / (2.0 * M_PI * 96.0);

  CHECK(chop.canSurvive(probeX(r, 0.0), probeY(r, 0.0), tEdge));
  CHECK(chop.canSurvive(probeX(r, 10.0), probeY(r, 10.0), tEdge));
  CHECK(chop.canSurvive(probeX(r, 356.0), probeY(r, 356.0), tEdge));
  CHECK_FALSE(chop.canSurvive(probeX(r, 350.0), probeY(r, 350.0), tEdge));
}

TEST_CASE("test_diskchopper_phase15_controls_unaffected")
{
  // With phase=15 deg the opening edge at T0 is +5 deg (opening
  // [5, 25] deg): no wrap is involved, so acceptance is identical before
  // and after the edge normalisation.
  const pt::DiskChopper chop(20.0, 50.0, 15.0, 96.0, 1);
  constexpr double r = 80.0;

  // Audit cases 4-5: phase-shifted controls behave as before the fix.
  CHECK(chop.canSurvive(probeX(r, 15.0), probeY(r, 15.0), 0.0));
  CHECK_FALSE(chop.canSurvive(probeX(r, 355.0), probeY(r, 355.0), 0.0));
  // Interior and exterior points of the shifted opening.
  CHECK(chop.canSurvive(probeX(r, 10.0), probeY(r, 10.0), 0.0));
  CHECK_FALSE(chop.canSurvive(probeX(r, 0.0), probeY(r, 0.0), 0.0));
  CHECK_FALSE(chop.canSurvive(probeX(r, 30.0), probeY(r, 30.0), 0.0));
}
