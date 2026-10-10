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

// GunFactory::createGun config-string dispatch: exact dynamic type of the
// produced gun, mandatory/optional parameter handling, the unknown-gun error
// listing the valid names, and an MCPLGun round trip against a small /tmp
// file (the only case doing file IO, ~5 ms).

#include "../doctest.h"

#include "PTGunFactory.hh"
#include "PTMaxwellianGun.hh"
#include "PTSimpleThermalGun.hh"
#include "PTIsotropicGun.hh"
#include "PTUniModeratorGun.hh"
#include "PTMCPLGun.hh"
#include "PTMCPLBinaryWrite.hh"
#include "PTNeutron.hh"
#include "PTRandCanonical.hh"
#include "PTException.hh"
#include "PTVector.hh"

#include <cstdio>
#include <cmath>
#include <string>
#include <sys/types.h>
#include <unistd.h>

namespace pt = Prompt;

namespace {

// Re-seed the shared prompt RNG so statistical checks are deterministic and
// independent of the order in which doctest runs the cases.
void seedGunRng(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

} // namespace

TEST_CASE("gunfactory_maxwellian_dispatch_and_temperature")
{
  seedGunRng(20260801);
  const double temperature = 500.;
  const double kT = temperature * pt::const_boltzmann;
  std::string cfg = "gun=MaxwellianGun;src_w=100;src_h=50;src_z=-10;"
                    "slit_w=5;slit_h=10;slit_z=10;temperature=500;";
  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(cfg);
  REQUIRE(gun != nullptr);
  // exact dynamic type: the factory must not silently substitute a base gun
  CHECK(dynamic_cast<pt::MaxwellianGun *>(gun.get()) != nullptr);
  // the requested temperature only lives on as the private m_wlT, so verify
  // it through the Gamma(2,1) law of E/kT: mean E = 2kT; scale(0.) keeps the
  // epsilon a relative window despite the eV-scale magnitude of 2kT
  const unsigned n = 10000;
  double sum = 0.;
  for(unsigned i = 0; i < n; i++)
    sum += gun->generate()->getEKin();
  CHECK(sum / n == doctest::Approx(2. * kT).epsilon(0.03).scale(0.));
}

TEST_CASE("gunfactory_simplethermal_dispatch")
{
  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=SimpleThermalGun;energy=0.05;position=0,0,-500");
  REQUIRE(gun != nullptr);
  CHECK(dynamic_cast<pt::SimpleThermalGun *>(gun.get()) != nullptr);
  auto p = gun->generate();
  CHECK(p->getEKin() == doctest::Approx(0.05).epsilon(1e-12));
  CHECK(p->getPosition().z() == doctest::Approx(-500.).epsilon(1e-12));
}

TEST_CASE("gunfactory_isotropic_dispatch")
{
  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=IsotropicGun;energy=0.0253;position=0,0,-10");
  REQUIRE(gun != nullptr);
  CHECK(dynamic_cast<pt::IsotropicGun *>(gun.get()) != nullptr);
  CHECK(gun->generate()->getEKin() == doctest::Approx(0.0253).epsilon(1e-12));
}

TEST_CASE("gunfactory_missing_mandatory_param_throws")
{
  // src_w is mandatory for MaxwellianGun
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=MaxwellianGun;src_h=50;src_z=-10;"
                      "slit_w=5;slit_h=10;slit_z=10;temperature=293.15;"),
                  pt::Error::BadInput);
  // position is mandatory for SimpleThermalGun
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=SimpleThermalGun;energy=0.05"),
                  pt::Error::BadInput);
}

TEST_CASE("gunfactory_extra_param_throws")
{
  // one parameter more than the expected parCount must be rejected
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=MaxwellianGun;src_w=100;src_h=50;src_z=-10;"
                      "slit_w=5;slit_h=10;slit_z=10;temperature=293.15;"
                      "unexpected=1;"),
                  pt::Error::BadInput);
}

TEST_CASE("gunfactory_missing_gun_key_throws")
{
  CHECK_THROWS_AS(
      pt::Singleton<pt::GunFactory>::getInstance().createGun("src_w=100;"),
      pt::Error::BadInput);
}

TEST_CASE("gunfactory_unknown_gun_name_throws_with_valid_list")
{
  // unknown guns are rejected (no silent fall-back to IsotropicGun) and the
  // message lists the supported gun names
  try {
    pt::Singleton<pt::GunFactory>::getInstance().createGun("gun=NotAGun;position=0,0,0");
    CHECK_MESSAGE(false, "unknown gun name must throw");
  } catch (const pt::Error::BadInput &e) {
    std::string msg(e.what());
    CHECK(msg.find("NotAGun") != std::string::npos);
    CHECK(msg.find("MaxwellianGun") != std::string::npos);
    CHECK(msg.find("SimpleThermalGun") != std::string::npos);
    CHECK(msg.find("IsotropicGun") != std::string::npos);
    CHECK(msg.find("UniModeratorGun") != std::string::npos);
    CHECK(msg.find("MPIGun") != std::string::npos);
    CHECK(msg.find("SANSGun") != std::string::npos);
    CHECK(msg.find("MCPLGun") != std::string::npos);
  }
}

TEST_CASE("gunfactory_mcplgun_file_energies")
{
  // per-process name so parallel ctest invocations cannot collide
  std::string fn = "/tmp/cinema_cxxtest_gunfactory_" + std::to_string(getpid()) + ".mcpl";
  {
    pt::MCPLBinaryWrite w(fn, /*enable_double=*/true, /*enable_extra3double=*/false,
                          /*enable_extraUnsigned=*/true, /*compress=*/false);
    pt::Particle p1(0.0253, pt::Vector(0, 0, 1), pt::Vector(0, 0, -100));
    p1.setTime(1e-7);
    pt::Particle p2(1.0, pt::Vector(0, 0, 1), pt::Vector(0, 0, -100));
    p2.setWeight(0.5);
    p2.setTime(2e-7);
    w.write(p1);
    w.write(p2);
    w.close();
  }

  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=MCPLGun;mcplfile=" + fn + ";");
  REQUIRE(gun != nullptr);
  CHECK(dynamic_cast<pt::MCPLGun *>(gun.get()) != nullptr);
  // the gun replays the file content in order, with file energies and weights
  auto p1 = gun->generate();
  CHECK(p1->getEKin() == doctest::Approx(0.0253).epsilon(1e-10));
  CHECK(p1->getWeight() == doctest::Approx(1.0).epsilon(1e-12));
  auto p2 = gun->generate();
  CHECK(p2->getEKin() == doctest::Approx(1.0).epsilon(1e-10));
  CHECK(p2->getWeight() == doctest::Approx(0.5).epsilon(1e-12));
  // the reader was opened in repeat mode: past the end it wraps around
  auto p3 = gun->generate();
  CHECK(p3->getEKin() == doctest::Approx(0.0253).epsilon(1e-10));

  std::remove(fn.c_str());
}
