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

#include "PTScorerESpectrum.hh"
#include "PTScorerMultiScat.hh"

Prompt::ScorerESpectrum::ScorerESpectrum(const std::string &name, bool scoreTransfer, double xmin, double xmax, unsigned nxbins,
                                         unsigned pdg, ScorerType stype, int groupid, bool linear)
:Scorer1D("ScorerESpectrum_"+name, stype, std::make_unique<Hist1D>("ScorerESpectrum_"+name, xmin, xmax, nxbins, linear), pdg, groupid),
m_scoreTransfer(scoreTransfer)
{}

Prompt::ScorerESpectrum::~ScorerESpectrum() 
{
}

void Prompt::ScorerESpectrum::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;

  m_scoreTransfer ? m_hist->fill(particle.getEKin0()-particle.getEKin(),  particle.getWeight()*particle.getSurviveP() ) :
                    m_hist->fill(particle.getEKin(),  particle.getWeight()*particle.getSurviveP() );
  

  // if (!m_scoreTransfer)
  //   m_hist->fill(particle.getEKin(),  particle.getWeight() );
  // else if (particle.getEKin0()!=particle.getEKin()) 
  // // FIXME: neither elastic scattered or transmitted neutrons are recorded. 
  // // Should better score elastic scattered neutrons, with PEA scorer?
  //   m_hist->fill(particle.getEKin0()-particle.getEKin(),  particle.getWeight() );

  //XX, elastic scattered and transmitted neutrons can be removed by setting xmin>0. Above code is comment out
}


