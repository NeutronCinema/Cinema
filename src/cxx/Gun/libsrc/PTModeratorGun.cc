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

#include "PTModeratorGun.hh"

Prompt::ModeratorGun::ModeratorGun(const Particle &aParticle, std::array<double, 6> sourceSize)
:PrimaryGun(aParticle), m_sourceSize(sourceSize)
{ }

Prompt::ModeratorGun::~ModeratorGun()
{ }

void Prompt::ModeratorGun::samplePosDir(Vector &pos, Vector &dir)
{
  double moderator_x = (m_rng.generate()-0.5)*m_sourceSize[0];
  double moderator_y = (m_rng.generate()-0.5)*m_sourceSize[1];
  double flightPath = m_sourceSize[5]-m_sourceSize[2];
  pos = Vector{moderator_x, moderator_y, m_sourceSize[2]};

  double slit_x = (m_rng.generate()-0.5)*m_sourceSize[3];
  double slit_y = (m_rng.generate()-0.5)*m_sourceSize[4];
  dir = Vector{-moderator_x+slit_x, -moderator_y+slit_y, flightPath};
  dir = dir.unit();
}
