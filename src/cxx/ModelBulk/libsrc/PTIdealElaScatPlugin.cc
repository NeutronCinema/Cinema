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

#include "PTIdealElaScatPlugin.hh"
#include "PTUnitSystem.hh"

#include <cmath>

// Sampling replicates the legacy IdealElaScat::sampleReaction draw-for-draw:
// two random numbers, consumed ONLY in the transfer branch, u = 2*r1-1 with
// v = temp*cos(2*pi*r2), w = temp*sin(2*pi*r2).

namespace Prompt::Plugin {

IdealElaScatModel::IdealElaScatModel(double xs_barn, double density_per_aa3, double ekin_transfer)
:m_xs(xs_barn*Unit::barn), m_numdensity(density_per_aa3), m_ekin_t(ekin_transfer*Unit::eV)
{
  std::cout<<"Created IdealElaScat physics. xs :" << xs_barn
           << ", density_per_aa3 " << density_per_aa3 <<std::endl;
}

PluginXs IdealElaScatModel::crossSection(PluginEkin ekin, const double* dir) const
{
  (void)ekin; (void)dir;
  return m_xs;
}

void IdealElaScatModel::sample(PluginEkin ekin, const double* dir, Rng& rng,
                               SampleResult& out, SecondarySink* sink)
{
  (void)sink;
  if (ekin<m_ekin_t)
  {
    out.final_ekin = ekin;
    out.final_dir[0] = dir[0];
    out.final_dir[1] = dir[1];
    out.final_dir[2] = dir[2];
    out.deposition = 0.;
  }
  else
  {
    out.final_ekin = ekin - m_ekin_t;

    double r1 = rng.next();
    double r2 = rng.next();

    double u = 2*r1-1;
    double temp = sqrt(1-u*u);
    double v = temp*cos(2*M_PI*r2);
    double w = temp*sin(2*M_PI*r2);

    out.final_dir[0] = u;
    out.final_dir[1] = v;
    out.final_dir[2] = w;
    out.deposition = m_ekin_t;
  }
  out.absorbed = false;
}

std::unique_ptr<ScatterModel> IdealElaScatFactory::produce(const CfgView& cfg) const
{
  // legacy validation order (createIdealElaScat): value checks first, the
  // unknown/extra-key rejection LAST (it used to be the parCount equality)
  double xs = 1.;
  if(cfg.has("xs_barn"))
    xs = cfg.number("xs_barn");
  if(!xs)
    PROMPT_THROW(BadInput, "\"xs_barn\" should be non-zero");

  double density_per_aa3 = 0.05;
  if(cfg.has("density_per_aa3"))
    density_per_aa3 = cfg.number("density_per_aa3");
  if(!density_per_aa3)
    PROMPT_THROW(BadInput, "\"density_per_aa3\" should be non-zero");

  double ekin_transfer = 0.;
  if(cfg.has("energy_transfer_eV"))
    ekin_transfer = cfg.number("energy_transfer_eV");

  for(const auto &key : cfg.keys())
  {
    if(key != "xs_barn" && key != "density_per_aa3" && key != "energy_transfer_eV")
      PROMPT_THROW2(BadInput, "physics=" << cfg.ns() << ": unknown key '" << key << "'");
  }

  return std::make_unique<IdealElaScatModel>(xs, density_per_aa3, ekin_transfer);
}

void IdealElaScatFactory::produceAll(const CfgView& cfg, const HostBias& bias,
                                     const ModelEmit& emit) const
{
  // the host consumed scatter_bias before the factory saw the cfg; the
  // legacy non-zero rule is enforced here so the error text stays
  if(!bias.scatter)
    PROMPT_THROW(BadInput, "\"scatter_bias\" should be non-zero");

  emit(produce(cfg), ModelRole::Scatter);
}

}
