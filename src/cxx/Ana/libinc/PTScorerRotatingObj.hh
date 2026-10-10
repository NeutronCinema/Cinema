#ifndef Prompt_ScorerRotatingObj_hh
#define Prompt_ScorerRotatingObj_hh

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
#include "PTScorer1D.hh"
#include "PTVector.hh"

namespace Prompt {

  class ScorerRotatingObj  : public Scorer1D {
  public:
    ScorerRotatingObj(const std::string &name, const Vector &dir, const Vector &point,
      double rotFreq, unsigned int pdg);
    virtual ~ScorerRotatingObj();
    virtual void score(Particle &particle) override;
  private:
    Vector getLinearVelocity(const Vector &pos);
    const Vector m_rotaxis, m_point;
    double m_angularfreq;
  };
}
#endif
