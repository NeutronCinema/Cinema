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

#include "PTEst1D.hh"
#include "PTMath.hh"

Prompt::Est1D::Est1D(const std::string &name, double xmin, double xmax, unsigned nbins, bool linear)
:Hist1D(name, xmin, xmax, nbins, linear)
{
}

Prompt::Est1D::~Est1D()
{
}

//Normal filling:
void Prompt::Est1D::fill(double val)
{
  PROMPT_THROW2(BadInput, "Prompt::Est1D::fill(double val) is not implemented");
}

void Prompt::Est1D::fill(double val, double w)
{
  PROMPT_THROW2(BadInput, "Prompt::Est1D::fill(double val, double w) is not implemented");
}


void Prompt::Est1D::fill(double val, double w, double error)
{
  std::lock_guard<std::mutex> guard(m_hist_mutex);

  m_sumW+=w;
  if(val<m_xmin) {
    m_underflow += w;
    return;
  }
  else if(val>m_xmax) {
    m_overflow += w;
    return;
  }

  unsigned i = m_linear ? floor((val-m_xmin)*m_binfactor) : floor((log10(val)-m_logxmin)*m_binfactor) ;
  //val==xmax computes the one-past-the-last bin index (floor(nbins)); clamp it
  //into the last bin, as the [xmin, xmax] range is right-closed here
  if(i>=m_nbins)
    i=m_nbins-1;
  m_data[i] += w;
  m_hit[i] =  std::sqrt(error*error+m_hit[i]*m_hit[i]); //fixme: should convert error back to hit
}
