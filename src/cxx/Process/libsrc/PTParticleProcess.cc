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

#include "PTSurfaceProcess.hh"
#include "PTUnitSystem.hh" //const_neutron_pgd

#include <cmath>
#include <limits>
#include <memory>
#include "NCrystal/NCrystal.hh"
#include "PTIdealElaScat.hh"
#include "PTPhysicsFactory.hh"
#include "PTActiveVolume.hh"
#include "PTNCrystalScat.hh"
#include "PTNCrystalAbs.hh"
#include "PTCfgParser.hh"
#include "PTMaterialDecomposer.hh"
#ifdef ENABLE_GIDI
#include "PTGIDIModel.hh"
#include "PTGIDIFactory.hh"
#include "PTGidiSetting.hh"
#endif
#include "PTStackManager.hh"
#include "PTPluginRegistry.hh"
#include "PTNCrystalPlugin.hh"
#include "PTPluginModelAdapter.hh"

Prompt::ParticleProcess::ParticleProcess(const std::string &name, int pdg, bool absorp_in_weight)
    : m_rng(Singleton<SingletonPTRand>::getInstance()),
      m_discretModels(std::make_unique<ModelCollection>(pdg)),
      m_numdensity(0.), m_name(name), m_absorp_in_weight(absorp_in_weight)
{
  cfgPhysicsModel(name);
}

Prompt::ParticleProcess::~ParticleProcess() {}

double Prompt::ParticleProcess::macroCrossSection(const Prompt::Particle &particle) const
{
  double ekin =  particle.getEKin();
  const auto &dir =  particle.getDirection();
  return m_numdensity * m_discretModels->totalCrossSection(particle.getPDG(), ekin, dir);
}

bool Prompt::ParticleProcess::sampleFinalState(Prompt::Particle &particle, double stepLength, bool hitWall) const
{
  // if (m_discretModels->getSupportedGPD() != particle.getPDG())
  //   PROMPT_THROW2(CalcError, "ParticleProcess::sampleFinalState " << m_name << " does not support particle " << particle.getPDG() << ", " << m_discretModels->getSupportedGPD());

  if (!particle.isAlive())
    PROMPT_THROW(CalcError, "Particle is not alive");

  if(m_absorp_in_weight) 
  {
      double absxs = m_discretModels->unbiasedAbsorptionCrossSection(particle.getPDG(), particle.getEKin());
      particle.scaleSurviveP(exp(-absxs*stepLength*m_numdensity));
  }

  // if particle is escaped to the the next volume
  if (hitWall)
  {
    if (stepLength)
    {
      particle.scaleWeight(m_discretModels->calculateWeight(stepLength * m_numdensity, true));
    }
    return false;
  }

  auto &res = m_discretModels->pickAndSample(particle.getEKin(), particle.getDirection());

  // fixme: when a particle exiting a volume, a reaction channel is forced to sampled at the moment
  // lab_ekin could be -1 in those cases, but the transport keeps going, that is very confusing.

  double weightCorrection = m_discretModels->calculateWeight(stepLength * m_numdensity, false);

  // treating secondaries
  auto &stm = Singleton<StackManager>::getInstance();
  int secNum = stm.getUnweightedNum();
  for(int i=0; i<secNum; i++)
  {
    stm.scalceSecondary(i, weightCorrection);
  }

  if(res.dispeared) //Sample results = Absorption
  {
    if(!m_absorp_in_weight)
      particle.kill(Particle::KillType::ABSORB);
  }
  else
  {
    particle.setEKin(res.final_ekin);
    particle.setDirection(res.final_dir);
  }
  particle.setDeposition(res.deposition);
  particle.scaleWeight(weightCorrection);
  return !res.dispeared;
}

