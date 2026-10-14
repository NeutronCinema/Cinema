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
#include "PTException.hh"
#include "PTUtils.hh"

#include <dlfcn.h>
#include <cstdlib>
#include <mutex>
#include <set>

namespace pt = Prompt;

namespace {

bool isValidNamespace(const std::string& ns)
{
  // The namespace IS the cfg value of physics=<ns>, so the rule cannot be
  // tighter than CfgParser value shapes: the builtin namespaces are frozen
  // legacy cfg keys (idealElaScat is camelCase), and external plugins must
  // not be forced into a different dialect. Still rejects empty names,
  // leading digits and punctuation (shell/quote hazards).
  if(ns.empty() || !(ns[0]>='a' && ns[0]<='z') && !(ns[0]>='A' && ns[0]<='Z'))
    return false;
  for(char c : ns)
    if(!((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9') || c=='_'))
      return false;
  return true;
}

// One dlopened plugin: handle is deliberately leaked (NCrystal's production
// scar - closing it would leave dangling vtables inside constructed models).
struct LoadedPlugin {
  void *handle;
  std::string name;
  std::string path;
};

std::vector<LoadedPlugin> loadPluginFile(const std::string& path)
{
  dlerror();
  void *handle = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
  if(!handle)
  {
    const char *err = dlerror();
    PROMPT_THROW2(BadInput, "cinplugin: failed to load plugin file " << path << ": " << (err?err:"unknown dlerror"));
  }

  auto resolve = [&](const char *sym) -> void* {
    dlerror();
    void *p = dlsym(handle, sym);
    if(!p)
    {
      const char *err = dlerror();
      PROMPT_THROW2(BadInput, "cinplugin: plugin file " << path << " does not export " << sym
                    << (err?": ":"") << (err?err:""));
    }
    return p;
  };

  auto abifn = reinterpret_cast<std::uint32_t(*)()>(resolve("cinplugin_abi"));
  std::uint32_t abi = abifn();
  if(abi != PROMPT_PLUGIN_ABI)
  {
    PROMPT_THROW2(BadInput, "cinplugin: plugin file " << path << " reports ABI " << abi
                  << " but this cinema provides ABI " << PROMPT_PLUGIN_ABI
                  << " - rebuild the plugin against this cinema version");
  }

  auto namefn = reinterpret_cast<const char*(*)()>(resolve("cinplugin_getname"));
  std::string name(namefn());
  if(name.empty())
    PROMPT_THROW2(BadInput, "cinplugin: plugin file " << path << " returned an empty plugin name");

  auto regfn = reinterpret_cast<void(*)()>(resolve("cinplugin_register"));
  regfn();

  std::vector<LoadedPlugin> out;
  out.push_back(LoadedPlugin{handle, name, path});
  return out;
}

}

namespace Prompt::Plugin {

PluginRegistry& PluginRegistry::instance()
{
  // Function-local static: process-global by definition, thread-safe
  // initialisation since C++11. Deliberately not the thread_local Singleton:
  // the factory table must be one object per process.
  static PluginRegistry reg;
  return reg;
}

void PluginRegistry::setBuiltinBootstrap(BuiltinHook hook)
{
  m_builtinHook = hook;
}

void PluginRegistry::registerFactory(std::unique_ptr<ModelFactory> factory)
{
  if(!factory)
    PROMPT_THROW(BadInput, "cinplugin: refusing to register a null factory");

  const std::string ns = factory->ns();
  if(!isValidNamespace(ns))
    PROMPT_THROW2(BadInput, "cinplugin: factory namespace '" << ns
                  << "' is invalid (need [A-Za-z][A-Za-z0-9_]*)");

  std::lock_guard<std::recursive_mutex> lock(m_mutex);
  if(m_loaded)
    PROMPT_THROW2(BadInput, "cinplugin: registration of namespace '" << ns
                  << "' refused: plugin loading already completed");
  if(m_factories.count(ns))
    PROMPT_THROW2(BadInput, "cinplugin: duplicate factory namespace '" << ns << "'");

  m_factories[ns] = std::move(factory);
}

void PluginRegistry::loadFile(const std::string& path)
{
  std::lock_guard<std::recursive_mutex> lock(m_mutex);
  for(auto &lp : loadPluginFile(path))
  {
    if(!m_loadedNames.insert(lp.name).second)
      PROMPT_THROW2(BadInput, "cinplugin: duplicate plugin name '" << lp.name << "' (from " << lp.path << ")");
  }
}

void PluginRegistry::ensureLoaded()
{
  std::lock_guard<std::recursive_mutex> lock(m_mutex);
  if(m_loaded)
    return;

  // Builtins first: the concrete model code registers through this hook at
  // load time (see PTPluginBuiltins.cc in ModelBulk).
  if(m_builtinHook)
    m_builtinHook();

  // Then CINEMA_PLUGIN_LIST: colon-separated .so paths, authoritative and
  // exclusive when set (the Python-side scan never runs; mirrors
  // NCRYSTAL_PLUGIN_LIST replace semantics for reproducible HPC scripts).
  const char *env = std::getenv("CINEMA_PLUGIN_LIST");
  if(env && *env)
  {
    std::string item;
    std::string liststr(env);
    for(size_t i=0; i<=liststr.size(); ++i)
    {
      if(i==liststr.size() || liststr[i]==':')
      {
        if(!item.empty())
        {
          for(auto &lp : loadPluginFile(item))
          {
            if(!m_loadedNames.insert(lp.name).second)
              PROMPT_THROW2(BadInput, "cinplugin: duplicate plugin name '" << lp.name << "'");
          }
        }
        item.clear();
      }
      else
        item += liststr[i];
    }
  }

  m_loaded = true;
}

const ModelFactory* PluginRegistry::lookup(const std::string& ns)
{
  ensureLoaded();
  // Read-only after loading completed: no lock needed on the hot path.
  auto it = m_factories.find(ns);
  return it==m_factories.end() ? nullptr : it->second.get();
}

std::vector<std::pair<std::string, std::string>> PluginRegistry::list()
{
  ensureLoaded();
  std::vector<std::pair<std::string, std::string>> out;
  for(auto &pr : m_factories)
    out.emplace_back(pr.first, pr.second->description());
  return out;
}

}

// The exported free function plugins call from cinplugin_register().
namespace Prompt::Plugin {
void registerModelFactory(std::unique_ptr<ModelFactory> factory)
{
  PluginRegistry::instance().registerFactory(std::move(factory));
}
}
