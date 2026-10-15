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
#include "PTMath.hh"
#include "PTVector.hh"

namespace pt = Prompt;

TEST_CASE("Math")
{
  auto n = pt::Neutron( 100, pt::Vector(1,0,0), pt::Vector(0,0,0) );
  printf("%.16g\n", n.calcSpeed());
  CHECK(pt::floateq(n.calcSpeed(), 138315926.4696229));
}
