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

#include "PTPhysicsModel.hh"
#include "PTRandCanonical.hh"

namespace pt = Prompt;

namespace {

// PhysicsBase is directly instantiable and carries the direction kernels
// (randIsotropicDirection / randDirectionGivenScatterMu) under test.
pt::PhysicsBase makePhysics()
{
  return pt::PhysicsBase("randdir-test", pt::const_neutron_pgd, 1e-10, 1e10);
}

// Seeded singleton RNG. resetSeed() is needed since setSeed() throws
// BadInput if a seed was already set on the singleton.
void reseedRNG(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

} // namespace

TEST_CASE("test_randdirection_isotropic_unit_norm_10k")
{
  auto phys = makePhysics();
  reseedRNG(20261010u);

  constexpr unsigned N = 10000;
  double maxDev = 0.0;
  for (unsigned i = 0; i < N; ++i) {
    const auto dir = phys.randIsotropicDirection();
    const double dev = std::fabs(dir.mag2() - 1.0);
    if (dev > maxDev)
      maxDev = dev;
  }
  CHECK(maxDev < 1e-12);
}

TEST_CASE("test_randdirection_isotropic_mean_z_10k")
{
  auto phys = makePhysics();
  reseedRNG(20261010u);

  constexpr unsigned N = 10000;
  double sumZ = 0.0;
  for (unsigned i = 0; i < N; ++i)
    sumZ += phys.randIsotropicDirection().z();
  CHECK(std::fabs(sumZ / N) < 0.02);
}

TEST_CASE("test_randdirection_isotropic_cos_uniformity_10k")
{
  auto phys = makePhysics();
  reseedRNG(20261010u);

  // Uniform on the sphere <=> z uniform in [-1,1]: Var(z) == 1/3 and
  // P(z>0) == 1/2. Tolerances are several sigma of the 10k-sample
  // estimators (seeded, so the values are deterministic).
  constexpr unsigned N = 10000;
  double sumZ = 0.0, sumZ2 = 0.0;
  unsigned nPos = 0;
  for (unsigned i = 0; i < N; ++i) {
    const double z = phys.randIsotropicDirection().z();
    sumZ += z;
    sumZ2 += z * z;
    if (z > 0.0)
      ++nPos;
  }
  const double meanZ = sumZ / N;
  const double varZ = sumZ2 / N - meanZ * meanZ;
  CHECK(varZ == doctest::Approx(1.0 / 3.0).epsilon(0.02));
  CHECK(nPos > 0.48 * N);
  CHECK(nPos < 0.52 * N);
}

TEST_CASE("test_randdirection_scatter_mu_forward_backward_exact")
{
  auto phys = makePhysics();

  // mu == 1 with a unit incident direction reproduces it exactly, mu == -1
  // its exact opposite (the random azimuthal contribution is scaled by 0).
  const pt::Vector axis(0.0, 0.6, 0.8);
  const pt::Vector diag(std::sqrt(1.0 / 3.0), std::sqrt(1.0 / 3.0), std::sqrt(1.0 / 3.0));
  const pt::Vector indirs[] = { axis, diag };
  for (const auto &indir : indirs) {
    CHECK(phys.randDirectionGivenScatterMu(1.0, indir) == indir);
    CHECK(phys.randDirectionGivenScatterMu(-1.0, indir) == -indir);
  }
}

TEST_CASE("test_randdirection_scatter_mu_cosine_1k")
{
  auto phys = makePhysics();
  reseedRNG(777u);

  const pt::Vector indir(1.0, 2.0, 3.0);
  constexpr unsigned N = 1000;
  double maxDev = 0.0;
  for (unsigned i = 0; i < N; ++i) {
    const auto res = phys.randDirectionGivenScatterMu(0.5, indir);
    const double dev = std::fabs(res.angleCos(indir) - 0.5);
    if (dev > maxDev)
      maxDev = dev;
  }
  CHECK(maxDev < 1e-12);
}

TEST_CASE("test_randdirection_scatter_mu_unit_norm_nonunit_input_1k")
{
  auto phys = makePhysics();
  reseedRNG(778u);

  // mag2 == 14, deliberately not a unit vector.
  const pt::Vector indir(1.0, 2.0, 3.0);
  constexpr unsigned N = 1000;
  double maxDev = 0.0;
  for (unsigned i = 0; i < N; ++i) {
    const auto res = phys.randDirectionGivenScatterMu(0.3, indir);
    const double dev = std::fabs(res.mag2() - 1.0);
    if (dev > maxDev)
      maxDev = dev;
  }
  CHECK(maxDev < 1e-12);
}

TEST_CASE("test_randdirection_scatter_mu_azimuthal_uniformity_1k")
{
  auto phys = makePhysics();
  reseedRNG(779u);

  // Orthonormal basis perpendicular to the incident direction, so the
  // azimuth of the scattered direction can be measured around that axis.
  const pt::Vector u = pt::Vector(1.0, 2.0, 3.0).unit();
  const pt::Vector a = pt::Vector(1.0, 0.0, 0.0).cross(u).unit();
  const pt::Vector b = u.cross(a);

  constexpr unsigned N = 1000;
  double sumCos = 0.0, sumSin = 0.0, maxCosDev = 0.0;
  for (unsigned i = 0; i < N; ++i) {
    // mu == 0 puts all the deflection into the azimuthal angle.
    const auto res = phys.randDirectionGivenScatterMu(0.0, pt::Vector(1.0, 2.0, 3.0));
    const double phi = std::atan2(res.dot(b), res.dot(a));
    sumCos += std::cos(phi);
    sumSin += std::sin(phi);
    const double dev = std::fabs(res.angleCos(u));
    if (dev > maxCosDev)
      maxCosDev = dev;
  }
  // Circular means of a uniform azimuth vanish; 5/sqrt(2N) is ~5 sigma of
  // the estimator (seeded, deterministic).
  const double tol = 5.0 / std::sqrt(2.0 * N);
  CHECK(std::fabs(sumCos / N) < tol);
  CHECK(std::fabs(sumSin / N) < tol);
  // mu == 0 must scatter orthogonally to the incident direction.
  CHECK(maxCosDev < 1e-12);
}
