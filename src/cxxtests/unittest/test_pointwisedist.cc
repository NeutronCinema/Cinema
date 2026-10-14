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

#include "PTPointwiseDist.hh"
#include "PTRandCanonical.hh"
#include "PTSingleton.hh"

#include <cmath>
#include <utility>
#include <vector>
#include <string>

namespace pt = Prompt;

namespace {

// Absolute-difference comparison. Used instead of bare doctest::Approx where
// the expected value is small, since Approx's default scale would otherwise
// turn a relative epsilon into a vacuous absolute window.
bool closeAbs(double value, double expected, double tol)
{
  return std::fabs(value - expected) <= tol;
}

// Independent trapezoid integral (the constructor's own normalisation recipe).
double trapz(const std::vector<double>& x, const std::vector<double>& y)
{
  double area = 0.;
  for (std::size_t i = 1; i < x.size(); ++i)
    area += (x[i] - x[i - 1]) * 0.5 * (y[i] + y[i - 1]);
  return area;
}

// Seeded singleton RNG. resetSeed() is needed since setSeed() throws BadInput
// if a seed was already set on the singleton.
void reseedRNG(uint64_t seed)
{
  auto& rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

// The "tent" density: f(x) = x on [0,1], f(x) = 2-x on [1,2]. Normalised by
// construction (area 1 after scaling), with analytic mean E[X] = 1 and
// var(X) = 1/6.
pt::PointwiseDist makeTent()
{
  return pt::PointwiseDist(std::vector<double>{ 0., 1., 2. },
                           std::vector<double>{ 0., 2., 0. });
}

} // namespace

TEST_CASE("pointwisedist_ctor_rejects_mismatched_or_short_vectors")
{
  std::vector<double> x = { 0., 1., 2. };
  std::vector<double> y = { 1., 2. };
  CHECK_THROWS_AS(pt::PointwiseDist(x, y), pt::Error::CalcError);

  // y longer than x must fail just as well:
  std::vector<double> y2 = { 1., 1., 1., 1. };
  CHECK_THROWS_AS(pt::PointwiseDist(x, y2), pt::Error::CalcError);

  // fewer than two points can not define a distribution:
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{}, std::vector<double>{}),
                  pt::Error::CalcError);
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 1. }, std::vector<double>{ 1. }),
                  pt::Error::CalcError);
}

TEST_CASE("pointwisedist_ctor_rejects_unsorted_grid")
{
  // strictly decreasing:
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 2., 1., 0. },
                                    std::vector<double>{ 1., 1., 1. }),
                  pt::Error::CalcError);
  // locally unsorted:
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 0., 2., 1. },
                                    std::vector<double>{ 1., 1., 1. }),
                  pt::Error::CalcError);
  // repeated x values are accepted by the ctor (non-decreasing), and simply
  // contribute zero area in that bin - pin this documented tolerance:
  pt::PointwiseDist repeated(std::vector<double>{ 0., 1., 1., 2. },
                             std::vector<double>{ 1., 1., 2., 1. });
  CHECK(repeated.getCDF().back() == doctest::Approx(1.0));
}

TEST_CASE("pointwisedist_ctor_rejects_negative_densities")
{
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 0., 1., 2. },
                                    std::vector<double>{ 1., -0.5, 1. }),
                  pt::Error::CalcError);
  // a single negative entry is enough:
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 0., 1. },
                                    std::vector<double>{ 1., -1e-30 }),
                  pt::Error::CalcError);
}

TEST_CASE("pointwisedist_ctor_rejects_zero_area_and_nonfinite_values")
{
  // all-zero densities carry no probability:
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 0., 1., 2. },
                                    std::vector<double>{ 0., 0., 0. }),
                  pt::Error::CalcError);
  // non-finite densities are rejected:
  double inf = std::numeric_limits<double>::infinity();
  CHECK_THROWS_AS(pt::PointwiseDist(std::vector<double>{ 0., 1. },
                                    std::vector<double>{ 1., inf }),
                  pt::Error::CalcError);
}

