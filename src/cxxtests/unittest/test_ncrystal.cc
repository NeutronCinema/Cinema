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
#include "PTNCrystalScat.hh"
#include "PTNCrystalAbs.hh"
#include "PTMath.hh"
#include "PTMaterialDecomposer.hh"


TEST_CASE("NCrystal scattering physics")
{

  // class CustomRNG : public NC::RNGStream {
  //   std::mt19937_64 m_gen;
  // protected:
  //   double actualGenerate() override { return NC::randUInt64ToFP01(static_cast<uint64_t>(m_gen())); }
  //   //For the sake of example, we wrongly claim that this generator is safe and
  //   //sensible to use multithreaded (see NCRNG.hh for how to correctly deal with
  //   //MT safety, RNG states, etc.):
  //   bool useInAllThreads() const override { return true; }
  // };
  //
  // //The NCrystal makeSO function is similar to std::make_shared
  // //and should be used instead of raw calls to new and delete:
  // auto rng = NC::makeSO<CustomRNG>();
  //
  // //Register:
  // NC::setDefaultRNG(rng);

  //////////////////////////////////////
  // Create and use aluminium powder: //
  //////////////////////////////////////
  // std::vector<double> expectedEnergyOut;
  // expectedEnergyOut = {0.895688481646089, 0.913113714008026, 0.893634719170785 };
  // std::vector<std::vector<double>> expectedDirOut;
  // expectedDirOut ={
  //   { -0.667313017257404, -0.443201936751825, 0.598552738075978 },
  //   { -0.569071523546255, -0.478398437813209, -0.668799324002818 },
  //   { -0.476695834028235, 0.192041130941706, 0.857835232341711 },
  // };

  auto pc = Prompt::NCrystalScat( "Al_sg225.ncmat;dcutoff=0.5;temp=25C" );
  double xs = pc.getCrossSection(1);
 
  std::cout.precision(15);
  std::cout << xs << std::endl;
  printf("%.15f\n", xs);

  CHECK(Prompt::floateq(1.378536096609809*Prompt::Unit::barn, xs ));

  // double inE(1.);
  // auto inDir = Prompt::Vector({1.,0.,0.});
  // double finE(0.);
  // Prompt::Vector finDir;
 
  // for(size_t i=0;i<3;i++)
  // {
  //   std::cout << "In energy: " << inE << std::endl;
  //   std::cout << "In dir: " << inDir << std::endl;
  //   pc.generate(inE, inDir, finE, finDir);
  //   std::cout << "Out energy: " << finE << std::endl;
  //   CHECK(Prompt::floateq(finE, expectedEnergyOut[i]));
  //   std::cout << "Out dir: " << finDir << std::endl;
  //   CHECK(Prompt::floateq(finDir.x(), expectedDirOut[i][0]));
  //   CHECK(Prompt::floateq(finDir.y(), expectedDirOut[i][1]));
  //   CHECK(Prompt::floateq(finDir.z(), expectedDirOut[i][2]));
  //   std::cout << "  " << std::endl;
  // }

  // pc.generate(1., {1,0,0}, final, out);
  // std::cout << final << " " << out << std::endl;


  //
  NCrystal::MatCfg gecfg("Ge_sg227.ncmat;dcutoff=0.5;mos=40arcsec;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,-1,1@lab:0,1,0" );
  auto ge = NCrystal::createScatter(gecfg);

  auto wl = NCrystal::NeutronWavelength{1.540};
  auto xsect = ge.crossSection( wl, { 0.0, 1.0, 1.0 } );
  std::cout << "single crystal Ge x-sect at "<<wl<<" Aa is "<<xsect<<" barn (orientation 1)"<<std::endl;

  auto &nm = Prompt::Singleton<Prompt::MaterialDecomposer>::getInstance();
  nm.getComposition(10);
  // auto res = nm.decompose("Ge_sg227.ncmat");
  // auto res = nm.decompose("solid::B4C/2500gcm3/B_is_1.00_B10");
  double temp=0.;
  auto res = nm.decompose("solid::B4C/2500gcm3/B_is_0.95_B10_0.05_B11", temp);

  for(auto it=res.begin();it!=res.end();++it)
    std::cout << *it << std::endl;


}


TEST_CASE("Ncrystal absorption physics")
{
  double inE(1.);
  auto inDir = Prompt::Vector({1.,0.,0.});
  double finE(0.);
  Prompt::Vector finDir;

  auto absModel = Prompt::NCrystalAbs("LiquidWaterH2O_T293.6K.ncmat");
  double absxs = absModel.getCrossSection(inE);
  std::cout << "Absorption XS at "<< inE << "eV : " << absxs << std::endl;
  CHECK(Prompt::floateq(absxs, .52781258905735e-24));

  // absModel.generate(inE, inDir, finE, finDir);
  // CHECK(Prompt::floateq(finE, -1.));
}