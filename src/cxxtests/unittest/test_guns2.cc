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

// Second gun test file, complementary to test_gun_stats (sampling moments of
// the analytic guns) and test_gunfactory (factory dispatch). Covered here:
//  - every parameter-validation branch of GunFactory::createGun that the
//    first two files do not touch (negative energy, non-positive mean_wl,
//    negative range_wl, and the ==0 / ==0 boundary acceptances),
//  - the exact exception types of the PointwiseDist input guards backing the
//    MPIGun/SANSGun built-in spectra ("empty src arrays" and friends),
//  - the ModeratorGun divergence law shared by MPIGun/SANSGun: the horizontal
//    offset is the difference of two independent uniforms (trapezoid law with
//    closed-form CDF), and for a point slit the direction density on the
//    source rectangle is uniform, which gives an exact pi*r^2/(W*H)
//    solid-angle acceptance per direction ring,
//  - MPIGun/SANSGun energy spectra against quantiles derived independently
//    from the hardcoded tables (trapezoidal CDF reproduced offline),
//  - ModeratorGun emission-time structure (time 0, weight 1, eventid count),
//  - the PythonGun 9-double buffer contract (direct API and C ABI),
//  - the MCPLGun missing-file error path, made observable by installing a
//    throwing MCPL error handler (the default handler would exit(1)).
// Every sampled quantity uses a reseeded shared RNG; NB: doctest::Approx
// carries an absolute floor epsilon*scale, so all eV-scale checks below pass
// .scale(0.) to keep the epsilon purely relative.

#include "../doctest.h"

#include "PTGunFactory.hh"
#include "PTPrimaryGun.hh"
#include "PTMPIGun.hh"
#include "PTSANSGun.hh"
#include "PTUniModeratorGun.hh"
#include "PTIsotropicGun.hh"
#include "PTSimpleThermalGun.hh"
#include "PTPythonGun.hh"
#include "PTMCPLGun.hh"
#include "PTStackManager.hh"
#include "PTNeutron.hh"
#include "PTRandCanonical.hh"
#include "PTException.hh"
#include "PTMath.hh"
#include "PTVector.hh"

#include <mcpl.h>

#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>
#include <sys/types.h>
#include <unistd.h>

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

// Fraction of sampled values strictly below xstar.
double fractionBelow(const std::vector<double> &v, double xstar)
{
  std::size_t n = 0;
  for(double x : v)
    n += (x < xstar) ? 1u : 0u;
  return static_cast<double>(n) / static_cast<double>(v.size());
}

// Closed-form CDF of X = U(-a,a) + U(-b,b) (a >= b > 0): the horizontal
// offset of the ModeratorGun direction is sx - mx with mx, sx uniform on the
// source/slit widths, i.e. exactly this trapezoid law. With a = 50 (source
// width 100) and b = 5 (slit width 10) the integer pins below fall on the
// flat-top edges and read off as exact rationals.
double trapezoidCdf(double q, double a, double b)
{
  if(q <= -(a + b))
    return 0.;
  if(q <= -(a - b))
    return (q + a + b) * (q + a + b) / (8. * a * b);
  if(q <= (a - b))
    return (q + a) / (2. * a);
  if(q < (a + b))
    return 1. - (a + b - q) * (a + b - q) / (8. * a * b);
  return 1.;
}

// MCPL reports errors through a pluggable handler whose default action is
// printf + exit(1). To observe Cinema's missing-file error path as an
// exception (instead of killing the test process) we install a handler that
// throws this sentinel, and restore the library default afterwards.
// mcpl_default_error_handler is defined non-static in mcpl.c and exported by
// libmcpl, so the exact original behaviour can be re-installed.
struct McplRoutedError {
  const char *msg;
};
void mcplThrowingHandler(const char *msg) { throw McplRoutedError{msg}; }
extern "C" void mcpl_default_error_handler(const char *);

} // namespace

////////////////////////////////////////////////////////////////////////////////

