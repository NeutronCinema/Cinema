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

// Hand-written plugin symbols reporting a WRONG ABI version: the loader must
// refuse it with a diagnostic instead of registering anything (this converts
// "mysterious crash after a cinema upgrade" into "rebuild your plugin").
// Deliberately does NOT use PTPluginBoilerplate.hh, which always reports the
// current ABI.

#include <cstdint>
#include "PTPluginTypes.hh"

extern "C" {

__attribute__((visibility("default"))) void cinplugin_register()
{
}

__attribute__((visibility("default"))) const char* cinplugin_getname()
{
  return "TestBadAbi";
}

__attribute__((visibility("default"))) std::uint32_t cinplugin_abi()
{
  // one ahead of whatever this cinema provides
  return PROMPT_PLUGIN_ABI + 1;
}

}
