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

//Hist2D behaviour with deterministic fills: no RNG, no save() (no file IO),
//all cases millisecond-scale.

#include "../doctest.h"

#include "PTHist2D.hh"

#include <vector>

namespace pt = Prompt;

TEST_CASE("Hist2D_ctor_guards")
{
  REQUIRE_THROWS_AS(pt::Hist2D("h1", 0., 1., 2, 0., 1., 0), pt::Error::BadInput); //zero y bins
  REQUIRE_THROWS_AS(pt::Hist2D("h2", 0., 1., 0, 0., 1., 2), pt::Error::BadInput); //zero x bins
  REQUIRE_THROWS_AS(pt::Hist2D("h3", 1., 0., 2, 0., 1., 2), pt::Error::BadInput); //xmax<xmin
  REQUIRE_THROWS_AS(pt::Hist2D("h4", 0., 1., 2, 1., 1., 2), pt::Error::BadInput); //ymax==ymin
}

TEST_CASE("Hist2D_fill_layout_row_major")
{
  //content index is ix*ynbins+iy; pin it with exact cell contents
  pt::Hist2D h("h", 0., 3., 3, 0., 2., 2);
  REQUIRE(h.getDataSize() == 6u);

  h.fill(0.5, 0.5); //ix=0 iy=0 -> 0*2+0 == 0
  h.fill(0.5, 1.5); //ix=0 iy=1 -> 0*2+1 == 1
  h.fill(1.5, 0.5); //ix=1 iy=0 -> 1*2+0 == 2
  h.fill(2.5, 1.5); //ix=2 iy=1 -> 2*2+1 == 5

  const auto &d = h.getRaw();
  CHECK(d[0] == doctest::Approx(1.0));
  CHECK(d[1] == doctest::Approx(1.0));
  CHECK(d[2] == doctest::Approx(1.0));
  CHECK(d[3] == doctest::Approx(0.0));
  CHECK(d[4] == doctest::Approx(0.0));
  CHECK(d[5] == doctest::Approx(1.0));
  CHECK(h.getAccWeight() == doctest::Approx(4.0));
}

TEST_CASE("Hist2D_underflow_overflow_per_axis")
{
  //an out-of-range coordinate on either axis routes the whole point
  pt::Hist2D h("h", 0., 3., 3, 0., 2., 2);
  h.fill(-0.5, 1.0);      //x below xmin
  h.fill(1.0, -0.5, 2.0); //y below ymin
  h.fill(3.5, 1.0, 0.5);  //x above xmax
  h.fill(1.0, 2.5, 1.5);  //y above ymax

  CHECK(h.getUnderflow() == doctest::Approx(3.0)); //1 + 2
  CHECK(h.getOverflow()  == doctest::Approx(2.0)); //0.5 + 1.5
  CHECK(h.getTotalWeight() == doctest::Approx(5.0));
  CHECK(h.getAccWeight() == doctest::Approx(0.0));
  CHECK(h.getTotalHit() == doctest::Approx(0.0));
}

TEST_CASE("Hist2D_fill_at_upper_edges_stays_in_bounds")
{
  //regression: xval==xmax / yval==ymax used to index one row/column past
  //the end (m_data[ix*ynbins+iy] with ix==xnbins or iy==ynbins)
  pt::Hist2D h("h", 0., 3., 3, 0., 2., 2);
  h.fill(3.0, 0.5); //x==xmax -> clamped to ix=2, index 4
  h.fill(0.5, 2.0); //y==ymax -> clamped to iy=1, index 1
  h.fill(3.0, 2.0); //both upper edges -> index 5

  const auto &d = h.getRaw();
  CHECK(d[4] == doctest::Approx(1.0));
  CHECK(d[1] == doctest::Approx(1.0));
  CHECK(d[5] == doctest::Approx(1.0));
  CHECK(d[0] == doctest::Approx(0.0));
  CHECK(h.getOverflow() == doctest::Approx(0.0)); //upper edge is not overflow
  CHECK(h.getAccWeight() == doctest::Approx(3.0));
  CHECK(h.getAccWeight() == doctest::Approx(h.getTotalWeight()-h.getOverflow()-h.getUnderflow()));
}

