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

#include <fstream>
#include <iostream>
#include <cmath>
#include <iterator>
#include <limits>
#include <vector>
#include "PTGIDIModel.hh"
#include "PTModelCollection.hh"
#include "PTMaterialDecomposer.hh"
#include "PTGIDIFactory.hh"
#include "PTGidiSetting.hh"
#include "PTStackManager.hh"

namespace pt = Prompt;

#ifdef ENABLE_GIDI

// The first photon of a back-to-back pair used to draw its azimuth from
// [0,pi) only (its partner then sat in [pi,2pi)), so each labelled photon was
// anisotropic by construction. The fix draws the pair-plane azimuth from the
// full circle in the vendored gidiplus (PairProductionGamma::sample). Gidiplus
// upgrades must not bring the old line back: pin it on the header cinema
// actually compiles against (CINEMAPATH-relative, same path as the build).
TEST_CASE("gidiplus PairProductionGamma azimuth covers the full 2pi")
{
  const char *envVar = std::getenv("CINEMAPATH");
  REQUIRE(envVar != nullptr);
  const std::string header = std::string(envVar)
                           + "/external/gidiplus/include/MCGIDI_headerSource.hpp";
  std::ifstream in(header);
  REQUIRE_MESSAGE(in.good(), "cannot open the vendored gidiplus header " << header);
  std::string src((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());

  const std::string bad = "a_input.m_phi = M_PI * a_rng( ); }";
  const std::string good = "a_input.m_phi = 2.0 * M_PI * a_rng( ); }";
  CHECK_MESSAGE(src.find(bad) == std::string::npos,
                "PairProductionGamma::sample is back to the half-plane azimuth");
  CHECK_MESSAGE(src.find(good) != std::string::npos,
                "the full-circle azimuth line is missing");
}

namespace
{
  // The full data root: the reduced neutron testdata map has no photo-atomic
  // entries, so the photon tests need external/ptdata (the shipped gidi data).
  void configPhotonTestData()
  {
    auto &cdata = Prompt::Singleton<Prompt::GidiSetting>::getInstance();
    cdata.setEnableGidi(true);
    cdata.setGammaTransport(true);
    cdata.setGammaCutEkin(0.); // keep every photon transportable in this test
    const char *envVar = std::getenv("CINEMAPATH");
    REQUIRE(envVar != nullptr);
    const std::string cpath(envVar);
    const std::string pops = cpath + "/external/ptdata/pops.xml";
    const std::string gmap = cpath + "/external/ptdata/all.map";
    REQUIRE_MESSAGE(std::ifstream(pops).good(), "missing gidi data file " << pops);
    REQUIRE_MESSAGE(std::ifstream(gmap).good(), "missing gidi data file " << gmap);
    cdata.setGidiPops(pops);
    cdata.setGidiMap(gmap);
  }

  // drain the secondaries a sampleReaction left on the main stack
  std::vector<Prompt::Particle> drainStack()
  {
    auto &stm = Prompt::Singleton<Prompt::StackManager>::getInstance();
    std::vector<Prompt::Particle> out;
    while(!stm.empty())
    {
      int n = stm.getUnweightedNum();
      for(int j = 0; j < n; ++j)
        stm.scalceSecondary(j, 1.0);
      out.emplace_back(*stm.pop());
    }
    return out;
  }
}

// Regression for the photon-model segfault: for an element entry the gidi map
// hands back a ProtareSingle (there is no nuclear half), and the old code
// static_cast it to ProtareComposite and read out of bounds - every material
// with gammaTransport on crashed at first photon collision. The factory now
// dispatches on protareType(), and the two passes ask for disjoint data:
// the isotope pass photonuclear-only, the element pass photo-atomic-only,
// so the atomic cross section is registered exactly once.
TEST_CASE("photon GIDI factory: element and isotope passes build and sample")
{
  configPhotonTestData();

  auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();

  // water by mass: O16 16/18, H1 2/18 (the fractions feed GIDIModel's xs
  // scaling m_frac, so a wrong fraction only skews the printed values)
  std::vector<Prompt::IsotopeComposition> water = {
    Prompt::IsotopeComposition{8, 16, 16.0/18.0, "O16"},
    Prompt::IsotopeComposition{1, 1, 2.0/18.0, "H1"}
  };

  // isotope pass: photonuclear data where it exists (O16 yes, H1 no)
  auto nuclear_models = gidifactory.createPhotonGIDIModel(water, 1., true, true);
  std::cout << "isotope pass produced " << nuclear_models.size() << " model(s)" << std::endl;
  CHECK(nuclear_models.size() == 1); // H1 has no photonuclear file: warned and skipped
  if(nuclear_models.size() == 1)
  {
    // 18 MeV: above the O16 (gamma,n) threshold of 15.7 MeV, inside the
    // endf80_g grid (which tops out around 20 MeV)
    double xs = nuclear_models[0]->getCrossSection(1.8e7, pt::Vector{0, 0, 1});
    std::cout << std::scientific << "O16 photonuclear xs at 18 MeV: "
              << xs / pt::Unit::barn << " barn" << std::endl;
    CHECK(xs > 0.);
  }

  // element pass: photo-atomic data for both elements - the old segfault path
  auto atomic_models = gidifactory.createPhotonGIDIModel(
      Prompt::shrink2element(water), 1., true, true,
      0., std::numeric_limits<double>::max(),
      0., std::numeric_limits<double>::max(), true);
  std::cout << "element pass produced " << atomic_models.size() << " model(s)" << std::endl;
  REQUIRE(atomic_models.size() == 2);

  // the printed values are fraction-weighted (shrink2element gives each
  // element its mass fraction and GIDIModel::getCrossSection scales by it):
  // H prints 12.08 barn x 2/18 = 1.34 barn at 1 keV, the per-atom value being
  // 12.08 barn (xraylib: 12.10 barn). The absolute per-atom pin lives in the
  // python suite (test_gidi_photon.py::test_photoatomic_absolute_xs), which
  // goes through the ModelCollection user path where the double-count
  // regression would actually appear.
  for(size_t mi = 0; mi < atomic_models.size(); ++mi)
  {
    auto &m = atomic_models[mi];
    std::cout << std::scientific;
    for(double e : {1e3, 1e4, 1e5, 1e6, 1e7})
    {
      double xs = m->getCrossSection(e, pt::Vector{0, 0, 1});
      std::cout << "photo-atomic xs of model " << mi << " at " << e
                << " eV: " << xs / pt::Unit::barn << " barn" << std::endl;
      if(e == 1e5)
        CHECK(xs > 0.);
    }
  }
}

// End-to-end sampling on the photo-atomic models: pair production at 10 MeV
// must hand back two back-to-back ~511 keV photons through the stack, with a
// combined azimuth about the incident direction that fills the full circle.
TEST_CASE("pair production sampling yields two 511 keV photons")
{
  configPhotonTestData();

  auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();
  std::vector<Prompt::IsotopeComposition> pb = {
    Prompt::IsotopeComposition{82, 208, 1., "Pb"}
  };
  // Pair production is an atomic-channel process: build through the element
  // pass (PhotoMode::atomicOnly), the documented route. (Handing the isotope
  // pass a bare element name would silently serve the photo-atomic entry too
  // - the gidiplus map lookup ignores the interaction attribute - but that
  // quirk must not become load-bearing here.)
  auto models = gidifactory.createPhotonGIDIModel(
      Prompt::shrink2element(pb), 1., true, true,
      0., std::numeric_limits<double>::max(),
      0., std::numeric_limits<double>::max(), true);
  REQUIRE(models.size() == 1);

  auto &model = *models[0];
  const double ekin = 1e7; // 10 MeV, well above the 1.022 MeV threshold
  const pt::Vector indir{0, 0, 1};
  double xs = model.getCrossSection(ekin, indir);
  std::cout << std::scientific << "Pb photo-atomic xs at 10 MeV: "
            << xs / pt::Unit::barn << " barn" << std::endl;
  CHECK(xs > 0.);

  const int nevent = 20000;
  int pairEvents = 0;
  // per-product-index azimuths (atan2(y, x) of each 511 keV photon). The
  // regression guard MUST be per photon: pooling both into one histogram is
  // exactly uniform even with the old half-plane bug (photon A on [0,pi),
  // partner at A+pi), so it has no power. Under the bug the first-sampled
  // photon is confined to [0,pi) whichever slot it lands in, so both
  // per-index histograms go non-uniform.
  std::vector<double> azimuth0, azimuth1;
  azimuth0.reserve(nevent);
  azimuth1.reserve(nevent);
  auto &stm = Prompt::Singleton<Prompt::StackManager>::getInstance();
  for(int i = 0; i < nevent; ++i)
  {
    model.sampleReaction(ekin, indir);
    auto products = drainStack();
    if(products.size() != 2)
      continue;
    if(products[0].getPDG() != 22 || products[1].getPDG() != 22)
      continue;
    if(products[0].getEKin() < 5.05e5 || products[0].getEKin() > 5.2e5)
      continue;
    if(products[1].getEKin() < 5.05e5 || products[1].getEKin() > 5.2e5)
      continue;
    ++pairEvents;
    azimuth0.emplace_back(std::atan2(products[0].getDirection().y(),
                                     products[0].getDirection().x()));
    azimuth1.emplace_back(std::atan2(products[1].getDirection().y(),
                                     products[1].getDirection().x()));
  }
  std::cout << "pair-production signature in " << pairEvents << "/" << nevent
            << " events" << std::endl;
  // pair production is a sizeable channel at 10 MeV on Pb; a data or dispatch
  // failure shows up as (near) zero
  CHECK(pairEvents > nevent / 20);

  // per-index azimuth uniformity over the full circle: 36 bins, no empty bin
  // and a chi2 consistent with uniformity (dof 35, mean 35, sigma ~8.4; the
  // bound fails only at a p-value far below 1e-4). This is the braces; the
  // source-pin test in this file is the belt (a stale binary with a fresh
  // header passes here but fails there, and vice versa for a fresh binary
  // linked against a stale library).
  const int nbin = 36;
  for(const auto *azimuth : {&azimuth0, &azimuth1})
  {
    REQUIRE(azimuth->size() == static_cast<size_t>(pairEvents));
    std::vector<double> bin(nbin, 0.);
    for(double a : *azimuth)
    {
      double phi = std::fmod(a + 2.0 * M_PI, 2.0 * M_PI);
      int idx = static_cast<int>(phi / (2.0 * M_PI) * nbin);
      if(idx >= nbin) idx = nbin - 1;
      ++bin[idx];
    }
    double expected = azimuth->size() / nbin;
    double chi2 = 0.;
    int empty = 0;
    for(double b : bin)
    {
      chi2 += (b - expected) * (b - expected) / expected;
      if(b == 0.) ++empty;
    }
    std::cout << "azimuth chi2(35) = " << chi2
              << ", empty bins: " << empty << std::endl;
    CHECK(empty == 0);
    CHECK(chi2 < 80.);
  }
}

// The data-reuse invariant: the MCGIDI tables are the large persistent
// objects, so two materials sharing a nuclide must share ONE protare, keyed
// by the canonical (Z, A) identity rather than the name spelling. This also
// pins the photon path, which used to rebuild the photo-atomic protare for
// every material.
TEST_CASE("gidi protare reuse across materials")
{
  configPhotonTestData();

  auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();

  std::vector<Prompt::IsotopeComposition> water = {
    Prompt::IsotopeComposition{8, 16, 16.0/18.0, "O16"},
    Prompt::IsotopeComposition{1, 1, 2.0/18.0, "H1"}
  };

  // "first material": two neutron protares enter the cache
  auto first = gidifactory.createNeutronGIDIModel(water, 293.15, 1., 0., true, true);
  CHECK(first.size() == 2);
  const size_t after_first = gidifactory.protareCacheSize();
  CHECK(after_first >= 2);

  // "second material", same nuclides: the cache must absorb it
  auto second = gidifactory.createNeutronGIDIModel(water, 293.15, 1., 0., true, true);
  CHECK(second.size() == 2);
  CHECK(gidifactory.protareCacheSize() == after_first);

  // the photon element pass is cached the same way (earlier test cases in
  // this file may already have cached O/H, so growth is not asserted here —
  // only that a repeat build adds nothing)
  auto p1 = gidifactory.createPhotonGIDIModel(
      Prompt::shrink2element(water), 1., true, true,
      0., std::numeric_limits<double>::max(),
      0., std::numeric_limits<double>::max(), true);
  const size_t after_photon = gidifactory.protareCacheSize();
  auto p2 = gidifactory.createPhotonGIDIModel(
      Prompt::shrink2element(water), 1., true, true,
      0., std::numeric_limits<double>::max(),
      0., std::numeric_limits<double>::max(), true);
  CHECK(p1.size() == p2.size());
  CHECK(gidifactory.protareCacheSize() == after_photon);
}

#endif // ENABLE_GIDI
