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
#include <vector>

#include "PTScorerAngular.hh"
#include "PTScorerTOF.hh"
#include "PTScorerDeltaMomentum.hh"
#include "PTScorerVolFluence.hh"
#include "PTScorerESpectrum.hh"
#include "PTEst1D.hh"
#include "PTParticle.hh"
#include "PTMath.hh"

namespace pt = Prompt;

namespace
{
  // linear bin index a Hist1D::fill() lands on (guards against silent
  // re-indexing of the surrounding test values)
  unsigned linBin(double val, double xmin, double xmax, unsigned nbins)
  {
    return static_cast<unsigned>(std::floor((val - xmin) * nbins / (xmax - xmin)));
  }
}

TEST_CASE("scorer_angular_degree_mode_lands_in_expected_bin")
{
  pt::ScorerAngular scorer("deg1", 10.0, 160.0, 150, pt::const_neutron_pgd,
                           pt::Vector(0., 0., 1.), pt::Scorer::ScorerType::ENTRY,
                           true, true);
  CHECK(scorer.getName() == "ScorerAngular_deg1");

  const pt::HistBase *hist = scorer.getHist();
  REQUIRE(hist != nullptr);
  CHECK(hist->getXMin() == doctest::Approx(10.0));
  CHECK(hist->getXMax() == doctest::Approx(160.0));
  CHECK(hist->getDataSize() == 150u);

  // direction at 30.5 degrees from the +z reference direction (off the bin
  // edges so the acos roundtrip cannot flip the floor())
  const double th1 = 30.5 * pt::const_deg2rad;
  pt::Particle p(0.05, pt::Vector(std::sin(th1), 0., std::cos(th1)), pt::Vector(0., 0., 0.));
  p.setWeight(1.3);
  p.scaleSurviveP(0.5);
  scorer.score(p);

  // 30.5deg -> bin floor(30.5-10) = 20; content must be weight*surviveP
  const double expected = 1.3 * 0.5;
  CHECK(hist->getRaw()[20] == doctest::Approx(expected));
  CHECK(hist->getTotalWeight() == doctest::Approx(expected));
  CHECK(hist->getAccWeight() == doctest::Approx(expected)); // nothing outside range
  CHECK(hist->getTotalHit() == doctest::Approx(1.0));
  CHECK(hist->getOverflow() == doctest::Approx(0.0));
  CHECK(hist->getUnderflow() == doctest::Approx(0.0));

  // a direction 90.7 degrees away must land in bin floor(90.7-10) = 80
  const double th2 = 90.7 * pt::const_deg2rad;
  pt::Particle q(0.05, pt::Vector(std::sin(th2), 0., std::cos(th2)), pt::Vector(0., 0., 0.));
  scorer.score(q);
  CHECK(hist->getRaw()[80] == doctest::Approx(1.0));
}

