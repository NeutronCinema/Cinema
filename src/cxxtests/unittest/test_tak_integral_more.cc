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

// Filon quadrature kernels of Trj/Filon.cc not covered by test_tak_integral.cc:
// f(x)=x integrals, alpha/beta/gamma branch continuity at the series/closed-form
// switch points, tak_cal_limit closed forms, zero-time integral and tak_cal_PDF.

#include "../doctest.h"

#include "Filon.hh"
#include "PTMath.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

// Internal helper of Trj/Filon.cc: not declared in Filon.hh (and Window.hh cannot be
// included here since both headers share the "Filon_hh" include guard). It is defined
// with C++ linkage, so a plain declaration resolves against the same object file.
void alpha_beta_gamma_single(double theta, double &alpha, double &beta, double &gamma);

namespace {

// y = x sampled on [x0, x1] with 2*panels+1 points (the Filon input layout)
void makeXy(std::vector<double> &x, std::vector<double> &y, unsigned panels, double x0,
            double x1)
{
  x.resize(2 * panels + 1);
  y.resize(2 * panels + 1);
  double h = (x1 - x0) / (2. * panels);
  for (unsigned i = 0; i <= 2 * panels; ++i) {
    x[i] = x0 + h * i;
    y[i] = x[i];
  }
}

} // namespace

TEST_CASE("tak_sin_integral_single_yeqx")
{
  // integral of x*sin(t*x) over [0,1]: (sin(t) - t*cos(t))/t^2 by parts.
  // t=0.5/1 exercise the small-theta series branch, t=100 the closed form branch.
  unsigned panels = 512;
  std::vector<double> x, y;
  makeXy(x, y, panels, 0.0, 1.0);
  for (double t : {0.5, 1.0, 100.0}) {
    double res = 0.0;
    tak_sin_integral_single(panels, x.data(), y.data(), t, res);
    double ref = (std::sin(t) - t * std::cos(t)) / (t * t);
    CHECK(pt::floateq(res, ref, 1e-12, 1e-15));
  }
}

TEST_CASE("tak_cos_integral_single_yeqx")
{
  // integral of x*cos(t*x) over [0,1]: (t*sin(t) + cos(t) - 1)/t^2 by parts
  unsigned panels = 512;
  std::vector<double> x, y;
  makeXy(x, y, panels, 0.0, 1.0);
  for (double t : {0.5, 1.0, 100.0}) {
    double res = 0.0;
    tak_cos_integral_single(panels, x.data(), y.data(), t, res);
    double ref = (t * std::sin(t) + std::cos(t) - 1.0) / (t * t);
    CHECK(pt::floateq(res, ref, 1e-12, 1e-15));
  }
}

TEST_CASE("alpha_beta_gamma_branch_continuity")
{
  // The series (small theta) and closed-form (large theta) expressions must agree
  // at the switch points 0.0218 / 0.0365 / 0.086; straddle each by 1e-6 relative.
  const double breakpoints[] = {0.0218, 0.0365, 0.086};
  for (double b : breakpoints) {
    double a1, be1, g1, a2, be2, g2;
    alpha_beta_gamma_single(b * (1 - 1e-6), a1, be1, g1);
    alpha_beta_gamma_single(b * (1 + 1e-6), a2, be2, g2);
    CHECK(std::fabs(a2 - a1) < 1e-8);
    CHECK(std::fabs(be2 - be1) < 1e-8);
    CHECK(std::fabs(g2 - g1) < 1e-8);
  }
  // the integral of y=x stays analytic to rounding level on both sides of each
  // branch switch (theta = h*t, h = 1/2048)
  unsigned panels = 1024;
  std::vector<double> x, y;
  makeXy(x, y, panels, 0.0, 1.0);
  double h = x[1] - x[0];
  for (double b : breakpoints) {
    for (double sgn : {-1.0, 1.0}) {
      double t = b * (1 + sgn * 1e-6) / h;
      double res = 0.0;
      tak_sin_integral_single(panels, x.data(), y.data(), t, res);
      double ref = (std::sin(t) - t * std::cos(t)) / (t * t);
      CHECK(std::fabs(res - ref) < 1e-12);
    }
  }
}

