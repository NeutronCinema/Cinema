#ifndef Prompt_PluginBoilerplate_hh
#define Prompt_PluginBoilerplate_hh

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

// Convenience header for cinema physics-model plugins, mirroring NCrystal's
// NCPluginBoilerplate.hh. Include it from plugin code (and nowhere else).
// Usage: compile the plugin with -DCINPLUGIN_NAME=<Name>, put ALL plugin code
// in `namespace CINPluginNamespace { ... }`, implement
// `CINPluginNamespace::registerPlugin()` calling
// Prompt::Plugin::registerModelFactory(...), and in exactly one .cc define
// CINPLUGIN_BOILERPLATE_CC before including this header. That generates the
// three required extern "C" symbols:
//   void      cinplugin_register();
//   const char* cinplugin_getname();
//   uint32_t  cinplugin_abi();
// The basic requirement is only the three C-mangled symbols - this header is
// a convenience, not a necessity.

#include <string>
#include "PTPluginFactory.hh"

#ifndef CINPLUGIN_NAME
#  error CINPLUGIN_NAME undefined
#endif

// Internal macros needed below:
#define cinpluginhh_str2(s) #s
#define cinpluginhh_str(s) cinpluginhh_str2(s)
#define cinpluginhh_nsgen0(m) CinemaPlugin_##m
#define cinpluginhh_nsgen(m) cinpluginhh_nsgen0(m)

// All plugin code should be in the CINPluginNamespace!
#define CINPLUGIN_NAME_CSTR cinpluginhh_str(CINPLUGIN_NAME)
#define CINPluginNamespace cinpluginhh_nsgen(CINPLUGIN_NAME)

namespace CINPluginNamespace {
  void registerPlugin();
  const std::string& pluginName();
}

// Exactly one .cc in a plugin defines CINPLUGIN_BOILERPLATE_CC before
// including this file, generating the C-mangled hooks for dynamic loading.
#if defined(CINPLUGIN_BOILERPLATE_CC)
extern "C" {

PROMPT_PLUGIN_EXPORT void cinplugin_register()
{
  CINPluginNamespace::registerPlugin();
}

PROMPT_PLUGIN_EXPORT const char* cinplugin_getname()
{
  return CINPLUGIN_NAME_CSTR;
}

PROMPT_PLUGIN_EXPORT std::uint32_t cinplugin_abi()
{
  return PROMPT_PLUGIN_ABI;
}

} // extern "C"

const std::string& CINPluginNamespace::pluginName()
{
  static std::string s_name(CINPLUGIN_NAME_CSTR);
  return s_name;
}
#endif//CINPLUGIN_BOILERPLATE_CC

#endif
