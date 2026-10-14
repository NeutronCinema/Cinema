#ifndef Prompt_IdealElaScatPlugin_hh
#define Prompt_IdealElaScatPlugin_hh

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

#include <limits>
#include <string>

#include "PTException.hh"
#include "PTPluginFactory.hh"
#include "PTPluginModel.hh"

// Plugin #1: the analytic idealElaScat model re-hosted on the plugin ABI,
// replacing PhysicsFactory::createIdealElaScat's duplicated parsing and the
// reinterpret_cast number-density extraction in cfgPhysicsModel. The model
// is deliberately trivial: constant microscopic cross section, isotropic
// elastic scatter that loses a fixed energy transfer above a threshold and
// passes through below it. Serves as the smallest template for external
// single-model factories.

namespace Prompt::Plugin {

class IdealElaScatModel final : public ScatterModel {
public:
  IdealElaScatModel(double xs_barn, double density_per_aa3, double ekin_transfer);

  PluginNumDensity numberDensity() const override { return m_numdensity; }
  // legacy IdealElaScat carried the DiscreteModel validity range
  // [DBL_MIN, DBL_MAX]; keep it exactly
  PluginEkin emin() const override { return std::numeric_limits<double>::min(); }
  PluginEkin emax() const override { return std::numeric_limits<double>::max(); }

  PluginXs crossSection(PluginEkin ekin, const double* dir) const override;

  void sample(PluginEkin ekin, const double* dir, Rng& rng,
              SampleResult& out, SecondarySink* sink) override;

private:
  PluginXs m_xs;                 // mm^2, unbiased (the host adapter applies bias)
  PluginNumDensity m_numdensity; // atoms/A^3 (ABI boundary unit)
  PluginEkin m_ekin_t;           // eV
};

class IdealElaScatFactory final : public ModelFactory {
public:
  const char* ns() const override { return "idealElaScat"; }
  const char* description() const override
  { return "builtin analytic elastic scatter with fixed energy transfer (plugin #1)"; }

  // Key set (legacy-exact defaults and validation order):
  //   xs_barn=1., density_per_aa3=0.05, energy_transfer_eV=0.,
  //   scatter_bias=1. (host-reserved, consumed by the host and applied by
  //   the adapter; the factory only enforces the legacy non-zero rule).
  std::unique_ptr<ScatterModel> produce(const CfgView& cfg) const override;

  void produceAll(const CfgView& cfg, const HostBias& bias,
                  const ModelEmit& emit) const override;
};

}

#endif
