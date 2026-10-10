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

#include "PTPython.hh"

namespace pt = Prompt;

// Converters
double pt_eKin2k(double ekin) { return Prompt::neutronEKin2k(ekin); }
double pt_angleCosine2Q(double anglecosine, double enin_eV, double enout_eV) {  return Prompt::neutronAngleCosine2Q(anglecosine, enin_eV, enout_eV); }
double pt_wl2ekin( double wl) { return Prompt::wl2ekin(wl); }
double pt_ekin2wl( double ekin) { return Prompt::ekin2wl(ekin); }
double pt_ekin2speed( double ekin) { return std::sqrt(2*ekin/Prompt::const_neutron_mass_evc2);}
double pt_speed2ekin( double v) { return v*v*0.5*Prompt::const_neutron_mass_evc2; }
