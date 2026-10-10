#ifndef Prompt_RandEngine_hh
#define Prompt_RandEngine_hh

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

#include "PromptCore.hh"

namespace Prompt {
  //This is the RandXRSR class of NCrystal to be removed

  class RandEngine final {
  public:
    RandEngine(uint64_t seed = 6402);
    double operator()();
    uint64_t min() const {return 0;}
    uint64_t max() const {return std::numeric_limits<uint64_t>::max();}
    ~RandEngine();
  private:
    void seed(uint64_t seed);

    uint64_t genUInt64();
    static uint64_t splitmix64(uint64_t& state);
    uint64_t m_s[2];
  };

}

#endif