TEST_CASE("scorer_angular_mu_mode_clamps_collinear_directions")
{
  // mu range capped below 1 so the clamped cos==1 (mu=1, strictly above the
  // mu_max range) books as overflow rather than near the upper edge
  pt::ScorerAngular scorer("mu1", -0.5, 0.5, 10, pt::const_neutron_pgd,
                           pt::Vector(0., 0., 1.), pt::Scorer::ScorerType::ENTRY,
                           false, true);

  const pt::HistBase *hist = scorer.getHist();

  // collinear: angleCos clamps to exactly +1 -> overflow
  pt::Particle collinear(0.05, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  scorer.score(collinear);
  CHECK(hist->getOverflow() == doctest::Approx(1.0));

  // antiparallel: angleCos clamps to exactly -1 -> underflow
  pt::Particle antiparallel(0.05, pt::Vector(0., 0., -1.), pt::Vector(0., 0., 0.));
  antiparallel.setWeight(0.7);
  scorer.score(antiparallel);
  CHECK(hist->getUnderflow() == doctest::Approx(0.7));

  // 15/16 = 0.9375 and 1/16 = 0.0625 are exact, so mu == 0.25 exactly -> bin 7
  pt::Particle mid(0.05, pt::Vector(0.9682458365518543, 0., 0.25), pt::Vector(0., 0., 0.));
  mid.setWeight(2.0);
  scorer.score(mid);
  CHECK(hist->getRaw()[7] == doctest::Approx(2.0));

  CHECK(hist->getTotalWeight() == doctest::Approx(1.0 + 0.7 + 2.0));
}

TEST_CASE("scorer_angular_ctor_rejects_invalid_ranges")
{
  // degree mode: max>180
  REQUIRE_THROWS_AS(pt::ScorerAngular("bad1", 10.0, 181.0, 10, pt::const_neutron_pgd,
                                      pt::Vector(0., 0., 1.),
                                      pt::Scorer::ScorerType::ENTRY, true, true),
                    pt::Error::BadInput);
  // degree mode: min<0
  REQUIRE_THROWS_AS(pt::ScorerAngular("bad2", -5.0, 100.0, 10, pt::const_neutron_pgd,
                                      pt::Vector(0., 0., 1.),
                                      pt::Scorer::ScorerType::ENTRY, true, true),
                    pt::Error::BadInput);
  // degree mode: min>=max
  REQUIRE_THROWS_AS(pt::ScorerAngular("bad3", 20.0, 10.0, 10, pt::const_neutron_pgd,
                                      pt::Vector(0., 0., 1.),
                                      pt::Scorer::ScorerType::ENTRY, true, true),
                    pt::Error::BadInput);
  // mu mode: max>1
  REQUIRE_THROWS_AS(pt::ScorerAngular("bad4", -0.5, 1.5, 10, pt::const_neutron_pgd,
                                      pt::Vector(0., 0., 1.),
                                      pt::Scorer::ScorerType::ENTRY, false, true),
                    pt::Error::BadInput);
  // mu mode: min<-1
  REQUIRE_THROWS_AS(pt::ScorerAngular("bad5", -1.5, 0.5, 10, pt::const_neutron_pgd,
                                      pt::Vector(0., 0., 1.),
                                      pt::Scorer::ScorerType::ENTRY, false, true),
                    pt::Error::BadInput);
  // mu mode: min>=max
  REQUIRE_THROWS_AS(pt::ScorerAngular("bad6", 0.5, -0.5, 10, pt::const_neutron_pgd,
                                      pt::Vector(0., 0., 1.),
                                      pt::Scorer::ScorerType::ENTRY, false, true),
                    pt::Error::BadInput);
}

TEST_CASE("scorer_tof_bins_particle_time")
{
  pt::ScorerTOF scorer("tof1", 0.0, 1.0, 100, pt::const_neutron_pgd);

  pt::Particle p(0.025, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p.setTime(0.567);
  p.setWeight(0.7);
  scorer.score(p);

  const pt::HistBase *hist = scorer.getHist();
  CHECK(hist->getRaw()[56] == doctest::Approx(0.7)); // floor(0.567*100) = 56
  CHECK(hist->getTotalWeight() == doctest::Approx(0.7));
  CHECK(hist->getTotalHit() == doctest::Approx(1.0));
  CHECK(hist->getOverflow() == doctest::Approx(0.0));
  CHECK(hist->getUnderflow() == doctest::Approx(0.0));
}

TEST_CASE("scorer_ignores_particle_with_wrong_pdg")
{
  pt::ScorerTOF scorer("pdgtest", 0.0, 1.0, 100, pt::const_neutron_pgd);

  // a proton must not be scored by a neutron scorer
  pt::Particle proton(0.025, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.),
                      pt::const_proton_pgd);
  proton.setTime(0.5);
  scorer.score(proton);

  const pt::HistBase *hist = scorer.getHist();
  CHECK(hist->getTotalWeight() == doctest::Approx(0.0));
  CHECK(hist->getTotalHit() == doctest::Approx(0.0));
  CHECK(hist->getRaw()[50] == doctest::Approx(0.0));

  // the same kinematics from a neutron do score
  pt::Particle neutron(0.025, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.),
                       pt::const_neutron_pgd);
  neutron.setTime(0.5);
  scorer.score(neutron);
  CHECK(hist->getTotalWeight() == doctest::Approx(1.0));
  CHECK(hist->getRaw()[50] == doctest::Approx(1.0));
}

