#ifndef Prompt_MaxwellianGun_hh
#define Prompt_MaxwellianGun_hh

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
#include "PTModeratorGun.hh"
#include "PTVector.hh"
#include "PTRandCanonical.hh"

namespace Prompt {
  class MaxwellianGun : public ModeratorGun {
  public:
    //source size consist of 6 numbers x_front, y_front, z_front, x_back, y_back, z_back
    MaxwellianGun(const Particle &aParticle, double temperature, std::array<double, 6> sourceSize);
    virtual ~MaxwellianGun();
    virtual void sampleEnergy(double &ekin) override;

  private:
    double m_wlT;


  };
}


#endif