TEST_CASE("Hist2D_fill_unguard_broadcast_matches_loop")
{
  pt::Hist2D a("a", 0., 3., 3, 0., 2., 2);
  pt::Hist2D b("b", 0., 3., 3, 0., 2., 2);

  const double x = 2.5;
  std::vector<double> ys{0.5, 1.5, 0.2};
  std::vector<double> ws{1.0, 2.0, 3.0};
  a.fill_unguard(x, ys, ws);
  for(unsigned i=0;i<ys.size();++i)
    b.fill_unguard(x, ys[i], ws[i]);

  CHECK(a.getRaw() == b.getRaw());
  CHECK(a.getHit() == b.getHit());
  CHECK(a.getww()  == b.getww());
  CHECK(a.getAccWeight() == doctest::Approx(6.0));
  //(2.5,0.5) and (2.5,0.2) share cell 4, (2.5,1.5) is cell 5
  CHECK(a.getHit()[4] == doctest::Approx(2.0));
  CHECK(a.getHit()[5] == doctest::Approx(1.0));
  CHECK(a.getRaw()[4] == doctest::Approx(4.0)); //1 + 3
  CHECK(a.getRaw()[5] == doctest::Approx(2.0));
}

TEST_CASE("Hist2D_fill_unguard_vector_and_size_mismatch")
{
  pt::Hist2D a("a", 0., 3., 3, 0., 2., 2);
  pt::Hist2D b("b", 0., 3., 3, 0., 2., 2);

  std::vector<double> xs{0.5, 1.5, 2.5};
  std::vector<double> ys{0.5, 1.5, 0.5};
  std::vector<double> ws{1.0, 1.0, 2.0};
  a.fill_unguard(xs, ys, ws);
  for(unsigned i=0;i<xs.size();++i)
    b.fill_unguard(xs[i], ys[i], ws[i]);

  CHECK(a.getRaw() == b.getRaw());
  CHECK(a.getHit() == b.getHit());
  CHECK(a.getAccWeight() == doctest::Approx(4.0));

  std::vector<double> two{1.0, 2.0}; //wrong length
  REQUIRE_THROWS_AS(a.fill_unguard(two, ys, ws), pt::Error::BadInput);   //x vs y/w mismatch
  REQUIRE_THROWS_AS(a.fill_unguard(1.0, two, ws), pt::Error::BadInput);  //y vs w mismatch
}

TEST_CASE("Hist2D_operator_plus_adds_content_only")
{
  //operator+= is documented to add bin content only
  pt::Hist2D a("a", 0., 3., 3, 0., 2., 2);
  pt::Hist2D b("b", 0., 3., 3, 0., 2., 2);
  a.fill(0.5, 0.5, 1.0);
  a.fill(1.5, 0.5, 1.0); //cell ix=1,iy=0 -> index 2
  b.fill(0.5, 0.5, 4.0);
  b.fill(-1.0, 0.5, 2.0); //b underflow must not leak into a

  a += b;

  CHECK(a.getRaw()[0] == doctest::Approx(5.0));
  CHECK(a.getRaw()[2] == doctest::Approx(1.0));
  CHECK(a.getUnderflow() == doctest::Approx(0.0));
  CHECK(a.getOverflow()  == doctest::Approx(0.0));
  CHECK(a.getTotalWeight() == doctest::Approx(2.0)); //sumW untouched
  CHECK(a.getHit()[0] == doctest::Approx(1.0));      //hit untouched
  CHECK(a.getww()[0]  == doctest::Approx(1.0));      //ww untouched
}