double Prompt::ParticleProcess::sampleStepLength(const Prompt::Particle &particle, double &mxs) const
{
  // if (m_discretModels->getSupportedGPD() != particle.getPDG())
  //   PROMPT_THROW2(CalcError, "ParticleProcess::sampleStepLength " << m_name << " does not support particle " << particle.getPDG() << ", " << m_discretModels->getSupportedGPD());

  mxs = macroCrossSection(particle);
  if (mxs)
  {
    return -log(m_rng.generate()) / mxs;
  }
  else
  {
    return std::numeric_limits<double>::max();
  }
}

void Prompt::ParticleProcess::cfgPhysicsModel(const std::string &cfgstr)
{
  std::cout << "Configuring physics model: " << cfgstr << std::endl;
  pt_assert_always(!m_numdensity); //multiple configuration

  auto &pfact = Singleton<PhysicsFactory>::getInstance();
  PhysicsFactory::PhysicsType type = pfact.checkPhysicsType(cfgstr);

  if (type != PhysicsFactory::PhysicsType::NC_RAW)
  {
    // Parse the config string to check for absorp_in_weight parameter
    auto &ps = Singleton<CfgParser>::getInstance();
    auto cfg = ps.parse(cfgstr);
    
    // Check for absorp_in_weight parameter and set it accordingly
    bool absorp_in_weight_cfg = m_absorp_in_weight; // Use default value
    cfg.getBoolIfExist("absorp_in_weight", absorp_in_weight_cfg);
    m_absorp_in_weight = absorp_in_weight_cfg;
  }

  #ifdef ENABLE_GIDI
  auto &cd = Singleton<GidiSetting>::getInstance();
  const bool enablegidi = cd.getEnableGidi();
  const double gidithreshold = cd.getGidiThreshold();
  #endif

  // The non-gidi ncrystal branches below route through the plugin registry
  // (ncrystal = plugin #0): the builtin NCrystalFactory emits the same
  // channels in the legacy order and each becomes a PluginModelAdapter, so
  // ModelCollection's channel-pick math is unchanged. The gidi branches
  // stay on the legacy constructors - the PendingGidi/DeferredModel
  // machinery is ModelCollection state, not expressible as model emission.
  // The factory ships in the core library until M5 repackages it.
  if (type == PhysicsFactory::PhysicsType::NC_RAW)
  {
    m_numdensity = pfact.nccalNumDensity(cfgstr);

    #ifdef ENABLE_GIDI
    if(enablegidi)
    {
      // in this mode, abs and nonelastic scattering (e.g. MT!=2) are all be done in GIDI+
      // ncrystal only does the scattering below the threshold
      std::cout << "enabled gidi model for " << cfgstr
      << ", the swithching energy from ncrystal to digi is at " << gidithreshold << "eV.\n";
      // NCrystal models
      if(gidithreshold>0)
         m_discretModels->addPhysicsModel(std::make_shared<NCrystalScat>(cfgstr, 1.0, 0, gidithreshold));

      // GIDI models: decompose now (cheap, front-loads config errors) but
      // defer the GNDS parsing to the first transport event (P2.1); the
      // settings below are frozen here (P2.2)
      auto &nm = Prompt::Singleton<Prompt::MaterialDecomposer>::getInstance();
      double temperature(0.);
      auto isotopes = nm.decompose(cfgstr, temperature);
      for(const auto &v: isotopes)
        std::cout << v << std::endl;

      m_discretModels->registerPendingGidi(std::move(isotopes), temperature, 1.,
                                           gidithreshold<=0.?0.:gidithreshold, cd.getGammaTransport(),
                                           cd.getGidiSampleNTP());
    }
    else
    #endif
    {
      // plugin #0: the same Abs+Scat pair in the same order, at unit bias,
      // produced through the registry instead of direct construction
      cfgNCrystalViaPlugin(cfgstr, 1.0, 1.0);
    }


  }
  else if (type == PhysicsFactory::PhysicsType::NC_SCATTER)
  {
    CfgParser::StringCfg cfg = Singleton<CfgParser>::getInstance().parse(cfgstr);
    double scatter_bias = 1.0;
    cfg.getDoubleIfExist("scatter_bias", scatter_bias);

    double abs_bias = 1.0;
    cfg.getDoubleIfExist("abs_bias", abs_bias);

    std::string nccfg;
    cfg.getStringIfExist("nccfg", nccfg);
    m_numdensity = pfact.nccalNumDensity(nccfg);

    #ifdef ENABLE_GIDI
    //fixme: todo: how to disable absorption when abs_bias is zero?
    if(enablegidi)
    {
      std::cout << "enabled gidi model for " << cfgstr
      << ", the switching energy at " << gidithreshold << "eV.\n";

      // GIDI models: decompose now (cheap, front-loads config errors) but
      // defer the GNDS parsing to the first transport event (P2.1); the
      // settings below are frozen here (P2.2)
      auto &nm = Prompt::Singleton<Prompt::MaterialDecomposer>::getInstance();
      double temperature (0);
      auto isotopes = nm.decompose(nccfg, temperature);
      for(const auto &v: isotopes)
        std::cout << v << std::endl;

      m_discretModels->registerPendingGidi(std::move(isotopes), temperature, abs_bias,
                                           gidithreshold<=0.?0:gidithreshold, cd.getGammaTransport(),
                                           cd.getGidiSampleNTP());

      // NCrystal models: held back so that the deferred gidi models land
      // before them, matching the eager model order
      if(gidithreshold>0.)
      {
        m_discretModels->registerDeferredModel(std::make_shared<NCrystalScat>(nccfg, scatter_bias, 0, gidithreshold));
      }
      else
        std::cout << "!The ncrystal elastic scatter is not created!\n";
    }
    else
    #endif
    {
      // plugin #0: the factory applies the same channel-enablement rule
      // (bias <= 0 skips, before construction) and the Scat-then-Abs order
      cfgNCrystalViaPlugin(cfgstr, scatter_bias, abs_bias);
    }
  }
  else if (type == PhysicsFactory::PhysicsType::NC_IDEALSCAT)
  {
    auto idsct = pfact.createIdealElaScat(cfgstr);
    m_discretModels->addPhysicsModel(idsct);
    m_numdensity =  reinterpret_cast<IdealElaScat *>(idsct.get())->getNumberDensity();
  }

}

