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

#include "PTPython.hh"
#include "PTMCPLBinaryWrite.hh"

void* pt_MCPLBinaryWrite_new(const char *fn, bool enable_double, bool enable_extra3double, 
                bool enable_extraUnsigned)
{
  return static_cast<void *>(new Prompt::MCPLBinaryWrite(fn, enable_double, enable_extra3double, enable_extraUnsigned ));
}

void pt_MCPLBinaryWrite_delete(void* obj)
{
  delete static_cast<Prompt::MCPLBinaryWrite *>(obj);
}

// mcpl_particle_t is a 104-byte MEMORY-class argument in the SysV ABI: it
// must cross the ctypes boundary as a pointer (the python side passes
// POINTER(MCPLParticle)), never by value.
void pt_MCPLBinaryWrite_write(void* obj, const mcpl_particle_t* par)
{
  static_cast<Prompt::MCPLBinaryWrite *>(obj)->write(*par);
}

void pt_MCPLBinaryWrite_close(void* obj)
{
  static_cast<Prompt::MCPLBinaryWrite *>(obj)->close();
}

