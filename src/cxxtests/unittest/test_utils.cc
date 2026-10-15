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
#include <limits>
#include <string>
#include <vector>

#include "PTMath.hh"
#include "PTUtils.hh"

namespace pt = Prompt;

TEST_CASE("split strips whitespace and drops empty tokens")
{
  CHECK( pt::split("a, b ,, c ,", ',') == std::vector<std::string>{"a", "b", "c"} );
  //Whitespace inside and around tokens is stripped:
  CHECK( pt::split("  x  ", ',') == std::vector<std::string>{"x"} );
  CHECK( pt::split("a\tb\nc", ',') == std::vector<std::string>{"abc"} );
  //A string without the delimiter is a single token:
  CHECK( pt::split("nosuchdelim", ',') == std::vector<std::string>{"nosuchdelim"} );
  //Only delimiters and blanks yield an empty result:
  CHECK( pt::split(",,,", ',').empty() );
  CHECK( pt::split("", ',').empty() );
}

TEST_CASE("split with custom delimiter character")
{
  CHECK( pt::split("a;b;c", ';') == std::vector<std::string>{"a", "b", "c"} );
  CHECK( pt::split("path/to/file", '/') == std::vector<std::string>{"path", "to", "file"} );
  CHECK( pt::split("k=v", '=') == std::vector<std::string>{"k", "v"} );
  CHECK( pt::split("a b c", ' ') == std::vector<std::string>{"a", "b", "c"} );
  CHECK( pt::split("1,2,3", ',') == std::vector<std::string>{"1", "2", "3"} );
}

TEST_CASE("string2vec parses comma triplets and rejects wrong token counts")
{
  pt::Vector v = pt::string2vec("1,2,3");
  CHECK( v == pt::Vector(1.0, 2.0, 3.0) );
  //Whitespace is tolerated around the tokens:
  CHECK( pt::string2vec("1, 2 , 3") == pt::Vector(1.0, 2.0, 3.0) );
  //Empty tokens are dropped before the count check:
  CHECK( pt::string2vec("1,,2,3") == pt::Vector(1.0, 2.0, 3.0) );

  REQUIRE_THROWS_AS( pt::string2vec("1,2"), pt::Error::BadInput );
  REQUIRE_THROWS_AS( pt::string2vec("1,2,3,4"), pt::Error::BadInput );
  REQUIRE_THROWS_AS( pt::string2vec(""), pt::Error::BadInput );
}

TEST_CASE("ptstod handles scientific notation, prefix parsing and rejects garbage")
{
  CHECK( pt::ptstod("2.5") == 2.5 );
  CHECK( pt::ptstod("1e-3") == 0.001 );
  CHECK( pt::ptstod("-7.25e2") == -725.0 );
  //std::stod parses the longest valid prefix, trailing garbage is ignored:
  CHECK( pt::ptstod("3.5abc") == 3.5 );
  //Non-numeric input is re-thrown as BadInput:
  REQUIRE_THROWS_AS( pt::ptstod("abc"), pt::Error::BadInput );
  REQUIRE_THROWS_AS( pt::ptstod(""), pt::Error::BadInput );
}

TEST_CASE("ptstoi and ptstou convert with prefix parsing and reject garbage")
{
  CHECK( pt::ptstoi("42") == 42 );
  CHECK( pt::ptstoi("-17") == -17 );
  CHECK( pt::ptstoi("42abc") == 42 );
  REQUIRE_THROWS_AS( pt::ptstoi("abc"), pt::Error::BadInput );
  REQUIRE_THROWS_AS( pt::ptstoi(""), pt::Error::BadInput );

  CHECK( pt::ptstou("7") == 7 );
  REQUIRE_THROWS_AS( pt::ptstou("abc"), pt::Error::BadInput );
  //Pinned quirk: ptstou is implemented on top of std::stol into an int and
  //accepts negative strings without any unsigned range check:
  CHECK( pt::ptstou("-5") == -5 );
}

