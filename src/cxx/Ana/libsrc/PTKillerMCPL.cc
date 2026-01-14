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

#include "PTKillerMCPL.hh"
#include "PTMCPLBinaryWrite.hh"

Prompt::KillerMCPL::KillerMCPL(const std::string &name, unsigned int pdg, int groupid, bool kill, bool compress)
:Scorer1D("KillerMCPL_"+name, Scorer::ScorerType::ENTRY, std::make_unique<Hist1D>("KillerMCPL_"+name, -2.5, 100.5, 103, true), pdg=pdg, groupid=groupid),
m_writer(new MCPLBinaryWrite(name+".mcpl", false, true, true, compress)),
m_kill(kill)
{
}

Prompt::KillerMCPL::~KillerMCPL() 
{
  delete m_writer;
}

void Prompt::KillerMCPL::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;

  if(m_scatterCounter==nullptr)
  {
    m_writer->write(particle, -3);
  }
  else
    m_writer->write(particle, m_scatterCounter->getScatNumber());

  m_hist->fill(m_scatterNumberRequired);
  if(m_kill)
    particle.kill(Particle::KillType::SCORE);

}


