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

#include <vector>
#include "PTMath.hh"
#include "PTException.hh"
#include <cstring> //memcpy

std::vector<double> Prompt::logspace(double start, double stop, unsigned num)
{
  pt_assert(num>1);
  pt_assert(stop>start);
  std::vector<double> vec(num) ;
  double interval = (stop-start)/(num-1);
  for(std::vector<double>::iterator it=vec.begin();it!=vec.end();++it)  {
    *it = std::pow(10.0,start);
    start += interval;
  }
  vec.back() = std::pow(10.0,stop);
  return vec;
}

std::vector<double>  Prompt::linspace(double start, double stop, unsigned num)
{
  pt_assert(num>1);
  pt_assert(stop>start);
  std::vector<double> v;
  v.reserve(num) ;
  const double interval = (stop-start)/(num-1);
  //Like this for highest numerical precision:
  for (unsigned i = 0; i<num;++i)
    v.push_back(start+i*interval);
  v.back() = stop;
  return v;
}

#include "omp.h"
#include <complex>
#include "fftw3.h"
#include <chrono>

void autocorrelation(const double *in1, double *out, size_t start_x, size_t end_x,
                 size_t spacing_x, size_t y, size_t fftSize, size_t numcpu)
{
  std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();

  omp_set_num_threads(numcpu);
  double add(0.), mul(0.), fma(0.);
  std::fill(out, out+ fftSize, 0.); //padding with zero


  #pragma omp parallel default(none) shared(in1) firstprivate(y, fftSize, start_x, end_x, spacing_x) reduction (+ : out[:fftSize], add, mul, fma)
  {
    fftw_plan fftPlan_r2c;
    fftw_complex *fftwComplexBuffer = (fftw_complex*)fftw_malloc(sizeof(fftw_complex)*fftSize);
    double *realBuffer  = (double *)fftw_malloc(sizeof(double)*fftSize);

    // create FFTW plan
    #pragma omp critical
    {
      fftPlan_r2c = fftw_plan_dft_r2c_1d(fftSize, realBuffer, fftwComplexBuffer, FFTW_ESTIMATE |  FFTW_PATIENT);
      // if(!Q.empty())
      //   fftPlan_c2c = fftw_plan_dft_1d(fftSize, sqwfftwComplexBuffer, fftwComplexBuffer_out, FFTW_FORWARD, FFTW_ESTIMATE  |  FFTW_PATIENT);
    }

    double tadd(0.), tmul(0.), tfma(0.);
    #pragma omp for simd
    for(size_t ix=start_x ; ix < end_x ; ix+=spacing_x)
    {
      std::fill(realBuffer, realBuffer+ fftSize, 0.); //padding with zero
      for(size_t i=0;i<y;i++)
      {
        realBuffer[i] = in1[i+y*ix];
      }
      fftw_execute(fftPlan_r2c);
      fftw_flops(fftPlan_r2c, &tadd, &tmul, &tfma);
      add += tadd;
      mul += tmul;
      fma += tfma;

      for(size_t j=0;j<fftSize;j++)
      {
        out[j]+=fftwComplexBuffer[j][0]*fftwComplexBuffer[j][0]+fftwComplexBuffer[j][1]*fftwComplexBuffer[j][1] ;
      }
    }

    #pragma omp critical
    {
      fftw_cleanup();
      fftw_destroy_plan(fftPlan_r2c);
    }

    // clean up
    fftw_free(realBuffer);
    fftw_free(fftwComplexBuffer);
  }

  std::chrono::steady_clock::time_point end = std::chrono::steady_clock::now();
  std::cout << "autocorrelation: Number of FFT math operations: additions " << add
        << ", multiplications "<< mul
        << ", multiply-add operations " << fma << std::endl;

  std::cout << "Elapsed time "
        << std::chrono::duration_cast<std::chrono::milliseconds>(end - begin).count()
        << "[ms]" << std::endl << std::endl;

}


