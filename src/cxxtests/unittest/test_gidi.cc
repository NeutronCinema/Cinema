////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
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

#include <iostream>
#include <memory>
#include "PTGIDIModel.hh"
#include "PTNCrystalScat.hh"
#include "PTHist1D.hh"
#include "PTModelCollection.hh"
#include "PTMaterialDecomposer.hh"
#include "PTGIDIFactory.hh"
#include "PTGidiSetting.hh"


namespace pt = Prompt;

void configTestData()
{
  auto &cdata = Prompt::Singleton<Prompt::GidiSetting>::getInstance();

  cdata.setEnableGidi(true);
  const char* envVar = std::getenv("CINEMAPATH");
  std::cout << envVar << std::endl;
  const std::string cpath(envVar);
  const std::string fmap = cpath + "/testdata/all.map";
  cdata.setGidiMap(fmap);
  const std::string fpop = cpath + "/testdata/pops.xml";
  cdata.setGidiPops(fpop);
}

TEST_CASE("GIDIfactory")
{
  auto &cdata = Prompt::Singleton<Prompt::GidiSetting>::getInstance();
  configTestData();
  std::cout << "GidiSetting info: " << std::endl;
  std::cout << "  " << cdata.getGidiMap() << std::endl;
  std::cout << "  " << cdata.getGidiPops() << std::endl;
  auto isotope = Prompt::IsotopeComposition{4, 7, 1., "Be7"};
  auto isotopes = {isotope};
  for(const auto& v : isotopes)
    std::cout << v << std::endl;
  auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();  

  auto model = gidifactory.createNeutronGIDIModel(isotopes, 300, 1., 0.);
  std::cout << "Info: model number " << model.size() << std::endl;
  CHECK(model.size()==1);

  pt::Vector in(1,0,0);
  int i = 0;
  for(auto v: model)
  {
    std::cout.precision(15);
    std::cout << "Info: xs " << v->getCrossSection(1e6) * 1e24 << std::endl; // in cm^2
    CHECK(Prompt::floateq(v->getCrossSection(1e6) * 1e24, 296.096663564745484));
    auto res = v->sampleReaction(1e6, in);
    std::cout << "Sampled result: " << int(res.dispeared) << std::endl; // in MeV
    CHECK(Prompt::floateq(float(res.dispeared), 1.));
  }
}


TEST_CASE("H1")
{
  std::vector<double> expectedXS;
  expectedXS = {2.06942784133667e-21, 5.29027296368866e-24};
  std::cout.precision(15);
  auto &cdata = Prompt::Singleton<Prompt::GidiSetting>::getInstance();
  std::cout << "GidiSetting info: " << std::endl;
  std::cout << "  " << cdata.getGidiMap() << std::endl;
  std::cout << "  " << cdata.getGidiPops() << std::endl;
  auto isotope = Prompt::IsotopeComposition{1, 1, 1., "H1"};
  auto isotopes = {isotope};
  for(const auto& v : isotopes)
    std::cout << v << std::endl;
  auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();  

  auto model = gidifactory.createNeutronGIDIModel(isotopes, 300, 1., 1 );
  std::cout << "Info: model number " << model.size() << std::endl;
  CHECK(model.size()==2);
  int i = 0;
  for(auto v: model)
  {
    std::cout << "Info: xs " << v->getCrossSection(1.) << std::endl;
    CHECK(Prompt::floateq(v->getCrossSection(1.), expectedXS[i]));
    i++;
  }
}

// // Too heavy test data for U235
// TEST_CASE("U235")
// {
//   std::vector<double> expectedXS;
//   expectedXS = {1.26423125537086e-21, 7.99475113325076e-21};
//   auto &cdata = Prompt::Singleton<Prompt::GidiSetting>::getInstance();
//   std::cout << "GidiSetting info: " << std::endl;
//   std::cout << cdata.getGidiMap() << std::endl;
//   std::cout << cdata.getGidiPops() << std::endl;
//   auto isotope = Prompt::IsotopeComposition{235, 92, 1., "U235"};
//   auto isotopes = {isotope};
//   for(const auto& v : isotopes)
//     std::cout << v << std::endl;
//   auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();  

//   auto model = gidifactory.createNeutronGIDIModel(isotopes, 300, 1., 1. );
//   std::cout << "Info: model number " << model.size() << std::endl;
//   CHECK(model.size()==2);
//   int i = 0;
//   for(auto v: model)
//   {
//     std::cout << "Info: xs " << v->getCrossSection(1.) << std::endl;
//     CHECK(Prompt::floateq(v->getCrossSection(1.), expectedXS[i]));
//     i++;
//   }
// }


  // auto &fac = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();  
  // std::shared_ptr<Prompt::GIDIModel> gidimodel = fac.createNeutronGIDIModel("u235");
  // double ekin(1e6);

  // std::cout << "Gidi xs "<<gidimodel->getCrossSection(ekin)/Prompt::Unit::barn << std::endl;

  // pt::Vector in(1,0,0);
  // pt::Vector out(0,0,0);
  // double ekin_out;
  // double gidiekin(0);
  // int loop=1000;
  // auto hist1 = pt::Hist1D("gidi_hist", 0, 0.1, 100);
  // for(int i=0;i<loop;i++)
  // {
  //   gidimodel->generate(ekin, in, ekin_out, out );
  //   if(ekin_out!=-1.)
  //   gidiekin += ekin_out;
  //   hist1.fill(ekin_out);
  // }
  // std::cout << "gidiekin " << gidiekin/loop << std::endl;
  // hist1.save("histgidi.mcpl");

  // // auto pc = Prompt::NCrystalScat( "freegas::C/1.225kgm3/C_is_1.00_C12;temp=299.397" );
  // // std::cout << "NCrystal xs " <<pc.getCrossSection(ekin)/Prompt::Unit::barn << std::endl;
  // // gidiekin = 0;

  // // auto hist2 = pt::Hist1D("ncrystal_hist", 0, 0.1, 100);

  // // for(int i=0;i<loop;i++)
  // // {
  // //   pc.generate(ekin, in, ekin_out, out );
  // //   gidiekin += ekin_out;
  // //   hist2.fill(ekin_out);
  // // }
  // // std::cout << "gidiekin ncrystal " << gidiekin/loop << std::endl;
  // hist2.save("histnc.mcpl");


