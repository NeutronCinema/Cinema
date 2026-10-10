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

#include <limits>

#include "PTNCrystalAbs.hh"
#include "PTUnitSystem.hh"
#include "PTRandCanonical.hh"
#include "PTLauncher.hh"


Prompt::NCrystalAbs::NCrystalAbs(const std::string &cfgstring, double bias,
    double lowerlimt, double upperlimt)
:Prompt::DiscreteModel(cfgstring+"_abs", const_neutron_pgd, lowerlimt, upperlimt, bias),
                      m_abs(NCrystal::createAbsorption(cfgstring))
{
  if( m_abs.isOriented() ) {
    PROMPT_THROW(CalcError, "Absorption process is not oriented");
  }
  m_res.dispeared = true;
}

Prompt::NCrystalAbs::~NCrystalAbs()
{
  std::cout<<"Destructing NCrystal absorption physics " << m_modelName <<", energy between [" << m_modelvalid.minEkin << ", " << m_modelvalid.maxEkin << "]"<< std::endl;
}


double Prompt::NCrystalAbs::getCrossSection(double ekin) const
{
  return m_abs.crossSectionIsotropic(NCrystal::NeutronEnergy(ekin)).get()*Unit::barn*m_bias;
}

double Prompt::NCrystalAbs::getCrossSection(double ekin, const Prompt::Vector &dir) const
{
  return getCrossSection(ekin);
}


const Prompt::SampledResult& Prompt::NCrystalAbs::sampleReaction(double ekin, const Vector &dir) const
{
  // fixme: this model does not include the Q valude
  m_res.deposition = ekin;
  return m_res;
}
