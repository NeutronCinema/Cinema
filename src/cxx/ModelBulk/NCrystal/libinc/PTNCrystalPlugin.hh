#ifndef Prompt_NCrystalPlugin_hh
#define Prompt_NCrystalPlugin_hh

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
#include "NCrystal/NCrystal.hh"

// Plugin #0: the builtin NCrystal physics re-hosted on the plugin ABI. The
// host's NC_RAW/NC_SCATTER non-gidi branches route through the registry to
// NCrystalFactory below, which emits the same two channels in the same order
// the legacy NCrystalAbs/NCrystalScat constructors did - the transport
// pathway (xs cache, channel picking, disappearing election) is unchanged,
// only the model objects themselves are plugin-shaped now. The legacy
// classes stay for the gidi branches, which the registry route does not
// serve (the PendingGidi machinery is host-side ModelCollection state).

namespace Prompt::Plugin {

// The elastic/inelastic scatter channel. Oriented when the material is; the
// adapter handles the local-frame transform and applies the bias.
class NCrystalScatModel final : public ScatterModel {
public:
  // maxekin caps the model validity (the gidi switching threshold; unlimited
  // for the registry route, which serves the non-gidi paths only).
  explicit NCrystalScatModel(const std::string& nccfg,
                             double maxekin = std::numeric_limits<double>::max());

  PluginNumDensity numberDensity() const override { return m_numdensity; }
  PluginEkin emax() const override { return m_maxekin; }
  bool oriented() const override { return m_scat.isOriented(); }

  PluginXs crossSection(PluginEkin ekin, const double* dir) const override;

  void sample(PluginEkin ekin, const double* dir, Rng& rng,
              SampleResult& out, SecondarySink* sink) override;

private:
  // mutable: NCrystal's Process methods are non-const (they update an
  // internal cache) while crossSection is const in the plugin ABI - the
  // legacy NCrystalScat carries the same scar.
  mutable NCrystal::Scatter m_scat;
  PluginEkin m_maxekin;
  PluginNumDensity m_numdensity;
};

// The absorption channel: every collision terminates the primary and
// deposits its full kinetic energy.
class NCrystalAbsModel final : public ScatterModel {
public:
  explicit NCrystalAbsModel(const std::string& nccfg);

  PluginNumDensity numberDensity() const override { return m_numdensity; }
  // legacy NCrystalAbs carried the DiscreteModel default (unbounded above)
  PluginEkin emax() const override { return std::numeric_limits<double>::max(); }
  bool declaresAbsorption() const override { return true; }

  PluginXs crossSection(PluginEkin ekin, const double* dir) const override;
  PluginXs absorptionCrossSection(PluginEkin ekin, const double* dir) const override;

  void sample(PluginEkin ekin, const double* dir, Rng& rng,
              SampleResult& out, SecondarySink* sink) override;

private:
  mutable NCrystal::Absorption m_abs;  // non-const NCrystal API, see above
  PluginNumDensity m_numdensity;
};

// Serves BOTH ncrystal dispatch shapes. The mode follows the host's own
// discriminator (PhysicsFactory::checkPhysicsType): a cfg string CfgParser
// cannot parse is NC_RAW and arrives here with an empty namespace (raw()
// carries the NCrystal cfg); physics=ncrystal is NC_SCATTER and arrives with
// ns=="ncrystal" and nccfg= set. Emission order per mode matches the legacy
// constructors exactly (RAW: Abs then Scat; SCATTER: Scat then Abs, a
// channel with non-positive bias skipped before construction).
class NCrystalFactory final : public ModelFactory {
public:
  const char* ns() const override { return "ncrystal"; }
  const char* description() const override
  { return "builtin NCrystal scattering+absorption (plugin #0)"; }

  std::unique_ptr<ScatterModel> produce(const CfgView&) const override
  {
    PROMPT_THROW(BadInput, "physics=ncrystal: this factory only produces model sets; use produceAll");
  }

  void produceAll(const CfgView& cfg, const HostBias& bias,
                  const ModelEmit& emit) const override;
};

}

#endif
