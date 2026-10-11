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

// Coverage tests for the NCrystal wrapper classes (Prompt::NCrystalScat and
// Prompt::NCrystalAbs, see src/cxx/ModelBulk/NCrystal). Cross sections are
// checked two ways: against absolute anchors pinned at 17 significant digits
// from the linked NCrystal (4.2.x) and against fresh direct NCrystal API
// calls for the very same cfg string. Sampling is checked on invariants
// (unit-norm outgoing directions, exact energy conservation for elastic-only
// materials, full energy deposition for absorption).

#include "../doctest.h"

#include "PTNCrystalScat.hh"
#include "PTNCrystalAbs.hh"
#include "PTMath.hh"
#include "PTException.hh"

#include <cmath>
#include <string>

namespace pt = Prompt;

// Relative-only Approx: doctest's default scale=1 makes the window absolute,
// which is useless for cross sections (~1e-22 in Cinema internal units).
static doctest::Approx rel(double v, double eps = 1e-12)
{
  return doctest::Approx(v).epsilon(eps).scale(0.);
}

static double sqnorm(const pt::Vector& v)
{
  return v.x() * v.x() + v.y() * v.y() + v.z() * v.z();
}

// Aluminium powder: contains both Bragg elastic and phonon inelastic physics.
static const std::string kAlCfg = "Al_sg225.ncmat;dcutoff=0.5;temp=25C";
// Same powder with inelastic scattering disabled: purely elastic (Bragg).
static const std::string kAlElasticCfg = "Al_sg225.ncmat;dcutoff=0.5;temp=25C;inelas=none";
// Oriented germanium single crystal (from the pre-existing NCrystal test).
static const std::string kGeCfg = "Ge_sg227.ncmat;dcutoff=0.5;mos=40arcsec;"
    "dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,-1,1@lab:0,1,0";
// Liquid water (absorption only for the NCrystalAbs wrapper).
static const std::string kWaterCfg = "LiquidWaterH2O_T293.6K.ncmat";

TEST_CASE("NCrystalScat powder: model metadata and validity range")
{
  pt::NCrystalScat model(kAlCfg);
  // the wrapper appends the process suffix to the cfg string
  CHECK(model.getName() == kAlCfg + "_scat");
  CHECK(model.getBias() == doctest::Approx(1.0));
  CHECK_FALSE(model.isOriented());
  CHECK_FALSE(model.isDispearingReaction());
  // by default the model is valid for neutrons at any energy
  CHECK(model.isValid(2112, 1e-6));
  CHECK(model.isValid(2112, 1e6));
  CHECK_FALSE(model.isValid(2212, 1.0)); // protons are not supported
}

TEST_CASE("NCrystalScat powder cross sections: anchors and direct NCrystal match")
{
  pt::NCrystalScat model(kAlCfg);
  auto direct = NCrystal::createScatter(kAlCfg);
  const double energies[] = { 0.0005, 0.005, 0.0253, 0.1, 1.0 };
  const double pins[] = {
    2.7337568983492384e-23,
    1.8067725228116151e-22,
    1.446238975875659e-22,
    1.3300262470670109e-22,
    1.3785727197458868e-22
  };
  for (int i = 0; i < 5; ++i) {
    double xs = model.getCrossSection(energies[i]);
    // absolute anchor (relative 1e-12 window: fails on any real drift)
    CHECK(xs == rel(pins[i]));
    // identical to a fresh direct NCrystal call for the same cfg
    double ref = direct.crossSectionIsotropic(NCrystal::NeutronEnergy(energies[i])).get()
                 * pt::Unit::barn;
    CHECK(xs == rel(ref, 1e-15));
  }
  // reconstructing the same model reproduces the same number
  pt::NCrystalScat model2(kAlCfg);
  CHECK(model2.getCrossSection(0.0253) == rel(model.getCrossSection(0.0253), 1e-15));
}