TEST_CASE("crc32 matches the standard CRC-32 check values")
{
  CHECK( pt::crc32(std::string("")) == 0u );
  //Standard CRC-32 check value of the reference string:
  CHECK( pt::crc32(std::string("123456789")) == 0xCBF43926u );
  //Further standard check values:
  CHECK( pt::crc32(std::string("a")) == 0xE8B7BE43u );
  CHECK( pt::crc32(std::string("abc")) == 0x352441C2u );
  //The string and raw-buffer overloads agree:
  const std::string str = "The quick brown fox jumps over the lazy dog";
  CHECK( pt::crc32(str) == 0x414FA339u );
  CHECK( pt::crc32(str) == pt::crc32(str.c_str(), static_cast<int>(str.size())) );
}

TEST_CASE("linspace has exact endpoints and uniform steps")
{
  auto v = pt::linspace(1.0, 10.0, 10);
  REQUIRE( v.size() == 10u );
  CHECK( v.front() == 1.0 );
  CHECK( v.back() == 10.0 );//stop is assigned exactly
  //interval == 1.0 is exact, so every element is an exact integer here:
  for (size_t i = 0; i < v.size(); ++i)
    CHECK( v[i] == 1.0 + i );

  auto w = pt::linspace(0.0, 1.0, 5);
  REQUIRE( w.size() == 5u );
  CHECK( w.front() == 0.0 );
  CHECK( w.back() == 1.0 );
  //interval == 0.25 is a power of two, so the elements are exact:
  for (size_t i = 0; i < w.size(); ++i)
    CHECK( w[i] == 0.25 * i );
}

TEST_CASE("logspace has exact endpoints and constant ratio")
{
  auto v = pt::logspace(0.0, 3.0, 4);
  REQUIRE( v.size() == 4u );
  CHECK( v.front() == 1.0 );
  CHECK( v.back() == 1000.0 );//stop is assigned exactly
  //Powers of ten are exact, so the ratio is exactly 10:
  for (size_t i = 1; i < v.size(); ++i)
    CHECK( v[i] / v[i - 1] == 10.0 );

  //Decades below unity work as well:
  auto w = pt::logspace(-3.0, 0.0, 4);
  REQUIRE( w.size() == 4u );
  CHECK( w.front() == doctest::Approx(0.001).epsilon(1e-12) );
  CHECK( w.back() == 1.0 );

  //The log convention: endpoints are exactly 10^start and 10^stop (this is
  //the convention Hist1D::getEdges() relies on in log mode):
  auto u = pt::logspace(-1.5, 2.5, 9);
  REQUIRE( u.size() == 9u );
  CHECK( u.front() == std::pow(10.0, -1.5) );
  CHECK( u.back() == std::pow(10.0, 2.5) );
}

TEST_CASE("StableSum recovers small additions lost by naive summation")
{
  pt::StableSum s;
  double naive = 1e16;
  s.add(1e16);
  //1e16 has an ulp of 2, so each +1.0 is lost by naive accumulation:
  for (int i = 0; i < 10000; ++i) {
    s.add(1.0);
    naive += 1.0;
  }
  CHECK( naive == 1e16 );
  CHECK( s.sum() == 1e16 + 10000.0 );
  CHECK( s.sum() - naive == 10000.0 );

  //clear() resets both accumulators:
  s.clear();
  CHECK( s.sum() == 0.0 );
  s.add(2.5);
  CHECK( s.sum() == 2.5 );

  //Repeated additions of 0.1 also land on the exact mathematical result:
  pt::StableSum s2;
  for (int i = 0; i < 10; ++i)
    s2.add(0.1);
  CHECK( std::fabs(s2.sum() - 1.0) < 1e-12 );
}