TEST_CASE("gunfactory_simplethermal_negative_energy_throws")
{
  // SimpleThermalGun/IsotropicGun accept energy >= 0 only; the negative
  // branch must be a BadInput naming the offending parameter.
  try {
    pt::Singleton<pt::GunFactory>::getInstance().createGun(
        "gun=SimpleThermalGun;energy=-0.05;position=0,0,-500");
    CHECK_MESSAGE(false, "negative energy must be rejected");
  } catch (const pt::Error::BadInput &e) {
    std::string msg(e.what());
    CHECK(msg.find("energy") != std::string::npos);
    CHECK(msg.find("greater than or equal to 0") != std::string::npos);
  }
}

TEST_CASE("gunfactory_isotropic_negative_energy_throws_zero_accepted")
{
  // same guard on IsotropicGun ...
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=IsotropicGun;energy=-0.5;position=0,0,-10"),
                  pt::Error::BadInput);
  // ... with energy == 0 as the accepted boundary. An IsotropicGun created
  // with energy 0 inherits SimpleThermalGun's built-in boiling spectrum, so
  // every generated energy is strictly positive (never stuck at 0).
  seedGunRng(20261001);
  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=IsotropicGun;energy=0;position=0,0,-10");
  REQUIRE(gun != nullptr);
  for(unsigned i = 0; i < 5; i++)
    CHECK(gun->generate()->getEKin() > 0.);
}

TEST_CASE("gunfactory_unimoderator_wl_parameter_bounds")
{
  // UniModeratorGun requires mean_wl > 0 strictly ...
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=UniModeratorGun;mean_wl=0;range_wl=0.3;src_w=100;"
                      "src_h=50;src_z=-400;slit_w=5;slit_h=10;slit_z=1;"),
                  pt::Error::BadInput);
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=UniModeratorGun;mean_wl=-1;range_wl=0.3;src_w=100;"
                      "src_h=50;src_z=-400;slit_w=5;slit_h=10;slit_z=1;"),
                  pt::Error::BadInput);
  // ... and range_wl >= 0.
  CHECK_THROWS_AS(pt::Singleton<pt::GunFactory>::getInstance().createGun(
                      "gun=UniModeratorGun;mean_wl=3.39;range_wl=-0.5;src_w=100;"
                      "src_h=50;src_z=-400;slit_w=5;slit_h=10;slit_z=1;"),
                  pt::Error::BadInput);
  // range_wl == 0 is the accepted boundary and collapses the uniform law to
  // a delta: every generated wavelength (recovered from the energy) is
  // exactly mean_wl, i.e. every energy is wl2ekin(3.39).
  seedGunRng(20261002);
  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=UniModeratorGun;mean_wl=3.39;range_wl=0;src_w=100;"
      "src_h=50;src_z=-400;slit_w=5;slit_h=10;slit_z=1;");
  REQUIRE(gun != nullptr);
  const double expected = pt::wl2ekin(3.39);
  for(unsigned i = 0; i < 10; i++)
    CHECK(gun->generate()->getEKin() == doctest::Approx(expected).epsilon(1e-12));
}

TEST_CASE("pointwisedist_invalid_grids_throw_calcerror")
{
  // The MPIGun/SANSGun energy spectra are PointwiseDist objects; their input
  // guards define what happens for degenerate "src arrays". Every invalid
  // grid must fail loudly with the exact exception type CalcError, never
  // segfault. Empty arrays fall to the size<2 guard.
  std::vector<double> empty;
  std::vector<double> one{1.};
  std::vector<double> two{1., 2.};
  std::vector<double> three{1., 2., 3.};
  CHECK_THROWS_AS(pt::PointwiseDist(empty, empty), pt::Error::CalcError);
  CHECK_THROWS_AS(pt::PointwiseDist(one, one), pt::Error::CalcError);
  CHECK_THROWS_AS(pt::PointwiseDist(two, three), pt::Error::CalcError);
  std::vector<double> unsorted{1., 3., 2.};
  CHECK_THROWS_AS(pt::PointwiseDist(unsorted, three), pt::Error::CalcError);
  std::vector<double> negy{1., -1., 1.};
  CHECK_THROWS_AS(pt::PointwiseDist(three, negy), pt::Error::CalcError);
  std::vector<double> zeros{0., 0., 0.};
  CHECK_THROWS_AS(pt::PointwiseDist(three, zeros), pt::Error::CalcError);
}