void parFFT(double _Complex *in1, double _Complex *out, size_t start_x, size_t end_x,
                 size_t spacing_x, size_t y, size_t fftSize, size_t numcpu)
{
  std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();

  omp_set_num_threads(numcpu);
  double add(0.), mul(0.), fma(0.);
  size_t x = 1 + ((end_x-1)-start_x)/spacing_x;
  std::fill(out, out+ fftSize*x, 0.);

  #pragma omp parallel default(none) shared(in1, out) firstprivate(y, fftSize, x, start_x, end_x, spacing_x) reduction (+ : add, mul, fma)
  {
    fftw_plan fftPlan_c2c;
    fftw_complex *fftwComplexBuffer = (fftw_complex*)fftw_malloc(sizeof(fftw_complex)*fftSize);
    fftw_complex *fftwComplexBuffer_out = (fftw_complex*)fftw_malloc(sizeof(fftw_complex)*fftSize);
    auto buffAsComplexVec = reinterpret_cast<std::complex<double>* > (fftwComplexBuffer);

    // create FFTW plan
    #pragma omp critical
    {
      fftPlan_c2c = fftw_plan_dft_1d(fftSize, fftwComplexBuffer, fftwComplexBuffer_out, FFTW_FORWARD, FFTW_ESTIMATE  |  FFTW_PATIENT);
    }

    double tadd(0.), tmul(0.), tfma(0.);
    #pragma omp for simd
    for(size_t ix=start_x; ix < end_x ; ix+=spacing_x)
    {
      if(fftSize>y) //where padding of zero is needed
        std::fill(buffAsComplexVec, buffAsComplexVec+ fftSize, std::complex<double>(0.)); //padding with zero
      memcpy(fftwComplexBuffer, in1+y*ix, y*sizeof(double _Complex));
      fftw_execute(fftPlan_c2c);
      fftw_flops(fftPlan_c2c, &tadd, &tmul, &tfma);
      add += tadd;
      mul += tmul;
      fma += tfma;

      size_t idx =  ((end_x-1)-ix)/spacing_x;
      memcpy(out+y*(x-1-idx), fftwComplexBuffer_out, fftSize*sizeof(double _Complex));
    }

    #pragma omp critical
    {
      fftw_cleanup();
      fftw_destroy_plan(fftPlan_c2c);
    }

    // clean up
    fftw_free(fftwComplexBuffer_out);
    fftw_free(fftwComplexBuffer);
  }

  std::chrono::steady_clock::time_point end = std::chrono::steady_clock::now();
  std::cout << "parFFT: Number of FFT math operations: additions " << add
        << ", multiplications "<< mul
        << ", multiply-add operations " << fma << std::endl;

  std::cout << "Elapsed time "
        << std::chrono::duration_cast<std::chrono::milliseconds>(end - begin).count()
        << "[ms]" << std::endl << std::endl;

}

// out: size y
// in: size x, y
void coherent_stablesum(double _Complex *in1, double *out, size_t x, size_t y, size_t numcpu)
{
  std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
  omp_set_num_threads(numcpu);
  Prompt::StableSum rsum, isum;
  std::fill(out, out+y, 0.);
  // #pragma omp for shared(in1, out) firstprivate(x, y)
  for(size_t j=0;j<y;j++)
  {
    rsum.clear();
    isum.clear();
    for(size_t i=0;i<x;i++)
    {
      rsum.add(creal(in1[j+i*y]));
      isum.add(cimag(in1[j+i*y]));
    }
    double totr = rsum.sum();
    double toti = isum.sum();
    out[j] = totr*totr + toti*toti;
  }
  std::chrono::steady_clock::time_point end = std::chrono::steady_clock::now();
  std::cout << "coherent_stablesum Elapsed time "
        << std::chrono::duration_cast<std::chrono::milliseconds>(end - begin).count()
        << "[ms]" << std::endl << std::endl;
}
