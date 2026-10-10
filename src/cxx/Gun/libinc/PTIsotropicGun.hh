#ifndef Prompt_IsotropicGun_hh
#define Prompt_IsotropicGun_hh

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
#include "PTParticle.hh"
#include "PTVector.hh"
#include "PTSimpleThermalGun.hh"

namespace Prompt {
  class IsotropicGun : public SimpleThermalGun {
  public:
    IsotropicGun(const Particle &aParticle, double ekin, const Vector &pos )
    : SimpleThermalGun(aParticle, ekin, pos), m_pos(pos) {};
    virtual ~IsotropicGun() {};
    virtual void samplePosDir(Vector &pos, Vector &dir) override
    {
        pos = m_pos;
        double r1 = m_rng.generate();
        double r2 = m_rng.generate();

        double u = 2*r1-1;
        double temp = sqrt(1-u*u);
        double v = temp*cos(2*M_PI*r2);
        double w = temp*sin(2*M_PI*r2);

        dir = Vector(u, v, w);
    }
  private:
    Vector m_pos;
  };
}


#endif
