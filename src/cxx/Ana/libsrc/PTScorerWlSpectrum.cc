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

#include "PTScorerWlSpectrum.hh"


Prompt::ScorerWlSpectrum::ScorerWlSpectrum(const std::string &name, double xmin, double xmax, unsigned nxbins, unsigned int pdg, ScorerType stype, int groupid, bool linear)
:Scorer1D("ScorerWlSpectrum_"+name, stype, std::make_unique<Hist1D>("ScorerWlSpectrum_"+name, xmin, xmax, nxbins, linear), pdg, groupid)
{}

Prompt::ScorerWlSpectrum::~ScorerWlSpectrum() {}

void Prompt::ScorerWlSpectrum::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;
  m_hist->fill(ekin2wl(particle.getEKin()),  particle.getWeight() );
}
