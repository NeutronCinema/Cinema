#ifndef Prompt_PluginRegistry_hh
#define Prompt_PluginRegistry_hh

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

#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <vector>
#include "PTPluginFactory.hh"

// Process-global registry of physics-model factories, keyed by cfg
// namespace. Deliberately NOT the thread_local Singleton<> of the transport
// universes: a plugin registers once per process (its dlopen is global) and
// every thread then looks up the same immutable factory table, while the
// MODELS a factory produces stay per-thread.
//
// Loading is one-shot and lazy: the first lookup triggers the builtin
// bootstrap hook plus the dlopen of every path in the CINEMA_PLUGIN_LIST
// environment variable (colon-separated .so paths, authoritative and
// exclusive when set). Mirrors NCrystal's NCPluginMgmt policy: RTLD_LOCAL |
// RTLD_NOW, all symbols resolved eagerly, and the handle is deliberately
// never closed (a dlclose would leave dangling vtables in constructed
// models).

namespace Prompt::Plugin {

class PluginRegistry {
public:
  static PluginRegistry& instance();

  // Register one factory; throws BadInput on a duplicate namespace or after
  // loading completed. Called by plugins and by the builtin bootstrap.
  void registerFactory(std::unique_ptr<ModelFactory> factory);

  // The factory serving a namespace, or nullptr. Triggers ensureLoaded().
  const ModelFactory* lookup(const std::string& ns);

  // All registered namespaces with their descriptions; triggers ensureLoaded().
  std::vector<std::pair<std::string, std::string>> list();

  // One-shot: run the builtin bootstrap hook, then dlopen CINEMA_PLUGIN_LIST.
  // Idempotent; further registerFactory() calls are rejected afterwards.
  void ensureLoaded();

  // Manually dlopen ONE plugin file and register its factories (checked
  // bridge path for tests and the python-side discovery; the env-var path
  // of ensureLoaded stays the exclusive HPC route). Throws BadInput on any
  // load or duplicate-name problem. Does not by itself complete loading.
  void loadFile(const std::string& path);

  // Set by ModelBulk at static-init time so PluginAPI needs no dependency on
  // the concrete model code (dependency direction: ModelBulk -> PluginAPI).
  using BuiltinHook = void(*)();
  void setBuiltinBootstrap(BuiltinHook hook);

  PluginRegistry(const PluginRegistry&) = delete;
  PluginRegistry& operator=(const PluginRegistry&) = delete;

private:
  PluginRegistry() = default;

  // recursive: registerModelFactory re-enters from cinplugin_register()
  // while loadFile()/ensureLoaded() hold the lock during their dlopen.
  std::recursive_mutex m_mutex;
  std::map<std::string, std::unique_ptr<ModelFactory>> m_factories;
  std::set<std::string> m_loadedNames;
  BuiltinHook m_builtinHook = nullptr;
  bool m_loaded = false;
};

}

#endif
