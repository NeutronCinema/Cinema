#ifndef Prompt_UniModeratorGun_hh
#define Prompt_UniModeratorGun_hh

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
  class UniModeratorGun : public ModeratorGun {
  public:
    UniModeratorGun(const Particle &aParticle, double wl0, double dlt_wl, std::array<double, 6> sourceSize)
    :ModeratorGun(aParticle, sourceSize), m_wl0(wl0), m_dlt_wl(dlt_wl) {}

    virtual ~UniModeratorGun() {};
    virtual void sampleEnergy(double &ekin) override
    {
      ekin = wl2ekin(m_wl0+ m_dlt_wl*(m_rng.generate()-0.5));
    }

  private:
    double m_wl0, m_dlt_wl;


  };
}


#endif
