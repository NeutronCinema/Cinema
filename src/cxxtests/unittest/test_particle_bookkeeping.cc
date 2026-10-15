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

// Particle inline bookkeeping invariants: propagate-and-track semantics of
// moveForward/setEKin, the frozen initial energy, kill bookkeeping, weight
// scaling and constructor normalisation/rest-mass conventions.

#include "../doctest.h"

#include "PTParticle.hh"
#include "PTNeutron.hh"
#include "PTProton.hh"
#include "PTMath.hh"
#include "PTUnitSystem.hh"
#include "PTVector.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

TEST_CASE("particle_moveforward_position")
{
  pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(1., 2., 3.));
  p.moveForward(10.);
  // unit direction: position advances by len*dir
  CHECK(p.getPosition().x() == doctest::Approx(1.).epsilon(1e-12));
  CHECK(p.getPosition().y() == doctest::Approx(2.).epsilon(1e-12));
  CHECK(p.getPosition().z() == doctest::Approx(13.).epsilon(1e-12));

  // an oblique unit direction moves all three components
  pt::Neutron q(1.0, pt::Vector(1., 2., 2.), pt::Vector(0., 0., 0.));
  q.moveForward(6.);
  CHECK(q.getPosition().x() == doctest::Approx(2.).epsilon(1e-12));
  CHECK(q.getPosition().y() == doctest::Approx(4.).epsilon(1e-12));
  CHECK(q.getPosition().z() == doctest::Approx(4.).epsilon(1e-12));
}

