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

// Statistical moments of the gun samplers over 10k seeded samples. These
// cases replace the assertion-free test_isotropicgun: every sampler is
// checked against its analytical distribution (mean, variance, bound) with
// tolerances well above the sampling fluctuations of 10k draws, so the
// assertions stay stable for the fixed seeds used here.
// NB: doctest's Approx carries an absolute floor of epsilon*scale with the
// default scale=1; the sampled quantities here are eV-scale or smaller, so
// every moment check passes .scale(0.) to keep the epsilon a pure relative
// window as commented.

#include "../doctest.h"

#include "PTIsotropicGun.hh"
#include "PTMaxwellianGun.hh"
#include "PTUniModeratorGun.hh"
#include "PTSimpleThermalGun.hh"
#include "PTNeutron.hh"
#include "PTRandCanonical.hh"
#include "PTMath.hh"
#include "PTVector.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

namespace {

// Re-seed the shared prompt RNG so every case below is deterministic and
// independent of the order in which doctest runs the cases.
void seedGunRng(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

double meanOf(const std::vector<double> &v)
{
  double s = 0.;
  for(double x : v)
    s += x;
  return s / static_cast<double>(v.size());
}

double varianceOf(const std::vector<double> &v)
{
  double m = meanOf(v);
  double s = 0.;
  for(double x : v)
    s += (x - m) * (x - m);
  return s / static_cast<double>(v.size());
}

} // namespace

TEST_CASE("isotropic_gun_direction_moments")
{
  // IsotropicGun samples uniformly on the unit sphere, hence the cosine of
  // the polar angle (any fixed component) is uniform in [-1,1]:
  // mean 0 and variance 1/3.
  seedGunRng(20260701);
  pt::IsotropicGun gun(pt::Neutron(), 0.0253, pt::Vector(0., 0., -12000.));
  const unsigned n = 10000;
  std::vector<double> cosz;
  cosz.reserve(n);
  for(unsigned i = 0; i < n; i++)
    cosz.push_back(gun.generate()->getDirection().z());

  double mean = meanOf(cosz);
  double var = varianceOf(cosz);
  // standard error of the mean is 1/sqrt(3n) ~ 0.006, so 0.02 is >3 sigma
  CHECK(mean > -0.02);
  CHECK(mean < 0.02);
  // the variance estimator itself has ~0.6% relative std at 10k draws; the
  // pinned seed realises ~2%, so 5% leaves a comfortable margin
  CHECK(var == doctest::Approx(1. / 3.).epsilon(0.05).scale(0.));
}

TEST_CASE("isotropic_gun_direction_unit_norm")
{
  seedGunRng(20260702);
  pt::IsotropicGun gun(pt::Neutron(), 0.0253, pt::Vector(0., 0., -12000.));
  const unsigned n = 10000;
  double maxdev = 0.;
  for(unsigned i = 0; i < n; i++)
  {
    double mag2 = gun.generate()->getDirection().mag2();
    double dev = std::abs(mag2 - 1.);
    if(dev > maxdev)
      maxdev = dev;
  }
  CHECK(maxdev < 1e-12);
}

TEST_CASE("maxwellian_gun_mean_energy")
{
  // MaxwellianGun samples wl = wlT/sqrt(-ln(u1*u2)) with wlT=ekin2wl(kT),
  // which makes E/kT the sum of two unit exponentials, i.e. Gamma(2,1):
  // mean E = 2kT.
  seedGunRng(20260703);
  const double temperature = 300.;
  const double kT = temperature * pt::const_boltzmann;
  pt::MaxwellianGun gun(pt::Neutron(), temperature, {1., 1., -1400., 1., 1., 0.});
  const unsigned n = 10000;
  double sum = 0.;
  for(unsigned i = 0; i < n; i++)
    sum += gun.generate()->getEKin();
  double mean = sum / n;
  CHECK(mean == doctest::Approx(2. * kT).epsilon(0.03).scale(0.));
}

TEST_CASE("maxwellian_gun_energy_variance")
{
  // Var of a Gamma(2,1) distributed E/kT is 2, i.e. Var(E) = 2(kT)^2.
  // The relative standard deviation of the variance estimator itself is
  // ~5% at 10k samples, hence the loose 12% window.
  seedGunRng(20260704);
  const double temperature = 300.;
  const double kT = temperature * pt::const_boltzmann;
  pt::MaxwellianGun gun(pt::Neutron(), temperature, {1., 1., -1400., 1., 1., 0.});
  const unsigned n = 10000;
  std::vector<double> ekin;
  ekin.reserve(n);
  for(unsigned i = 0; i < n; i++)
    ekin.push_back(gun.generate()->getEKin());
  double var = varianceOf(ekin);
  CHECK(var == doctest::Approx(2. * kT * kT).epsilon(0.12).scale(0.));
}

TEST_CASE("maxwellian_gun_cumulative_fraction")
{
  // P(E < 2kT) for Gamma(2,1) is 1 - exp(-2)(1+2) = 1 - 3exp(-2) ~ 0.594.
  seedGunRng(20260705);
  const double temperature = 300.;
  const double kT = temperature * pt::const_boltzmann;
  pt::MaxwellianGun gun(pt::Neutron(), temperature, {1., 1., -1400., 1., 1., 0.});
  const unsigned n = 10000;
  unsigned below = 0;
  for(unsigned i = 0; i < n; i++)
  {
    if(gun.generate()->getEKin() < 2. * kT)
      below++;
  }
  double frac = static_cast<double>(below) / n;
  CHECK(frac == doctest::Approx(1. - 3. * std::exp(-2.)).epsilon(0.02).scale(0.));
}

TEST_CASE("maxwellian_gun_source_position_bounds")
{
  // The moderator position is sampled uniformly on the source rectangle at
  // the fixed source z: pos.z == src_z and |x|,|y| within half the widths.
  seedGunRng(20260706);
  const std::array<double, 6> size = {100., 50., -1400., 5., 10., 0.};
  pt::MaxwellianGun gun(pt::Neutron(), 293.15, size);
  const unsigned n = 1000;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    const pt::Vector &pos = p->getPosition();
    CHECK(pos.z() == doctest::Approx(size[2]).epsilon(1e-12));
    CHECK(std::abs(pos.x()) <= 0.5 * size[0]);
    CHECK(std::abs(pos.y()) <= 0.5 * size[1]);
  }
}

