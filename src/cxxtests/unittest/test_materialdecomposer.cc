////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    //
//                                                                            //
//  Copyright 2021-2026 Cinema developers                                     //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  you may not use this file except in compliance with the License.          //
//  you may obtain a copy of the License at                                   //
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

#include "PTMaterialDecomposer.hh"
#include "PTSingleton.hh"

#include <cmath>
#include <string>
#include <vector>

namespace pt = Prompt;

namespace {

// Absolute-difference comparison, robust also for the small natural-abundance
// fractions where doctest::Approx's default scale would be too coarse.
bool closeAbs(double value, double expected, double tol)
{
  return std::fabs(value - expected) <= tol;
}

pt::IsotopeComposition iso(unsigned Z, unsigned A, double frac, const std::string& name)
{
  pt::IsotopeComposition c;
  c.Z = Z;
  c.A = A;
  c.frac = frac;
  c.name = name;
  return c;
}

} // namespace

TEST_CASE("materialdecomposer_shrink2element_merges_isotopes_of_same_z")
{
  // hydrogen: two isotopes collapse onto one element entry:
  std::vector<pt::IsotopeComposition> h = { iso(1, 1, 0.999885, "H1"),
                                            iso(1, 2, 0.000115, "H2") };
  auto shrunk = pt::shrink2element(h);
  REQUIRE(shrunk.size() == 1u);
  CHECK(shrunk[0].Z == 1u);
  CHECK(shrunk[0].A == 0u); // element entries carry no mass number
  CHECK(closeAbs(shrunk[0].frac, 1.0, 1e-12));
  CHECK(shrunk[0].name == "H"); // trailing mass digits stripped

  // three isotopes merge into one entry as well:
  std::vector<pt::IsotopeComposition> o = { iso(8, 16, 0.6, "O16"),
                                            iso(8, 17, 0.3, "O17"),
                                            iso(8, 18, 0.1, "O18") };
  shrunk = pt::shrink2element(o);
  REQUIRE(shrunk.size() == 1u);
  CHECK(shrunk[0].Z == 8u);
  CHECK(shrunk[0].A == 0u);
  CHECK(closeAbs(shrunk[0].frac, 1.0, 1e-12));
  CHECK(shrunk[0].name == "O");

  // multi-digit mass numbers and digit-free names are both handled:
  std::vector<pt::IsotopeComposition> fe = { iso(26, 54, 0.25, "Fe54"),
                                             iso(26, 56, 0.75, "Fe56") };
  shrunk = pt::shrink2element(fe);
  REQUIRE(shrunk.size() == 1u);
  CHECK(shrunk[0].name == "Fe");
  CHECK(closeAbs(shrunk[0].frac, 1.0, 1e-12));

  // a name without trailing digits passes through unchanged:
  std::vector<pt::IsotopeComposition> plain = { iso(1, 0, 1.0, "H") };
  shrunk = pt::shrink2element(plain);
  REQUIRE(shrunk.size() == 1u);
  CHECK(shrunk[0].name == "H");

  // an empty input stays empty:
  CHECK(pt::shrink2element({}).empty());
}

TEST_CASE("materialdecomposer_shrink2element_keeps_first_appearance_order")
{
  std::vector<pt::IsotopeComposition> mix = { iso(5, 10, 0.2, "B10"),
                                              iso(6, 12, 0.7, "C12"),
                                              iso(5, 11, 0.8, "B11"),
                                              iso(8, 16, 0.5, "O16"),
                                              iso(6, 13, 0.3, "C13") };
  auto shrunk = pt::shrink2element(mix);
  REQUIRE(shrunk.size() == 3u);

  // elements appear in the order in which their first isotope showed up:
  CHECK(shrunk[0].Z == 5u);
  CHECK(shrunk[1].Z == 6u);
  CHECK(shrunk[2].Z == 8u);
  CHECK(shrunk[0].name == "B");
  CHECK(shrunk[1].name == "C");
  CHECK(shrunk[2].name == "O");

  // fractions of repeated isotopes are accumulated onto the first entry:
  CHECK(closeAbs(shrunk[0].frac, 0.2 + 0.8, 1e-12));
  CHECK(closeAbs(shrunk[1].frac, 0.7 + 0.3, 1e-12));
  CHECK(closeAbs(shrunk[2].frac, 0.5, 1e-12));
}

TEST_CASE("materialdecomposer_getcomposition_returns_natural_table")
{
  auto& decomposer = pt::Singleton<pt::MaterialDecomposer>::getInstance();

  // natural hydrogen: H1 and H2 with the tabulated abundances:
  auto h = decomposer.getComposition(1);
  REQUIRE(h.size() == 2u);
  CHECK(h[0].Z == 1u);
  CHECK(h[0].A == 1u);
  CHECK(h[0].name == "H1");
  CHECK(closeAbs(h[0].frac, 0.999885, 1e-12));
  CHECK(h[1].Z == 1u);
  CHECK(h[1].A == 2u);
  CHECK(h[1].name == "H2");
  CHECK(closeAbs(h[1].frac, 0.000115, 1e-12));

  // single-isotope elements come back with unity fraction:
  auto al = decomposer.getComposition(13);
  REQUIRE(al.size() == 1u);
  CHECK(al[0].Z == 13u);
  CHECK(al[0].A == 27u);
  CHECK(al[0].name == "Al27");
  CHECK(closeAbs(al[0].frac, 1.0, 1e-12));

  // natural abundances of a few multi-isotope elements sum to unity:
  const int elems[] = { 5, 8, 20, 26, 82, 92 };
  for (int Z : elems) {
    auto comp = decomposer.getComposition(Z);
    double sum = 0.;
    for (const auto& c : comp) {
      sum += c.frac;
      CHECK(c.Z == static_cast<unsigned>(Z));
    }
    CHECK(closeAbs(sum, 1.0, 1e-9));
  }

  // boron is a two-isotope element with well known abundances:
  auto b = decomposer.getComposition(5);
  REQUIRE(b.size() == 2u);
  CHECK(b[0].name == "B10");
  CHECK(closeAbs(b[0].frac, 0.199, 1e-12));
  CHECK(b[1].name == "B11");
  CHECK(closeAbs(b[1].frac, 0.801, 1e-12));

  // an unknown Z is rejected:
  bool threw = false;
  try {
    decomposer.getComposition(999);
  } catch (const pt::Error::CalcError& e) {
    threw = true;
    CHECK(std::string(e.what()).find("Z=999") != std::string::npos);
  }
  CHECK(threw);
}