TEST_CASE("pointwisedist_uniform_pdf_gives_exactly_linear_cdf")
{
  // two-point uniform on [0,1]:
  pt::PointwiseDist u(std::vector<double>{ 0., 1. }, std::vector<double>{ 1., 1. });
  const std::vector<double>& cdf = u.getCDF();
  REQUIRE(cdf.size() == 2u);
  CHECK(cdf[0] == 0.0);
  CHECK(cdf[1] == 1.0);

  // three-point uniform on [0,2]: CDF must rise exactly linearly to 1:
  pt::PointwiseDist u3(std::vector<double>{ 0., 1., 2. }, std::vector<double>{ 7., 7., 7. });
  const std::vector<double>& cdf3 = u3.getCDF();
  REQUIRE(cdf3.size() == 3u);
  CHECK(cdf3[0] == 0.0);
  CHECK(cdf3[1] == doctest::Approx(0.5));
  CHECK(cdf3[2] == 1.0);
  CHECK(cdf3.back() == 1.0);
}

TEST_CASE("pointwisedist_uniform_pdf_percentile_is_the_identity")
{
  pt::PointwiseDist u(std::vector<double>{ 0., 1. }, std::vector<double>{ 1., 1. });
  for (int i = 0; i <= 20; ++i) {
    double p = i / 20.;
    CHECK(closeAbs(u.percentile(p), p, 1e-12));
  }

  // the identity holds on a shifted interval as well:
  pt::PointwiseDist us(std::vector<double>{ -2., 3. }, std::vector<double>{ 1., 1. });
  for (int i = 0; i <= 10; ++i) {
    double p = i / 10.;
    CHECK(closeAbs(us.percentile(p), -2. + 5. * p, 1e-12));
  }
}

TEST_CASE("pointwisedist_cdf_equals_hand_computed_trapezoid_areas")
{
  // x = {0,1,3,6}, y = {1,2,0,4}: segment areas 1.5, 2, 6, total 9.5.
  pt::PointwiseDist d(std::vector<double>{ 0., 1., 3., 6. },
                      std::vector<double>{ 1., 2., 0., 4. });
  const std::vector<double>& cdf = d.getCDF();
  const double total = 9.5;
  CHECK(cdf[0] == 0.0);
  CHECK(closeAbs(cdf[1], 1.5 / total, 1e-14));
  CHECK(closeAbs(cdf[2], 3.5 / total, 1e-14));
  CHECK(cdf[3] == 1.0);
  CHECK(cdf.back() == 1.0);

  // monotone by construction:
  for (std::size_t i = 1; i < cdf.size(); ++i)
    CHECK(cdf[i] >= cdf[i - 1]);
}

TEST_CASE("pointwisedist_ctor_normalises_y_to_unit_integral")
{
  pt::PointwiseDist d(std::vector<double>{ 0., 1., 3., 6. },
                      std::vector<double>{ 1., 2., 0., 4. });

  // the three accessors expose consistent, ctor-sized views:
  REQUIRE(d.getXVals().size() == 4u);
  REQUIRE(d.getYVals().size() == 4u);
  REQUIRE(d.getCDF().size() == 4u);
  CHECK(d.getCDF().front() == 0.0);
  CHECK(d.getCDF().back() == 1.0);

  CHECK(closeAbs(trapz(d.getXVals(), d.getYVals()), 1.0, 1e-12));

  // the same must hold after normalising a raw table with area != 1:
  pt::PointwiseDist t = makeTent();
  REQUIRE(t.getXVals().size() == t.getYVals().size());
  REQUIRE(t.getYVals().size() == t.getCDF().size());
  CHECK(closeAbs(trapz(t.getXVals(), t.getYVals()), 1.0, 1e-12));
}

