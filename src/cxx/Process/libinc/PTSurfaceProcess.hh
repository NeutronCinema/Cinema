#ifndef Prompt_SurfaceProcess_hh
#define Prompt_SurfaceProcess_hh

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

#include <string>
#include "PromptCore.hh"
#include "PTParticle.hh"
#include "PTRandCanonical.hh"
#include "PTPhysicsModel.hh"

namespace Prompt {
  class SurfaceProcess : public PhysicsBase  {
  public:
    // by default the physics is applicable for neutron (2112)
    SurfaceProcess(const std::string& name, unsigned pgd=2112, double en_lowerlimt=0, double en_upperlim=std::numeric_limits<double>::max())
      : PhysicsBase(name, pgd, en_lowerlimt, en_upperlim)  {};
    virtual ~SurfaceProcess() = default;
    virtual void sampleFinalState(Particle &particle) const = 0;
  };

}

#endif
