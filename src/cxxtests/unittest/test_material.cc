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
#include "PTParticleProcess.hh"
#include "PTPhoton.hh"
#include "PTNeutron.hh"

TEST_CASE("ParticleProcess")
{
  auto mat = Prompt::ParticleProcess("LiquidWaterH2O_T293.6K.ncmat") ;
  double ekin  = 0.0253;
  auto n = Prompt::Neutron(ekin, Prompt::Vector(1,0,0), Prompt::Vector(0,0,0) );
  // auto n = Prompt::Photon(ekin, Prompt::Vector(1,0,0), Prompt::Vector(0,0,0) );

  double totlength(0.);
  unsigned loop(100000);
  double fmp(0.);
  for(unsigned i=0;i<loop;i++)
  {
    totlength += mat.sampleStepLength(n, fmp);
  }
  printf("%.16f \n", totlength/loop);
  CHECK(Prompt::floateq(totlength/loop, 2.7599510379162586));
}
