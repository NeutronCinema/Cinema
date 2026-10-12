#ifndef Prompt_PluginModelAdapter_hh
#define Prompt_PluginModelAdapter_hh

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

#include <atomic>
#include <memory>
#include "PTDiscreteModel.hh"
#include "PTLauncher.hh"
#include "PTPluginModel.hh"
#include "PTStackManager.hh"

namespace Prompt {

// Bridges a Prompt::Plugin::ScatterModel (the plugin ABI of PluginAPI) onto
// the in-core DiscreteModel machinery, so ModelCollection keeps its xs cache,
// bias handling, channel picking and disappearing-model election unchanged.
// The adapter owns the plugin model; ModelCollection's shared_ptr owns the
// adapter. Host-reserved cfg keys (scatter_bias etc.) are applied by the
// host exactly like for the builtin models, never by the plugin.
class PluginModelAdapter final : public DiscreteModel {
public:
  PluginModelAdapter(std::unique_ptr<Plugin::ScatterModel> plugin,
                     const std::string &ns, double bias=1.0);
  ~PluginModelAdapter() override;

  double getCrossSection(double ekin) const override;
  double getCrossSection(double ekin, const Vector &dir) const override;
  const SampledResult& sampleReaction(double ekin, const Vector &dir) const override;

private:
  // Binds the shared transport RNG stream to the plugin's Rng interface.
  // The stream reference is bound in the adapter ctor (a nested class has
  // no access to the enclosing PhysicsBase members).
  struct RngView final : public Plugin::Rng {
    SingletonPTRand *rng = nullptr;
    double next() override { return rng->generate(); }
  };

  // Receives plugin secondaries and routes them onto the transport stack,
  // replicating the PDG routing of GIDIModel::sampleReaction in core. The
  // secondary takes the current particle's position: a plugin cannot know
  // it, so SecondarySpec::pos is advisory and ignored here.
  struct SinkView final : public Plugin::SecondarySink {
    void add(const Plugin::SecondarySpec& spec) override;
  };

  // mutable: sampleReaction is const while the ABI calls (Rng::next,
  // SecondarySink::add) are non-const.
  mutable RngView m_rngView;
  mutable SinkView m_sinkView;

  std::unique_ptr<Plugin::ScatterModel> m_plugin;
  std::string m_ns;
};

}

#endif
