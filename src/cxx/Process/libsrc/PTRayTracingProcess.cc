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

#include "PTRayTracingProcess.hh"

Prompt::RayTracingProcess::RayTracingProcess()
:Prompt::SurfaceProcess("RayTracing") 
, m_activeVol(Singleton<ActiveVolume>::getInstance()) { }

void Prompt::RayTracingProcess::sampleFinalState(Prompt::Particle &p) const
{
    auto loc_pos = m_activeVol.getGeoTranslator().global2Local(p.getPosition());
    auto loc_dir = m_activeVol.getGeoTranslator().global2Local_direction(p.getDirection());
    canSurvive(loc_pos, loc_dir, p.getTime()) ? p.moveForward(m_activeVol.distanceToOut(loc_pos, loc_dir)) : p.kill(Particle::KillType::RT_ABSORB);
}