TEST_CASE("particle_moveforward_time_and_step")
{
  const double ekin = 0.0253;
  const double len = 40.;
  pt::Neutron p(ekin, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  const double speed = p.calcSpeed();
  REQUIRE(speed > 0.);
  p.moveForward(len);
  CHECK(p.getStep() == doctest::Approx(len).epsilon(1e-12));
  CHECK(p.getTime() == doctest::Approx(len / speed).epsilon(1e-12));
  // a second propagation accumulates the flight time
  p.moveForward(len);
  CHECK(p.getTime() == doctest::Approx(2. * len / speed).epsilon(1e-12));
  CHECK(p.getStep() == doctest::Approx(len).epsilon(1e-12));
}

TEST_CASE("particle_moveforward_zero_length")
{
  const double ekin = 1.;
  pt::Neutron p(ekin, pt::Vector(0., 0., 1.), pt::Vector(3., 4., 5.));
  p.moveForward(2.);
  const pt::Vector posAfterMove = p.getPosition();
  const double timeAfterMove = p.getTime();
  // zero step clears the step/deposition trackers and moves nothing
  p.setDeposition(7.5);
  p.moveForward(0.);
  CHECK(p.getStep() == 0.);
  CHECK(p.getDeposition() == 0.);
  CHECK(p.getPosition().x() == doctest::Approx(posAfterMove.x()).epsilon(1e-12));
  CHECK(p.getPosition().y() == doctest::Approx(posAfterMove.y()).epsilon(1e-12));
  CHECK(p.getPosition().z() == doctest::Approx(posAfterMove.z()).epsilon(1e-12));
  CHECK(p.getTime() == doctest::Approx(timeAfterMove).epsilon(1e-12));
}

TEST_CASE("particle_setekin_delta")
{
  pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p.setEKin(0.25);
  CHECK(p.getEKin() == doctest::Approx(0.25).epsilon(1e-12));
  CHECK(p.getEnergyChange() == doctest::Approx(0.75).epsilon(1e-12));
  // an energy gain gives a negative change
  p.setEKin(1.5);
  CHECK(p.getEnergyChange() == doctest::Approx(-1.25).epsilon(1e-12));
}

TEST_CASE("particle_ekin0_frozen")
{
  const double ekin0 = 2.0;
  pt::Neutron p(ekin0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  CHECK(p.getEKin0() == doctest::Approx(ekin0).epsilon(1e-12));
  p.setEKin(0.1);
  p.setEKin(0.01);
  // the construction energy is the bookkeeping anchor and never changes
  CHECK(p.getEKin0() == doctest::Approx(ekin0).epsilon(1e-12));
  CHECK(p.getEKin() == doctest::Approx(0.01).epsilon(1e-12));
}

TEST_CASE("particle_calc_speed_consistency")
{
  const std::vector<double> energies = {1e-5, 0.0253, 1., 10., 100.};
  for(double ekin : energies)
  {
    pt::Neutron p(ekin, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    double expected = std::sqrt(2. * ekin / pt::const_neutron_mass_evc2);
    CHECK(p.calcSpeed() == doctest::Approx(expected).epsilon(1e-12));
    // and agrees with the free helper function of PTMath
    CHECK(pt::floateq(p.calcSpeed(), pt::neutronEkin2Speed(ekin)));
    // speed/energy round trip
    CHECK(pt::floateq(pt::neutronSpeed2Ekin(p.calcSpeed()), ekin));
  }
}

TEST_CASE("particle_kill_bookkeeping")
{
  pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  CHECK(p.isAlive());
  p.kill(Prompt::Particle::KillType::ABSORB);
  CHECK_FALSE(p.isAlive());
  CHECK(p.getKillType() == Prompt::Particle::KillType::ABSORB);
  // other kill types are recorded as given
  pt::Neutron q(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  q.kill(Prompt::Particle::KillType::SCORE);
  CHECK_FALSE(q.isAlive());
  CHECK(q.getKillType() == Prompt::Particle::KillType::SCORE);
}

TEST_CASE("particle_weight_and_survival_scaling")
{
  pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  CHECK(p.getWeight() == doctest::Approx(1.).epsilon(1e-12));
  CHECK(p.getSurviveP() == doctest::Approx(1.).epsilon(1e-12));
  p.scaleWeight(0.5);
  p.scaleWeight(4.);
  CHECK(p.getWeight() == doctest::Approx(2.).epsilon(1e-12));
  p.scaleSurviveP(0.3);
  p.scaleSurviveP(0.1);
  CHECK(p.getSurviveP() == doctest::Approx(0.03).epsilon(1e-12));
  // explicit setter still works alongside the scaling
  p.setWeight(0.75);
  CHECK(p.getWeight() == doctest::Approx(0.75).epsilon(1e-12));
}

TEST_CASE("particle_ctor_normalises_direction")
{
  pt::Neutron p(1.0, pt::Vector(3., 4., 0.), pt::Vector(0., 0., 0.));
  CHECK(p.getDirection().mag2() == doctest::Approx(1.).epsilon(1e-12));
  CHECK(p.getDirection().x() == doctest::Approx(0.6).epsilon(1e-12));
  CHECK(p.getDirection().y() == doctest::Approx(0.8).epsilon(1e-12));
  CHECK(p.getDirection().z() == doctest::Approx(0.).epsilon(1e-12));
  // moveForward uses the normalised direction: 5mm along (0,3,4)/5 moves 4mm in z
  pt::Neutron q(1.0, pt::Vector(0., 3., 4.), pt::Vector(0., 0., 0.));
  q.moveForward(5.);
  CHECK(q.getPosition().y() == doctest::Approx(3.).epsilon(1e-12));
  CHECK(q.getPosition().z() == doctest::Approx(4.).epsilon(1e-12));
}

TEST_CASE("particle_default_pdg_and_rest_masses")
{
  // default is a neutron at rest with the neutron mass; scale(0.) makes the
  // epsilon a pure relative window (the masses are ~1e-14 in internal units,
  // far below doctest's default scale=1 absolute floor)
  pt::Particle n;
  CHECK(n.getPDG() == pt::const_neutron_pgd);
  CHECK(n.getMass() == doctest::Approx(pt::const_neutron_mass_evc2).epsilon(1e-12).scale(0.));
  // protons carry the proton mass; only the derived Proton class assigns it,
  // a base Particle with a proton pdg would keep rest mass 0
  pt::Proton p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  CHECK(p.getPDG() == pt::const_proton_pgd);
  CHECK(p.getMass() == doctest::Approx(pt::const_proton_mass_evc2).epsilon(1e-12).scale(0.));
  // zero rest mass (e.g. a gamma-like pdg) propagates at the speed of light
  pt::Particle g(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.), 22);
  CHECK(g.getMass() == 0.);
  CHECK(g.calcSpeed() == doctest::Approx(pt::const_c).epsilon(1e-12));
  // neutron speed is the nonrelativistic sqrt(2E/m) at thermal energy
  pt::Neutron th(0.0253, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  CHECK(th.calcSpeed() < pt::const_c);
}
