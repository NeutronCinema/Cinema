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

#include "PTScorerSplit.hh"
#include "PTStackManager.hh"

Prompt::ScorerSplit::ScorerSplit(const std::string &name, unsigned split, unsigned int pdg)
:Scorer1D("ScorerSplit_"+ name, Scorer::ScorerType::ENTRY, 
  std::make_unique<Hist1D>("ScorerSplit_"+ name, 1e-10, 1e2, 1200, false), pdg), m_split(split), m_lastsplit(-1)
{ }

Prompt::ScorerSplit::~ScorerSplit() {}

void Prompt::ScorerSplit::score(Particle &particle)
{
  if(!rightScorer(particle))
    return;
    
  if(m_lastsplit != particle.getEventID() )
  {
    m_hist->fill(particle.getWeight()*particle.getSurviveP());
    if (m_split>1)
    {
      particle.scaleWeight(1./m_split);
      auto &stackManager = Singleton<StackManager>::getInstance();
      stackManager.add(particle, m_split-1);
    }
    m_lastsplit = particle.getEventID();
  }
}