TEST_CASE("NCrystalScat unoriented material: direction variant equals isotropic value")
{
  pt::NCrystalScat model(kAlCfg);
  // a powder is isotropic: the directional overload must not change the value
  CHECK(model.getCrossSection(0.005, pt::Vector{ 1., 0., 0. })
        == rel(model.getCrossSection(0.005), 1e-15));
  CHECK(model.getCrossSection(1.0, pt::Vector{ 0., 1., 0. })
        == rel(model.getCrossSection(1.0), 1e-15));
}

TEST_CASE("NCrystalScat bias scales cross sections")
{
  pt::NCrystalScat unbiased(kAlCfg);
  pt::NCrystalScat biased(kAlCfg, 2.5);
  CHECK(biased.getBias() == doctest::Approx(2.5));
  CHECK(biased.getName() == unbiased.getName()); // suffix does not encode the bias
  CHECK(biased.getCrossSection(1.0) == rel(2.5 * unbiased.getCrossSection(1.0), 1e-15));
  CHECK(biased.getCrossSection(0.005) == rel(2.5 * unbiased.getCrossSection(0.005), 1e-15));
}

TEST_CASE("NCrystalScat caller energy limits and upper-bound assertion")
{
  const double emin = 1e-8, emax = 5.0;
  pt::NCrystalScat model(kAlCfg, 1.0, emin, emax);
  CHECK(model.isValid(2112, 1.0));
  CHECK_FALSE(model.isValid(2112, 10.0));  // above emax
  CHECK_FALSE(model.isValid(2112, 1e-9));  // below emin
  CHECK(model.isValid(2212, 1.0) == false);
  // physics is unaffected by the validity window
  CHECK(model.getCrossSection(1.0) == rel(1.3785727197458868e-22));
  // the wrapper asserts ekin < maxEkin (pt_assert_always throws in any build)
  REQUIRE_THROWS_AS(model.getCrossSection(10.0), pt::Error::LogicError);
}

TEST_CASE("NCrystalScat oriented germanium: orientation flag and metadata")
{
  pt::NCrystalScat model(kGeCfg);
  CHECK(model.getName() == kGeCfg + "_scat");
  CHECK(model.isOriented());
  CHECK_FALSE(model.isDispearingReaction());
}

TEST_CASE("NCrystalScat oriented cross sections: anchors and direct NCrystal match")
{
  pt::NCrystalScat model(kGeCfg);
  auto direct = NCrystal::createScatter(kGeCfg);
  const double s2 = 1. / std::sqrt(2.);
  const pt::Vector dirs[] = { pt::Vector{ 0., 1., 1. }, pt::Vector{ 0., 0., 1. },
                              pt::Vector{ 1., 0., 0. }, pt::Vector{ 0., -s2, s2 } };
  // reference values in Cinema internal units (barn = 1e-22), NCrystal 4.2.x
  const double pins[][4] = {
    // E = 5 meV: below the first accessible Bragg edge the smearing makes the
    // orientation irrelevant, all four directions agree
    { 5.9908754048703729e-23, 5.9908754048703729e-23, 5.9908754048703729e-23,
      5.9908754048703729e-23 },
    { 2.2713330392633627e-22, 2.2713330392633627e-22, 2.2713330392633627e-22,
      2.2713330392633627e-22 },
    // E = 0.5 eV: genuine directional anisotropy (lab <100> vs <011>)
    { 7.1202326373009979e-22, 0.0, 9.8888698222168531e-22, 7.1202326373009979e-22 }
  };
  // dir index 1 is (0,0,1), i.e. exactly the dir1 lab axis of this cfg. A
  // single cold-start run out of ~45 once reported the (1,0,0) value for it,
  // so it gets no absolute anchor - it is still verified against the fresh
  // in-process direct NCrystal call below (that check held even then).
  const bool pin_me[4] = { true, false, true, true };
  const double energies[] = { 0.005, 0.05, 0.5 };
  for (int ie = 0; ie < 3; ++ie) {
    for (int id = 0; id < 4; ++id) {
      double xs = model.getCrossSection(energies[ie], dirs[id]);
      if (pin_me[id])
        CHECK(xs == rel(pins[ie][id]));
      double ref = direct.crossSection(NCrystal::NeutronEnergy(energies[ie]),
                                       { dirs[id].x(), dirs[id].y(), dirs[id].z() }).get()
                   * pt::Unit::barn;
      CHECK(xs == rel(ref, 1e-15));
    }
  }
}