void Prompt::ParticleProcess::cfgNCrystalViaPlugin(const std::string &cfgstr, double scatter_bias, double abs_bias)
{
  auto *factory = Plugin::PluginRegistry::instance().lookup("ncrystal");
  if(!factory)
    PROMPT_THROW(BadInput, "the builtin ncrystal plugin factory is not registered");

  Plugin::HostBias hb;
  hb.scatter = scatter_bias;
  hb.abs = abs_bias;

  bool numdensityChecked = false;
  factory->produceAll(Plugin::CfgView(cfgstr), hb,
    [this,scatter_bias,abs_bias,&numdensityChecked](std::unique_ptr<Plugin::ScatterModel> model,
                                                    Plugin::ModelRole role)
    {
      // Cross-check the plugin number-density contract against m_numdensity
      // (the host keeps calling nccalNumDensity; both values go through the
      // identical NCrystal call, so a mismatch means a lying plugin, not a
      // unit problem).
      if(!numdensityChecked)
      {
        numdensityChecked = true;
        double mdd = model->numberDensity();
        if(mdd > 0. && std::abs(mdd - m_numdensity) > 1e-12*std::abs(m_numdensity))
          PROMPT_THROW2(CalcError, "plugin number density " << mdd
                        << " disagrees with the material density " << m_numdensity);
      }

      double bias = (role == Plugin::ModelRole::Absorption) ? abs_bias : scatter_bias;
      m_discretModels->addPhysicsModel(
        std::make_shared<PluginModelAdapter>(std::move(model), "ncrystal", bias));
    });
}