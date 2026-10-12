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

// A minimal but complete physics-model plugin, built as a MODULE library by
// the test harness and dlopen()ed by test_pluginregistry. Serves as the
// in-tree template of the extern "C" boilerplate + factory + model shape.
// Physics: constant cross section, elastic isotropic scatter, no absorption.

#define CINPLUGIN_BOILERPLATE_CC
#include "PTPluginBoilerplate.hh"
#include "PTException.hh"

#include <cmath>

namespace CINPluginNamespace {

using namespace Prompt::Plugin;

class HelloModel final : public ScatterModel {
public:
  explicit HelloModel(double xs) : m_xs(xs) {}

  PluginNumDensity numberDensity() const override { return 0.01; } // atoms/A^3
  PluginEkin emax() const override { return 1e8; }

  PluginXs crossSection(PluginEkin ekin, const double* dir) const override
  {
    (void)ekin; (void)dir;
    return m_xs; // mm^2
  }

  void sample(PluginEkin ekin, const double* dir, Rng& rng,
              SampleResult& out, SecondarySink* sink) override
  {
    (void)dir; (void)sink;
    // isotropic elastic scatter at unchanged energy
    double cosT = 2.0*rng.next() - 1.0;
    double sinT = std::sqrt(1.0 - cosT*cosT);
    double phi = 2.0*M_PI*rng.next();
    out.final_ekin = ekin;
    out.deposition = 0.0;
    out.final_dir[0] = sinT*std::cos(phi);
    out.final_dir[1] = sinT*std::sin(phi);
    out.final_dir[2] = cosT;
    out.absorbed = false;
  }

private:
  double m_xs;
};

class HelloFactory final : public ModelFactory {
public:
  const char* ns() const override { return "hello"; }
  const char* description() const override { return "unittest: constant-xs isotropic model"; }

  std::unique_ptr<ScatterModel> produce(const CfgView& cfg) const override
  {
    // known-key validation with the key named in the error: the contract
    // that replaces the old parCount boilerplate
    double xs = 3.0;
    for(const auto &key : cfg.keys())
    {
      if(key == "xs")
        xs = cfg.number("xs");
      else
        PROMPT_THROW2(BadInput, "physics=" << cfg.ns() << ": unknown key '" << key << "'");
    }
    return std::make_unique<HelloModel>(xs);
  }
};

void registerPlugin()
{
  registerModelFactory(std::make_unique<HelloFactory>());
}

}
