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

#include <chrono>
#include <iostream>

#include "PTRandCanonical.hh"

namespace pt = Prompt;

#include "../doctest.h"
TEST_CASE("SingletonRNG")
{
  auto &ref1 = pt::Singleton<pt::SingletonPTRand>::getInstance();
  printf("ref poniter %p\n", &ref1);

  auto &ref2 = pt::Singleton<pt::SingletonPTRand>::getInstance();
  printf("ref poniter %p\n", &ref2);

  CHECK(&ref1==&ref2);
}
