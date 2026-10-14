#ifndef Est1D_hh
#define Est1D_hh

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

#include "PTHist1D.hh"
#include <cmath>

namespace Prompt {
  class Est1D : public Hist1D {
  public:
    explicit Est1D(const std::string &name, double xmin, double xmax, unsigned nbins,bool linear=true);
    virtual ~Est1D();
    void fill(double val) override;
    void fill(double val, double weight) override;
    void fill(double val, double weight, double error);
    //Est1D keeps its sdev in m_hit (m_ww stays 0): merge combines that
    //channel in quadrature and scale rescales it by the absolute factor,
    //both instead of the base-class linear/variance treatment. See
    //HistBase::merge()/scale() for the two-channel documentation.
    void merge(const HistBase &hist) override;
    void scale(double scalefact) override;
  };
}

#endif