TEST_CASE("sansgun_divergence_trapezoid_marginal_law")
{
  // ModeratorGun::samplePosDir (inherited by MPIGun/SANSGun) draws the
  // direction towards a uniform point on the slit from a uniform point on
  // the source, so the un-normalised horizontal offset dx = sx - mx is the
  // difference of U(-50,50) and U(-5,5): the trapezoid law with half widths
  // a=50, b=5 and closed-form CDF. dir is normalised with a fixed z
  // component L = 2000, hence dx = dir.x()/dir.z()*L. The quantile pins
  // {-45,-20,0,20,45} sit exactly on the analytic values
  // {0.05, 0.3, 0.5, 0.7, 0.95}.
  seedGunRng(20261003);
  pt::SANSGun gun(pt::Neutron(), {100., 50., -2000., 10., 10., 0.});
  const double L = 2000., a = 50., b = 5.;
  const unsigned n = 40000;
  const double qs[] = {-45., -20., 0., 20., 45.};
  unsigned below[5] = {0, 0, 0, 0, 0};
  unsigned outOfSupport = 0;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    const pt::Vector &dir = p->getDirection();
    if(dir.z() <= 0.)
      outOfSupport++; // flight path along +z: dz = L/|v| > 0 always
    double dx = dir.x() / dir.z() * L;
    if(std::abs(dx) > a + b)
      outOfSupport++;
    for(unsigned k = 0; k < 5; k++)
      if(dx < qs[k])
        below[k]++;
  }
  CHECK(outOfSupport == 0);
  const double expected[5] = {0.05, 0.3, 0.5, 0.7, 0.95};
  for(unsigned k = 0; k < 5; k++)
  {
    double obs = static_cast<double>(below[k]) / n;
    // binomial std at n=40000 is <= 0.0025, so 0.01 is a >3-sigma window
    CHECK(std::abs(obs - expected[k]) < 0.01);
    // and the closed form agrees with the pin at these points by construction
    CHECK(trapezoidCdf(qs[k], a, b) == doctest::Approx(expected[k]).epsilon(1e-12));
  }
}

TEST_CASE("mpigun_divergence_point_slit_solid_angle_rings")
{
  // With a zero-size slit the direction offset reduces to -moderator point:
  // dx, dy independent U(-5,5) on the 10x10 source. The probability that the
  // direction falls in the cone tan(theta) <= r/L is exactly the area
  // fraction of the disk of radius r*L/L = r on the rectangle: pi*r^2/(W*H),
  // valid while the disk fits inside (r <= W/2 = 5). Pinned rings:
  // cone r=2 and annulus 2 < rho < 4.
  seedGunRng(20261004);
  pt::MPIGun gun(pt::Neutron(), {10., 10., -2000., 0., 0., 0.});
  const double L = 2000., halfW = 5.;
  const unsigned n = 40000;
  unsigned cone = 0, ring = 0, outOfSquare = 0;
  unsigned dxBelow[3] = {0, 0, 0}; // dx < -2.5, < 0, < 2.5
  const double corner = std::sqrt(2. * halfW * halfW);
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    const pt::Vector &dir = p->getDirection();
    double dx = dir.x() / dir.z() * L;
    double dy = dir.y() / dir.z() * L;
    double rho = std::sqrt(dx * dx + dy * dy);
    if(rho > corner)
      outOfSquare++;
    if(rho < 2.)
      cone++;
    if(rho > 2. && rho < 4.)
      ring++;
    if(dx < -2.5)
      dxBelow[0]++;
    if(dx < 0.)
      dxBelow[1]++;
    if(dx < 2.5)
      dxBelow[2]++;
  }
  CHECK(outOfSquare == 0);
  const double coneExp = M_PI * 2. * 2. / (10. * 10.);   // 0.12566370614359174
  const double ringExp = M_PI * (16. - 4.) / (10. * 10.); // 0.37699111843077515
  double coneObs = static_cast<double>(cone) / n;
  double ringObs = static_cast<double>(ring) / n;
  CHECK(std::abs(coneObs - coneExp) < 0.01);
  CHECK(std::abs(ringObs - ringExp) < 0.01);
  // uniform marginal of dx: exact quartile pins of U(-5,5)
  const double uniExp[3] = {0.25, 0.5, 0.75};
  for(unsigned k = 0; k < 3; k++)
  {
    double obs = static_cast<double>(dxBelow[k]) / n;
    CHECK(std::abs(obs - uniExp[k]) < 0.01);
  }
}

