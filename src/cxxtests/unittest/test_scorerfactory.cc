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

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "PTScorerFactory.hh"
#include "PTScorer.hh"
#include "PTScorer2D.hh"
#include "PTHist1D.hh"
#include "PTHist2D.hh"
#include "PTSingleton.hh"

namespace pt = Prompt;

// Only the public createScorer() entry point is exercised: getPTS() is private,
// so the ptstate string -> ScorerType mapping is verified through the parsed
// "ptstate=..." config key, which createScorer forwards to getPTS(). The
// default-constructed ActiveVolume singleton is sufficient, no GDML needed.

TEST_CASE("scorerfactory_ptstate_string_maps_to_all_8_scorer_types")
{
  // The (string -> enum) table mirrors getPTS() and pairs with the integer
  // ABI pin in test_scorertype.cc.
  const std::vector<std::pair<std::string, pt::Scorer::ScorerType>> states = {
    {"ENTRY", pt::Scorer::ScorerType::ENTRY},
    {"ABSORB", pt::Scorer::ScorerType::ABSORB},
    {"SURFACE", pt::Scorer::ScorerType::SURFACE},
    {"PROPAGATE_POST", pt::Scorer::ScorerType::PROPAGATE_POST},
    {"PROPAGATE_PRE", pt::Scorer::ScorerType::PROPAGATE_PRE},
    {"EXIT", pt::Scorer::ScorerType::EXIT},
    {"PEA_PRE", pt::Scorer::ScorerType::PEA_PRE},
    {"PEA_POST", pt::Scorer::ScorerType::PEA_POST},
  };

  for(const auto &st : states)
  {
    auto scorer = std::unique_ptr<pt::Scorer>(
      pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
        "Scorer=TOF; name=pts_" + st.first + "; min=0.; max=1.; numbin=4; ptstate=" + st.first,
        1000.0));
    MESSAGE("ptstate=", st.first);
    CHECK(scorer->getType() == st.second);
  }
}

TEST_CASE("scorerfactory_unknown_ptstate_throws_badinput")
{
  REQUIRE_THROWS_AS(pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
    "Scorer=TOF; name=pts_bogus; min=0.; max=1.; numbin=4; ptstate=bogus", 1000.0),
    pt::Error::BadInput);
}

TEST_CASE("scorerfactory_create_espectrum_hist_type_and_name")
{
  auto scorer = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      // ESpectrum is always log-binned (no linear key exists), so min>0 is required
      "Scorer=ESpectrum; name=detector; min=1e-5; max=0.0253; numbin=120; ptstate=ENTRY",
      1000.0));

  CHECK(scorer->getName() == "ScorerESpectrum_detector");
  CHECK(scorer->getType() == pt::Scorer::ScorerType::ENTRY);
  const pt::HistBase *hist = scorer->getHist();
  REQUIRE(hist != nullptr);
  CHECK(hist->getDataSize() == 120);
  CHECK(hist->getXMin() == doctest::Approx(1e-5));
  CHECK(hist->getXMax() == doctest::Approx(0.0253));
  CHECK(hist->dimension() == 1);
}

TEST_CASE("scorerfactory_scoretransfer_forces_exit_ptstate")
{
  // scoreTransfer=true must override an explicitly given ptstate=ENTRY
  auto scorer = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=ESpectrum; name=transfer; min=1e-5; max=1.0; numbin=10; "
      "scoreTransfer=true; ptstate=ENTRY",
      1000.0));

  CHECK(scorer->getName() == "ScorerESpectrum_transfer");
  CHECK(scorer->getType() == pt::Scorer::ScorerType::EXIT);
}

TEST_CASE("scorerfactory_malformed_cfg_throws_badinput")
{
  // no "Scorer" key at all
  REQUIRE_THROWS_AS(pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
    "name=lonely; min=0.; max=1.", 1000.0),
    pt::Error::BadInput);

  // unknown scorer type
  REQUIRE_THROWS_AS(pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
    "Scorer=Bogus; name=x", 1000.0),
    pt::Error::BadInput);

  // DeltaMomentum accepts exactly 12 keys (incl. "Scorer"); one extra key
  // trips the parCount check
  REQUIRE_THROWS_AS(pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
    "Scorer=DeltaMomentum; name=SofQ; sample_pos=0,0,1; beam_dir=0,0,1; dist=-100; "
    "min=0.5; max=50; numbin=1000; ptstate=ENTRY; linear=yes; method=0; scatnum=-1; "
    "Qtrue=yes", 1000.0),
    pt::Error::BadInput);
}