TEST_CASE("pointwisedist_cumulative_integral_is_zero_and_one_outside_support")
{
  pt::PointwiseDist d(std::vector<double>{ 0., 1., 3., 6. },
                      std::vector<double>{ 1., 2., 0., 4. });
  const double front = d.getXVals().front();
  const double back = d.getXVals().back();

  CHECK(d.commulIntegral(-1e300) == 0.0);
  CHECK(d.commulIntegral(front) == 0.0);
  CHECK(d.commulIntegral(back) == 1.0);
  CHECK(d.commulIntegral(1e300) == 1.0);

  // same convention for a table starting below zero:
  pt::PointwiseDist u(std::vector<double>{ -2., 3. }, std::vector<double>{ 1., 1. });
  CHECK(u.commulIntegral(-2.) == 0.0);
  CHECK(u.commulIntegral(3.) == 1.0);
  CHECK(u.commulIntegral(0.) == doctest::Approx(2. / 5.));
}

TEST_CASE("pointwisedist_cumulative_integral_matches_analytic_interior_values")
{
  // uniform on [0,1]: CDF(x) = x:
  pt::PointwiseDist u(std::vector<double>{ 0., 1. }, std::vector<double>{ 1., 1. });
  CHECK(u.commulIntegral(0.5) == doctest::Approx(0.5));
  CHECK(u.commulIntegral(0.25) == doctest::Approx(0.25));

  // 4-point table, partial bin [1,3] (y normalised by 1/9.5):
  // integral up to x=2 is (1.5 + 1.5)/9.5 = 3/9.5.
  pt::PointwiseDist d(std::vector<double>{ 0., 1., 3., 6. },
                      std::vector<double>{ 1., 2., 0., 4. });
  CHECK(closeAbs(d.commulIntegral(2.), 3. / 9.5, 1e-14));

  // tent density: CDF(x) = x^2/2 on [0,1] and 1-(2-x)^2/2 on [1,2]:
  pt::PointwiseDist t = makeTent();
  CHECK(closeAbs(t.commulIntegral(0.5), 0.125, 1e-14));
  CHECK(closeAbs(t.commulIntegral(1.5), 0.875, 1e-14));
  CHECK(closeAbs(t.commulIntegral(1.0), 0.5, 1e-14));

  // monotone over a fixed grid:
  double prev = -1.0;
  for (int i = 0; i <= 40; ++i) {
    double x = 2. * i / 40.;
    double c = t.commulIntegral(x);
    CHECK(c >= prev);
    CHECK(c >= 0.0);
    CHECK(c <= 1.0);
    prev = c;
  }
}

TEST_CASE("pointwisedist_percentile_endpoints_reach_grid_edges")
{
  pt::PointwiseDist d(std::vector<double>{ 0., 1., 3., 6. },
                      std::vector<double>{ 1., 2., 0., 4. });
  CHECK(d.percentile(0.) == d.getXVals().front());
  CHECK(d.percentile(1.) == d.getXVals().back());

  // works also when the first density value is zero:
  pt::PointwiseDist t = makeTent();
  CHECK(t.percentile(0.) == 0.0);
  CHECK(t.percentile(1.) == 2.0);
}

TEST_CASE("pointwisedist_percentile_half_is_the_uniform_midpoint")
{
  CHECK(pt::PointwiseDist(std::vector<double>{ 0., 1. },
                          std::vector<double>{ 1., 1. }).percentile(0.5) ==
        doctest::Approx(0.5));
  // shifted interval:
  CHECK(pt::PointwiseDist(std::vector<double>{ 2., 5. },
                          std::vector<double>{ 1., 1. }).percentile(0.5) ==
        doctest::Approx(3.5));
  // flat table over three points spanning [0,2]:
  CHECK(pt::PointwiseDist(std::vector<double>{ 0., 1., 2. },
                          std::vector<double>{ 5., 5., 5. }).percentile(0.5) ==
        doctest::Approx(1.0));
}

TEST_CASE("pointwisedist_percentile_with_index_brackets_value_in_bin")
{
  pt::PointwiseDist t = makeTent();
  const std::vector<double>& x = t.getXVals();

  for (int i = 0; i <= 40; ++i) {
    double p = i / 40.;
    auto res = t.percentileWithIndex(p);
    double v = res.first;
    unsigned idx = res.second;
    REQUIRE(idx < x.size() - 1);
    CHECK(v >= x[idx]);
    CHECK(v <= x[idx + 1]);
  }

  // p == 1 is documented to land in the last bin:
  auto last = t.percentileWithIndex(1.);
  CHECK(last.second == x.size() - 2);
  CHECK(last.first == x.back());

  // p == 0 lands in the first bin at the first grid point:
  auto first = t.percentileWithIndex(0.);
  CHECK(first.second == 0u);
  CHECK(first.first == x.front());
}

