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
#include <stdexcept>
#include <fstream>
#include <cstring>
#include "PTRandCanonical.hh"


Prompt::HistBase::HistBase(const std::string &name, unsigned nbin)
:m_name(name), m_data(nbin,0.), m_note(), m_hit(nbin,0.),  m_ww(nbin,0.), m_xmin(0), m_xmax(0),
 m_sumW(0), m_underflow(0), m_overflow(0),m_nbins(0)
{
  auto seed = Singleton<SingletonPTRand>::getInstance().getSeed();
  m_mcpl_file_name = m_name+"_seed"+std::to_string(seed);
}

Prompt::HistBase::~HistBase()
{
}


void Prompt::HistBase::merge(const Prompt::HistBase &hist)
{
  if(m_xmin!=hist.m_xmin)
    PROMPT_THROW2(CalcError, "m_xmin " << m_xmin << " is different with the m_xmin of another histogram " << hist.m_xmin);

  if(m_xmax!=hist.m_xmax)
    PROMPT_THROW2(CalcError, "m_xmax " << m_xmax << " is different with the m_xmax of another histogram " << hist.m_xmax);

  if(m_nbins!=hist.m_nbins)
      PROMPT_THROW2(CalcError, "m_nbins " << m_nbins << " is different with the m_nbins of another histogram " << hist.m_nbins);


  for(size_t i=0;i<m_data.size();i++)
  {
    m_data[i] += hist.m_data[i];
    m_hit[i] += hist.m_hit[i];
    m_ww[i] = sqrt(m_ww[i]*m_ww[i] + hist.m_ww[i]*hist.m_ww[i]);
  }

  m_underflow += hist.m_underflow;
  m_overflow += hist.m_overflow;
  m_sumW += hist.m_sumW;

}



void Prompt::HistBase::setWeight(double *data, size_t n)
{
  if(n != m_data.size())
    PROMPT_THROW(CalcError, "wrong vector size");
  memcpy(m_data.data(), data, sizeof(double)*n);
}

void Prompt::HistBase::setHit(double *data, size_t n)
{
  if(n != m_hit.size())
    PROMPT_THROW(CalcError, "wrong vector size");
  memcpy(m_hit.data(), data, sizeof(double)*n);
}


void Prompt::HistBase::setWW(double *data, size_t n)
{
  if(n != m_ww.size())
    PROMPT_THROW(CalcError, "wrong vector size");
  memcpy(m_ww.data(), data, sizeof(double)*n);
}


void Prompt::HistBase::scale(double scalefact)
{

  for(unsigned i=0;i<m_nbins;i++)
    m_data[i] *= scalefact;

  m_sumW *= scalefact;
  m_underflow *= scalefact;
  m_overflow *= scalefact;

}

void Prompt::HistBase::reset()
{
  std::fill(m_data.begin(), m_data.begin()+m_nbins, 0.);
  std::fill(m_hit.begin(), m_hit.begin()+m_nbins, 0.);
  std::fill(m_ww.begin(), m_ww.begin()+m_nbins, 0.);

  m_sumW = 0.;
  m_underflow = 0.;
  m_overflow = 0.;
}
