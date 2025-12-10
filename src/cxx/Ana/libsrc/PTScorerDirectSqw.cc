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

#include "PTScorerDirectSqw.hh"

Prompt::ScorerDirectSqw::ScorerDirectSqw(const std::string &name, double qmin, double qmax, unsigned xbin,
      double ekinmin, double ekinmax, unsigned nybins, unsigned int pdg, int group_id,
      double mod_smp_dist, double mean_ekin, const Vector& mean_incident_dir, const Vector& sample_position, 
      ScorerType stype)
:Scorer2D("ScorerDirectSqw_"+name, stype,
          std::make_unique<Hist2D>("ScorerDirectSqw_"+name, qmin, qmax, xbin, ekinmin, ekinmax, nybins), 
          pdg, group_id),
m_incident_dir(mean_incident_dir), m_sample_position(sample_position), 
m_mean_ekin(mean_ekin), m_mod_smp_dist(mod_smp_dist), m_time_L1(mod_smp_dist/neutronEkin2Speed(mean_ekin)),
m_scatterCounter(nullptr),
m_scatterNumberRequired(0)
{}

Prompt::ScorerDirectSqw::~ScorerDirectSqw() {}

void Prompt::ScorerDirectSqw::score(Prompt::Particle &particle)
{
  if(!rightScorer(particle))
    return;

  // std::cout << particle.getPosition() << "  "
  // << m_sample_position << std::endl;

  Vector dir = particle.getPosition()-m_sample_position;
  double flight_dist = dir.mag();
  double time = particle.getTime()-m_time_L1;
  double ekin = neutronSpeed2Ekin(time ? flight_dist/time: 0.);
  double q = neutronAngleCosine2Q(dir.angleCos(m_incident_dir), m_mean_ekin, ekin);
  m_hist->fill(q, m_mean_ekin-ekin, particle.getWeight()*particle.getSurviveP());
}
