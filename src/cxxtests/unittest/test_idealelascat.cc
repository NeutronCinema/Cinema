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

#include "PTIdealElaScat.hh"
#include "PTUnitSystem.hh"
#include "PTRandCanonical.hh"

namespace pt = Prompt;

namespace {

// Fixed model parameters shared by all the cases below.
constexpr double g_xsBarn = 81.7;        // [barn]
constexpr double g_densityPerAa3 = 0.05; // [atoms/Aa^3]
constexpr double g_bias = 1.3;
constexpr double g_ekinTransfer = 0.5;   // [eV]

// Seeded singleton RNG. resetSeed() is needed since setSeed() throws
// BadInput if a seed was already set on the singleton.
void reseedRNG(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

} // namespace

TEST_CASE("test_idealelascat_xs_energy_independent")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);
  const double expected = g_xsBarn * pt::Unit::barn * g_bias;

  const double ekins[] = { 1e-3, 0.0253, 1.0 };
  for (double ekin : ekins)
    CHECK(model.getCrossSection(ekin) == doctest::Approx(expected));

  // The stored cross section does not depend on the probe energy at all.
  CHECK(model.getCrossSection(1.0) == model.getCrossSection(1e-3));
  CHECK(model.getCrossSection(1.0) == model.getCrossSection(100.0));

  CHECK(model.getNumberDensity() == doctest::Approx(g_densityPerAa3 / pt::Unit::Aa3));
}

TEST_CASE("test_idealelascat_xs_direction_independent")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);
  const double expected = g_xsBarn * pt::Unit::barn * g_bias;

  const pt::Vector dirs[] = { { 1.0, 0.0, 0.0 }, { 0.0, 1.0, 0.0 },
                              { 0.0, 0.0, 1.0 }, { -1.0, 2.0, -0.5 } };
  const double ekins[] = { 1e-3, 0.0253, 1.0 };
  for (double ekin : ekins) {
    for (const auto &dir : dirs)
      CHECK(model.getCrossSection(ekin, dir) == doctest::Approx(expected));
  }
}

TEST_CASE("test_idealelascat_sample_below_threshold_noop")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);

  // ekin strictly below the transfer energy: the reaction is a no-op.
  const double ekin = 0.25;
  const pt::Vector dir(0.6, 0.0, 0.8);
  const auto &res = model.sampleReaction(ekin, dir);
  CHECK(res.final_ekin == ekin);
  CHECK(res.deposition == 0.0);
  CHECK(res.final_dir == dir);
}

TEST_CASE("test_idealelascat_sample_above_threshold_ekin_transfer")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);

  const pt::Vector dir(0.0, 0.0, 1.0);
  const double ekins[] = { 0.5, 2.5, 100.0 };
  for (double ekin : ekins) {
    reseedRNG(113u);
    const auto &res = model.sampleReaction(ekin, dir);
    // final_ekin == ekin - transfer exactly (same floating point expression
    // as the implementation). The first entry pins the strict '<' of the
    // threshold comparison: ekin == transfer goes through the transfer branch.
    CHECK(res.final_ekin == ekin - g_ekinTransfer);
  }
}

TEST_CASE("test_idealelascat_sample_deposition")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);

  reseedRNG(113u);
  const double ekin = 2.5;
  const auto &res = model.sampleReaction(ekin, pt::Vector(0.0, 0.0, 1.0));
  CHECK(res.deposition == g_ekinTransfer);
  // The deposited energy is exactly the lost kinetic energy.
  CHECK(res.final_ekin + res.deposition == ekin);
}

TEST_CASE("test_idealelascat_sample_final_dir_unit_10k")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);
  reseedRNG(113u);

  const pt::Vector indir(0.0, 0.0, 1.0);
  constexpr unsigned N = 10000;
  unsigned nTransfered = 0;
  double maxDev = 0.0;
  for (unsigned i = 0; i < N; ++i) {
    const auto &res = model.sampleReaction(2.5, indir);
    ++nTransfered;
    const double dev = std::fabs(res.final_dir.mag2() - 1.0);
    if (dev > maxDev)
      maxDev = dev;
  }
  CHECK(nTransfered == N);
  CHECK(maxDev < 1e-12);
}

TEST_CASE("test_idealelascat_sample_final_dir_isotropy_10k")
{
  pt::IdealElaScat model(g_xsBarn, g_densityPerAa3, g_bias, g_ekinTransfer);
  reseedRNG(113u);

  const pt::Vector indir(0.0, 0.0, 1.0);
  constexpr unsigned N = 10000;
  double sumMu = 0.0, sumMu2 = 0.0, sumPhi = 0.0;
  unsigned nPosMu = 0;
  for (unsigned i = 0; i < N; ++i) {
    const auto &res = model.sampleReaction(2.5, indir);
    // Polar cosine along the first component, azimuth from the other two.
    const double mu = res.final_dir.x();
    double phi = std::atan2(res.final_dir.z(), res.final_dir.y());
    if (phi < 0.0)
      phi += 2.0 * M_PI;
    sumMu += mu;
    sumMu2 += mu * mu;
    sumPhi += phi;
    if (mu > 0.0)
      ++nPosMu;
  }
  const double meanMu = sumMu / N;
  const double varMu = sumMu2 / N - meanMu * meanMu;
  const double meanPhi = sumPhi / N;
  const double pi = std::acos(-1.0);

  // Uniform on the sphere: mu uniform in [-1,1] and phi uniform in [0,2pi).
  // Tolerances are several sigma of the 10k-sample means (seeded, so the
  // sampled values are deterministic).
  CHECK(std::fabs(meanMu) < 0.03);
  CHECK(varMu == doctest::Approx(1.0 / 3.0).epsilon(0.02));
  CHECK(nPosMu > 0.47 * N);
  CHECK(nPosMu < 0.53 * N);
  CHECK(meanPhi == doctest::Approx(pi).epsilon(0.032)); // ~pi +- 0.1
}
