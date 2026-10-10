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

#include "PTLookUpTable.hh"
#include  <algorithm>
namespace PT = Prompt;

PT::LookUpTable::LookUpTable() = default;
PT::LookUpTable::~LookUpTable() = default;

PT::LookUpTable::LookUpTable(const std::vector<double>& x, const std::vector<double>& f, Extrapolate extrap)
:m_x(x), m_f(f)
{
  switch(extrap) {
    case kConst_Zero:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapConstLower, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapZero, this, std::placeholders::_1);
      break;
    case kZero_Zero:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapZero, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapZero, this, std::placeholders::_1);
      break;
    case kZero_Const:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapZero, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapConstUpper, this, std::placeholders::_1);
      break;
    case kOverX_Zero:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapOverXLower, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapZero, this, std::placeholders::_1);
      break;
    case kOverSqrtX_Zero:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapOverSqrtXLower, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapZero, this, std::placeholders::_1);
      break;
    case kOverSqrtX_OverSqrtX:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapOverSqrtXLower, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapOverSqrtXUpper, this, std::placeholders::_1);
      break;
    case kConst_OverSqrtX:
      m_func_extrapLower = std::bind( &PT::LookUpTable::extrapConstLower, this, std::placeholders::_1);
      m_func_extrapUpper = std::bind( &PT::LookUpTable::extrapOverSqrtXUpper, this, std::placeholders::_1);
      break;
    default :
      PROMPT_THROW(CalcError, "extrapolation functions are not defined");
  }

  sanityCheck();
}

void PT::LookUpTable::sanityCheck() const
{
  if(m_x.size()!=m_f.size())
    PROMPT_THROW(BadInput, "x and f have different size");

  if(m_x.empty())
    PROMPT_THROW(BadInput, "empty input array");

  if(!std::is_sorted(std::begin(m_x), std::end(m_x)))
    PROMPT_THROW(BadInput, "x is not sorted");
}

void PT::LookUpTable::print() const
{
  sanityCheck();
  printf("Look-up table content:\n");
  for(unsigned i=0;i<m_x.size();i++)
  {
    printf("%e %e\n", m_x[i], m_f[i]);
  }
}

bool PT::LookUpTable::empty() const
{
  return m_x.empty() && m_f.empty();
}

double PT::LookUpTable::integrate(double , double )
{
  PROMPT_THROW(CalcError, "PT::LookUpTable::integral to be implemented");
  return -1;
}
