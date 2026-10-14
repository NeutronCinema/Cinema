#ifndef Prompt_Math_hh
#define Prompt_Math_hh

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

namespace Prompt {
  constexpr double ptclamp(double val, double low, double up);
  constexpr bool floateq(double a, double b, double rtol=1e-14, double atol=1e-14);
  std::vector<double> logspace(double start, double stop, unsigned num);
  std::vector<double> linspace(double start, double stop, unsigned num);

  constexpr double neutronEKin2k(double ekin);
  constexpr double neutronEkin2Speed(double ekin);
  constexpr double neutronSpeed2Ekin(double speed);
  constexpr double neutronAngleCosine2Q(double anglecosine, double enin_eV, double enout_eV);
  constexpr double wl2ekin( double wl);
  constexpr double ekin2wl( double ekin);
  constexpr double wlsq2ekin( double wlsq );
  constexpr double ekin2wlsq( double ekin);
  constexpr double ekin2wlsqinv( double ekin);

  class StableSum {
  public:
    //Numerically stable summation, based on Neumaier's
    //algorithm (doi:10.1002/zamm.19740540106).
    StableSum();
    ~StableSum();
    void add(double x);
    double sum() const;
    void clear() {m_sum=0; m_correction=0.;};
  private:
    double m_sum, m_correction;
  };
}

#ifdef __cplusplus
extern "C" {
#endif
#include <complex.h>
void autocorrelation(const double *in1, double *out, size_t start_x, size_t end_x,
                 size_t spacing_x, size_t y, size_t fftSize, size_t numcpu);

void parFFT(double _Complex *in1, double _Complex *out, size_t start_x, size_t end_x,
                 size_t spacing_x, size_t y, size_t fftSize, size_t numcpu);

void coherent_stablesum(double _Complex *in1, double *out, size_t x, size_t y, size_t numcpu);


#ifdef __cplusplus
}
#endif


#include "PTMath.icc"
#endif