TEST_CASE("maxwellian_gun_direction_hits_slit")
{
  // The sampled direction is the line from the moderator point to a uniform
  // point on the slit rectangle: its intersection with the slit plane must
  // lie inside the slit bounds.
  seedGunRng(20260707);
  const double src_w = 100., src_h = 50., src_z = -100.;
  const double slit_w = 5., slit_h = 10., slit_z = 0.;
  pt::MaxwellianGun gun(pt::Neutron(), 293.15,
                        {src_w, src_h, src_z, slit_w, slit_h, slit_z});
  const unsigned n = 100;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    const pt::Vector &pos = p->getPosition();
    const pt::Vector &dir = p->getDirection();
    // line-plane intersection with the slit plane z == slit_z
    double t = (slit_z - pos.z()) / dir.z();
    double ix = pos.x() + t * dir.x();
    double iy = pos.y() + t * dir.y();
    // tiny relative slack for the direction normalisation rounding
    CHECK(ix <= 0.5 * slit_w * (1. + 1e-9) + 1e-9);
    CHECK(ix >= -0.5 * slit_w * (1. + 1e-9) - 1e-9);
    CHECK(iy <= 0.5 * slit_h * (1. + 1e-9) + 1e-9);
    CHECK(iy >= -0.5 * slit_h * (1. + 1e-9) - 1e-9);
  }
}

TEST_CASE("uni_moderator_gun_wavelength_uniform_bounds")
{
  // UniModeratorGun samples the wavelength uniformly in
  // [wl0-dlt/2, wl0+dlt/2]; recover it from the energy and check bounds,
  // mean and spread of the uniform law.
  seedGunRng(20260708);
  const double wl0 = 3.39, dlt = 0.3;
  pt::UniModeratorGun gun(pt::Neutron(), wl0, dlt, {100., 50., -400., 5., 10., 1.});
  const unsigned n = 10000;
  std::vector<double> wl;
  wl.reserve(n);
  for(unsigned i = 0; i < n; i++)
  {
    double w = pt::ekin2wl(gun.generate()->getEKin());
    CHECK(w <= wl0 + 0.5 * dlt);
    CHECK(w >= wl0 - 0.5 * dlt);
    wl.push_back(w);
  }
  double mean = meanOf(wl);
  double var = varianceOf(wl);
  CHECK(mean == doctest::Approx(wl0).epsilon(0.02).scale(0.));
  // uniform variance is dlt^2/12 ~ 0.0075
  CHECK(var == doctest::Approx(dlt * dlt / 12.).epsilon(0.05).scale(0.));
}

TEST_CASE("simple_thermal_gun_fixed_energy")
{
  // A positive m_ekin is returned unchanged, with the configured position
  // and direction.
  pt::SimpleThermalGun gun(pt::Neutron(), 0.05, pt::Vector(0., 0., -500.),
                           pt::Vector(0., 0., 1.));
  const unsigned n = 100;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    CHECK(p->getEKin() == doctest::Approx(0.05).epsilon(1e-12));
    CHECK(p->getPosition().z() == doctest::Approx(-500.).epsilon(1e-12));
    CHECK(p->getDirection().mag2() == doctest::Approx(1.).epsilon(1e-12));
  }
}

TEST_CASE("simple_thermal_gun_zero_energy_maxwellian")
{
  // m_ekin == 0 activates the boiling-spectrum law
  // E = 0.0253*(-ln u1 - ln u2 * cos^2(pi u / 2)) whose mean factor is
  // E[A] + E[B]*E[cos^2] = 1 + 1*1/2 = 1.5.
  seedGunRng(20260710);
  pt::SimpleThermalGun gun(pt::Neutron(), 0., pt::Vector(0., 0., -12000.));
  const unsigned n = 10000;
  double sum = 0.;
  for(unsigned i = 0; i < n; i++)
    sum += gun.generate()->getEKin();
  double mean = sum / n;
  CHECK(mean == doctest::Approx(1.5 * 0.0253).epsilon(0.05).scale(0.));
}
