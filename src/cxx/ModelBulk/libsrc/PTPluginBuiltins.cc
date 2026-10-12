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

#include "PTPluginRegistry.hh"

// Bootstrap of the builtin physics models onto the plugin registry. Lives in
// ModelBulk so PluginAPI needs no dependency on the concrete model code
// (dependency direction: ModelBulk -> PluginAPI); the hook pointer is the
// only contact surface. Registration happens inside ensureLoaded(), i.e. on
// the first cfg dispatch, not at static-init time.

namespace {

void registerBuiltinFactories()
{
  // Milestone M2/M3: the builtin ncrystal and idealElaScat factories
  // register here, turning them into plugin #0 and #1 behind the same
  // Prompt::Plugin::ModelFactory interface as any external model. Until
  // then the builtin stack is wired directly in cfgPhysicsModel and this
  // hook deliberately registers nothing.
}

struct BuiltinRegistrar {
  BuiltinRegistrar()
  {
    Prompt::Plugin::PluginRegistry::instance().setBuiltinBootstrap(&registerBuiltinFactories);
  }
};

BuiltinRegistrar g_builtinRegistrar;

}