TEST_CASE("moderatorgun_geometry_norm_position_structure")
{
  // Geometric invariants of the shared ModeratorGun sampling, checked on the
  // concrete MPIGun: unit direction, forward hemisphere, source point on the
  // source plane inside the source rectangle.
  seedGunRng(20261005);
  const std::array<double, 6> size = {100., 50., -2000., 10., 10., 0.};
  pt::MPIGun gun(pt::Neutron(), size);
  const unsigned n = 2000;
  unsigned violations = 0;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    const pt::Vector &pos = p->getPosition();
    const pt::Vector &dir = p->getDirection();
    if(std::abs(dir.mag2() - 1.) > 1e-12)
      violations++;
    if(dir.z() <= 0.)
      violations++;
    if(pos.z() != size[2])
      violations++;
    if(std::abs(pos.x()) > 0.5 * size[0])
      violations++;
    if(std::abs(pos.y()) > 0.5 * size[1])
      violations++;
  }
  CHECK(violations == 0);
}

TEST_CASE("moderatorgun_emission_time_weight_eventid")
{
  // Emission-time structure pinned from PrimaryGun::generate: ModeratorGun
  // lineage overrides neither getTime() nor getParticleWeight(), so every
  // particle carries time exactly 0 and weight exactly 1, the event id
  // counts up from 1, and the sampled energy is recorded as both ekin and
  // ekin0. That is: all divergence is in position/direction, never time.
  seedGunRng(20261006);
  pt::MPIGun gun(pt::Neutron(), {100., 50., -2000., 10., 10., 0.});
  const unsigned n = 1000;
  unsigned violations = 0;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    if(p->getTime() != 0.)
      violations++;
    if(p->getWeight() != 1.)
      violations++;
    if(p->getEventID() != static_cast<unsigned long long>(i + 1))
      violations++;
    if(!p->isAlive())
      violations++;
    if(p->getEKin0() != p->getEKin())
      violations++;
  }
  CHECK(violations == 0);
}

TEST_CASE("mpigun_energy_spectrum_bounds_and_quantiles")
{
  // MPIGun::sampleEnergy returns the built-in spectrum table percentile
  // directly as the energy. The table support is [2.85073350e-03,
  // 4.45427109e+03]; the quantile pins below were derived independently by
  // rebuilding the trapezoidal CDF of the hardcoded x/y arrays offline and
  // reading off grid points at CDF = {0.1, 0.5, 0.9}. A wrong table, a
  // broken percentile inversion or a lost conversion would move these
  // fractions by far more than the 0.01 (>3 sigma) window.
  seedGunRng(20261007);
  pt::MPIGun gun(pt::Neutron(), {100., 50., -2000., 10., 10., 0.});
  const unsigned n = 40000;
  std::vector<double> ekin;
  ekin.reserve(n);
  unsigned outOfSupport = 0;
  for(unsigned i = 0; i < n; i++)
  {
    double e = gun.generate()->getEKin();
    if(e < 2.85073350e-03 || e > 4.45427109e+03)
      outOfSupport++;
    ekin.push_back(e);
  }
  CHECK(outOfSupport == 0);
  const double xs[3] = {0.0118925175, 0.0411514222, 0.159714263};
  const double cdfs[3] = {0.09974412109891644, 0.5000058324524401,
                          0.9003848265656114};
  for(unsigned k = 0; k < 3; k++)
    CHECK(std::abs(fractionBelow(ekin, xs[k]) - cdfs[k]) < 0.01);
}

