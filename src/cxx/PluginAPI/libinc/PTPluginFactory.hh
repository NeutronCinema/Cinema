#ifndef Prompt_PluginFactory_hh
#define Prompt_PluginFactory_hh

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

#include <memory>
#include "PTPluginModel.hh"

#if defined(__GNUC__) || defined(__clang__)
#  define PROMPT_PLUGIN_EXPORT __attribute__ ((visibility ("default")))
#else
#  define PROMPT_PLUGIN_EXPORT
#endif

// Factory side of the plugin ABI. A factory owns one cfg namespace: the value
// of the host dispatcher key physics=<ns>. Namespaces are lowercase
// [a-z][a-z0-9_]*, distinct from surface-model names (Mirror, DiskChopper,
// ...) which live on their own configuration path.
namespace Prompt::Plugin {

class ModelFactory {
public:
  virtual ~ModelFactory() = default;

  // The cfg namespace this factory serves (value of physics=<ns>).
  virtual const char* ns() const = 0;

  virtual const char* description() const { return ""; }

  // Build a model from the cfg view. Must be deterministic from the string
  // alone (materials are deduplicated by cfg string) and thread-safe.
  // Unknown or invalid keys must throw Prompt::Error::BadInput naming the
  // key - there is no parCount boilerplate any more.
  virtual std::unique_ptr<ScatterModel> produce(const CfgView&) const = 0;
};

// Exported from prompt_core with default visibility; called by
// cinplugin_register() of a plugin and by the builtin bootstrap. Throws
// Prompt::Error::BadInput on a duplicate namespace or a registration after
// loading completed.
PROMPT_PLUGIN_EXPORT void registerModelFactory(std::unique_ptr<ModelFactory>);

}

#endif