TEST_CASE("tak_cal_limit_closed_forms")
{
  // Gaussian S(omega); compare against an independent evaluation of the f0/f1
  // closed-form expressions used by tak_cal_limit
  const unsigned len = 65;
  std::vector<double> om(len), S(len);
  for (unsigned i = 0; i < len; ++i) {
    om[i] = 0.5 + 4.5 / (len - 1) * i;
    S[i] = std::exp(-om[i] * om[i] / (2 * 1.5 * 1.5));
  }
  const unsigned nt = 5;
  std::vector<double> tv(nt), lim(nt), limr(nt), limi(nt);
  for (unsigned i = 0; i < nt; ++i)
    tv[i] = 0.1 * (i + 1);
  double massNum = 12.0, T = 300.0;
  tak_cal_limit(massNum, T, om.data(), S.data(), nt, tv.data(), lim.data(), limr.data(),
                limi.data());

  double i_mbeta = pt::const_boltzmann * T / (pt::const_neutron_mass_evc2 * massNum);
  double hbar_m = pt::const_hbar / (pt::const_neutron_mass_evc2 * massNum);
  double hbarbeta = pt::const_hbar / pt::const_boltzmann / T;
  double step = om[1] - om[0];
  for (unsigned i = 0; i < nt; ++i) {
    double t = tv[i];
    double f0c = S[0] * i_mbeta * t * t;
    double f0r = f0c;
    double f0i = hbar_m * S[0] * t;
    double sv = std::sin(om[1] * t * 0.5);
    double f1c = 4 * S[1] * i_mbeta / (om[1] * om[1]) * sv * sv;
    double f1r = hbar_m * 2 * S[1] / om[1] * sv * sv * 1. / std::tanh(0.5 * hbarbeta * om[1]);
    double f1i = hbar_m * S[1] / om[1] * std::sin(om[1] * t);
    CHECK(pt::floateq(lim[i], (f0c + f1c) * step * 0.5, 1e-12, 1e-12));
    CHECK(pt::floateq(limr[i], (f0r + f1r) * step * 0.5, 1e-12, 1e-12));
    CHECK(pt::floateq(limi[i], (f0i + f1i) * step * 0.5, 1e-12, 1e-12));
  }
}

TEST_CASE("tak_cal_integral_zero_time")
{
  // at t = 0 the sine-transform of every gamma integrand vanishes
  const unsigned panels = 32;
  const unsigned len = 2 * panels + 1;
  std::vector<double> om(len), S(len, 0.0);
  for (unsigned i = 0; i < len; ++i) {
    om[i] = 0.5 + 4.5 / (len - 1) * i; // omega grid must exclude zero (1/omega^2)
    S[i] = std::exp(-om[i] * om[i] / 4.5);
  }
  double massNum = 12.0, T = 300.0;
  double t0 = 0.0;
  double gc = 123.0, gr = 456.0, gi = 789.0; // must be overwritten
  tak_cal_integral(massNum, T, panels, om.data(), S.data(), 1, &t0, &gc, &gr, &gi);
  CHECK(gc == 0.0);
  CHECK(gr == 0.0);
  CHECK(gi == 0.0);
}

TEST_CASE("tak_cal_PDF_zero_and_constant_offset")
{
  // g(r)-1 = 1/(2*pi^2*rho*r) * integral of q*(S(q)-1)*sin(qr) dq.
  // With S(q)-1 = 0 everywhere the PDF vanishes identically.
  const unsigned panels = 512;
  const unsigned len = 2 * panels + 1;
  std::vector<double> q(len);
  for (unsigned i = 0; i < len; ++i)
    q[i] = 0.5 + 9.5 / (2. * panels) * i;
  const unsigned nr = 7;
  std::vector<double> rv(nr), pdf(nr);
  for (unsigned i = 0; i < nr; ++i)
    rv[i] = 0.5 * (i + 1);
  double rho = 0.07;

  std::vector<double> zero(len, 0.0);
  tak_cal_PDF(rho, panels, q.data(), zero.data(), nr, rv.data(), pdf.data());
  for (unsigned i = 0; i < nr; ++i)
    CHECK(pdf[i] == 0.0);

  // constant offset S(q)-1 = c: the analytic reference follows from integrating
  // q*sin(qr) dq = [sin(qr)/r^2 - q*cos(qr)/r] over [qmin, qmax]
  const double c = 0.3, q0 = q.front(), q1 = q.back();
  std::vector<double> flat(len, c), pdf2(nr);
  tak_cal_PDF(rho, panels, q.data(), flat.data(), nr, rv.data(), pdf2.data());
  for (unsigned i = 0; i < nr; ++i) {
    double r = rv[i];
    double F = (std::sin(r * q1) / (r * r) - q1 * std::cos(r * q1) / r) -
               (std::sin(r * q0) / (r * r) - q0 * std::cos(r * q0) / r);
    double ref = c * 0.5 / (M_PI * M_PI) / rho / r * F;
    CHECK(pdf2[i] != 0.0);
    CHECK(pt::floateq(pdf2[i], ref, 1e-11, 1e-14));
  }
}
