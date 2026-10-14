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
#include <iostream>

#include "PTNeutron.hh"
#include "PTProton.hh"

#include "PTMath.hh"
#include "PTVector.hh"
#include <vector>
namespace pt = Prompt;

TEST_CASE("Particle")
{
  auto en_vec = pt::logspace(-5, 2, 100);
  double pn_mass_ratio=pt::const_neutron_mass_amu/pt::const_proton_mass_amu;

  auto n = pt::Neutron(0., pt::Vector(1,0,0), pt::Vector(0,0,0) );
  auto p = pt::Proton(0., pt::Vector(1,0,0), pt::Vector(0,0,0) );
  std::cout << n << std::endl;

  for(auto en : en_vec)
  {
    n.setEKin(en);
    p.setEKin(en);
    printf("ekin %g, speed n %g, p %g\n\n", en, n.calcSpeed(), p.calcSpeed());
    double speedRatio = p.calcSpeed()/n.calcSpeed();
    CHECK(pt::floateq(speedRatio*speedRatio, pn_mass_ratio));
  }

  n.setEKin(pt::const_ekin_2200m_s);
  printf("referce energy at 2200m/s %g \n\n", pt::const_ekin_2200m_s);
  CHECK(pt::floateq(n.calcSpeed(), 2200*pt::Unit::m/pt::Unit::s));

}
