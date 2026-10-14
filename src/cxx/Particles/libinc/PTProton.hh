#ifndef Prompt_Proton_hh
#define Prompt_Proton_hh

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

#include "PTParticle.hh"
#include "PTMath.hh"

namespace Prompt {
  class Proton : public Particle {
  public:
    Proton();
    Proton(double ekin, const Vector& dir, const Vector& pos);
    virtual ~Proton(){};
  };
}

inline Prompt::Proton::Proton()
:Particle()
{
   m_pdg = const_proton_pgd;
   m_rest_mass = const_proton_mass_evc2;
}


inline Prompt::Proton::Proton(double ekin, const Vector& dir, const Vector& pos)
:Particle(ekin, dir, pos)
{
  m_pdg = const_proton_pgd;
  m_rest_mass = const_proton_mass_evc2;
}

#endif