TEST_CASE("pointwisedist_percentile_inverts_cumulative_integral_on_tent")
{
  pt::PointwiseDist t = makeTent();

  // percentile(p) must be the p-quantile: commulIntegral(percentile(p)) == p.
  for (int i = 0; i <= 100; ++i) {
    double p = i / 100.;
    double v = t.percentile(p);
    CHECK(closeAbs(t.commulIntegral(v), p, 1e-12));
  }

  // and the inverse direction: percentile(commulIntegral(x)) recovers x.
  for (int i = 0; i <= 100; ++i) {
    double x = 2. * i / 100.;
    double recovered = t.percentile(t.commulIntegral(x));
    CHECK(closeAbs(recovered, x, 1e-12));
  }
}

TEST_CASE("pointwisedist_sample_mean_matches_analytic_tent_mean")
{
  // The tent density has analytic mean E[X] = 1 and sd = sqrt(1/6) ~ 0.408,
  // so the standard error of 100k samples is ~0.0013. The 2% window is
  // ~15 standard errors, i.e. rock stable for any reasonable seed.
  pt::PointwiseDist t = makeTent();
  auto& rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  reseedRNG(20261010u);

  const unsigned n = 100000;
  double sum = 0.;
  for (unsigned i = 0; i < n; ++i) {
    double v = t.sample(rng);
    CHECK(v >= 0.);
    CHECK(v <= 2.);
    sum += v;
  }
  double mean = sum / n;
  CHECK(closeAbs(mean, 1.0, 0.02));
}

TEST_CASE("pointwisedist_sample_below_respects_truncation_point")
{
  pt::PointwiseDist t = makeTent();
  auto& rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  reseedRNG(424242u);

  const double xt = 0.7;
  const unsigned n = 10000;
  const double cdfXt = t.commulIntegral(xt);
  for (unsigned i = 0; i < n; ++i) {
    double v = t.sampleBelow(rng, xt);
    CHECK(v <= xt + 1e-9); // tiny fp margin only
    CHECK(v >= t.getXVals().front());
    // sampled mass must stay within the retained part of the distribution:
    CHECK(t.commulIntegral(v) <= cdfXt + 1e-12);
  }

  // truncating exactly at the first grid point always returns that point:
  reseedRNG(424243u);
  for (int i = 0; i < 100; ++i)
    CHECK(t.sampleBelow(rng, t.getXVals().front()) == t.getXVals().front());
}

TEST_CASE("pointwisedist_sample_below_throws_below_support_and_degrades_above")
{
  pt::PointwiseDist t = makeTent();
  auto& rng = pt::Singleton<pt::SingletonPTRand>::getInstance();

  // below the support -> BadInput, with a helpful message:
  bool threw = false;
  try {
    t.sampleBelow(rng, t.getXVals().front() - 1.0);
  } catch (const pt::Error::BadInput& e) {
    threw = true;
    CHECK(std::string(e.what()).find("below distribution") != std::string::npos);
  }
  CHECK(threw);

  // even a hair below the front is rejected:
  REQUIRE_THROWS_AS(t.sampleBelow(rng, t.getXVals().front() - 1e-9),
                    pt::Error::BadInput);

  // at or above the last grid point sampleBelow must degenerate to the
  // untruncated sample(): with identical seeds the two streams must agree
  // draw by draw (exact, no statistics involved).
  reseedRNG(97531u);
  std::vector<double> plain(100);
  for (int i = 0; i < 100; ++i)
    plain[i] = t.sample(rng);
  reseedRNG(97531u);
  for (int i = 0; i < 100; ++i)
    CHECK(t.sampleBelow(rng, t.getXVals().back()) == plain[i]);
}
