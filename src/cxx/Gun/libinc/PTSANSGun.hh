#ifndef Prompt_SANSGun_hh
#define Prompt_SANSGun_hh

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

#include "PromptCore.hh"
#include "PTMPIGun.hh"
#include "PTVector.hh"
#include "PTRandCanonical.hh"
#include "PTPointwiseDist.hh"

namespace Prompt {
  class SANSGun : public MPIGun {
  public:
    //source size consist of 6 numbers x_front, y_front, z_front, x_back, y_back, z_back
    SANSGun(const Particle &aParticle, std::array<double, 6> sourceSize);
    virtual ~SANSGun();
    virtual void sampleEnergy(double &ekin) override;

  private:
    std::unique_ptr<PointwiseDist> m_distr;
  };
}


#endif