TEST_CASE("scorer_deltamomentum_method0_q_and_normalization")
{
  pt::ScorerDeltaMomentum scorer("SofQ", pt::Vector(0., 0., 0.), pt::Vector(0., 0., 1.),
                                 -100.0, 0.5, 50.0, 100, pt::const_neutron_pgd,
                                 pt::Scorer::ScorerType::ENTRY, 0);

  // inelastic 45-degree geometry: particle at (100,0,100) sees cos=1/sqrt(2)
  pt::Particle p(2.0, pt::Vector(0., 0., 1.), pt::Vector(100., 0., 100.));
  p.setEKin(1.0);
  p.setTime(1.0); // method 0 does not use time, keep it finite anyway
  scorer.score(p);

  // independent reference: law of cosines q = sqrt(k0^2+k1^2-2*k0*k1*cos)
  const double k0 = std::sqrt(2.0 * pt::const_eV2kk);
  const double k1 = std::sqrt(1.0 * pt::const_eV2kk);
  const double cos45 = 100.0 / std::sqrt(100.0 * 100.0 + 100.0 * 100.0);
  const double qexp = std::sqrt(k0 * k0 + k1 * k1 - 2.0 * k0 * k1 * cos45);
  const unsigned bin = linBin(qexp, 0.5, 50.0, 100);
  REQUIRE(bin < 100u);

  const pt::HistBase *hist = scorer.getHist();
  CHECK(hist->getRaw()[bin] == doctest::Approx(1.0 / qexp)); // fill(q, w/q)
  CHECK(hist->getTotalWeight() == doctest::Approx(1.0 / qexp));
  CHECK(hist->getTotalHit() == doctest::Approx(1.0));

  // elastic 90-degree geometry: ekin0==ekin, cos=0 -> q = k*sqrt(2)
  pt::ScorerDeltaMomentum scorer2("SofQ90", pt::Vector(0., 0., 0.), pt::Vector(0., 0., 1.),
                                  -100.0, 0.5, 50.0, 100, pt::const_neutron_pgd,
                                  pt::Scorer::ScorerType::ENTRY, 0);
  pt::Particle q(0.5, pt::Vector(0., 0., 1.), pt::Vector(300., 0., 0.));
  q.setTime(1.0);
  scorer2.score(q);
  const double k = std::sqrt(0.5 * pt::const_eV2kk);
  const double q90 = k * std::sqrt(2.0);
  const unsigned bin90 = linBin(q90, 0.5, 50.0, 100);
  REQUIRE(bin90 < 100u);
  CHECK(scorer2.getHist()->getRaw()[bin90] == doctest::Approx(1.0 / q90));
}

TEST_CASE("scorer_deltamomentum_method1_static_approximation")
{
  pt::ScorerDeltaMomentum scorer("SofQstatic", pt::Vector(0., 0., 0.),
                                 pt::Vector(0., 0., 1.), 1000.0, 0.5, 50.0, 100,
                                 pt::const_neutron_pgd, pt::Scorer::ScorerType::ENTRY, 1);

  // particle 300 mm from the sample, so the static path length is 1300 mm;
  // pick the flight time so that the inferred energy is exactly 1 eV
  pt::Particle p(1.0, pt::Vector(0., 0., 1.), pt::Vector(300., 0., 0.));
  const double v = std::sqrt(2.0 * 1.0 / pt::const_neutron_mass_evc2); // speed of 1 eV
  p.setTime(1300.0 / v);
  scorer.score(p);

  // independent reference: ekin = 0.5*m*v^2, elastic cos=0 -> q = k*sqrt(2)
  const double vimpl = 1300.0 / p.getTime();
  const double ekin = 0.5 * pt::const_neutron_mass_evc2 * vimpl * vimpl;
  const double k = std::sqrt(ekin * pt::const_eV2kk);
  const double qexp = k * std::sqrt(2.0);
  const unsigned bin = linBin(qexp, 0.5, 50.0, 100);
  REQUIRE(bin < 100u);

  const pt::HistBase *hist = scorer.getHist();
  CHECK(hist->getRaw()[bin] == doctest::Approx(1.0 / qexp));
  CHECK(hist->getTotalWeight() == doctest::Approx(1.0 / qexp));
  CHECK(hist->getTotalHit() == doctest::Approx(1.0));
}

