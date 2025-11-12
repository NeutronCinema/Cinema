#ifndef Prompt_KillerMCPL_hh
#define Prompt_KillerMCPL_hh

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

#include "PromptCore.hh"
#include "PTScorer1D.hh"

namespace Prompt {
  class MCPLBinaryWrite;

  class KillerMCPL  : public Scorer1D {
  public:
    KillerMCPL(const std::string &name, unsigned int pdg, int groupid, bool kill=false, bool compress=true);
    virtual ~KillerMCPL();
    virtual void score(Particle &particle) override;
  private:
    MCPLBinaryWrite *m_writer;
    bool m_kill, m_compress;
  };
  
}

#endif