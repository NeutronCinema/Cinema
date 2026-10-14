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

void Prompt::Particle::kill(KillType t)
{
  m_alive = false;
  m_killtype = t;
}

std::ostream& Prompt::operator << (std::ostream &o, const Prompt::Particle& p)
{
  return o<<"Particle: { " << p.getEventID() <<", ekin " << p.getEKin() 
          <<", time " << p.getTime() 
          <<", deposition " << p.getDeposition()
          <<", weight " << p.getWeight() << ", position "
          << p.getPosition() << ", direction " << p.getDirection() << " }";
}
