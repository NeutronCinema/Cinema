#ifndef Prompt_MultiScatMixin_hh
#define Prompt_MultiScatMixin_hh

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
#include "PTScorerMultiScat.hh"
#include "PTParticle.hh"

namespace Prompt {
  template <typename T>
  class MultiScatMixin {
  public:
    // Constructor to initialize the log level
    // m_scatterNumberRequired==-2, rightScatterNumber() always returns true for every particle.
    // m_scatterNumberRequired==-1, rightScatterNumber() returns true for particle not entering the region of interest.
    // m_scatterNumberRequired== 0, rightScatterNumber() returns true for particle entered but not interacted with the region of interest (direct exit).
    // m_scatterNumberRequired== n, rightScatterNumber() returns true for particle scattered n times in the region.
    MultiScatMixin(const ScorerMultiScat* scatterCounter, int scatNumReq=-2) : 
      m_scatterNumberRequired(scatNumReq), m_scatterCounter(scatterCounter) {}

    void addMultiScatter(const Prompt::ScorerMultiScat* scatterCounter, int scatNumReq=-2 ) 
    {
      m_scatterCounter=scatterCounter;
      m_scatterNumberRequired = scatNumReq;
      std::cout << "Scattering number req: " << m_scatterNumberRequired << std::endl;
    }

    bool rightScatterNumber(const Particle &particle) const {

      // ScorerMultiScat is not provided, so accepts all particles
      if(m_scatterCounter==nullptr)
        return true;

      if(m_scatterNumberRequired==-2 )
      {
        return true;
      }

      // if a particle transmitted through the region of interest, current particle id must be recorded
      // then if the current pid != mscpid, meaning that the particle did not go through ROI
      if(m_scatterNumberRequired==-1)
      {
        return particle.getEventID()!=m_scatterCounter->getCurrentEventID();
      }

      // Only particles transmitted through the region of interest, in this case, IDs must be equal otherwise miscount the last particles
      if(m_scatterNumberRequired==0)
      {
        return particle.getEventID()==m_scatterCounter->getCurrentEventID()?
        m_scatterCounter->getScatNumber()==m_scatterNumberRequired:false;
      }

      // IDs must be equal otherwise miscount the last particles
      return m_scatterCounter->getScatNumber()==m_scatterNumberRequired?
      particle.getEventID()==m_scatterCounter->getCurrentEventID():false;

    }
    
  protected:
    const ScorerMultiScat* m_scatterCounter;
    int m_scatterNumberRequired;
  };

}
#endif
