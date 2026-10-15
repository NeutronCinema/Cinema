#ifndef Prompt_MCPLParticleReader_hh
#define Prompt_MCPLParticleReader_hh

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

#include "PTMCPLBinary.hh"

namespace Prompt {

  class MCPLParticleReader : public MCPLBinary {
    public:
      MCPLParticleReader(const std::string &fn, bool repeat = true) ;
      virtual ~MCPLParticleReader() = default; 

      uint64_t particleCount() const;
      bool readOneParticle() const;

      double getEnergy() const;
      double getWeight() const;
      double getTime() const;
      void getDirection( Vector& dir) const;
      void getPosition( Vector& pos) const;
      int32_t getPDG() const;

      // void getPolorisation( Vector& dir) const; // not yet be used 
    
    private:
      uint64_t m_parNum;
      bool m_repeat;



  };
}
#endif
