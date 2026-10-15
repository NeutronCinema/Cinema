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

// Pure numerical kernels of Trj/Utils.cc and Utils/PTMath.icc, checked against
// analytic references and numpy-consistent values. No file IO, sub-millisecond bodies.

#include "../doctest.h"

#include "Utils.hh"
#include "PTMath.hh"

#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace pt = Prompt;

TEST_CASE("minMaxQ_elastic")
{
  // Elastic scattering (enout == enin): q ranges from 0 (forward) to 2*k0 (backward)
  double enin = 0.0253; // eV
  double k0 = eKin2k(enin);
  auto mm = minMaxQ(enin, enin);
  CHECK(mm.first == doctest::Approx(0.0));
  CHECK(mm.second == doctest::Approx(2 * k0));
  // cross check against the independent angle-cosine kernel
  CHECK(pt::neutronAngleCosine2Q(1.0, enin, enin) == doctest::Approx(mm.first));
  CHECK(pt::neutronAngleCosine2Q(-1.0, enin, enin) == doctest::Approx(mm.second));
}

TEST_CASE("minMaxQ_inelastic")
{
  // Inelastic scattering: qmin = k0*sqrt(1+r-2*sqrt(r)), qmax = k0*sqrt(1+r+2*sqrt(r))
  double enin = 1.0;
  double k0 = eKin2k(enin);
  {
    double ratio = 2.0; // energy gain (enout > enin)
    auto mm = minMaxQ(enin, enin * ratio);
    double s = std::sqrt(ratio);
    CHECK(mm.first == doctest::Approx(k0 * std::sqrt(1 + ratio - 2 * s)));
    CHECK(mm.second == doctest::Approx(k0 * std::sqrt(1 + ratio + 2 * s)));
  }
  {
    double ratio = 0.25; // energy loss
    auto mm = minMaxQ(enin, enin * ratio);
    double s = std::sqrt(ratio);
    CHECK(mm.first == doctest::Approx(k0 * std::sqrt(1 + ratio - 2 * s))); // 0.5*k0
    CHECK(mm.second == doctest::Approx(k0 * std::sqrt(1 + ratio + 2 * s))); // 1.5*k0
  }
}

TEST_CASE("minMaxQ_negative_energy_throws")
{
  CHECK_THROWS_AS(minMaxQ(1.0, -1e-12), std::runtime_error);
}

TEST_CASE("lininterp_endpoints_and_midpoint")
{
  CHECK(lininterp(0.0, 10.0, 1.0, 20.0, 0.0) == doctest::Approx(10.0));
  CHECK(lininterp(0.0, 10.0, 1.0, 20.0, 1.0) == doctest::Approx(20.0));
  CHECK(lininterp(0.0, 10.0, 1.0, 20.0, 0.5) == doctest::Approx(15.0));
  // a second, asymmetric interval
  CHECK(lininterp(2.0, 4.0, 6.0, 12.0, 3.0) == doctest::Approx(6.0));
  CHECK(lininterp(2.0, 4.0, 6.0, 12.0, 6.0) == doctest::Approx(12.0));
}

TEST_CASE("nextGoodFFTNumber_round_up_to_pow2")
{
  CHECK(nextGoodFFTNumber(100.0) == 128u);
  CHECK(nextGoodFFTNumber(128.0) == 128u); // exact power of two stays
  CHECK(nextGoodFFTNumber(129.0) == 256u);
  CHECK(nextGoodFFTNumber(64.0) == 64u);
  CHECK(nextGoodFFTNumber(3.0) == 4u);
}

TEST_CASE("fftfreq_matches_numpy")
{
  // numpy.fft.fftfreq(8) == [0, 1/8, 2/8, 3/8, -4/8, -3/8, -2/8, -1/8]
  auto f = fftfreq(8);
  REQUIRE(f.size() == 8u);
  const double ref[] = {0.0, 0.125, 0.25, 0.375, -0.5, -0.375, -0.25, -0.125};
  for (unsigned i = 0; i < 8; ++i)
    CHECK(f[i] == doctest::Approx(ref[i]));
  // first half positive ascending, second half negative ascending
  for (unsigned i = 0; i < 3; ++i)
    CHECK(f[i] < f[i + 1]);
  auto f4 = fftfreq(4);
  REQUIRE(f4.size() == 4u);
  CHECK(f4[0] == doctest::Approx(0.0));
  CHECK(f4[1] == doctest::Approx(0.25));
  CHECK(f4[2] == doctest::Approx(-0.5));
  CHECK(f4[3] == doctest::Approx(-0.25));
}

