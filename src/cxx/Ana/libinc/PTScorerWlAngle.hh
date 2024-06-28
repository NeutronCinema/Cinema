#ifndef Prompt_ScorerWlAngle_hh
#define Prompt_ScorerWlAngle_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2022 Prompt developers                                     //
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

  class ScorerWlAngle  : public Scorer2D {
  public:
    ScorerWlAngle(const std::string &name, const Vector &samplePos, const Vector &refDir, double sourceSampleDist,
      double wl_min, double wl_max, unsigned wl_nbins, double angle_min, double angle_max, unsigned angle_nbins, ScorerType stype=Scorer::ScorerType::ENTRY, int method=0, int scatnum=-1);
    virtual ~ScorerWlAngle();
    virtual void score(Particle &particle) override;
  protected:
    const Vector m_samplePos, m_refDir;
    const double m_sourceSampleDist;
    int m_method;
    int m_scatnum;
  };
}
#endif
