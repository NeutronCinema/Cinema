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

#include "PTScorerAngular.hh"
#include <algorithm>

Prompt::ScorerAngular::ScorerAngular(const std::string &name, 
      double min, double max, unsigned numbin, unsigned int pdg,
      Vector refDir,  ScorerType stype, bool inDegree, bool linear)
:Scorer1D("ScorerAngular_" + name, stype, std::make_unique<Hist1D>("ScorerAngular_" + name, 
min, max, numbin, linear), pdg), m_refDir(refDir.unit()), m_inDegree(inDegree)
{
  if(inDegree)
  {
    if(max>180 || min<0 || min>=max)
      PROMPT_THROW2(BadInput, "angular range should be within 0 to 180 degrees and and min<max" 
                  << "the given min is " << min
                  << ", the given max is " << max )
  }
  else
  {
    if(max>1 || min<-1 || min>=max)
      PROMPT_THROW2(BadInput, "mu range should be within -1 to 1 and min<max"
                  << "the given min is " << min
                  << ", the given max is " << max  )
  }
}

Prompt::ScorerAngular::~ScorerAngular()
{
}

void Prompt::ScorerAngular::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;

  double angle_cos = std::clamp(m_refDir.angleCos(particle.getDirection()), -1., 1.);
  m_hist->fill(m_inDegree ? std::acos(angle_cos)*const_rad2deg: angle_cos, particle.getWeight()*particle.getSurviveP());  
}