TEST_CASE("sansgun_energy_spectrum_bounds_and_quantiles")
{
  // SANSGun::sampleEnergy maps the built-in wavelength table percentile
  // through wl2ekin: E = 0.081804209605330899/wl^2 with wl in angstrom.
  // Table support is wl in [0.18, 4.37], i.e. ekin in
  // [wl2ekin(4.37), wl2ekin(0.18)] = [0.0042836381614466687,
  // 2.5248212841151512] eV. Quantile pins again from the offline trapezoidal
  // CDF of the hardcoded table, at CDF = {0.25, 0.5, 0.9}.
  seedGunRng(20261008);
  pt::SANSGun gun(pt::Neutron(), {100., 50., -2000., 10., 10., 0.});
  const unsigned n = 40000;
  const double eMin = pt::wl2ekin(4.37);
  const double eMax = pt::wl2ekin(0.18);
  // the conversion constants must be the documented ones
  CHECK(eMax == doctest::Approx(2.5248212841151512).epsilon(1e-12));
  CHECK(eMin == doctest::Approx(0.0042836381614466687).epsilon(1e-12));
  std::vector<double> wl;
  wl.reserve(n);
  unsigned outOfSupport = 0;
  for(unsigned i = 0; i < n; i++)
  {
    auto p = gun.generate();
    double e = p->getEKin();
    if(e <= 0. || e < eMin || e > eMax)
      outOfSupport++;
    wl.push_back(pt::ekin2wl(e));
  }
  CHECK(outOfSupport == 0);
  const double xs[3] = {0.9056832028, 1.1645953, 2.141897302};
  const double cdfs[3] = {0.25160004257579066, 0.49874912799180876,
                          0.9001522075883762};
  for(unsigned k = 0; k < 3; k++)
    CHECK(std::abs(fractionBelow(wl, xs[k]) - cdfs[k]) < 0.01);
}

TEST_CASE("mpigun_seeded_sequence_determinism")
{
  // A rank split of the primary stream is only meaningful if the gun replay
  // is deterministic per seed: identical seeds reproduce the energy sequence
  // exactly, a different seed produces a different one.
  pt::MPIGun gun(pt::Neutron(), {100., 50., -2000., 10., 10., 0.});
  const unsigned n = 32;
  std::vector<double> first, second;
  seedGunRng(20261009);
  for(unsigned i = 0; i < n; i++)
    first.push_back(gun.generate()->getEKin());
  seedGunRng(20261009);
  for(unsigned i = 0; i < n; i++)
    second.push_back(gun.generate()->getEKin());
  CHECK(first == second);
  seedGunRng(20261010);
  unsigned differing = 0;
  for(unsigned i = 0; i < n; i++)
    if(gun.generate()->getEKin() != first[i])
      differing++;
  CHECK(differing > 0);
}

TEST_CASE("gun_event_block_partition_contract")
{
  // Cinema's C++ gun layer exports no communicator or partition helper (the
  // MPI in "MPIGun" refers to the simulated source, not to a comm), so the
  // rank split of the N-event primary stream is a caller-side convention.
  // Pin the canonical contiguous block partition begin = N*r/R,
  // end = N*(r+1)/R that any serialisable fake-comm must satisfy, and which
  // degenerates to the full range [0,N) for the single-rank serial runs used
  // everywhere in this file. Properties: contiguity, exactly-once coverage,
  // counts summing to N, and empty ranks only at the tail.
  auto blockRange = [](uint64_t total, unsigned ranks, unsigned r) {
    return std::pair<uint64_t, uint64_t>(total * r / ranks,
                                         total * (r + 1) / ranks);
  };
  const uint64_t sizes[] = {0, 1, 2, 3, 5, 16, 1000};
  const unsigned rankss[] = {1, 2, 3, 7, 16};
  for(uint64_t total : sizes)
  {
    for(unsigned ranks : rankss)
    {
      std::vector<unsigned> mark(static_cast<std::size_t>(total), 0u);
      uint64_t sum = 0;
      std::pair<uint64_t, uint64_t> prev{0, 0};
      for(unsigned r = 0; r < ranks; r++)
      {
        auto range = blockRange(total, ranks, r);
        CHECK(range.first <= range.second);
        // contiguity: next rank starts where this one ends
        if(r > 0)
          CHECK(range.first == prev.second);
        // if a rank owns two or more events then N > R, and since every
        // rank stride is floor(N/R) or ceil(N/R), no rank can be empty
        if(r > 0 && prev.second - prev.first > 1)
          CHECK(range.first != range.second);
        sum += range.second - range.first;
        for(uint64_t i = range.first; i < range.second; i++)
          mark[static_cast<std::size_t>(i)]++;
        prev = range;
      }
      CHECK(sum == total); // counts sum to N
      for(unsigned m : mark)
        CHECK(m == 1); // every index in exactly one rank
    }
  }
  // exact closed-form split of 7 events over 3 ranks: 2 + 2 + 3
  CHECK(blockRange(7, 3, 0) == std::make_pair(uint64_t{0}, uint64_t{2}));
  CHECK(blockRange(7, 3, 1) == std::make_pair(uint64_t{2}, uint64_t{4}));
  CHECK(blockRange(7, 3, 2) == std::make_pair(uint64_t{4}, uint64_t{7}));
  // serial mode: rank 0 takes everything
  CHECK(blockRange(1000, 1, 0) == std::make_pair(uint64_t{0}, uint64_t{1000}));
}

