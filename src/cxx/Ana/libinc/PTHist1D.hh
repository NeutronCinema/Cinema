#ifndef Hist1D_hh
#define Hist1D_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
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

#include "PTHistBase.hh"
#include <cmath>

namespace Prompt {
  class Hist1D : public HistBase {
  public:
    explicit Hist1D(const std::string &name, double xmin, double xmax, unsigned nbins,bool linear=true);
    virtual ~Hist1D();

    unsigned dimension() const override { return 1; }  
    std::vector<double> getEdges() const;
    void save(const std::string &filename) const override;

    virtual void fill(double val);
    virtual void fill(double val, double weight);

  protected:
    double m_binfactor;
    double m_logxmin;
    bool m_linear;
  };
}

#endif
