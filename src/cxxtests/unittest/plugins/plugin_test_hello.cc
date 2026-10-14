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

// An absorption-channel model: every collision terminates the particle.
class PairAbsModel final : public ScatterModel {
public:
  explicit PairAbsModel(double xs) : m_xs(xs) {}

  PluginNumDensity numberDensity() const override { return 0.02; } // atoms/A^3
  bool declaresAbsorption() const override { return true; }

  PluginXs crossSection(PluginEkin ekin, const double* dir) const override
  {
    (void)ekin; (void)dir;
    return m_xs; // mm^2
  }

  PluginXs absorptionCrossSection(PluginEkin ekin, const double* dir) const override
  {
    (void)ekin; (void)dir;
    return m_xs;
  }

  void sample(PluginEkin ekin, const double* dir, Rng& rng,
              SampleResult& out, SecondarySink* sink) override
  {
    (void)dir; (void)rng; (void)sink;
    out.final_ekin = 0.0;
    out.deposition = ekin;
    out.absorbed = true;
  }

private:
  double m_xs;
};

// A two-model factory: the shape the ncrystal plugin needs (an absorption
// channel plus a scatter channel, emitted in registration order so the host
// adapters keep the builtin channel-pick math).
class PairFactory final : public ModelFactory {
public:
  const char* ns() const override { return "hellopair"; }
  const char* description() const override { return "unittest: absorbing + scattering model pair"; }

  std::unique_ptr<ScatterModel> produce(const CfgView&) const override
  {
    // This namespace only makes sense as a model SET.
    PROMPT_THROW(BadInput, "physics=hellopair: this factory only produces model sets; use produceAll");
  }

  void produceAll(const CfgView& cfg, const HostBias& bias, const ModelEmit& emit) const override
  {
    double xs_a = 1.0, xs_s = 2.0;
    for(const auto &key : cfg.keys())
    {
      if(key == "xs_a")
        xs_a = cfg.number("xs_a");
      else if(key == "xs_s")
        xs_s = cfg.number("xs_s");
      else
        PROMPT_THROW2(BadInput, "physics=" << cfg.ns() << ": unknown key '" << key << "'");
    }
    // same channel-enablement semantics as the ncrystal SCATTER path: a
    // non-positive role bias skips the emission before construction
    if(bias.scatter > 0.)
      emit(std::make_unique<HelloModel>(xs_s), ModelRole::Scatter);
    if(bias.abs > 0.)
      emit(std::make_unique<PairAbsModel>(xs_a), ModelRole::Absorption);
  }
};

void registerPlugin()
{
  registerModelFactory(std::make_unique<HelloFactory>());
  registerModelFactory(std::make_unique<PairFactory>());
}

}
