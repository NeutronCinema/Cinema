#ifndef Prompt_DiskChopper_hh
#define Prompt_DiskChopper_hh

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
#include "PTRayTracingProcess.hh"

namespace Prompt {

  // The class DiskChopper is a ray-tracing model for a finite thickness 
  // neutron black disk with n symmetrical openings. The disk is parallel
  // with the X-Y plane. The beginning of the opening
  // is aligned with the T0. The difference can be specified as the phase
  // The centre is defined using the reference frame of the volume.
  // The positive rotation direction is right handed in given rotation axis
  class DiskChopper  : public RayTracingProcess
  {
    public:
      DiskChopper(double theta0_deg, double r_mm, double phase_deg, double rotFreq_Hz, unsigned n);
      virtual ~DiskChopper() = default;
      virtual bool canSurvive(const Prompt::Vector &locPos, const Prompt::Vector &locDir, double time) const override;

      bool canSurvive(double x, double y, double time) const;

    private:
      double m_theta0, m_r, m_phase, m_angularSpeed, m_angularPeriod;
  };

  // // fixme: todo
  // class MultiDiskChopper 
  // {
  //   public:
  //     MultiDiskChopper();
  //     ~MultiDiskChopper();
  //   private:
  //     std::vector<MultiDiskChopper> m_disks;
  // }

}

#endif
