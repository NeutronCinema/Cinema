////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
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
  // std::cout << particle.getEventID() << ", is alive? " << particle.isAlive() << ", wall? "<< hitWall<<
  //  ", labEkin " << lab_ekin   << ", effEkin " << particle.getEffEKin() << "\n";

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
      
      // GIDI models 
      auto &nm = Prompt::Singleton<Prompt::MaterialDecomposer>::getInstance();
      double temperature(0.);
      auto isotopes = nm.decompose(cfgstr, temperature);
      for(const auto &v: isotopes)
        std::cout << v << std::endl;

      auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();  
      auto models = gidifactory.createNeutronGIDIModel(isotopes, temperature, 1., gidithreshold<=0.?0.:gidithreshold);

      for(const auto &v: models)
        m_discretModels->addPhysicsModel(v);

      if(cd.getGammaTransport())
      {
        auto models = gidifactory.createPhotonGIDIModel(isotopes, 1.);
        for(const auto &v: models)
           m_discretModels->addPhysicsModel(v);

        auto atomic_models = gidifactory.createPhotonGIDIModel(shrink2element(isotopes), 1.);
        for(const auto &v: atomic_models)
           m_discretModels->addPhysicsModel(v);
      }
    }
    else
    #endif
    {
      m_discretModels->addPhysicsModel(std::make_shared<NCrystalAbs>(cfgstr, 1.0, 0));
      m_discretModels->addPhysicsModel(std::make_shared<NCrystalScat>(cfgstr, 1.0, 0));
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

      // GIDI models
      auto &nm = Prompt::Singleton<Prompt::MaterialDecomposer>::getInstance();
      double temperature (0);
      auto isotopes = nm.decompose(nccfg, temperature);
      for(const auto &v: isotopes)
        std::cout << v << std::endl;


      auto &gidifactory = Prompt::Singleton<Prompt::GIDIFactory>::getInstance();  
      auto models = gidifactory.createNeutronGIDIModel(isotopes, temperature, abs_bias, gidithreshold<=0.?0:gidithreshold);

      for(const auto &v: models)
        m_discretModels->addPhysicsModel(v);

      // NCrystal models 
      if(gidithreshold>0.)
      {
        m_discretModels->addPhysicsModel(std::make_shared<NCrystalScat>(nccfg, scatter_bias, 0, gidithreshold));
      }
      else
        std::cout << "!The ncrystal elastic scatter is not created!\n";

      if(cd.getGammaTransport())
      {
        auto models = gidifactory.createPhotonGIDIModel(isotopes, 1.);
        for(const auto &v: models)
           m_discretModels->addPhysicsModel(v);

        auto atomic_models = gidifactory.createPhotonGIDIModel(shrink2element(isotopes), 1.);
        for(const auto &v: atomic_models)
           m_discretModels->addPhysicsModel(v);
      }
    }
    else
    #endif
    {
      if(scatter_bias > 0.)
        m_discretModels->addPhysicsModel(std::make_shared<NCrystalScat>(nccfg, scatter_bias, 0));
      if(abs_bias > 0.)
        m_discretModels->addPhysicsModel(std::make_shared<NCrystalAbs>(nccfg, abs_bias, 0));
    }
  }
  else if (type == PhysicsFactory::PhysicsType::NC_IDEALSCAT)
  {
    auto idsct = pfact.createIdealElaScat(cfgstr);
    m_discretModels->addPhysicsModel(idsct);
    m_numdensity =  reinterpret_cast<IdealElaScat *>(idsct.get())->getNumberDensity();
  }

}