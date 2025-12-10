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

#include "PTScorerPSD.hh"
#include "PTActiveVolume.hh"

Prompt::ScorerPSD::ScorerPSD(const std::string &name, double xmin, double xmax,
   unsigned nxbins, double ymin, double ymax, unsigned nybins, unsigned int pdg, ScorerType stype, PSDType type, int groupid, bool isGlobal)
:Scorer2D("ScorerPSD_"+name, stype,
  std::make_unique<Hist2D>("ScorerPSD_"+name, xmin, xmax, nxbins, ymin, ymax, nybins), pdg, groupid),
 m_type(type),
 m_isGlobal(isGlobal)
{}

Prompt::ScorerPSD::~ScorerPSD() {}

void Prompt::ScorerPSD::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;

  Vector vec;
  if(m_isGlobal)
    vec = particle.getPosition();
  else
    vec = m_activeVolume.getGeoTranslator().global2Local(particle.getPosition());

  if (m_type==PSDType::XY)
    m_hist->fill(vec.x(), vec.y(), particle.getWeight() *particle.getSurviveP());
  else if (m_type==PSDType::YZ)
    m_hist->fill(vec.y(), vec.z(), particle.getWeight() *particle.getSurviveP());
  else if (m_type==PSDType::XZ)
    m_hist->fill(vec.x(), vec.z(), particle.getWeight() *particle.getSurviveP() );
  else
    PROMPT_THROW2(BadInput, m_name << " not support type");
}
