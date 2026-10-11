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
#include "PTException.hh"
#include "PTNCrystalScat.hh"
#include "PTUnitSystem.hh"
#include "PTRandCanonical.hh"
#include "PTLauncher.hh"

Prompt::NCrystalScat::NCrystalScat(const std::string &cfgstring, double bias,
    double lowerlimt, double upperlimt)
:Prompt::DiscreteModel(cfgstring+"_scat", const_neutron_pgd,
                      lowerlimt, upperlimt, bias),
                      m_scat(NCrystal::createScatter(cfgstring))
{
  m_oriented = m_scat.isOriented();
  if(Unit::eV != 1.)
    PROMPT_THROW(CalcError, "The default unit of NCrystal is eV");
}

Prompt::NCrystalScat::~NCrystalScat()
{
  std::cout<<"Destructing NCrystal scattering physics " << m_modelName << ", energy between [" << m_modelvalid.minEkin << ", " << m_modelvalid.maxEkin << "]" << std::endl;
}


double Prompt::NCrystalScat::getCrossSection(double ekin) const
{
  pt_assert_always(ekin < m_modelvalid.maxEkin);

  if( m_scat.isOriented() ) {
    PROMPT_THROW(CalcError, "direction should be provided for oriented material");
  }
  else
  {
    auto xsect = m_scat.crossSectionIsotropic( NCrystal::NeutronEnergy(ekin) );
    return xsect.get()*m_bias*Unit::barn;
  }
}

double Prompt::NCrystalScat::getCrossSection(double ekin, const Prompt::Vector &dir) const
{
  // fixme
  pt_assert_always(ekin < m_modelvalid.maxEkin);

  NCrystal::CrossSect xsect;
  if( m_scat.isOriented() ) {
    xsect = m_scat.crossSection( NCrystal::NeutronEnergy(ekin), {dir.x(), dir.y(), dir.z()} );
  }
  else
  {
    xsect = m_scat.crossSectionIsotropic( NCrystal::NeutronEnergy(ekin) );
  }
  return xsect.get()*m_bias*Unit::barn;
}

const Prompt::SampledResult& Prompt::NCrystalScat::sampleReaction(double ekin, const Vector &dir) const
{
  // NCrystal normalises the incident direction internally: on a null vector
  // that division yields NaN and its rejection loop never terminates.
  if(dir.isStrictNullVector())
    PROMPT_THROW(BadInput, "null incident direction, NCrystal direction sampling would loop forever");

  auto outcome1 = m_scat.sampleScatter( NCrystal::NeutronEnergy(ekin), {dir.x(), dir.y(), dir.z()});
  m_res.final_ekin = outcome1.ekin.get();
  auto &outdir = outcome1.direction;
  m_res.final_dir.x() = outdir[0];
  m_res.final_dir.y() = outdir[1];
  m_res.final_dir.z() = outdir[2];
  m_res.deposition = ekin - m_res.final_ekin;
  return m_res;
}
