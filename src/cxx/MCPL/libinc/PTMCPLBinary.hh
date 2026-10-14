#ifndef Prompt_MCPLBinary_hh
#define Prompt_MCPLBinary_hh

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

#include <string>

#include "PromptCore.hh"
#include "mcpl.h"

namespace Prompt {

  class MCPLBinary {
    public:
      MCPLBinary(const std::string &fn) 
          : m_filename(fn), m_file()
          {
            m_file.internal = 0;
            m_file_r.internal = 0;
          };

      virtual ~MCPLBinary() = default; 
      const std::string& getFileName() { return m_filename; }
      mcpl_particle_t *getParticle() { return m_particleInFile;}

    protected:
      std::string m_filename;
      mcpl_outfile_t m_file;
      mutable mcpl_particle_t *m_particleInFile;

      mcpl_file_t m_file_r;

      bool m_using_double, m_with_extra3double, m_with_extraUserUnsigned;

  };
}
#endif
