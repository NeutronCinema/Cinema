#ifndef Prompt_MirrorPhyiscs_hh
#define Prompt_MirrorPhyiscs_hh

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

#include <string>

#include "PromptCore.hh"
#include "PTSurfaceProcess.hh"

namespace Prompt {

  class Mirror  : public SurfaceProcess {
    public:
      Mirror(double mvalue, double weightCut = 1e-3);
      virtual ~Mirror() = default;
      virtual void sampleFinalState(Prompt::Particle &particle) const override;
      double getEventWeight() const {return m_wAtQ;}

    private:
      double m_m, m_R0, m_Qc, m_alpha, m_W, m_i_W;
      const double m_wcut;
      mutable double m_wAtQ;
      mutable Vector m_refNorm;

  };

}

#endif