TEST_CASE("Hist2D_merge_and_mismatch")
{
  pt::Hist2D a("a", 0., 3., 3, 0., 2., 2);
  pt::Hist2D b("b", 0., 3., 3, 0., 2., 2);
  a.fill(0.5, 0.5, 1.0);
  a.fill(3.0, 2.0, 0.5);   //last cell
  b.fill(0.5, 0.5, 2.0);
  b.fill(-1.0, 0.5, 1.0);  //underflow
  b.fill(3.5, 2.5, 0.25);  //overflow

  a.merge(b);

  CHECK(a.getRaw()[0] == doctest::Approx(3.0));
  CHECK(a.getRaw()[5] == doctest::Approx(0.5));
  CHECK(a.getHit()[0] == doctest::Approx(2.0));
  CHECK(a.getTotalWeight() == doctest::Approx(4.75)); //1.5 + 3.25
  CHECK(a.getUnderflow() == doctest::Approx(1.0));
  CHECK(a.getOverflow()  == doctest::Approx(0.25));

  //merging histograms with different binning must throw
  pt::Hist2D c("c", 0., 6., 3, 0., 2., 2); //different xmax
  REQUIRE_THROWS_AS(a.merge(c), pt::Error::CalcError);
  pt::Hist2D d("d", 0., 3., 4, 0., 2., 2); //different xnbins
  REQUIRE_THROWS_AS(a.merge(d), pt::Error::CalcError);
  pt::Hist2D e("e", 0., 3., 3, 0., 4., 2); //different ymax
  REQUIRE_THROWS_AS(a.merge(e), pt::Error::CalcError);
}

TEST_CASE("Hist2D_edges_and_accessors")
{
  pt::Hist2D h("h", 0., 3., 3, -1., 1., 2);
  CHECK(h.getNBinX() == 3u);
  CHECK(h.getNBinY() == 2u);
  CHECK(h.getXMin() == doctest::Approx(0.0));
  CHECK(h.getXMax() == doctest::Approx(3.0));
  CHECK(h.getYMin() == doctest::Approx(-1.0));
  CHECK(h.getYMax() == doctest::Approx(1.0));

  auto xe = h.getXEdge();
  REQUIRE(xe.size() == 4u);
  CHECK(xe.front() == doctest::Approx(0.0));
  CHECK(xe.back()  == doctest::Approx(3.0));
  for(unsigned i=0;i<xe.size();++i)
    CHECK(xe[i] == doctest::Approx(static_cast<double>(i)));

  auto ye = h.getYEdge();
  REQUIRE(ye.size() == 3u);
  CHECK(ye.front() == doctest::Approx(-1.0));
  CHECK(ye[1]      == doctest::Approx(0.0));
  CHECK(ye.back()  == doctest::Approx(1.0));
}

TEST_CASE("Hist2D_scale_and_reset")
{
  pt::Hist2D h("h", 0., 3., 3, 0., 2., 2);
  h.fill(0.5, 0.5, 2.0);
  h.fill(-1.0, 0.5, 1.0); //underflow
  h.fill(3.5, 0.5, 0.5);  //overflow

  h.scale(2.0);
  CHECK(h.getRaw()[0] == doctest::Approx(4.0));
  CHECK(h.getTotalWeight() == doctest::Approx(7.0));
  CHECK(h.getUnderflow() == doctest::Approx(2.0));
  CHECK(h.getOverflow()  == doctest::Approx(1.0));
  //hits are entry counts and are not rescaled
  CHECK(h.getHit()[0] == doctest::Approx(1.0));

  h.reset();
  for(auto v : h.getRaw())
    CHECK(v == doctest::Approx(0.0));
  for(auto v : h.getHit())
    CHECK(v == doctest::Approx(0.0));
  for(auto v : h.getww())
    CHECK(v == doctest::Approx(0.0));
  CHECK(h.getTotalWeight() == doctest::Approx(0.0));
  CHECK(h.getUnderflow() == doctest::Approx(0.0));
  CHECK(h.getOverflow()  == doctest::Approx(0.0));
}
