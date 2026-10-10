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

//Edge/boundary behaviour of Hist1D/HistBase/Est1D with deterministic fills:
//no RNG, no save() (no file IO), all cases millisecond-scale.

#include "../doctest.h"

#include "PTHist1D.hh"
#include "PTEst1D.hh"
#include "PTMath.hh"

#include <cmath>
#include <vector>

namespace pt = Prompt;

TEST_CASE("Hist1D_fill_xmin_lands_in_first_bin")
{
  pt::Hist1D h("h", 0., 10., 5);
  h.fill(0.0); //left edge belongs to the first bin

  const auto &data = h.getRaw();
  const auto &hit  = h.getHit();
  REQUIRE(data.size() == 5u);
  CHECK(data[0] == doctest::Approx(1.0));
  CHECK(hit[0]  == doctest::Approx(1.0));
  double rest = 0.;
  for(unsigned i=1;i<data.size();++i)
    rest += data[i];
  CHECK(rest == doctest::Approx(0.0));
  CHECK(h.getAccWeight() == doctest::Approx(1.0));
  CHECK(h.getUnderflow() == doctest::Approx(0.0));
  CHECK(h.getOverflow()  == doctest::Approx(0.0));
}

TEST_CASE("Hist1D_fill_xmax_clamps_into_last_bin")
{
  //regression: val==xmax used to compute bin index floor(nbins) and write
  //m_data[nbins] out of bounds; the [xmin,xmax] range is right-closed
  pt::Hist1D h("h", 0., 10., 5);
  h.fill(10.0);
  h.fill(10.0, 2.5);

  const auto &data = h.getRaw();
  const auto &hit  = h.getHit();
  REQUIRE(data.size() == 5u);
  CHECK(data[4] == doctest::Approx(3.5)); //both fills land in the last bin
  CHECK(hit[4]  == doctest::Approx(2.0));
  for(unsigned i=0;i+1<data.size();++i)
    CHECK(data[i] == doctest::Approx(0.0));
  CHECK(h.getOverflow() == doctest::Approx(0.0));
  CHECK(h.getUnderflow() == doctest::Approx(0.0));
  //no weight may leak into an out-of-range slot
  CHECK(h.getAccWeight() == doctest::Approx(3.5));
  CHECK(h.getAccWeight() == doctest::Approx(h.getTotalWeight()-h.getOverflow()-h.getUnderflow()));
}

TEST_CASE("Hist1D_underflow_overflow_accounting")
{
  pt::Hist1D h("h", 0., 10., 5);
  h.fill(-0.1);
  h.fill(-1.0, 2.0);
  h.fill(10.0001, 3.0);
  h.fill(100.0, 1.5);

  CHECK(h.getUnderflow() == doctest::Approx(3.0)); //1 + 2
  CHECK(h.getOverflow()  == doctest::Approx(4.5)); //3 + 1.5
  CHECK(h.getTotalWeight() == doctest::Approx(7.5)); //counts everything
  CHECK(h.getAccWeight() == doctest::Approx(0.0)); //nothing reached a bin
  CHECK(h.getTotalHit()  == doctest::Approx(0.0));
}

TEST_CASE("Hist1D_total_vs_accumulated_weight")
{
  pt::Hist1D h("h", 0., 10., 5);
  h.fill(1.0, 1.0);
  h.fill(4.0, 2.0);
  h.fill(-3.0, 0.5);
  h.fill(12.0, 0.25);

  double sum = 0.;
  for(auto v : h.getRaw())
    sum += v;
  CHECK(h.getTotalWeight() == doctest::Approx(3.75));
  CHECK(sum == doctest::Approx(3.0));
  CHECK(h.getAccWeight() == doctest::Approx(sum));
  CHECK(h.getAccWeight() == doctest::Approx(h.getTotalWeight()-h.getOverflow()-h.getUnderflow()));
}

TEST_CASE("Hist1D_weighted_fill_updates_data_hit_ww")
{
  pt::Hist1D h("h", 0., 10., 5);
  h.fill(5.0, 3.0); //bin index floor((5-0)*0.5) == 2

  CHECK(h.getRaw()[2] == doctest::Approx(3.0));
  CHECK(h.getHit()[2] == doctest::Approx(1.0));  //hit counts entries, not weight
  CHECK(h.getww()[2]  == doctest::Approx(9.0));  //w*w
  CHECK(h.getww()[2]  == doctest::Approx(h.getRaw()[2]*h.getRaw()[2]));
}

