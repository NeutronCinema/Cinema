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

#include "PTMaxwellianGun.hh"

Prompt::MaxwellianGun::MaxwellianGun(const Particle &aParticle, double temperature, std::array<double, 6> sourceSize)
:ModeratorGun(aParticle, sourceSize), m_wlT(ekin2wl(temperature*const_boltzmann))
{ }

Prompt::MaxwellianGun::~MaxwellianGun()
{ }

void Prompt::MaxwellianGun::sampleEnergy(double &ekin)
{

    double wl = m_wlT/ sqrt(-log(m_rng.generate()*m_rng.generate()));
    ekin = wl2ekin(wl);
}
