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

Prompt::ScorerMultiScat::ScorerMultiScat(const std::string &name, double xmin, double xmax, unsigned nxbins, 
                                        unsigned int pdg, Scorer::ScorerType stype, bool linear, int groupid)
:ScorerWithoutMixin("ScorerMultiScat_"+ name, stype, std::make_unique<Hist1D>("ScorerMultiScat_"+ name, xmin, xmax, nxbins, linear), pdg, groupid), 
m_lasteventid(0), 
m_p_counter(0), 
m_p_weight(0)
{
  if(stype!=Scorer::ScorerType::PROPAGATE_POST)
    PROMPT_THROW(BadInput, "ScorerType must be PROPAGATE_POST for ScorerMultiScat");
}

Prompt::ScorerMultiScat::~ScorerMultiScat() 
{}

void Prompt::ScorerMultiScat::score(Particle &particle)
{
  if(!rightScorer(particle))
    return;

  if (m_lasteventid==particle.getEventID())
  {
    m_p_counter++;
    m_p_weight=particle.getWeight();
  }
  else
  {
    if(m_p_counter==0)
    {
      m_lasteventid=particle.getEventID();
      m_p_counter=1;
      m_p_weight=particle.getWeight();
    }
    else
    {
      m_hist->fill(m_p_counter-1, m_p_weight);
      m_lasteventid=particle.getEventID();
      m_p_counter=1;
      m_p_weight=particle.getWeight();
    }
  }

}