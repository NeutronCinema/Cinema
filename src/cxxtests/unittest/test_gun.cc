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

#include "PTMaxwellianGun.hh"
#include "PTNeutron.hh"
#include "PTHist1D.hh"

namespace pt = Prompt;

TEST_CASE("test_maxwellgun")
{
  std::vector<std::vector<double>> expectedPos ={
    { 0.210671228978656, 0.44666780096097, -1400 },
    { 0.0206431525734917, -0.155329693920812, -1400 },
    { 0.0219157100717673, 0.357077283552821, -1400 },
    { -0.260723379191671, -0.179935108337711, -1400 },
    { 0.215892721529083, 0.467824728715947, -1400 }
  }; 
  std::vector<std::vector<double>> expectedDir ={
    { -0.000493857167642691, -0.0003869753925094, 0.999999803177552 },
    { -0.000176033958720795, 0.0001545441344008, 0.999999972564077 },
    { -1.58152492727249e-05, -0.000312648027179254, 0.999999951000543 },
    { 0.000479445821360155, -0.000110879921343369, 0.999999878918666 },
    { 3.82420837009967e-05, -0.000633655143325756, 0.999999798509331 }
  }; 
  std::vector<double> expectedEkin = {0.0419869785110098, 0.1335482693416, 0.0665663356431823, 0.0435596911456489, 0.078129884568357}; 

  
  auto hist = std::make_unique<pt::Hist1D>("test_maxwellgun", 0.0001, 0.3 , 100, false);
  auto gun = pt::MaxwellianGun(pt::Neutron(), 300, {1,1,-1400,1,1,0});
  for(unsigned i=0;i<5;i++)
  {
    auto p = gun.generate();
    std::cout.precision(15);
    std::cout << "event id " 
    << p->getEventID()
    << " pos: " << p->getPosition()
    << " dir: " << p->getDirection() 
    << " ekin: " << p->getEKin()
    << std::endl;
    hist->fill(p->getEKin());
    CHECK(pt::floateq(p->getPosition().x(), expectedPos[i][0]));
    CHECK(pt::floateq(p->getPosition().y(), expectedPos[i][1]));
    CHECK(pt::floateq(p->getPosition().z(), expectedPos[i][2]));
    CHECK(pt::floateq(p->getDirection().x(), expectedDir[i][0]));
    CHECK(pt::floateq(p->getDirection().y(), expectedDir[i][1]));
    CHECK(pt::floateq(p->getDirection().z(), expectedDir[i][2]));
    CHECK(pt::floateq(p->getEKin(), expectedEkin[i]));
  }
  std::cout << "integral " << hist->getTotalWeight() << std::endl;
  hist->save("test_maxwellgun");

}