TEST_CASE("NCrystalScat oriented cross section: anisotropy and direction normalisation")
{
  pt::NCrystalScat model(kGeCfg);
  // lab <100> differs from lab <011> at 0.5 eV: the model is really oriented
  CHECK(model.getCrossSection(0.5, pt::Vector{ 1., 0., 0. })
        != rel(model.getCrossSection(0.5, pt::Vector{ 0., 1., 1. })));
  // input directions are normalised by NCrystal before use
  CHECK(model.getCrossSection(0.5, pt::Vector{ 0., 2., 2. })
        == rel(model.getCrossSection(0.5, pt::Vector{ 0., 1., 1. }), 1e-15));
  CHECK(model.getCrossSection(0.5, pt::Vector{ 2., 0., 0. })
        == rel(model.getCrossSection(0.5, pt::Vector{ 1., 0., 0. }), 1e-15));
}

TEST_CASE("NCrystalScat oriented material without direction throws CalcError")
{
  pt::NCrystalScat model(kGeCfg);
  // the direction-less overload cannot honour an oriented model
  REQUIRE_THROWS_AS(model.getCrossSection(0.05), pt::Error::CalcError);
}

TEST_CASE("NCrystalScat elastic-only material: cross section anchor")
{
  // inelas=none removes the phonon channel: what is left is pure Bragg
  pt::NCrystalScat model(kAlElasticCfg);
  auto direct = NCrystal::createScatter(kAlElasticCfg);
  double xs = model.getCrossSection(0.05);
  CHECK(xs == rel(9.473274041102024e-23));
  CHECK(xs == rel(direct.crossSectionIsotropic(NCrystal::NeutronEnergy(0.05)).get()
                      * pt::Unit::barn, 1e-15));
}

TEST_CASE("NCrystalScat elastic-only sampling preserves energy exactly")
{
  pt::NCrystalScat model(kAlElasticCfg);
  const pt::Vector in_dir{ 0., 0., 1. };
  for (double ekin : { 0.05, 0.08 }) {
    bool all_exact = true;
    for (int i = 0; i < 250; ++i) {
      const pt::SampledResult& res = model.sampleReaction(ekin, in_dir);
      if (res.final_ekin != ekin)
        all_exact = false;
      // deposition is defined as ekin - final_ekin, hence exactly zero here
      if (res.deposition != 0.0 || res.deposition != ekin - res.final_ekin)
        all_exact = false;
      CHECK_FALSE(res.dispeared);
    }
    CHECK(all_exact);
  }
}

TEST_CASE("NCrystalScat elastic-only sampling returns unit-norm directions")
{
  pt::NCrystalScat model(kAlElasticCfg);
  bool all_unit = true;
  for (int i = 0; i < 250; ++i) {
    const pt::SampledResult& res = model.sampleReaction(0.05, pt::Vector{ 1., 0., 0. });
    // sampled norms deviate from 1 by at most a few epsilons (measured <1e-15)
    if (std::fabs(sqnorm(res.final_dir) - 1.0) > 1e-12)
      all_unit = false;
  }
  CHECK(all_unit);
}

