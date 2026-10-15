#ifndef Prompt_PrimaryGun_hh
#define Prompt_PrimaryGun_hh

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
#include "PTRandCanonical.hh"

namespace Prompt {
  class PrimaryGun : public Particle {
  public:
    PrimaryGun(const Particle &aParticle)
    : Particle(aParticle), m_rng(Singleton<SingletonPTRand>::getInstance()) {  };
    virtual ~PrimaryGun() = default;
    virtual std::unique_ptr<Particle> generate();
    virtual void sampleEnergy(double &ekin) = 0;
    virtual void samplePosDir(Vector &pos, Vector &dir) = 0;
    virtual double getParticleWeight() { return 1.;}
    virtual double getTime() { return 0.;}

  protected:
    SingletonPTRand &m_rng;

  };
}


#endif
