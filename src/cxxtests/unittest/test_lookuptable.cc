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

#include "PTLookUpTable.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

TEST_CASE("LookUpTable get at knots returns the table values")
{
  std::vector<double> x = {1., 2., 3., 4.};
  std::vector<double> f = {10., 20., 30., 40.};

  // interior knots are exact (the interpolation formula degenerates to f[i])
  pt::LookUpTable t(x, f); // default extrapolation kZero_Zero
  CHECK(t.get(2.) == doctest::Approx(20.));
  CHECK(t.get(3.) == doctest::Approx(30.));
  // the upper knot is also reached by interpolation (lower_bound stops
  // before end()), so it is exact even for kZero_Zero
  CHECK(t.get(4.) == doctest::Approx(40.));

  // the FIRST knot is routed to the lower-extrapolation hook (lower_bound
  // returns begin()), so its value is the hook's, not f.front():
  // 0 for kZero_Zero, but exactly f.front() for kConst_Zero
  CHECK(t.get(1.) == doctest::Approx(0.));

  pt::LookUpTable tc(x, f, pt::LookUpTable::kConst_Zero);
  CHECK(tc.get(1.) == doctest::Approx(10.)); // == f.front()
  CHECK(tc.get(2.) == doctest::Approx(20.));
  CHECK(tc.get(4.) == doctest::Approx(40.));
}

TEST_CASE("LookUpTable linear interpolation is exact and monotone in range")
{
  // f = 2x
  std::vector<double> x = {1., 2., 4., 8.};
  std::vector<double> f = {2., 4., 8., 16.};
  pt::LookUpTable t(x, f, pt::LookUpTable::kConst_Zero);

  CHECK(t.get(1.5) == doctest::Approx(3.));
  CHECK(t.get(3.) == doctest::Approx(6.));
  CHECK(t.get(5.) == doctest::Approx(10.));
  CHECK(t.get(6.) == doctest::Approx(12.));

  // piecewise-linear interpolation of a monotone table stays monotone and
  // stays inside [f.front(), f.back()] over a fixed in-range grid
  double prev = -1e300;
  for (int i = 1; i <= 100; ++i) {
    double xt = 1. + 7. * i / 100.; // strictly inside (x.front(), x.back()]
    double v = t.get(xt);
    CHECK(v >= prev);
    CHECK(v >= 2.);
    CHECK(v <= 16.);
    prev = v;
  }
}

TEST_CASE("LookUpTable kZero_Zero extrapolates zero on both sides")
{
  std::vector<double> x = {1., 2., 3., 4.};
  std::vector<double> f = {10., 20., 30., 40.};
  pt::LookUpTable t(x, f, pt::LookUpTable::kZero_Zero);

  CHECK(t.get(0.5) == doctest::Approx(0.));
  CHECK(t.get(-7.) == doctest::Approx(0.));
  CHECK(t.get(4.5) == doctest::Approx(0.));
  CHECK(t.get(1e6) == doctest::Approx(0.));
}

TEST_CASE("LookUpTable kConst_Zero: constant below the range, zero above")
{
  std::vector<double> x = {1., 2., 3., 4.};
  std::vector<double> f = {10., 20., 30., 40.};
  pt::LookUpTable t(x, f, pt::LookUpTable::kConst_Zero);

  CHECK(t.get(0.25) == doctest::Approx(10.)); // f.front()
  CHECK(t.get(-1.) == doctest::Approx(10.));
  CHECK(t.get(5.) == doctest::Approx(0.));
  CHECK(t.get(1e6) == doctest::Approx(0.));
  // upper knot itself is still interpolated exactly
  CHECK(t.get(4.) == doctest::Approx(40.));
}

TEST_CASE("LookUpTable kZero_Const: zero below the range, constant above")
{
  std::vector<double> x = {1., 2., 3., 4.};
  std::vector<double> f = {10., 20., 30., 40.};
  pt::LookUpTable t(x, f, pt::LookUpTable::kZero_Const);

  CHECK(t.get(0.99) == doctest::Approx(0.));
  CHECK(t.get(-1.) == doctest::Approx(0.));
  CHECK(t.get(4.2) == doctest::Approx(40.)); // f.back()
  CHECK(t.get(100.) == doctest::Approx(40.));
}