TEST_CASE("floateq implements relative and absolute tolerance semantics")
{
  CHECK( pt::floateq(1.0, 1.0) );
  CHECK( pt::floateq(1.0, -1.0, 1.0, 3.0) );
  //rtol semantics: allowed difference is 0.5*rtol*(|a|+|b|)+atol, i.e. about
  //1e-14 relative for the default tolerances:
  CHECK( pt::floateq(1.0, 1.0 + 1e-15) );
  CHECK_FALSE( pt::floateq(1.0, 1.0 + 1e-13) );
  //atol floor keeps values near zero comparable:
  CHECK( pt::floateq(0.0, 1e-16) );
  CHECK_FALSE( pt::floateq(0.0, 1e-12) );
  //Large magnitudes agree relatively, not absolutely:
  CHECK( pt::floateq(1e10, 1e10 + 1e-5) );
  CHECK_FALSE( pt::floateq(1e10, 1e10 + 1e-3) );
  //Custom tolerances and symmetry:
  CHECK( pt::floateq(1.0, 1.1, 0.2) );
  CHECK( pt::floateq(1.0, 1.0 + 1e-13, 1e-12) );
  CHECK( pt::floateq(1.0 + 1e-15, 1.0) == pt::floateq(1.0, 1.0 + 1e-15) );
}

TEST_CASE("ptclamp clamps onto the given bounds")
{
  CHECK( pt::ptclamp(0.5, 0.0, 1.0) == 0.5 );
  CHECK( pt::ptclamp(-1.0, 0.0, 1.0) == 0.0 );
  CHECK( pt::ptclamp(2.0, 0.0, 1.0) == 1.0 );
  //Boundary values are returned exactly:
  CHECK( pt::ptclamp(0.0, 0.0, 1.0) == 0.0 );
  CHECK( pt::ptclamp(1.0, 0.0, 1.0) == 1.0 );
  CHECK( pt::ptclamp(-5.0, -5.0, 5.0) == -5.0 );

#ifndef NDEBUG
  //Debug builds throw a LogicError on an inverted range:
  CHECK_THROWS_AS( pt::ptclamp(0.5, 1.0, 0.0), pt::Error::LogicError );
#else
  //NDEBUG (the production configuration): pt_assert is compiled out and
  //ptclamp simply evaluates min(max(val,low),up):
  CHECK( pt::ptclamp(0.5, 1.0, 0.0) == 0.0 );
#endif
}

TEST_CASE("neutron wavelength/energy conversions round-trip and match anchors")
{
  //Zero energy is mapped to the largest representable wavelength and back:
  CHECK( pt::ekin2wl(0.0) == std::numeric_limits<double>::max() );
  CHECK( pt::wlsq2ekin(0.0) == std::numeric_limits<double>::max() );

  //wl2ekin(ekin2wl(E)) recovers E for a spread of thermal-to-epithermal
  //energies (within the default floateq tolerance):
  const double ekins[] = { 0.025293, 0.1, 1.0, 10.0, 100.0 };
  for (double E : ekins) {
    double wl = pt::ekin2wl(E);
    CHECK( wl > 0.0 );
    CHECK( pt::floateq(pt::wl2ekin(wl), E) );
    CHECK( pt::floateq(pt::wlsq2ekin(wl * wl), E) );
  }

  //Momentum transfer for elastic scattering: Q = 2 k sin(theta/2):
  const double E = 0.025293;
  const double mu = 0.5;
  const double k0 = pt::neutronEKin2k(E);
  const double theta = std::acos(mu);
  CHECK( std::fabs(pt::neutronAngleCosine2Q(mu, E, E)
                   - 2.0 * k0 * std::sin(0.5 * theta)) < 1e-12 );
  //Forward scattering has vanishing Q:
  CHECK( std::fabs(pt::neutronAngleCosine2Q(1.0, E, E)) < 1e-12 );

  //The thermal 2200 m/s anchor: E = m_n v^2 / 2 is about 25.3 meV, and the
  //speed conversion inverts it (the internal length unit of Prompt is mm):
  CHECK( pt::const_ekin_2200m_s == doctest::Approx(0.0252988617324).epsilon(1e-9) );
  CHECK( pt::neutronEkin2Speed(pt::const_ekin_2200m_s)
         == doctest::Approx(2200.0 * pt::Unit::m).epsilon(1e-9) );
  CHECK( pt::floateq(pt::neutronSpeed2Ekin(2200.0 * pt::Unit::m),
                     pt::const_ekin_2200m_s) );
}