TEST_CASE("simplethermal_builtin_spectrum_mean_and_variance")
{
  // The documented built-in spectrum E = 0.0253*(-ln u1 - ln u2 cos^2(pi
  // u3/2)) has mean factor E[A] + E[B]E[C^2] = 1 + 1*1/2 = 1.5 and second
  // moment E[A^2] + 2E[A]E[B]E[C^2] + E[B^2]E[C^4] = 2 + 1 + 2*(3/8) = 3.75
  // (with E[cos^2] = 1/2 and E[cos^4] = 3/8), i.e. mean 1.5*0.0253 =
  // 0.03795 eV (the documented ~0.0380 eV) and variance 1.5*0.0253^2 =
  // 9.60135e-4 eV^2. At n=50000 the standard error of the mean is ~0.37%
  // relative and of the variance estimator well under 1%, so the windows
  // below are >5 sigma (CLT). scale(0.) keeps the epsilon relative despite
  // the eV-scale magnitudes.
  seedGunRng(20261011);
  pt::SimpleThermalGun gun(pt::Neutron(), 0., pt::Vector(0., 0., -12000.));
  const unsigned n = 50000;
  double sum = 0., sum2 = 0.;
  for(unsigned i = 0; i < n; i++)
  {
    double e = gun.generate()->getEKin();
    sum += e;
    sum2 += e * e;
  }
  double mean = sum / n;
  double var = sum2 / n - mean * mean;
  CHECK(mean == doctest::Approx(1.5 * 0.0253).epsilon(0.02).scale(0.));
  CHECK(var == doctest::Approx(1.5 * 0.0253 * 0.0253).epsilon(0.06).scale(0.));
}

TEST_CASE("simplethermal_direction_parameter_wiring")
{
  // The optional factory direction reaches the gun normalised as given, the
  // default direction (omitted key) is +z, and a fixed positive energy is
  // replayed unchanged.
  seedGunRng(20261012);
  auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=SimpleThermalGun;energy=0.05;position=0,0,-500;direction=1,0,0");
  REQUIRE(gun != nullptr);
  auto p = gun->generate();
  CHECK(p->getEKin() == doctest::Approx(0.05).epsilon(1e-12));
  CHECK(p->getDirection().x() == doctest::Approx(1.).epsilon(1e-12));
  CHECK(p->getDirection().y() == doctest::Approx(0.).epsilon(1e-12));
  CHECK(p->getDirection().z() == doctest::Approx(0.).epsilon(1e-12));
  // omitted direction falls back to 0,0,1 (also exercises the optional-key
  // parCount accounting: 3 params instead of 4)
  auto gun2 = pt::Singleton<pt::GunFactory>::getInstance().createGun(
      "gun=SimpleThermalGun;energy=0.05;position=0,0,-500");
  REQUIRE(gun2 != nullptr);
  auto p2 = gun2->generate();
  CHECK(p2->getDirection().z() == doctest::Approx(1.).epsilon(1e-12));
  CHECK(p2->getDirection().x() == doctest::Approx(0.).epsilon(1e-12));
  CHECK(p2->getDirection().y() == doctest::Approx(0.).epsilon(1e-12));
}

////////////////////////////////////////////////////////////////////////////////