TEST_CASE("LookUpTable kOverX_Zero and kOverSqrtX_Zero formulas and error paths")
{
  // 1/x-type lower extrapolation: f0*x0/x, defined for any x != 0
  std::vector<double> x1 = {1., 2.};
  std::vector<double> f1 = {10., 20.};
  pt::LookUpTable toverx(x1, f1, pt::LookUpTable::kOverX_Zero);
  CHECK(toverx.get(0.5) == doctest::Approx(10. * 1. / 0.5));
  CHECK(toverx.get(-4.) == doctest::Approx(10. * 1. / -4.)); // negative x allowed
  CHECK(toverx.get(3.) == doctest::Approx(0.)); // zero beyond the upper bound
  REQUIRE_THROWS_AS(toverx.get(0.), Prompt::Error::CalcError);

  // 1/sqrt(x)-type lower extrapolation: f0*sqrt(x0/x), requires x > 0
  std::vector<double> x2 = {1., 4.};
  std::vector<double> f2 = {10., 20.};
  pt::LookUpTable tsqrt(x2, f2, pt::LookUpTable::kOverSqrtX_Zero);
  CHECK(tsqrt.get(0.25) == doctest::Approx(10. * std::sqrt(1. / 0.25)));
  CHECK(tsqrt.get(9.) == doctest::Approx(0.));
  REQUIRE_THROWS_AS(tsqrt.get(0.), Prompt::Error::CalcError);
  REQUIRE_THROWS_AS(tsqrt.get(-1.), Prompt::Error::CalcError);
}

TEST_CASE("LookUpTable kOverSqrtX_OverSqrtX and kConst_OverSqrtX both-side formulas")
{
  std::vector<double> x = {1., 4.};
  std::vector<double> f = {10., 20.};

  pt::LookUpTable tboth(x, f, pt::LookUpTable::kOverSqrtX_OverSqrtX);
  CHECK(tboth.get(0.25) == doctest::Approx(10. * std::sqrt(1. / 0.25))); // lower
  CHECK(tboth.get(16.) == doctest::Approx(20. * std::sqrt(4. / 16.)));   // upper
  CHECK(tboth.get(2.) == doctest::Approx(10. + 10. * (2. - 1.) / (4. - 1.))); // in range: linear

  pt::LookUpTable tconst(x, f, pt::LookUpTable::kConst_OverSqrtX);
  CHECK(tconst.get(0.25) == doctest::Approx(10.));                     // f.front()
  CHECK(tconst.get(16.) == doctest::Approx(20. * std::sqrt(4. / 16.)));
  CHECK(tconst.get(100.) == doctest::Approx(20. * std::sqrt(4. / 100.)));
}

TEST_CASE("LookUpTable sanityCheck, empty state and unimplemented integrate")
{
  // default-constructed table is empty and fails sanityCheck
  pt::LookUpTable tdef;
  CHECK(tdef.empty());
  REQUIRE_THROWS_AS(tdef.sanityCheck(), Prompt::Error::BadInput);

  // size mismatch
  std::vector<double> x2 = {1., 2.};
  std::vector<double> f1 = {1.};
  std::vector<double> fx = {1., 3., 2.}; // wrong size: 3 vs 2 (sanityCheck never sorts f)
  std::vector<double> f2 = {10., 20.};
  std::vector<double> xrev = {2., 1.};
  REQUIRE_THROWS_AS(pt::LookUpTable(x2, f1), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::LookUpTable(x2, fx), Prompt::Error::BadInput);
  REQUIRE_THROWS_AS(pt::LookUpTable(xrev, f2), Prompt::Error::BadInput);

  // a valid table is not empty and passes sanityCheck
  pt::LookUpTable t(x2, f2);
  CHECK_FALSE(t.empty());
  CHECK_NOTHROW(t.sanityCheck());

  // integrate() is deliberately unimplemented - pin it so a future
  // implementation is a conscious change
  REQUIRE_THROWS_AS(t.integrate(1., 2.), Prompt::Error::CalcError);
}
