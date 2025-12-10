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

#include "PTScorerDeposition.hh"

Prompt::ScorerDeposition::ScorerDeposition(const std::string &name, double e_min, double e_max, unsigned numbin, unsigned int pdg,
      Prompt::ScorerDeposition::ScorerType stype, bool linear, int groupid)
:Scorer1D("ScorerDeposition_" + name, stype, std::make_unique<Hist1D>("ScorerDeposition_" + name, 
e_min, e_max, numbin, linear), pdg, groupid)
{
}

Prompt::ScorerDeposition::~ScorerDeposition()
{
}

void Prompt::ScorerDeposition::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;
  m_hist->fill(particle.getDeposition(), particle.getWeight()*particle.getSurviveP());  
}
