////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
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

#include "PTEnergyReflector.hh"
#include "PTUtils.hh"
#include "PTActiveVolume.hh"

Prompt::EnergyReflector::EnergyReflector(double ekin, bool islessthan = true)
:Prompt::SurfaceProcess("EnergyReflector"), m_ekin(ekin), m_islessthan(islessthan)
{ 
  std::string lt = m_islessthan ? "<=" : ">";
  std::cout << "constructor EnergyReflector physics "
  << "Particles with energy " << lt << " " << m_ekin <<"are reflected"
  << std::endl;
}

void Prompt::EnergyReflector::sampleFinalState(Prompt::Particle &particle) const
{
  auto &activeVolume = Singleton<ActiveVolume>::getInstance();
  activeVolume.getNormal(particle.getPosition(), m_refNorm);

  double ekin = particle.getEKin();
  const auto &nDirInLab = particle.getDirection();

  Vector newDir = nDirInLab - m_refNorm*(2*(nDirInLab.dot(m_refNorm)));
  double angleCos = newDir.angleCos(nDirInLab);

  if(m_ekin==-1.)
  {
    particle.setDirection(newDir);
    return;
  }

  if(m_islessthan == particle.getEKin()<=m_ekin)
    particle.setDirection(newDir);

}
