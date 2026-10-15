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

// Window kernels of Trj/Window.cc not covered by test_tak_window.cc, checked
// against numpy/scipy-consistent formulas and symmetry/normalisation properties.

#include "../doctest.h"

#include "Window.hh"
#include "PTMath.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

// Window.hh declares blackmann() (C linkage) but Trj/Window.cc defines blackman()
// with C++ linkage, and both Window.hh and Filon.hh use the same include guard
// ("Filon_hh"), so only one of the two headers can be included per translation unit.
// Declare the actual definition here so the reference resolves.
void blackman(unsigned M, double *window);

static double hanningFormula(double i, double M)
{
  return 0.5 * (1 - std::cos(2 * M_PI * i / (M - 1)));
}

static double blackmanPeriodicFormula(double i, double M)
{
  // periodic (DFT-even) convention, denominator M (scipy sym=False); numpy.blackman
  // uses the symmetric denominator M-1 and therefore differs from this implementation
  return 0.42 - 0.5 * std::cos(2 * M_PI * i / M) + 0.08 * std::cos(4 * M_PI * i / M);
}

TEST_CASE("hanning_vs_numpy")
{
  // np.hanning(9)
  const double ref[] = {0.0, 0.14644660940672624, 0.49999999999999994, 0.8535533905932737,
                        1.0, 0.8535533905932737, 0.49999999999999994, 0.14644660940672624,
                        0.0};
  std::vector<double> w(9, 0.0);
  hanning(9, w.data());
  for (unsigned i = 0; i < 9; ++i) {
    CHECK(pt::floateq(w[i], ref[i], 1e-9, 1e-12));
    CHECK(pt::floateq(w[i], hanningFormula(i, 9.0), 1e-12, 1e-15));
  }
}

TEST_CASE("blackman_periodic_formula")
{
  std::vector<double> w(9, 0.0);
  blackman(9, w.data());
  for (unsigned i = 0; i < 9; ++i) {
    CHECK(pt::floateq(w[i], blackmanPeriodicFormula(i, 9.0), 1e-12, 1e-15));
    // periodic window wraps around: w[i] == w[M-i]
    CHECK(pt::floateq(w[i], blackmanPeriodicFormula((9 - i) % 9, 9.0), 1e-9, 1e-12));
  }
  // edge value is zero up to double rounding (0.42 - 0.5 + 0.08)
  CHECK(std::fabs(w[0]) < 1e-12);
  // pinned interior value
  CHECK(pt::floateq(w[1], 0.050869632653865, 1e-9, 1e-12));
}

TEST_CASE("gauss_formula")
{
  const unsigned M = 16;
  const double alpha = 2.5;
  std::vector<double> w(M, 0.0);
  gauss(alpha, M, w.data());
  CHECK(w[0] == 1.0);
  for (unsigned i = 0; i < M; ++i) {
    double x = 2 * alpha * i / double(M);
    double ref = std::exp(-0.5 * x * x);
    CHECK(pt::floateq(w[i], ref, 1e-12, 1e-15));
  }
}

TEST_CASE("hft_direct_evaluation")
{
  const unsigned M = 64;
  std::vector<double> w(M, 0.0);
  hft(M, w.data());
  for (unsigned i = 0; i < M; ++i) {
    double x = i * 2 * M_PI / M;
    double ref = 1. - 1.985844164102 * std::cos(x) + 1.791176438506 * std::cos(2 * x)
      - 1.282075284005 * std::cos(3 * x) + 0.667777530266 * std::cos(4 * x)
      - .240160796576 * std::cos(5 * x) + 0.056656381764 * std::cos(6 * x)
      - .008134974479 * std::cos(7 * x) + 0.000624544650 * std::cos(8 * x)
      - .000019808998 * std::cos(9 * x) + 0.000000132974 * std::cos(10 * x);
    CHECK(pt::floateq(w[i], ref, 1e-12, 1e-15));
  }
  // the coefficient sum vanishes at the edge and the flat-top centre peaks at ~7.03
  CHECK(std::fabs(w[0]) < 1e-12);
  CHECK(pt::floateq(w[M / 2], 7.032470056320, 1e-9, 1e-9));
}

TEST_CASE("kaiser_symmetry")
{
  for (unsigned M : {8u, 9u}) {
    std::vector<double> w(M, 0.0);
    kaiser(12, M, w.data());
    for (unsigned i = 0; i < M / 2; ++i)
      CHECK(w[i] == w[M - 1 - i]); // bitwise symmetric by construction
  }
}

TEST_CASE("kaiser_center_and_numpy_pin")
{
  std::vector<double> w(9, 0.0);
  kaiser(5, 9, w.data());
  CHECK(w[4] == 1.0); // centre is exactly one for odd M
  // np.kaiser(9, 12) regression pin (same reference values as test_tak_window.cc)
  std::vector<double> w12(9, 0.0);
  kaiser(12, 9, w12.data());
  const double ref[] = {5.27734413e-05, 2.12783766e-02, 2.15672745e-01, 6.94516009e-01,
                        1.00000000e+00, 6.94516009e-01, 2.15672745e-01, 2.12783766e-02,
                        5.27734413e-05};
  for (unsigned i = 0; i < 9; ++i)
    CHECK(pt::floateq(w12[i], ref[i], 1e-8, 1e-12)); // literals carry 8-digit rounding
}

TEST_CASE("kaiser_zero_beta_is_ones")
{
  for (unsigned M : {8u, 9u}) {
    std::vector<double> w(M, 0.0);
    kaiser(0, M, w.data());
    for (unsigned i = 0; i < M; ++i)
      CHECK(w[i] == 1.0);
  }
}

TEST_CASE("window_bounds_and_rise")
{
  // kaiser/hanning/blackman/gauss live in [0, 1]; the flat-top hft spans about
  // [-0.44, 7.04] for M=64 (envelope pinned from a reference run)
  std::vector<double> kaiser16(16, 0.0), hann16(16, 0.0), black16(16, 0.0), gauss16(16, 0.0);
  kaiser(12, 16, kaiser16.data());
  hanning(16, hann16.data());
  blackman(16, black16.data());
  gauss(2.5, 16, gauss16.data());
  const std::vector<double> *all[] = {&kaiser16, &hann16, &black16, &gauss16};
  for (const auto *w : all) {
    for (unsigned i = 0; i < 16; ++i) {
      CHECK((*w)[i] > -1e-9);
      CHECK((*w)[i] < 1.0 + 1e-9);
      CHECK(std::isfinite((*w)[i]));
    }
  }
  // kaiser/hanning/blackman rise from a near-zero edge towards the centre
  CHECK(kaiser16[0] < kaiser16[8]);
  CHECK(hann16[0] < hann16[8]);
  CHECK(black16[0] < black16[8]);
  // this gauss convention peaks at the edge and decays monotonically
  CHECK(gauss16[0] == 1.0);
  CHECK(gauss16[8] < gauss16[4]);

  std::vector<double> hf(64, 0.0);
  hft(64, hf.data());
  double mn = hf[0], mx = hf[0];
  for (unsigned i = 0; i < 64; ++i) {
    CHECK(std::isfinite(hf[i]));
    mn = std::min(mn, hf[i]);
    mx = std::max(mx, hf[i]);
  }
  CHECK(mn > -0.5);
  CHECK(mx < 7.1);
  CHECK(hf[0] < hf[32]);
}
