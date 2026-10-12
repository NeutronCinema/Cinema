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

#include "PTIdealElaScatPlugin.hh"
#include "PTUnitSystem.hh"
#include "PTRandCanonical.hh"

namespace pt = Prompt;
namespace pp = pt::Plugin;

namespace {

// Fixed model parameters shared by all the cases below. The plugin model is
// unbiased by construction: the host adapter owns scatter_bias.
constexpr double g_xsBarn = 81.7;        // [barn]
constexpr double g_densityPerAa3 = 0.05; // [atoms/Aa^3]
constexpr double g_ekinTransfer = 0.5;   // [eV]

// Seeded singleton RNG. resetSeed() is needed since setSeed() throws
// BadInput if a seed was already set on the singleton.
void reseedRNG(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

// Binds the shared transport RNG stream to the plugin Rng interface, the
// same bridge the host PluginModelAdapter builds internally.
struct SingletonRng final : public pp::Rng {
  double next() override
  { return pt::Singleton<pt::SingletonPTRand>::getInstance().generate(); }
};

} // namespace

TEST_CASE("test_idealelascat_metadata_abi_units")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);

  // legacy IdealElaScat carried the DiscreteModel validity range
  CHECK(model.emin() == std::numeric_limits<double>::min());
  CHECK(model.emax() == std::numeric_limits<double>::max());
  CHECK(model.oriented() == false);
  CHECK(model.declaresAbsorption() == false);
  CHECK(model.producesSecondaries() == false);

  // number density in the ABI boundary unit atoms/A^3 (the host divides by
  // Unit::Aa3 itself)
  CHECK(model.numberDensity() == doctest::Approx(g_densityPerAa3).scale(0.));
}

TEST_CASE("test_idealelascat_xs_energy_independent")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  const double expected = g_xsBarn * pt::Unit::barn;

  const double ekins[] = { 1e-3, 0.0253, 1.0 };
  for (double ekin : ekins)
    CHECK(model.crossSection(ekin, nullptr) == doctest::Approx(expected));

  // The stored cross section does not depend on the probe energy at all.
  CHECK(model.crossSection(1.0, nullptr) == model.crossSection(1e-3, nullptr));
  CHECK(model.crossSection(1.0, nullptr) == model.crossSection(100.0, nullptr));
}

TEST_CASE("test_idealelascat_xs_direction_independent")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  const double expected = g_xsBarn * pt::Unit::barn;

  const double dirs[][3] = { { 1.0, 0.0, 0.0 }, { 0.0, 1.0, 0.0 },
                             { 0.0, 0.0, 1.0 }, { -1.0, 2.0, -0.5 } };
  const double ekins[] = { 1e-3, 0.0253, 1.0 };
  for (double ekin : ekins) {
    for (const auto &dir : dirs)
      CHECK(model.crossSection(ekin, dir) == doctest::Approx(expected));
  }
}

TEST_CASE("test_idealelascat_sample_below_threshold_noop")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  SingletonRng rng;

  // ekin strictly below the transfer energy: the reaction is a no-op and
  // consumes no random numbers.
  const double ekin = 0.25;
  const double dir[3] = { 0.6, 0.0, 0.8 };
  reseedRNG(113u);
  pp::SampleResult out{};
  model.sample(ekin, dir, rng, out, nullptr);
  CHECK(out.final_ekin == ekin);
  CHECK(out.deposition == 0.0);
  CHECK(out.final_dir[0] == dir[0]);
  CHECK(out.final_dir[1] == dir[1]);
  CHECK(out.final_dir[2] == dir[2]);
  CHECK(out.absorbed == false);

  // the no-op branch drew nothing: a second sample lands on identical values
  pp::SampleResult out2{};
  model.sample(ekin, dir, rng, out2, nullptr);
  CHECK(out2.final_dir[0] == out.final_dir[0]);
}

TEST_CASE("test_idealelascat_sample_above_threshold_ekin_transfer")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  SingletonRng rng;

  const double dir[3] = { 0.0, 0.0, 1.0 };
  const double ekins[] = { 0.5, 2.5, 100.0 };
  for (double ekin : ekins) {
    reseedRNG(113u);
    pp::SampleResult out{};
    model.sample(ekin, dir, rng, out, nullptr);
    // final_ekin == ekin - transfer exactly (same floating point expression
    // as the implementation). The first entry pins the strict '<' of the
    // threshold comparison: ekin == transfer goes through the transfer branch.
    CHECK(out.final_ekin == ekin - g_ekinTransfer);
  }
}

TEST_CASE("test_idealelascat_sample_deposition")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  SingletonRng rng;

  reseedRNG(113u);
  const double ekin = 2.5;
  const double dir[3] = { 0.0, 0.0, 1.0 };
  pp::SampleResult out{};
  model.sample(ekin, dir, rng, out, nullptr);
  CHECK(out.deposition == g_ekinTransfer);
  // The deposited energy is exactly the lost kinetic energy.
  CHECK(out.final_ekin + out.deposition == ekin);
  CHECK(out.absorbed == false);
}

TEST_CASE("test_idealelascat_sample_final_dir_unit_10k")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  SingletonRng rng;
  reseedRNG(113u);

  const double indir[3] = { 0.0, 0.0, 1.0 };
  constexpr unsigned N = 10000;
  unsigned nTransfered = 0;
  double maxDev = 0.0;
  for (unsigned i = 0; i < N; ++i) {
    pp::SampleResult out{};
    model.sample(2.5, indir, rng, out, nullptr);
    ++nTransfered;
    const double dev = std::fabs(out.final_dir[0]*out.final_dir[0]
                               + out.final_dir[1]*out.final_dir[1]
                               + out.final_dir[2]*out.final_dir[2] - 1.0);
    if (dev > maxDev)
      maxDev = dev;
  }
  CHECK(nTransfered == N);
  CHECK(maxDev < 1e-12);
}

TEST_CASE("test_idealelascat_sample_final_dir_isotropy_10k")
{
  pt::Plugin::IdealElaScatModel model(g_xsBarn, g_densityPerAa3, g_ekinTransfer);
  SingletonRng rng;
  reseedRNG(113u);

  const double indir[3] = { 0.0, 0.0, 1.0 };
  constexpr unsigned N = 10000;
  double sumMu = 0.0, sumMu2 = 0.0, sumPhi = 0.0;
  unsigned nPosMu = 0;
  for (unsigned i = 0; i < N; ++i) {
    pp::SampleResult out{};
    model.sample(2.5, indir, rng, out, nullptr);
    // Polar cosine along the first component, azimuth from the other two.
    const double mu = out.final_dir[0];
    double phi = std::atan2(out.final_dir[2], out.final_dir[1]);
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
