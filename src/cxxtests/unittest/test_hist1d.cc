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

#include <chrono>
#include <iostream>
#include <memory>
#include "PTHist1D.hh"
#include "PTRandEngine.hh"
#include "PTRandCanonical.hh"
#include "PTMath.hh"

namespace pt = Prompt;

TEST_CASE("Hist1D_log")
{
  double xUpper = 100.;
  unsigned loop = 1000000;
  auto gen = std::make_shared<pt::RandEngine>(6402);
  auto hist = std::make_unique<pt::Hist1D>("Hist1D_log", 1,  xUpper, 10, false);
  auto RandCanonical = std::make_unique<pt::RandCanonical<pt::RandEngine>>(gen);

  auto start = std::chrono::steady_clock::now();
  for(unsigned i=0;i<loop;i++)
    hist->fill(RandCanonical->generate()*xUpper, RandCanonical->generate());

  auto end = std::chrono::steady_clock::now();
  double nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
  std::cout << "Elapsed time in milliseconds : "
    << nanos/1e6 << "ms , " << nanos/loop << " ns per iteration"
    << " " << std::endl;

  auto histraw = hist->getRaw();
  for(auto v: histraw)
    printf("histraw item: %.16f\n", v);

  CHECK(pt::floateq(histraw[0], 2929.4536619041314225 ));
  CHECK(pt::floateq(histraw[1], 4654.7256015907196343 ));
  CHECK(pt::floateq(histraw[2], 7542.0505569552533416 ));
  CHECK(pt::floateq(histraw[3], 11609.4578069848248560 ));
  CHECK(pt::floateq(histraw[4], 18377.6888057267569820 ));
  CHECK(pt::floateq(histraw[5], 29331.9209960537737061 ));
  CHECK(pt::floateq(histraw[6], 46645.8032369693828514 ));
  CHECK(pt::floateq(histraw[7], 73460.8587510505603859 ));
  CHECK(pt::floateq(histraw[8], 116198.1636109650571598 ));
  CHECK(pt::floateq(histraw[9], 183930.6297378933522850 ));

  printf("\n");
  printf("overflow %.16f%%\n", 100*hist->getOverflow()/loop);
  printf("underflow %.16f%%\n", 100*hist->getUnderflow()/loop);
  CHECK(pt::floateq(hist->getUnderflow(), 5025.039917673697 ));
  hist->save("hist1dlog_test");
}


TEST_CASE("Hist1D_lin")
{
  double xUpper = 100.;
  unsigned loop = 1000000;
  auto gen = std::make_shared<pt::RandEngine>(6402);
  auto hist = std::make_unique<pt::Hist1D>("Hist1D_lin", 0,  xUpper, 10);
  auto RandCanonical = std::make_unique<pt::RandCanonical<pt::RandEngine>>(gen);

  auto start = std::chrono::steady_clock::now();
  for(unsigned i=0;i<loop;i++)
    hist->fill(RandCanonical->generate()*xUpper,RandCanonical->generate());

  auto end = std::chrono::steady_clock::now();
  double nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
  std::cout << "Elapsed time in milliseconds : "
    << nanos/1e6 << "ms , " << nanos/loop << " ns per iteration"
    << " " << std::endl;

  auto histraw = hist->getRaw();
  for(auto v: histraw)
    printf("histraw item: %.16f\n", v);

  CHECK(pt::floateq(histraw[0], 50138.4163508361743880 ));
  CHECK(pt::floateq(histraw[1], 50177.8687991449041874 ));
  CHECK(pt::floateq(histraw[2], 50224.1189156772379647 ));
  CHECK(pt::floateq(histraw[3], 49969.8695915000062087 ));
  CHECK(pt::floateq(histraw[4], 50041.3764604097887059 ));
  CHECK(pt::floateq(histraw[5], 49741.7520416023035068 ));
  CHECK(pt::floateq(histraw[6], 49958.0512457187505788 ));
  CHECK(pt::floateq(histraw[7], 49782.6199229488847777 ));
  CHECK(pt::floateq(histraw[8], 49835.1400646744441474 ));
  CHECK(pt::floateq(histraw[9], 49836.5792912604956655 ));

  printf("\n");
  CHECK(pt::floateq(hist->getUnderflow(), 0 ));
  CHECK(pt::floateq(hist->getOverflow(), 0 ));
  hist->save("hist1dlin_test");
}