TEST_CASE("pythongun_push_to_stack_buffer_layout")
{
  // PythonGun receives fully specified particles from Python as flat
  // 9-double buffers: [ekin, weight, time, pos.x, pos.y, pos.z, dir.x,
  // dir.y, dir.z]. The buffer is copied field-by-field with no
  // normalisation or validation: pin the exact round trip, the event id
  // counting and the stack hand-over.
  auto &stack = pt::Singleton<pt::StackManager>::getInstance();
  while(!stack.empty())
    stack.pop();

  pt::PythonGun gun(2112);
  double buf[9] = {2.5, 0.7, 1.3, 1., 2., 3., 0., 0., 2.};
  gun.pushToStack(buf);
  CHECK(stack.getNumParticleInStack() == 1);
  auto p = stack.pop();
  REQUIRE(p != nullptr);
  CHECK(p->getPDG() == 2112);
  CHECK(p->getEKin() == doctest::Approx(2.5).epsilon(1e-12));
  CHECK(p->getEKin0() == doctest::Approx(2.5).epsilon(1e-12));
  CHECK(p->getWeight() == doctest::Approx(0.7).epsilon(1e-12));
  CHECK(p->getTime() == doctest::Approx(1.3).epsilon(1e-12));
  CHECK(p->getPosition().x() == doctest::Approx(1.).epsilon(1e-12));
  CHECK(p->getPosition().y() == doctest::Approx(2.).epsilon(1e-12));
  CHECK(p->getPosition().z() == doctest::Approx(3.).epsilon(1e-12));
  // directions are taken literally: (0,0,2) stays non-unit, mag2 = 4
  CHECK(p->getDirection().x() == doctest::Approx(0.).epsilon(1e-12));
  CHECK(p->getDirection().y() == doctest::Approx(0.).epsilon(1e-12));
  CHECK(p->getDirection().z() == doctest::Approx(2.).epsilon(1e-12));
  CHECK(p->getDirection().mag2() == doctest::Approx(4.).epsilon(1e-12));
  CHECK(p->getEventID() == 1);
  CHECK(p->isAlive());
  CHECK(stack.empty());
}

TEST_CASE("pythongun_push_many_and_c_abi")
{
  // The batch entry point consumed by Python walks the buffer with a fixed
  // stride of 9 doubles per particle (pt_PythonGun_pushToStackMany), and the
  // whole gun is also reachable through the flat C ABI
  // (pt_PythonGun_new/_pushToStack/_delete) used by the binding layer. The
  // stack is LIFO, so particles come back in reverse push order.
  auto &stack = pt::Singleton<pt::StackManager>::getInstance();
  while(!stack.empty())
    stack.pop();

  pt::PythonGun gun(2112);
  double many[18] = {0.05, 1.0, 0.0,  0., 0., -500., 0., 0., 1.,
                     1.0, 0.5, 1e-3, 4., 5., 6.,    1., 0., 0.};
  pt_PythonGun_pushToStackMany(&gun, many, 2);
  CHECK(stack.getNumParticleInStack() == 2);
  // each PythonGun instance counts its own pushes from 1
  auto pSecond = stack.pop(); // last pushed: second buffer particle
  REQUIRE(pSecond != nullptr);
  CHECK(pSecond->getEventID() == 2);
  CHECK(pSecond->getEKin() == doctest::Approx(1.0).epsilon(1e-12));
  CHECK(pSecond->getWeight() == doctest::Approx(0.5).epsilon(1e-12));
  CHECK(pSecond->getTime() == doctest::Approx(1e-3).epsilon(1e-15).scale(0.));
  CHECK(pSecond->getPosition().x() == doctest::Approx(4.).epsilon(1e-12));
  CHECK(pSecond->getPosition().y() == doctest::Approx(5.).epsilon(1e-12));
  CHECK(pSecond->getPosition().z() == doctest::Approx(6.).epsilon(1e-12));
  CHECK(pSecond->getDirection().x() == doctest::Approx(1.).epsilon(1e-12));
  auto pFirst = stack.pop();
  REQUIRE(pFirst != nullptr);
  CHECK(pFirst->getEventID() == 1);
  CHECK(pFirst->getEKin() == doctest::Approx(0.05).epsilon(1e-12));
  CHECK(pFirst->getWeight() == doctest::Approx(1.0).epsilon(1e-12));
  CHECK(pFirst->getPosition().z() == doctest::Approx(-500.).epsilon(1e-12));
  CHECK(stack.empty());

  // same buffer contract through the C ABI, with a different pdg
  void *raw = pt_PythonGun_new(2212);
  REQUIRE(raw != nullptr);
  double buf[9] = {100., 2., 0., 0., 0., 0., 0., 1., 0.};
  pt_PythonGun_pushToStack(raw, buf);
  auto pGamma = stack.pop();
  REQUIRE(pGamma != nullptr);
  CHECK(pGamma->getPDG() == 2212);
  CHECK(pGamma->getEKin() == doctest::Approx(100.).epsilon(1e-12));
  CHECK(pGamma->getWeight() == doctest::Approx(2.).epsilon(1e-12));
  CHECK(pGamma->getEventID() == 1); // the C-ABI gun instance counts from 1
  pt_PythonGun_delete(raw);
  CHECK(stack.empty());
}

