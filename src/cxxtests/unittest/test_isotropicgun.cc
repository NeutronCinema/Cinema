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
#include "PTIsotropicGun.hh"
#include "PTNeutron.hh"
#include "PTVector.hh"
#include "PTHist1D.hh"


namespace pt = Prompt;

TEST_CASE("test_isotropicgun")
{
  auto hist = std::make_unique<pt::Hist1D>("test_isotropicgun", 0.0001, 180 , 100, false);
  auto gun = pt::IsotropicGun(pt::Neutron(), 0.0253, pt::Vector(0.,0.,-12000.));
  double sum_theta = 0.0;
  double num = 10000;
  for(unsigned i=0;i<num;i++)
  {
    auto p = gun.generate();
    const pt::Vector& direction = p->getDirection();
    double theta = direction.angle(pt::Vector(0.,0.,1))*180/M_PI;
    sum_theta += theta;

    std::cout << "event id " << p->getEventID()
    << " " << p->getDirection()
    << " " << theta << std::endl;
    hist->fill(theta);
  }
  hist->save("test_isotropicgun");
  std::cout << "average of theta " <<sum_theta/num << "degrees" << std::endl;

}

