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

#include "PTScorerMultiScat.hh"
#include "PTLauncher.hh"
Prompt::ScorerMultiScat::ScorerMultiScat(const std::string &name, double xmin, double xmax, unsigned nxbins, 
                                        unsigned int pdg, Scorer::ScorerType stype, bool linear, int groupid)
:ScorerWithoutMixin("ScorerMultiScat_"+ name, stype, std::make_unique<Hist1D>("ScorerMultiScat_"+ name, xmin, xmax, nxbins, linear), pdg, groupid), 
m_currenteventid(0), 
m_p_counter(0), 
m_p_weight(0)
{
  if(stype!=Scorer::ScorerType::PEA_POST)
    PROMPT_THROW(BadInput, "ScorerType must be PROPAGATE_POST for ScorerMultiScat");
}

Prompt::ScorerMultiScat::~ScorerMultiScat() 
{}

/*
Type PEA_POST scorer, meaning both PROPAGATE_POST, EXIT, ABSORB trigger score action

When a new particle comes and trggers score action, direct EXIT and ABSORB without PROPAGATE will score (0, w)
PROPAGATE will score (1, w)

If a particle remains the same one as before, meaning multiple propagate or re-enter case, 
PROPAGATE_POST n times will score (n, w)

Notes: 
1. PROPAGATE_POST eg. 3 times will score both (1,w), (2,w), (3,w)
2. As a result, MUST BE VERY CAREFUL TO USE BIASING (VARIANCE REDUCTION) METHOD!!
*/
void Prompt::ScorerMultiScat::score(Particle &particle)
{
  if(!rightScorer(particle))
  return;

  if (m_currenteventid==particle.getEventID()) // the same particle as before, meaning multiple propagate or re-enter
  {
    // score only PROPAGATE_POST, to avoid re-enter case where multiple EXIT happens and score multiple times EXIT
    if(m_activeVolume.getCurrentTracingState()!=Scorer::ScorerType::PROPAGATE_POST) 
      return;
    m_p_counter++;
    m_p_weight=particle.getWeight();
  }
  else
  {
    // New particle comes, if PROPAGATE_POST, reset counter to 1, fill once; if direct EXIT or ABSORB, score (0, w)
    m_p_counter = (m_activeVolume.getCurrentTracingState()==Scorer::ScorerType::PROPAGATE_POST)? 1 : 0;
    m_p_weight=particle.getWeight();
    m_currenteventid=particle.getEventID();
    
    // if(m_p_counter==0)
    // {
      //   m_lasteventid=particle.getEventID();
      //   m_p_counter=1;
      //   m_p_weight=particle.getWeight();
      // }
      // else
      // {
        //   m_lasteventid=particle.getEventID();  // then reset
        //   m_p_counter=1;
        //   m_p_weight=particle.getWeight();
        // }
  }

  m_hist->fill(m_p_counter, m_p_weight);
      
}