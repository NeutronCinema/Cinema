#ifndef Prompt_SimpleThermalGun_hh
#define Prompt_SimpleThermalGun_hh

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
#include "PTPrimaryGun.hh"
#include "PTParticle.hh"
#include "PTVector.hh"

namespace Prompt {
  class SimpleThermalGun : public PrimaryGun {
  public:
    SimpleThermalGun(const Particle &aParticle, double ekin=0.0253, const Vector &pos=Vector{0.,0.,-12000.}, const Vector &dir=Vector{0.,0.,1.} )
    : PrimaryGun(aParticle), m_ekin(ekin), m_pos(pos), m_dir(dir.unit()) {};
    virtual ~SimpleThermalGun() {};
    virtual void sampleEnergy(double &ekin)
    {
      if(m_ekin==0.)
      {
        double cosr = cos(M_PI*0.5*m_rng.generate());
        ekin = 0.0253*(-log(m_rng.generate())-log(m_rng.generate())*cosr*cosr);
      }
      else if(m_ekin>0)
      {
        ekin = m_ekin;
      }
    };

    virtual void samplePosDir(Vector &pos, Vector &dir) { pos = m_pos; dir=m_dir; }
  private:
    double m_ekin;
    Vector m_pos, m_dir;
  };
}


#endif
