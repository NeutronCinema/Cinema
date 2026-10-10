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

// Regression tests for the Mirror surface process:
// - the factory default of the m parameter must be 1 (like the Python
//   Mirror(m=1.0) wrapper and McStas), not 0;
// - the reflectivity is clamped at zero (the McStas falloff factor turns
//   negative beyond Qc+1/alpha) so the wall never turns into a window;
// - a russian roulette loser is absorbed instead of flying through the wall;
// - the documented threshold=0 pure weighting mode keeps working.

#include <cmath>
#include <cstdlib>
#include <memory>

#include "../doctest.h"

#include "PTMirror.hh"
#include "PTPhysicsFactory.hh"
#include "PTGeoLoader.hh"
#include "PTActiveVolume.hh"
#include "PTNeutron.hh"
#include "PTMath.hh"
#include "PTUnitSystem.hh"

namespace pt = Prompt;

namespace {

// Mirror constants fixed in the Mirror constructor (McStas 2.7 guide
// defaults), duplicated here as an independent reference.
constexpr double g_R0 = 0.99;
constexpr double g_Qc = 0.0219; // [Aa^-1]
constexpr double g_alpha = 6.07;
constexpr double g_W = 0.003;   // [Aa^-1]

// Probe energy, chosen so that a wide range of q values is reachable.
constexpr double g_ekin = 0.0253; // [eV] thermal neutron

// Reference implementation of the reflectivity the model is expected to use.
double referenceReflectivity(double m, double Q)
{
  if (m == -1.)
    return g_R0;
  return Q < g_Qc
             ? g_R0
             : 0.5 * g_R0 * (1 - std::tanh((Q - m * g_Qc) / g_W))
                   * (1 - g_alpha * (Q - g_Qc));
}

// Seeded singleton RNG. resetSeed() is needed since setSeed() throws
// BadInput if a seed was already set on the singleton.
void reseedRNG(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

// Load the small all-vacuum demo geometry once for the navigation singleton.
bool initGeometry()
{
  static bool done = false;
  if (done)
    return true;
  done = true; // never retry: reloading would collide in the singletons
  const char *path = std::getenv("CINEMAPATH");
  if (!path)
  {
    WARN("CINEMAPATH is not set, cannot load the test geometry");
    return false;
  }
  // the demo materials live under $CINEMAPATH/ncmat; the Python package
  // exports the same variable on import, a plain ctest run has to do it here
  std::string dataPath = std::string(path) + "/ncmat";
  const char *existing = std::getenv("NCRYSTAL_DATA_PATH");
  if (existing && *existing)
    dataPath += ":" + std::string(existing);
  setenv("NCRYSTAL_DATA_PATH", dataPath.c_str(), 1);
  pt::Singleton<pt::GeoLoader>::getInstance().initFromGDML(
      std::string(path) + "/gdml/simple_geo.gdml");
  return true;
}

// Locate a neutron just inside the +z world face with a grazing flight
// direction chosen such that the elastic momentum transfer equals qWanted.
// The face normal is returned for checking the specular reflection.
pt::Neutron makeNeutronAtQ(double qWanted, pt::Vector &normal)
{
  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();
  const pt::Vector pos(0., 0., 300. * pt::Unit::mm); // inside the world box
  REQUIRE_FALSE(activeVolume.locateActiveVolume(pos));
  activeVolume.getNormal(pos, normal);

  const double k0 = pt::neutronEKin2k(g_ekin);
  const double c = qWanted / (2. * k0); // |cos| between flight and normal
  REQUIRE(c <= 1.);

  pt::Vector tangent(1., 0., 0.);
  tangent = tangent - normal * tangent.dot(normal);
  tangent.normalise();
  pt::Vector dir = tangent * std::sqrt(1. - c * c) + normal * c;
  dir.normalise();
  return pt::Neutron(g_ekin, dir, pos);
}

} // namespace

TEST_CASE("test_mirrorsurface_factory_default_m_reflects")
{
  if (!initGeometry())
    return;
  reseedRNG(20260712);

  auto &factory = pt::Singleton<pt::PhysicsFactory>::getInstance();
  auto mirror = std::dynamic_pointer_cast<pt::Mirror>(
      factory.createSurfaceProcess("physics=Mirror"));
  REQUIRE(mirror);
  auto m0 = std::dynamic_pointer_cast<pt::Mirror>(
      factory.createSurfaceProcess("physics=Mirror;m=0;"));
  REQUIRE(m0);

  pt::Vector normal, normal0;
  pt::Neutron neutron = makeNeutronAtQ(1.1 * g_Qc, normal);
  const pt::Vector indir = neutron.getDirection();

  // without m= the mirror must behave like m=1 (McStas convention): above
  // the critical momentum the McStas falloff weight is applied
  mirror->sampleFinalState(neutron);
  CHECK(neutron.isAlive());
  CHECK(neutron.getWeight() ==
        doctest::Approx(referenceReflectivity(1., 1.1 * g_Qc)).epsilon(1e-8));
  CHECK(neutron.getDirection().dot(normal) ==
        doctest::Approx(-indir.dot(normal)).epsilon(1e-10));

  // explicit m=0 still works: the reflectivity collapses far below the
  // roulette threshold, and the loser is absorbed instead of being
  // transmitted with weight 1
  pt::Neutron absorbed = makeNeutronAtQ(1.1 * g_Qc, normal0);
  m0->sampleFinalState(absorbed);
  CHECK_FALSE(absorbed.isAlive());
  CHECK(absorbed.getKillType() == pt::Particle::KillType::ABSORB);
  CHECK(absorbed.getWeight() == 1.); // the loser is absorbed as is
}

TEST_CASE("test_mirrorsurface_reflectivity_clamped_loser_absorbed")
{
  if (!initGeometry())
    return;
  reseedRNG(20260713);

  const double qHigh = 1.0; // [Aa^-1] far beyond Qc+1/alpha

  // the raw McStas formula yields -0.0 here; clamped to zero the roulette
  // always loses, and the loser must be absorbed rather than transmitted
  pt::Mirror mirror(1.0); // default threshold 1e-3
  pt::Vector normal;
  pt::Neutron neutron = makeNeutronAtQ(qHigh, normal);
  mirror.sampleFinalState(neutron);
  CHECK(mirror.getEventWeight() == 0.);
  CHECK_FALSE(neutron.isAlive());
  CHECK(neutron.getKillType() == pt::Particle::KillType::ABSORB);
  CHECK(neutron.getWeight() == 1.); // absorbed as is, no reflection weight

  // a large m shifts the tanh cutoff so high that the reflectivity becomes
  // strictly negative in a band below it, which the clamp must also cover
  const double qBand = 0.25; // inside the negative band of m=10
  pt::Mirror m10(10.0);
  pt::Neutron n10 = makeNeutronAtQ(qBand, normal);
  m10.sampleFinalState(n10);
  CHECK(m10.getEventWeight() == 0.);
  CHECK_FALSE(n10.isAlive());
}

TEST_CASE("test_mirrorsurface_threshold_zero_pure_weighting")
{
  if (!initGeometry())
    return;
  reseedRNG(20260714);

  // documented workaround threshold=0 disables the roulette: every hit is
  // reflected with its weight scaled by the clamped reflectivity, even when
  // the raw formula is negative (m=10 band) and even when it is zero
  pt::Mirror m10(10.0, 0.);
  pt::Vector normal;
  pt::Neutron n10 = makeNeutronAtQ(0.25, normal);
  const pt::Vector indir10 = n10.getDirection();
  m10.sampleFinalState(n10);
  CHECK(n10.isAlive());
  CHECK(n10.getWeight() == 0.);
  CHECK(m10.getEventWeight() == 0.);
  CHECK(n10.getDirection().dot(normal) ==
        doctest::Approx(-indir10.dot(normal)).epsilon(1e-10));

  // below the critical momentum the full R0 is applied as before
  pt::Mirror mirror(1.0, 0.);
  pt::Neutron neutron = makeNeutronAtQ(0.5 * g_Qc, normal);
  const pt::Vector indir = neutron.getDirection();
  mirror.sampleFinalState(neutron);
  CHECK(neutron.isAlive());
  CHECK(neutron.getWeight() == doctest::Approx(g_R0).epsilon(1e-12));
  CHECK(neutron.getDirection().dot(normal) ==
        doctest::Approx(-indir.dot(normal)).epsilon(1e-10));
}