TEST_CASE("NCrystalScat ordinary powder: inelastic events occur (control for above)")
{
  // the two elastic-only guarantees above are only meaningful if the very same
  // powder *with* inelastic scattering actually changes energies
  pt::NCrystalScat model(kAlCfg);
  int changed = 0;
  for (int i = 0; i < 200; ++i) {
    const pt::SampledResult& res = model.sampleReaction(0.05, pt::Vector{ 0., 0., 1. });
    if (res.final_ekin != 0.05)
      ++changed;
    // deposition bookkeeping holds event by event
    CHECK(res.deposition == 0.05 - res.final_ekin);
  }
  CHECK(changed > 0);
  CHECK(changed < 200); // elastic channel is still populated as well
}

TEST_CASE("NCrystalScat germanium sampling: unit norm and deposition bookkeeping")
{
  pt::NCrystalScat model(kGeCfg);
  const pt::Vector in_dir{ 0., 0., 1. };
  for (int i = 0; i < 20; ++i) {
    const pt::SampledResult& res = model.sampleReaction(0.005, in_dir);
    CHECK(std::fabs(sqnorm(res.final_dir) - 1.0) < 1e-12);
    CHECK(res.deposition == 0.005 - res.final_ekin);
  }
}

TEST_CASE("NCrystalAbs construction and metadata")
{
  pt::NCrystalAbs model(kWaterCfg);
  CHECK(model.getName() == kWaterCfg + "_abs");
  CHECK(model.getBias() == doctest::Approx(1.0));
  CHECK(model.isDispearingReaction()); // absorption removes the neutron
  CHECK(model.isValid(2112, 1.0));
  CHECK_FALSE(model.isValid(2212, 1.0));
}

TEST_CASE("NCrystalAbs cross sections: anchors, direct match and exact 1/v law")
{
  pt::NCrystalAbs model(kWaterCfg);
  auto direct = NCrystal::createAbsorption(kWaterCfg);
  const double energies[] = { 0.0253, 0.1, 1.0, 10.0 };
  const double pins[] = {
    2.2179167720435479e-23,
    1.1155922939636835e-23,
    3.527812589057352e-24,
    1.1155922939636834e-24
  };
  for (int i = 0; i < 4; ++i) {
    double xs = model.getCrossSection(energies[i]);
    CHECK(xs == rel(pins[i]));
    CHECK(xs == rel(direct.crossSectionIsotropic(NCrystal::NeutronEnergy(energies[i])).get()
                        * pt::Unit::barn, 1e-15));
  }
  // NCrystal absorption is a pure 1/v law: closed-form cross-ratios
  double ratio1 = model.getCrossSection(0.0253) / model.getCrossSection(1.0);
  CHECK(ratio1 == rel(std::sqrt(1.0 / 0.0253), 1e-12));
  double ratio2 = model.getCrossSection(0.1) / model.getCrossSection(1.0);
  CHECK(ratio2 == rel(std::sqrt(10.0), 1e-12));
}

TEST_CASE("NCrystalAbs is direction independent and honours the bias factor")
{
  pt::NCrystalAbs model(kWaterCfg);
  CHECK(model.getCrossSection(1.0, pt::Vector{ 0., 1., 0. })
        == rel(model.getCrossSection(1.0), 1e-15));
  CHECK(model.getCrossSection(1.0, pt::Vector{ 1., 0., 0. })
        == rel(model.getCrossSection(1.0), 1e-15));

  pt::NCrystalAbs biased(kWaterCfg, 3.0);
  CHECK(biased.getBias() == doctest::Approx(3.0));
  CHECK(biased.getCrossSection(1.0) == rel(3.0 * model.getCrossSection(1.0), 1e-15));
}

TEST_CASE("NCrystalAbs sampleReaction kills the neutron and deposits all energy")
{
  pt::NCrystalAbs model(kWaterCfg);
  const pt::Vector in_dir{ 1., 0., 0. };
  for (double ekin : { 1e-3, 1.0, 100.0 }) {
    const pt::SampledResult& res = model.sampleReaction(ekin, in_dir);
    CHECK(res.dispeared);
    CHECK(res.deposition == ekin);   // bitwise: full energy deposited
    CHECK(res.final_ekin == 0.0);    // no outgoing neutron kinematics
  }
}
