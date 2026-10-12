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
#include "PTNCrystalPlugin.hh"
#include "PTIdealElaScatPlugin.hh"

// Bootstrap of the builtin physics models onto the plugin registry. Lives in
// ModelBulk so PluginAPI needs no dependency on the concrete model code
// (dependency direction: ModelBulk -> PluginAPI); the hook pointer is the
// only contact surface. Registration happens inside ensureLoaded(), i.e. on
// the first cfg dispatch, not at static-init time.

namespace {

void registerBuiltinFactories()
{
  // Plugin #0: NCrystal (the host's NC_RAW/NC_SCATTER non-gidi branches
  // dispatch through the registry; see PTNCrystalPlugin.hh).
  // Plugin #1: idealElaScat, the generic-registry-route template (any
  // physics=<ns> without a host branch resolves through the registry).
  using namespace Prompt::Plugin;
  registerModelFactory(std::make_unique<NCrystalFactory>());
  registerModelFactory(std::make_unique<IdealElaScatFactory>());
}

struct BuiltinRegistrar {
  BuiltinRegistrar()
  {
    Prompt::Plugin::PluginRegistry::instance().setBuiltinBootstrap(&registerBuiltinFactories);
  }
};

BuiltinRegistrar g_builtinRegistrar;

}