TEST_CASE("pythongun_unimplemented_vmethods_throw_calcerror")
{
  // PythonGun is only a stack feeder: the PrimaryGun sampling entry points
  // are hard errors, and generate() must never be reachable.
  pt::PythonGun gun(2112);
  CHECK_THROWS_AS(gun.generate(), pt::Error::CalcError);
  double ekin = 0.;
  pt::Vector pos, dir;
  CHECK_THROWS_AS(gun.sampleEnergy(ekin), pt::Error::CalcError);
  CHECK_THROWS_AS(gun.samplePosDir(pos, dir), pt::Error::CalcError);
  try {
    pt::Vector p2, d2;
    gun.samplePosDir(p2, d2);
  } catch (const pt::Error::CalcError &e) {
    CHECK(std::string(e.what()).find("not implemented") != std::string::npos);
  }
}

////////////////////////////////////////////////////////////////////////////////

TEST_CASE("mcplgun_missing_file_error_path")
{
  // The .mcpl branch of MCPLGun opens through MCPL's mcpl_open_file, which
  // reports problems via a pluggable error handler whose default action is
  // print + exit(1). Install a throwing handler so the error path can be
  // asserted as a clean exception instead of killing the test process, and
  // restore the library default at the end. (The .xml/KDSource branch cannot
  // be exercised this way: KDSource has no pluggable handler, so only the
  // .mcpl branch is testable without a real file.)
  mcpl_set_error_handler(&mcplThrowingHandler);

  // 1) direct construction with a nonexistent file
  std::string missing = "/tmp/cinema_cxxtest_guns2_missing_" +
                        std::to_string(getpid()) + ".mcpl";
  bool routed = false;
  try {
    pt::MCPLGun gun(pt::Neutron(), missing);
    FAIL("a missing mcpl file must not yield a usable gun");
  } catch (const McplRoutedError &e) {
    routed = true;
    CHECK(std::string(e.msg).find("Unable to open") != std::string::npos);
  }
  CHECK(routed);

  // 2) same through the factory config string
  routed = false;
  try {
    auto gun = pt::Singleton<pt::GunFactory>::getInstance().createGun(
        "gun=MCPLGun;mcplfile=" + missing + ";");
    FAIL("the factory must propagate the mcpl open failure");
  } catch (const McplRoutedError &) {
    routed = true;
  }
  CHECK(routed);

  // 3) an existing file whose content is not MCPL fails the magic-word check
  std::string fn = "/tmp/cinema_cxxtest_guns2_text_" +
                   std::to_string(getpid()) + ".mcpl";
  {
    std::ofstream f(fn.c_str());
    f << "definitely not an MCPL file";
  }
  routed = false;
  try {
    pt::MCPLGun gun(pt::Neutron(), fn);
    FAIL("non-MCPL content must be rejected");
  } catch (const McplRoutedError &e) {
    routed = true;
    CHECK(std::string(e.msg).find("not an MCPL file") != std::string::npos);
  }
  CHECK(routed);
  std::remove(fn.c_str());

  mcpl_set_error_handler(&mcpl_default_error_handler);
}
