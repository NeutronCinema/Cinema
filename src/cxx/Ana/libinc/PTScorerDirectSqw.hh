#ifndef Prompt_ScorerDirectSqw_hh
#define Prompt_ScorerDirectSqw_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    //
//                                                                            //
//  Copyright 2021-2026 Cinema developers                                     //
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

#include "PromptCore.hh"
#include "PTScorer2D.hh"
#include "PTScorerMultiScat.hh"

namespace Prompt {

  class ScorerDirectSqw  : public Scorer2D {
  public:
    ScorerDirectSqw(const std::string &name, double qmin, double qmax, unsigned xbin,
      double ekinmin, double ekinmax, unsigned nybins, unsigned int pdg, int group_id,
      double mod_smp_dist, double mean_ekin, const Vector& mean_incident_dir, const Vector& sample_position, 
      ScorerType stype=Scorer::ScorerType::ENTRY);
    virtual ~ScorerDirectSqw();
    virtual void score(Particle &particle) override;
  private:
    Vector m_incident_dir, m_sample_position;
    double m_mean_ekin, m_mod_smp_dist;
    double m_time_L1;
    const ScorerMultiScat* m_scatterCounter;
    int m_scatterNumberRequired;

  };
}
#endif
