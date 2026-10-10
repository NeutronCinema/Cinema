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

#include "../doctest.h"

#include "PTGeoTree.hh"
#include "PTMCPLBinaryWrite.hh"
#include "PTNeutron.hh"
#include "PTUtils.hh"

#include<iostream>
using namespace std;

TEST_CASE("test_mcpl")
{

  auto bwr = Prompt::MCPLBinaryWrite("test_mcpl");

  std::vector<double> dvec {1,2,3,4,5,6,7,8,9.};
  std::vector<float> fvec {1,2,3,4,5,6,7,8,9.};
  std::vector<unsigned> uvec {1,2,3,4,5,6,7,8,9};

  bwr.addHeaderData("npdouble", dvec.data(), {3,3}, Prompt::NumpyWriter::NPDataType::f8);
  bwr.addHeaderData("npfloat", fvec.data(), {3,3}, Prompt::NumpyWriter::NPDataType::f4);
  bwr.addHeaderData("npunsigned", uvec.data(), {3,3}, Prompt::NumpyWriter::NPDataType::i4);

  bwr.closeHeader();
  bwr.write(Prompt::Neutron(0.0253, {0,0,1}, {0,0,0.}));

}
