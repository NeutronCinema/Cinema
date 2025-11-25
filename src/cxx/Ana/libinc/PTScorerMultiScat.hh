#ifndef Prompt_ScorerMultiScat_hh
#define Prompt_ScorerMultiScat_hh

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

#include "PromptCore.hh"
#include "PTScorer.hh"

namespace Prompt {
  class ScorerMultiScat : public ScorerWithoutMixin {
  public:
    ScorerMultiScat(const std::string &name, double xmin, double xmax, unsigned nxbins, 
                    unsigned int pdg, 
                    ScorerType stype=Scorer::ScorerType::PROPAGATE_POST,
                    bool linear=true,
                    int groupid=0);
    virtual ~ScorerMultiScat();
    virtual void score(Particle &particle) override;

    // remove the one counted by EXIT particle state that also count as PROPAGATE_POST
    // meaning the particle not entering the volume of interest returns -1
    int getScatNumber() const {return m_p_counter;} 
    unsigned long long getCurrentEventID() const {return m_currenteventid;}
  private:
    unsigned long long m_currenteventid;
    int m_p_counter;
    double m_p_weight;
  };
}
#endif
