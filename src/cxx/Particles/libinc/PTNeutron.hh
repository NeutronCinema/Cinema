#ifndef Prompt_Neutron_hh
#define Prompt_Neutron_hh

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
//! Neutron is neutron with pgd code of 2112 by defult. Proton (2212) is also supported.
//! m_erest is in the unit of eV*c^2
//! fixme: support Gamma (22) as well.
namespace Prompt {
  class Neutron : public Particle {
  public:
    Neutron();
    Neutron(double ekin, const Vector& dir, const Vector& pos);
    virtual ~Neutron(){};
  };
}

inline Prompt::Neutron::Neutron()
:Particle()
{
   m_pdg = const_neutron_pgd;
   m_rest_mass = const_neutron_mass_evc2;
}

inline Prompt::Neutron::Neutron(double ekin, const Vector& dir, const Vector& pos)
:Particle(ekin, dir, pos)
{
  m_pdg = const_neutron_pgd;
  m_rest_mass = const_neutron_mass_evc2;
}

#endif