TEST_CASE("scorer_deltamomentum_invalid_method_throws_on_score")
{
  // the constructor does not validate, scoring does (the factory validates
  // at parse time, so this state is only reachable by direct construction)
  pt::ScorerDeltaMomentum scorer("badmethod", pt::Vector(0., 0., 0.), pt::Vector(0., 0., 1.),
                                 100.0, 0.5, 50.0, 10, pt::const_neutron_pgd,
                                 pt::Scorer::ScorerType::ENTRY, 2);
  pt::Particle p(1.0, pt::Vector(0., 0., 1.), pt::Vector(100., 0., 0.));
  p.setTime(1.0);
  REQUIRE_THROWS_AS(scorer.score(p), pt::Error::BadInput);
}

TEST_CASE("scorer_volfluence_content_and_weight_uniformity_guard")
{
  const double volume = 100.0;
  pt::ScorerVolFluence scorer("sflux", 0.0, 1.0, 10, volume, pt::const_neutron_pgd);

  pt::Particle p(0.5, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p.moveForward(10.0); // step length 10, unchanged weight 1
  scorer.score(p);

  const pt::HistBase *hist = scorer.getHist();
  CHECK(hist->getRaw()[5] == doctest::Approx(10.0 / volume)); // ekin 0.5 -> bin 5
  CHECK(hist->getTotalWeight() == doctest::Approx(10.0 / volume));

  // a second particle with a different weight breaks the unit-bias assumption
  pt::Particle biased(0.5, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  biased.setWeight(2.0);
  REQUIRE_THROWS_AS(scorer.score(biased), pt::Error::LogicError);

  // the throwing fill must not have modified the histogram
  CHECK(hist->getTotalWeight() == doctest::Approx(10.0 / volume));
}

TEST_CASE("est1d_fills_throw_but_3arg_fill_accumulates_and_espectrum_bins_energy")
{
  // the 1-arg and 2-arg Est1D fills are deliberately unimplemented
  pt::Est1D est("est1d", 0.0, 1.0, 10);
  REQUIRE_THROWS_AS(est.fill(0.5), pt::Error::BadInput);
  REQUIRE_THROWS_AS(est.fill(0.5, 1.0), pt::Error::BadInput);

  // only fill(val, weight, error) accumulates; the hit is accumulated in
  // quadrature from the error
  est.fill(0.5, 2.0, 3.0);
  CHECK(est.getRaw()[5] == doctest::Approx(2.0));
  CHECK(est.getHit()[5] == doctest::Approx(3.0));
  CHECK(est.getTotalWeight() == doctest::Approx(2.0));

  // ESpectrum: single fill lands in the expected bin of a linear hist
  pt::ScorerESpectrum scorer("detector", false, 0.0, 2.0, 100, pt::const_neutron_pgd,
                             pt::Scorer::ScorerType::ENTRY, 0, true);
  pt::Particle p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  scorer.score(p);
  CHECK(scorer.getHist()->getRaw()[50] == doctest::Approx(1.0));

  // transfer mode scores ekin0-ekin instead
  pt::ScorerESpectrum transfer("transferred", true, 0.0, 2.0, 100, pt::const_neutron_pgd,
                               pt::Scorer::ScorerType::ENTRY, 0, true);
  pt::Particle q(2.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  q.setEKin(1.5);
  transfer.score(q);
  CHECK(transfer.getHist()->getRaw()[25] == doctest::Approx(1.0)); // transfer 0.5
}
