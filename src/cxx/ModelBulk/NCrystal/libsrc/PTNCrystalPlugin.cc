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
////////////////////////////////////////////////////////////////////////////////

#include "PTNCrystalPlugin.hh"
#include "PTUnitSystem.hh"

// The cross-section and sampling expressions replicate the legacy
// NCrystalScat/NCrystalAbs (PTNCrystalScat.cc / PTNCrystalAbs.cc) minus the
// bias factor, which the host adapter applies. Multiplication-order note:
// the adapter computes (xs * barn) * bias; the legacy ABS model multiplied
// barn first (bit-exact after cutover even with bias), the legacy SCAT
// model multiplied bias first (<= 1 ulp difference when bias != 1; the
// default-bias gold suite is bit-exact).

namespace Prompt::Plugin {

namespace {

// Same NCrystal call as PhysicsFactory::nccalNumDensity, but WITHOUT the
// /Unit::Aa3 conversion: the plugin ABI's number density is atoms/A^3 at
// the boundary (the host converts). The value exists so the host can
// cross-check the plugin contract against the legacy path.
PluginNumDensity ncrystalNumberDensity(const std::string& nccfg)
{
  NCrystal::MatCfg matcfg(nccfg);
  auto info = NCrystal::createInfo(matcfg);
  if(info->hasNumberDensity())
    return info->getNumberDensity().get();
  PROMPT_THROW2(CalcError, "material has no number density " << nccfg);
}

void assertEVUnits()
{
  if(Unit::eV != 1.)
    PROMPT_THROW(CalcError, "The default unit of NCrystal is eV");
}

}

NCrystalScatModel::NCrystalScatModel(const std::string& nccfg, double maxekin)
: m_scat(NCrystal::createScatter(nccfg)),
  m_maxekin(maxekin),
  m_numdensity(ncrystalNumberDensity(nccfg))
{
  assertEVUnits();
}

PluginXs NCrystalScatModel::crossSection(PluginEkin ekin, const double* dir) const
{
  if( m_scat.isOriented() )
  {
    // the adapter refuses a null direction for oriented models before this
    // call, so dir is a real unit vector here
    auto xsect = m_scat.crossSection( NCrystal::NeutronEnergy(ekin), {dir[0], dir[1], dir[2]} );
    return xsect.get()*Unit::barn;
  }
  auto xsect = m_scat.crossSectionIsotropic( NCrystal::NeutronEnergy(ekin) );
  return xsect.get()*Unit::barn;
}

void NCrystalScatModel::sample(PluginEkin ekin, const double* dir, Rng& rng,
                               SampleResult& out, SecondarySink* sink)
{
  (void)rng; (void)sink;
  // NCrystal normalises the incident direction internally: on a null vector
  // that division yields NaN and its rejection loop never terminates. (The
  // adapter guards the same hazard with its generic message; this one keeps
  // the ncrystal-specific diagnostic of the legacy model.)
  if(dir[0]==0. && dir[1]==0. && dir[2]==0.)
    PROMPT_THROW(BadInput, "null incident direction, NCrystal direction sampling would loop forever");

  auto outcome1 = m_scat.sampleScatter( NCrystal::NeutronEnergy(ekin), {dir[0], dir[1], dir[2]});
  out.final_ekin = outcome1.ekin.get();
  auto &outdir = outcome1.direction;
  out.final_dir[0] = outdir[0];
  out.final_dir[1] = outdir[1];
  out.final_dir[2] = outdir[2];
  out.deposition = ekin - out.final_ekin;
  out.absorbed = false;
}

NCrystalAbsModel::NCrystalAbsModel(const std::string& nccfg)
: m_abs(NCrystal::createAbsorption(nccfg)),
  m_numdensity(ncrystalNumberDensity(nccfg))
{
  if( m_abs.isOriented() ) {
    PROMPT_THROW(CalcError, "Absorption process is not oriented");
  }
}

PluginXs NCrystalAbsModel::crossSection(PluginEkin ekin, const double* dir) const
{
  (void)dir;
  return m_abs.crossSectionIsotropic(NCrystal::NeutronEnergy(ekin)).get()*Unit::barn;
}

PluginXs NCrystalAbsModel::absorptionCrossSection(PluginEkin ekin, const double* dir) const
{
  (void)dir;
  return m_abs.crossSectionIsotropic(NCrystal::NeutronEnergy(ekin)).get()*Unit::barn;
}

void NCrystalAbsModel::sample(PluginEkin ekin, const double* dir, Rng& rng,
                              SampleResult& out, SecondarySink* sink)
{
  (void)dir; (void)rng; (void)sink;
  // fixme: this model does not include the Q valude (legacy comment)
  out.final_ekin = 0.0;
  out.deposition = ekin;
  out.absorbed = true;
}

void NCrystalFactory::produceAll(const CfgView& cfg, const HostBias& bias,
                                 const ModelEmit& emit) const
{
  const bool rawMode = cfg.ns().empty();
  if(rawMode)
  {
    // NC_RAW: the string itself is the NCrystal cfg; both channels at unit
    // bias, absorption registered FIRST (legacy NC_RAW else-branch order).
    emit(std::make_unique<NCrystalAbsModel>(cfg.raw()), ModelRole::Absorption);
    emit(std::make_unique<NCrystalScatModel>(cfg.raw()), ModelRole::Scatter);
  }
  else
  {
    // NC_SCATTER: physics=ncrystal with nccfg=; scatter first, then
    // absorption, each skipped when its host bias is non-positive (before
    // construction: NCrystal::create* front-loads file access).
    const std::string nccfg = cfg.str("nccfg");
    if(bias.scatter > 0.)
      emit(std::make_unique<NCrystalScatModel>(nccfg), ModelRole::Scatter);
    if(bias.abs > 0.)
      emit(std::make_unique<NCrystalAbsModel>(nccfg), ModelRole::Absorption);
  }
}

}
