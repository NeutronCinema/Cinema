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

#include "PTDiskChopper.hh"
#include "PTUtils.hh"

Prompt::DiskChopper::DiskChopper(double theta0_deg, double r_mm, double phase_deg, double rotFreq_Hz, unsigned n)
:Prompt::RayTracingProcess(), m_theta0(theta0_deg*const_deg2rad), m_r(r_mm), m_phase(phase_deg*const_deg2rad), 
      m_angularSpeed(2*M_PI*rotFreq_Hz), m_angularPeriod(2*M_PI/n)
{
    if(m_angularPeriod < m_theta0)
        PROMPT_THROW(CalcError, "m_angularPeriod > m_theta0");
}


bool Prompt::DiskChopper::canSurvive(double x, double y, double time) const
{
    // Absorbed by the central part of the disk
    if(m_r*m_r>x*x+y*y)
        return false;

    // calculate the angular positon of the opening edge
    double angEdge = m_angularSpeed*time + m_phase - m_theta0/2;
    angEdge = fmod(angEdge, m_angularPeriod);

    double hitAngle = atan2(x, y);  
    if(hitAngle < 0) // so the range are between (0, 2pi)
        hitAngle += 2*M_PI;
    hitAngle = fmod(hitAngle, m_angularPeriod);

    // test intersection with the opening
    // std::cout << hitAngle << ", " << angEdge << ", " << m_theta0 << std::endl;
    // particle should also moves forward when it hits the slit of the last anglePeriod 
    if(hitAngle > angEdge-m_angularPeriod+m_theta0 && hitAngle < angEdge || hitAngle > angEdge+m_theta0 )
        return false;        
    else
        return true;
}

bool Prompt::DiskChopper::canSurvive(const Prompt::Vector &locPos, const Prompt::Vector &locDir, double time) const
{
    if(m_activeVol.numSubVolume())
        PROMPT_THROW2(CalcError, "Sub-volume is not allowed in a ray-tracing volume. The name of this volume is " << m_activeVol.getVolumeName());
    
    // check if the neutron hits the opening
    double x (locPos.x()), y(locPos.y());
    return canSurvive(x, y, time);
}

