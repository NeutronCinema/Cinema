#ifndef Prompt_Gamma_hh
#define Prompt_Gamma_hh

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
//! Gamma pgd code  22 
namespace Prompt {
  class Gamma : public Particle {
  public:
    Gamma();
    Gamma(double ekin, const Vector& dir, const Vector& pos);
    virtual ~Gamma(){};

    double calcSpeed() const override;
    double calcEffSpeed() const override;

  };
}

inline Prompt::Gamma::Gamma()
:Particle()
{
   m_pdg = const_photon_pgd;
   m_rest_mass = 0;
}

inline Prompt::Gamma::Gamma(double ekin, const Vector& dir, const Vector& pos)
:Particle(ekin, dir, pos)
{
  m_pdg = const_photon_pgd;
  m_rest_mass = 0;
}

double Prompt::Gamma::calcSpeed() const 
{
  PROMPT_THROW(NotImplemented, "Prompt::Gamma::calcSpeed()");
  return 0;
}

double Prompt::Gamma::calcEffSpeed() const 
{
  PROMPT_THROW(NotImplemented, "Prompt::Gamma::calcSpeed()");
  return 0;
}



#endif
