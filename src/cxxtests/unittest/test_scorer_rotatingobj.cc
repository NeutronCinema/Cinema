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

#include <cmath>
#include <memory>

#include "PTScorerRotatingObj.hh"
#include "PTParticle.hh"
#include "PTVector.hh"

namespace pt = Prompt;

// ScorerRotatingObj::getLinearVelocity() is private, so the rigid-rotation
// kinematics are verified through score(): a particle at rest (ekin=0) has
// zero lab velocity, hence comovingVel == -v_rot, which the scorer exposes as
//   getEffEKin()      = 0.5*|v_rot|^2*m
//   getEffDirection() = -unit(v_rot)
// All checks are pure computation on fixed kinematics, microseconds per case.

namespace
{
  const double kRotFreq = 3.0; // Hz, arbitrary

  // rigid-rotation speed |v| = 2*pi*f*rho derived from the scored eff energy
  double rotSpeedFromEff(const pt::Particle &p)
  {
    return std::sqrt(2.0 * p.getEffEKin() / p.getMass());
  }
}

TEST_CASE("rotatingobj_velocity_magnitude_is_2pi_f_rho")
{
  pt::ScorerRotatingObj scorer("mag", pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.),
                               kRotFreq, pt::const_neutron_pgd);

  pt::Particle p(0.0, pt::Vector(0., 0., 1.), pt::Vector(2., 0., 0.)); // rho = 2
  scorer.score(p);
  CHECK(rotSpeedFromEff(p) == doctest::Approx(2.0 * M_PI * kRotFreq * 2.0).epsilon(1e-12));

  // a point at half the distance must rotate at half the speed
  pt::Particle inner(0.0, pt::Vector(0., 0., 1.), pt::Vector(1., 0., 0.)); // rho = 1
  scorer.score(inner);
  CHECK(rotSpeedFromEff(inner) ==
        doctest::Approx(2.0 * M_PI * kRotFreq * 1.0).epsilon(1e-12));

  // the comoving energy of the resting particle is tiny in internal units
  // (mass in eV/(mm/s)^2), so both fills land in bin 0 with weight*surviveP
  CHECK(scorer.getHist()->getRaw()[0] == doctest::Approx(2.0)); // two fills, w=1
  CHECK(scorer.getHist()->getTotalWeight() == doctest::Approx(2.0));
  CHECK(scorer.getHist()->getOverflow() == doctest::Approx(0.0));
  CHECK(scorer.getHist()->getUnderflow() == doctest::Approx(0.0));
}

TEST_CASE("rotatingobj_velocity_is_perpendicular_to_radius_and_axis")
{
  pt::ScorerRotatingObj scorer("perp", pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.),
                               kRotFreq, pt::const_neutron_pgd);

  // generic off-axis point with a non-trivial perpendicular radius vector
  pt::Vector pos(1., 2., 0.5);
  pt::Particle p(0.0, pt::Vector(0., 0., 1.), pos);
  scorer.score(p);

  // radius vector from the rotation axis: B_perp = B - axis*(axis.B)
  pt::Vector b = pos - pt::Vector(0., 0., 0.);
  pt::Vector bPerp = b - pt::Vector(0., 0., 1.) * (pt::Vector(0., 0., 1.).dot(b));

  // effDirection == -unit(v_rot), so orthogonality of v_rot to the radius
  // vector and to the axis shows up as vanishing dot products
  const pt::Vector &vhat = p.getEffDirection();
  CHECK(vhat.dot(bPerp) == doctest::Approx(0.0).epsilon(1e-12));
  CHECK(vhat.dot(pt::Vector(0., 0., 1.)) == doctest::Approx(0.0).epsilon(1e-12));
}

TEST_CASE("rotatingobj_point_on_axis_has_no_rotation_velocity")
{
  pt::ScorerRotatingObj scorer("onaxis", pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.),
                               kRotFreq, pt::const_neutron_pgd);

  // a point exactly on the axis: v_rot = 0, so the effective kinematics of a
  // moving particle must be untouched by the scorer (0.407 eV -> bin 40 with
  // comfortable distance from the bin edge)
  pt::Particle p(0.407, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 5.));
  scorer.score(p);

  CHECK(p.getEffEKin() == doctest::Approx(0.407));
  CHECK(p.getEffDirection() == pt::Vector(0., 0., 1.));

  // comoving energy stayed inside the internal [0,1] histogram range
  CHECK(scorer.getHist()->getOverflow() == doctest::Approx(0.0));
  CHECK(scorer.getHist()->getRaw()[40] == doctest::Approx(1.0)); // 0.407 -> bin 40
}

TEST_CASE("rotatingobj_rotation_sense_follows_right_hand_rule")
{
  // +omega around +z: the point at +x moves towards +y, the point at +y
  // towards -x. With zero lab velocity the scorer reports -unit(v_rot).
  pt::ScorerRotatingObj scorer("sense", pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.),
                               kRotFreq, pt::const_neutron_pgd);

  pt::Particle onX(0.0, pt::Vector(0., 0., 1.), pt::Vector(1.5, 0., 0.));
  scorer.score(onX);
  CHECK(onX.getEffDirection().x() == doctest::Approx(0.0).epsilon(1e-12));
  CHECK(onX.getEffDirection().y() == doctest::Approx(-1.0)); // -v_hat = -y
  CHECK(onX.getEffDirection().z() == doctest::Approx(0.0).epsilon(1e-12));

  pt::Particle onY(0.0, pt::Vector(0., 0., 1.), pt::Vector(0., 1.5, 0.));
  scorer.score(onY);
  CHECK(onY.getEffDirection().x() == doctest::Approx(1.0)); // -v_hat = +x
  CHECK(onY.getEffDirection().y() == doctest::Approx(0.0).epsilon(1e-12));
  CHECK(onY.getEffDirection().z() == doctest::Approx(0.0).epsilon(1e-12));
}

TEST_CASE("rotatingobj_ctor_rejects_non_unit_axis")
{
  REQUIRE_THROWS_AS(pt::ScorerRotatingObj("bad1", pt::Vector(0., 0., 2.),
                                          pt::Vector(0., 0., 0.), kRotFreq,
                                          pt::const_neutron_pgd),
                    pt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::ScorerRotatingObj("bad2", pt::Vector(0.5, 0.5, 0.5),
                                          pt::Vector(0., 0., 0.), kRotFreq,
                                          pt::const_neutron_pgd),
                    pt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::ScorerRotatingObj("bad3", pt::Vector(1., 1., 0.),
                                          pt::Vector(0., 0., 0.), kRotFreq,
                                          pt::const_neutron_pgd),
                    pt::Error::BadInput);
}
