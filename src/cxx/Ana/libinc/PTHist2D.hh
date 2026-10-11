#ifndef Hist2D_hh
#define Hist2D_hh

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

#include "PTHistBase.hh"
#include <cmath>

namespace Prompt {

  class Hist2D : public HistBase {
  public:

    explicit Hist2D(const std::string &name, double xmin, double xmax, unsigned nxbins,
                 double ymin, double ymax, unsigned nybins);
    virtual ~Hist2D();

    //Independent copy: rebuilds the geometry through the normal constructor,
    //then takes over the scored state (the base forbids its own copy)
    Hist2D(const Hist2D& other)
    :Hist2D(other.m_name, other.m_xmin, other.m_xmax, other.m_xnbins,
            other.m_ymin, other.m_ymax, other.m_ynbins)
    {copyTrivialFrom(other);}

    void operator+=(const Hist2D& hist);
    unsigned dimension() const override { return 2; }  
    void save(const std::string &filename) const override;

    uint32_t getNBinX() const {return m_xnbins;}
    uint32_t getNBinY() const {return m_ynbins;}
    double getYMin() const {return m_ymin;}
    double getYMax() const {return m_ymax;}
    std::vector<double> getXEdge() const;
    std::vector<double> getYEdge() const;


    void fill(double xval, double yval);
    void fill(double xval, double yval, double weight);
    void fill_unguard(double xval, double yval, double weight);
    void fill_unguard(double xval, const std::vector<double>& yval, const std::vector<double>& weight);
    void fill_unguard(const std::vector<double>& xval, const std::vector<double>& yval, const std::vector<double>& weight);

    void merge(const HistBase &) override;

  private:
    //there is no function to modify private mambers, so they are not const
    double m_xbinfactor, m_ybinfactor;
    double m_ymin;
    double m_ymax;
    uint32_t m_xnbins, m_ynbins;
  };
  #include "PTHist2D.icc"
}



#endif