TEST_CASE("Hist1D_log_binning_indices")
{
  //log10 range [1,100] with 10 bins -> decade edges 10^0, 10^0.2, ..., 10^2
  pt::Hist1D h("hlog", 1., 100., 10, false);

  h.fill(0.1);  //below xmin
  h.fill(1.0);  //first edge -> bin 0
  h.fill(10.0); //10^1 -> index (1-0)*10/2 == 5
  h.fill(100.0); //upper boundary -> clamped into the last bin

  CHECK(h.getUnderflow() == doctest::Approx(1.0));
  CHECK(h.getOverflow()  == doctest::Approx(0.0));
  const auto &data = h.getRaw();
  REQUIRE(data.size() == 10u);
  CHECK(data[0] == doctest::Approx(1.0));
  CHECK(data[5] == doctest::Approx(1.0));
  CHECK(data[9] == doctest::Approx(1.0));
  CHECK(h.getAccWeight() == doctest::Approx(3.0));
}

TEST_CASE("Hist1D_linear_edges")
{
  pt::Hist1D h("h", 0., 10., 5);
  auto edges = h.getEdges();
  REQUIRE(edges.size() == 6u);
  CHECK(edges.front() == doctest::Approx(0.0));
  CHECK(edges.back()  == doctest::Approx(10.0));
  for(unsigned i=0;i<edges.size();++i)
    CHECK(edges[i] == doctest::Approx(2.0*i)); //uniform step
}

TEST_CASE("Hist1D_log_edges_geometric")
{
  pt::Hist1D h("hlog", 1., 100., 10, false);
  auto edges = h.getEdges();
  REQUIRE(edges.size() == 11u);
  CHECK(edges.front() == doctest::Approx(1.0));
  CHECK(edges.back()  == doctest::Approx(100.0));

  const double ratio = edges[1]/edges[0];
  CHECK(ratio == doctest::Approx(std::pow(10.0, 0.2)));
  for(unsigned i=0;i+1<edges.size();++i)
    CHECK(edges[i+1]/edges[i] == doctest::Approx(ratio).epsilon(1e-12));
}

TEST_CASE("Hist1D_merge_sums_and_quadrature_ww")
{
  pt::Hist1D a("a", 0., 10., 4);
  pt::Hist1D b("b", 0., 10., 4);
  a.fill(1.0, 3.0);  //bin 0: data 3, hit 1, ww 9
  a.fill(9.0);       //bin 3
  b.fill(1.0, 4.0);  //bin 0: data 4, hit 1, ww 16
  b.fill(-1.0, 1.0); //underflow
  b.fill(20.0, 2.0); //overflow

  a.merge(b);

  CHECK(a.getRaw()[0] == doctest::Approx(7.0));
  CHECK(a.getHit()[0] == doctest::Approx(2.0));
  CHECK(a.getww()[0]  == doctest::Approx(std::sqrt(9.0*9.0 + 16.0*16.0))); //combined in quadrature
  CHECK(a.getRaw()[3] == doctest::Approx(1.0));
  CHECK(a.getUnderflow() == doctest::Approx(1.0));
  CHECK(a.getOverflow()  == doctest::Approx(2.0));
  CHECK(a.getTotalWeight() == doctest::Approx(11.0)); //3+1+4+1+2
}

TEST_CASE("Hist1D_merge_rejects_mismatched_binning")
{
  pt::Hist1D ref("ref", 0., 10., 4);
  pt::Hist1D diffXMax("d1", 0., 20., 4);
  pt::Hist1D diffXMin("d2", 1., 10., 4);
  pt::Hist1D diffNbins("d3", 0., 10., 5);
  REQUIRE_THROWS_AS(ref.merge(diffXMax), pt::Error::CalcError);
  REQUIRE_THROWS_AS(ref.merge(diffXMin), pt::Error::CalcError);
  REQUIRE_THROWS_AS(ref.merge(diffNbins), pt::Error::CalcError);
}

