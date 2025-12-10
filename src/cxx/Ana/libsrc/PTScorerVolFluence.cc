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

#include "PTScorerVolFluence.hh"

Prompt::ScorerVolFluence::ScorerVolFluence(const std::string &name, double xmin, double xmax, unsigned nxbins, 
                                            double volme, unsigned int pdg, ScorerType stype, bool linear, int groupid)
:Scorer1D("ScorerVolFluence_"+ name, stype, std::make_unique<Hist1D>("ScorerVolFluence_"+ name, xmin, xmax, nxbins, linear), pdg, groupid), 
m_iVol(1./volme), 
m_weight(-1.)
{ }

Prompt::ScorerVolFluence::~ScorerVolFluence() {}

void Prompt::ScorerVolFluence::score(Particle &particle)
{
  if(!rightScorer(particle))
    return;

  if(m_weight == -1.) m_weight=particle.getWeight();

  if(particle.getWeight()!=m_weight)
    PROMPT_THROW(LogicError, "ScorerVolFluence is incorrect in the cross section biasing model. The D value for the material within the solid of insterest should be unity");

  #ifdef DEBUG_PTS
    std::cout << "Scoring VolFluence >> Particle "
    << "ID: " << particle.getEventID() 
    << " | Energy: " << particle.getEKin()
    << " | Delta Energy: " << particle.getEnergyChange()
    << " | step length: " << particle.getStep()
    << std::endl;
  #endif
  
  m_hist->fill(particle.getEKin(), m_iVol*particle.getStep()*particle.getSurviveP());
  
}
