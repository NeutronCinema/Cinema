#ifndef Prompt_H5PL_hh
#define Prompt_H5PL_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  You may not use this file except in compliance with the License.          //
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
#include "PTScorer1D.hh"

namespace Prompt {
  class HDF5BinaryWrite;

  class H5PL  : public Scorer1D {
  public:
    H5PL(const std::string &name, unsigned int pdg, int groupid, bool kill=false, bool compress=true);
    virtual ~H5PL();
    virtual void score(Particle &particle) override;
    
    // Additional methods for custom fields
    void addCustomField(const std::string& fieldName, const std::string& dataType);
    
  private:
    HDF5BinaryWrite *m_writer;
    bool m_kill;
  };
  
}

#endif