TEST_CASE("Hist1D_ctor_guards_scale_and_reset")
{
  //constructor guards
  REQUIRE_THROWS_AS(pt::Hist1D("h0", 0., 10., 0), pt::Error::BadInput); //zero bins
  REQUIRE_THROWS_AS(pt::Hist1D("h1", 5., 5., 4), pt::Error::BadInput);  //xmin==xmax
  REQUIRE_THROWS_AS(pt::Hist1D("h2", 10., 0., 4), pt::Error::BadInput); //xmin>xmax
  REQUIRE_THROWS_AS(pt::Hist1D("h3", 0., 10., 4, false), pt::Error::BadInput);  //log with xmin==0
  REQUIRE_THROWS_AS(pt::Hist1D("h4", -1., 10., 4, false), pt::Error::BadInput); //log with xmin<0

  pt::Hist1D h("h", 0., 10., 5);
  h.fill(1.0, 2.0);  //bin 0
  h.fill(7.0);       //bin 3
  h.fill(-1.0, 0.5); //underflow
  h.fill(11.0, 1.5); //overflow

  h.scale(2.0);
  CHECK(h.getRaw()[0] == doctest::Approx(4.0));
  CHECK(h.getRaw()[3] == doctest::Approx(2.0));
  CHECK(h.getTotalWeight() == doctest::Approx(10.0)); //5 doubled
  CHECK(h.getUnderflow() == doctest::Approx(1.0));
  CHECK(h.getOverflow()  == doctest::Approx(3.0));
  //hits are entry counts and are not rescaled
  CHECK(h.getTotalHit() == doctest::Approx(2.0));

  h.reset();
  for(auto v : h.getRaw())
    CHECK(v == doctest::Approx(0.0));
  CHECK(h.getww()[0]     == doctest::Approx(0.0));
  CHECK(h.getTotalHit()  == doctest::Approx(0.0));
  CHECK(h.getTotalWeight() == doctest::Approx(0.0));
  CHECK(h.getUnderflow() == doctest::Approx(0.0));
  CHECK(h.getOverflow()  == doctest::Approx(0.0));
}

TEST_CASE("Est1D_error_accumulation_and_HistBase_setters")
{
  //Est1D only supports the explicit (val, weight, error) fill
  pt::Est1D e("est", 0., 10., 5);
  REQUIRE_THROWS_AS(e.fill(1.0), pt::Error::BadInput);
  REQUIRE_THROWS_AS(e.fill(1.0, 1.0), pt::Error::BadInput);

  e.fill(1.0, 1.0, 3.0); //hit accumulated as sqrt(err^2 + hit^2)
  e.fill(1.0, 1.0, 4.0); //3-4-5 triangle in quadrature
  e.fill(10.0, 1.0, 0.0); //upper boundary clamps into the last bin
  CHECK(e.getRaw()[0] == doctest::Approx(2.0));
  CHECK(e.getHit()[0] == doctest::Approx(5.0));
  CHECK(e.getRaw()[4] == doctest::Approx(1.0));

  //setWeight/setHit/setWW roundtrip
  pt::Hist1D h("h", 0., 10., 5);
  std::vector<double> buf{1., 2., 3., 4., 5.};
  h.setWeight(buf.data(), buf.size());
  h.setHit(buf.data(), buf.size());
  h.setWW(buf.data(), buf.size());
  for(unsigned i=0;i<buf.size();++i) {
    CHECK(h.getRaw()[i] == doctest::Approx(buf[i]));
    CHECK(h.getHit()[i] == doctest::Approx(buf[i]));
    CHECK(h.getww()[i]  == doctest::Approx(buf[i]));
  }

  std::vector<double> bad{1., 2.}; //wrong size
  REQUIRE_THROWS_AS(h.setWeight(bad.data(), bad.size()), pt::Error::CalcError);
  REQUIRE_THROWS_AS(h.setHit(bad.data(), bad.size()), pt::Error::CalcError);
  REQUIRE_THROWS_AS(h.setWW(bad.data(), bad.size()), pt::Error::CalcError);

  //notes are ';'-concatenated
  CHECK(h.getNote() == std::string(""));
  h.addNote("first");
  h.addNote("second");
  CHECK(h.getNote() == std::string("first;second"));
}
