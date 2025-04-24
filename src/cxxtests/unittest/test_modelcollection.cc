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
#include "PTMath.hh"
#include "PTModelCollection.hh"
#include "PTParticleProcess.hh"
#include "PTLauncher.hh"
#include "PTGidiSetting.hh"

TEST_CASE("ModelCollection")
{
  // !! NCrystal scattering + NCrystal Abs != NCrystal scattering + GIDI Abs
  using namespace Prompt;
  // std::vector<double> expectedEnergyOut;
  // expectedEnergyOut = {0.0253, 0.0263, 0.045192303408606, 0.0283, -1, 0.00542322400666893 };
  // std::vector<std::vector<double>> expectedDirOut;
  // expectedDirOut ={
  //   { 0.211330297846913, -0.592201916881118, -0.777583689935858 },
  //   { -0.896705652516454, 0.227612286342529, -0.379620362798107 },
  //   { 0.349974039965383, -0.141170718428235, 0.926061012897511 },
  //   { -0.762662850218472, 0.547355775591302, -0.344596912092202 }, 
  //   { -0.762662850218472, 0.547355775591302, -0.344596912092202 }, //same as previous one due to absorption, variable outdir unchanged
  //   { -0.423603163886187, -0.904003071387581, 0.0577824062101281 }
  // };
  std::vector<double> expectedXS;
  #ifdef ENABLE_GIDI
  expectedXS={
    1.680228126153258,
    1.638541715024224,
    1.600408252103404,
    1.565449983578320,
    1.533417449071772,
    1.612889632139340
    };
  #else
  expectedXS={
    1.67763252179636,
    1.63598819378975,
    1.59790799293761,
    1.5630143018536,
    1.5310237678712,
    1.61052559545843
    };
  #endif
  double inE(0.0253);
  auto inDir = Vector({1.,0.,0.});
  #ifdef ENABLE_GIDI
  auto &cd = Singleton<GidiSetting>::getInstance();
  cd.setEnableGidi(true);
  #endif
  auto pp = ParticleProcess("Al_sg225.ncmat");
  auto compModel = pp.getModelCollection();
  double xs(0.);
  std::cout.precision(15);
  std::cout << "here "<< std::endl;

  double finE(0.);
  Vector finDir;
  for(size_t i=0;i<6;i++)
  {
    std::cout << "In energy: " << inE << std::endl;
    std::cout << "In dir: " << inDir << std::endl;
    xs = compModel->totalCrossSection(2112, inE, inDir);
      std::cout << "xs = compModel->totalCrossSection(2112, inE, inDir) "<< std::endl;

    std::cout << "Total XS: " << std::endl;
    std::cout << xs/Unit::barn << std::endl;
    std::cout << "  versus " << std::endl;
    std::cout << expectedXS[i] << std::endl;
    std::cout << "" << std::endl;
    
    CHECK(floateq(xs/Unit::barn, expectedXS[i]));
    // compModel->generate(inE, inDir, finE, finDir);
    // std::cout << "Out energy: " << finE << std::endl;
    // CHECK(floateq(finE, expectedEnergyOut[i]));
    // std::cout << "Out dir: " << finDir << std::endl;
    // CHECK(floateq(finDir.x(), expectedDirOut[i][0]));
    // CHECK(floateq(finDir.y(), expectedDirOut[i][1]));
    // CHECK(floateq(finDir.z(), expectedDirOut[i][2]));
    // std::cout << "  " << std::endl;
    inE += 0.001;
  }

  // auto collection = ModelCollection(2112) ;
  // collection.addNCScaAbsModels("Al_sg225.ncmat;dcutoff=0.5;temp=25C");

  // double xs(0.);
  // xs = collection.totalCrossSection(1., {0,0,0} );
  // Vector out;
  // double final;
  // std::cout << xs << std::endl;
  // printf("%.15f\n", xs);

  // CHECK(floateq(1.378536096609809*Unit::barn, xs ));


  // collection.generate(1., {1,0,0}, final, out);
  // std::cout << final << " " << out << std::endl;

  // collection.generate(1., {1,0,0}, final, out);
  // std::cout << final << " " << out << std::endl;

  // collection.generate(1., {1,0,0}, final, out);
  // std::cout << final << " " << out << std::endl;
}