TEST_CASE("fftshift_vector_matches_numpy")
{
  // numpy.fft.fftshift([0,1,2,3]) == [2,3,0,1]
  std::vector<double> even{0.0, 1.0, 2.0, 3.0};
  fftshift(even);
  REQUIRE(even.size() == 4u);
  CHECK(even[0] == doctest::Approx(2.0));
  CHECK(even[1] == doctest::Approx(3.0));
  CHECK(even[2] == doctest::Approx(0.0));
  CHECK(even[3] == doctest::Approx(1.0));
  // numpy.fft.fftshift([0,1,2,3,4]) == [3,4,0,1,2]
  std::vector<double> odd{0.0, 1.0, 2.0, 3.0, 4.0};
  fftshift(odd);
  REQUIRE(odd.size() == 5u);
  const double ref[] = {3.0, 4.0, 0.0, 1.0, 2.0};
  for (unsigned i = 0; i < 5; ++i)
    CHECK(odd[i] == doctest::Approx(ref[i]));
}

TEST_CASE("trapz_constant_function")
{
  // area under a constant function is exactly base*height
  std::vector<double> x{0.0, 1.0, 2.0};
  std::vector<double> y{3.0, 3.0, 3.0};
  CHECK(trapz(y, x) == doctest::Approx(6.0));
  // pointer overload gives the same value
  CHECK(trapz(y.data(), x.data(), y.size()) == doctest::Approx(6.0));
}

TEST_CASE("trapz_identity_and_size_mismatch")
{
  // integral of y = x on [0,1] is 0.5
  std::vector<double> x{0.0, 1.0};
  std::vector<double> y{0.0, 1.0};
  CHECK(trapz(y, x) == doctest::Approx(0.5));
  // mismatched sizes must throw
  std::vector<double> shortVec(1, 1.0);
  CHECK_THROWS_AS(trapz(y, shortVec), std::runtime_error);
}

TEST_CASE("stableSum_cancellation")
{
  // naive summation loses the 1.0; Neumaier compensation recovers it exactly
  std::vector<double> v{1e16, 1.0, -1e16};
  double naive = 0.0;
  for (double d : v)
    naive += d;
  CHECK(naive == 0.0); // pin the catastrophic cancellation
  CHECK(stableSum(v) == 1.0);
  CHECK(stableSum(v.data(), v.size()) == 1.0);
  // no-cancellation case agrees with the exact total
  std::vector<double> w{1.0, 2.0, 3.5};
  CHECK(stableSum(w) == doctest::Approx(6.5));
}

TEST_CASE("linspace_logspace_endpoints")
{
  auto lin = linspace(1.0, 10.0, 10);
  REQUIRE(lin.size() == 10u);
  CHECK(lin.front() == doctest::Approx(1.0));
  CHECK(lin.back() == doctest::Approx(10.0));
  CHECK(lin[2] == doctest::Approx(3.0)); // unit spacing
  auto lin2 = linspace(0.0, 1.0, 5);
  REQUIRE(lin2.size() == 5u);
  CHECK(lin2[1] == doctest::Approx(0.25));
  CHECK(lin2[3] == doctest::Approx(0.75));

  auto log = logspace(0.0, 2.0, 5);
  REQUIRE(log.size() == 5u);
  CHECK(log.front() == doctest::Approx(1.0));   // 10^0
  CHECK(log[2] == doctest::Approx(10.0));       // 10^1
  CHECK(log.back() == doctest::Approx(100.0));  // 10^2
}

TEST_CASE("ekin2wl_wl2ekin_roundtrip")
{
  const double energies[] = {1e-3, 0.0253, 1.0, 100.0};
  for (double e : energies) {
    double wl = pt::ekin2wl(e);
    CHECK(wl > 0.0);
    CHECK(pt::wl2ekin(wl) == doctest::Approx(e).epsilon(1e-12));
  }
  // pinned conversion constant: ekin2wl(1 eV) == sqrt(0.081804209605330899)
  CHECK(pt::ekin2wl(1.0) ==
        doctest::Approx(std::sqrt(0.081804209605330899)).epsilon(1e-15));
  // E = 0 maps to the largest representable wavelength, and back to zero energy
  CHECK(pt::ekin2wl(0.0) == std::numeric_limits<double>::max());
  CHECK(pt::wl2ekin(std::numeric_limits<double>::max()) == 0.0);
}
