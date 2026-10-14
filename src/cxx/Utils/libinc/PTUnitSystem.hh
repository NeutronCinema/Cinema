#ifndef Prompt_PTUnitSystem_hh
#define Prompt_PTUnitSystem_hh

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

#include <cmath>
namespace Prompt {
  namespace Unit {
    constexpr double eV = 1.;
    constexpr double MeV = 1.e6*eV;
    constexpr double GeV = 1.e9*eV;
    constexpr double keV = 1.e3*eV;
    constexpr double meV = 1.e-3*eV;

    constexpr double s = 1.;
    constexpr double ms = 1.e-3*s;
    constexpr double ns = 1.e-9*s;
    constexpr double ps = 1.e-12*s;
    constexpr double fs = 1.e-15*s;

    constexpr double mm = 1.;
    constexpr double cm = 10*mm;
    constexpr double m = 1e3*mm;
    constexpr double Aa = 1e-10*m;

    constexpr double Aa3 = Aa*Aa*Aa;
    constexpr double barn = 1e-28*m*m;


    constexpr double g = 1.;
    constexpr double kg = 1.e3*g;
    constexpr double kelvin = 1.;

  }

  constexpr int const_neutron_pgd = 2112;
  constexpr int const_proton_pgd = 2212;
  constexpr int const_photon_pgd = 22;
  constexpr double const_deg2rad = M_PI/180;
  constexpr double const_rad2deg = 180/M_PI;


  constexpr double const_eV2kk = 1.0/2.072124652399821e-3;

  ///！ constants are directly obtained from NCrystal's source code
  constexpr double const_c  = 299792458*Unit::m/Unit::s ;// speed of light 
  constexpr double const_dalton2kg =  1.660539040e-27*Unit::kg; // amu to kg (source: NIST/CODATA 2018)
  constexpr double const_dalton2eVc2 =  931494095.17*Unit::eV; // amu to eV/c^2 (source: NIST/CODATA 2018)
  constexpr double const_avogadro = 6.022140857e23; // mol^-1 (source: NIST/CODATA 2018)
  constexpr double const_dalton2gpermol = const_dalton2kg*const_avogadro; // dalton to gram/mol
  //NB: const_dalton2gmol is almost but not quite unity (cf. https://doi.org/10.1007/s00769-013-1004-9)

  constexpr double const_boltzmann = 8.6173303e-5*Unit::eV/Unit::kelvin;  // eV/K
  constexpr double const_neutron_mass_amu = 1.00866491588; // [amu]
  constexpr double const_proton_mass_amu = 1.007276466621; // [amu]
  constexpr double const_planck = 4.135667662e-15*Unit::eV*Unit::s ;//[eV*s]
  constexpr double const_hbar = const_planck*0.5/M_PI;  //[eV*s]6.582119569509068e-16

  //Derived values:
  constexpr double const_cc  = const_c*const_c;
  constexpr double const_neutron_mass_evc2 = const_neutron_mass_amu * const_dalton2eVc2 / (const_c*const_c);// [ eV/(Aa/s)^2 ]
  constexpr double const_proton_mass_evc2 = const_proton_mass_amu * const_dalton2eVc2 / (const_c*const_c);// [ eV/(Aa/s)^2 ]

  //used in unittest
  constexpr double const_ekin_2200m_s = 0.5 * const_neutron_mass_evc2 * 2200.0*Unit::m * 2200.0*Unit::m ; //neutron kinetic energy at 2200m/s [eV]
}
#endif