TEST_CASE("scorerfactory_psd_hist_dims_and_yrange")
{
  auto scorer = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=PSD; name=psd1; xmin=-10; xmax=10; ymin=-20; ymax=20; "
      "numbin_x=12; numbin_y=22; ptstate=ENTRY; type=XY",
      1000.0));

  const pt::HistBase *hist = scorer->getHist();
  REQUIRE(hist != nullptr);
  CHECK(hist->getDataSize() == 12u * 22u);
  CHECK(hist->getXMin() == doctest::Approx(-10.0));
  CHECK(hist->getXMax() == doctest::Approx(10.0));
  CHECK(hist->dimension() == 2);

  const auto *hist2d = dynamic_cast<const pt::Hist2D *>(hist);
  REQUIRE(hist2d != nullptr);
  CHECK(hist2d->getNBinX() == 12u);
  CHECK(hist2d->getNBinY() == 22u);
  CHECK(hist2d->getYMin() == doctest::Approx(-20.0));
  CHECK(hist2d->getYMax() == doctest::Approx(20.0));

  // the XY/XZ/YZ selection does not change the histogram binning; it only
  // decides which particle position components are scored
  auto scorerYZ = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=PSD; name=psd2; xmin=-10; xmax=10; ymin=-20; ymax=20; "
      "numbin_x=12; numbin_y=22; ptstate=ENTRY; type=YZ",
      1000.0));
  CHECK(scorerYZ->getHist()->getDataSize() == 12u * 22u);
  const auto *hist2dYZ = dynamic_cast<const pt::Hist2D *>(scorerYZ->getHist());
  REQUIRE(hist2dYZ != nullptr);
  CHECK(hist2dYZ->getYMin() == doctest::Approx(-20.0));
  CHECK(hist2dYZ->getYMax() == doctest::Approx(20.0));
}

TEST_CASE("scorerfactory_multiscat_edges_and_1d_scorer_dims")
{
  // MultiScat min=1, max=5 builds the hist on [min-0.5, max+0.5] with one bin
  // per allowed scattering number
  auto ms = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=MultiScat; name=D2O; min=1; max=5; linear=yes", 1000.0));
  CHECK(ms->getName() == "ScorerMultiScat_D2O");
  CHECK(ms->getType() == pt::Scorer::ScorerType::PEA_POST);
  REQUIRE(ms->getHist() != nullptr);
  CHECK(ms->getHist()->getDataSize() == 5u);
  CHECK(ms->getHist()->getXMin() == doctest::Approx(0.5));
  CHECK(ms->getHist()->getXMax() == doctest::Approx(5.5));

  auto vf = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=VolFluence; name=sflux; min=0; max=1; numbin=10; ptstate=PEA_PRE; linear=yes",
      1000.0));
  CHECK(vf->getType() == pt::Scorer::ScorerType::PEA_PRE);
  CHECK(vf->getHist()->getDataSize() == 10u);

  auto tof = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=TOF; name=tofdim; min=0.; max=0.04; numbin=100; ptstate=ENTRY", 1000.0));
  CHECK(tof->getHist()->getDataSize() == 100u);
  CHECK(tof->getHist()->getXMax() == doctest::Approx(0.04));

  auto wl = std::unique_ptr<pt::Scorer>(
    pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
      "Scorer=WlSpectrum; name=wldim; min=0.5; max=5; numbin=77; ptstate=ENTRY", 1000.0));
  CHECK(wl->getHist()->getDataSize() == 77u);
}

TEST_CASE("scorerfactory_wlangle_invalid_method_throws_badinput")
{
  REQUIRE_THROWS_AS(pt::Singleton<pt::ScorerFactory>::getInstance().createScorer(
    "Scorer=WlAngle; name=wla; sample_pos=0,0,0; beam_dir=0,0,1; dist=1000; "
    "wl_min=0.5; wl_max=5; angle_min=0; angle_max=3; numbin_wl=10; numbin_angle=10; "
    "method=3", 1000.0),
    pt::Error::BadInput);
}
