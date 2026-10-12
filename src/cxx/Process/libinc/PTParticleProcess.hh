#ifndef Prompt_ParticleProcess_hh
#define Prompt_ParticleProcess_hh

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

#include <string>
#include "PromptCore.hh"
#include "PTModelCollection.hh"
#include "PTParticle.hh"

namespace Prompt {
  class ParticleProcess  {
  public:
    ParticleProcess(const std::string& name, int pdg = const_neutron_pgd, bool absorp_in_weight = false);
    const std::string& getName() const { return m_name; }
    virtual ~ParticleProcess();
    ModelCollection* getModelCollection() {return m_discretModels.get(); }
    double getNumDensity() {return m_numdensity; }
    void setAbsorpInWeight(bool enable) { m_absorp_in_weight = enable; } 

    double sampleStepLength(const Prompt::Particle &particle, double &macxs) const;
    bool sampleFinalState(Prompt::Particle &particle, double stepLength=0., bool hitWall=false) const;
    void cfgPhysicsModel(const std::string &cfg);
    bool containOrentied() const { return m_discretModels->containOriented(); }

  private:
    double macroCrossSection(const Prompt::Particle &particle) const;
    // Route the non-gidi ncrystal paths (NC_RAW and NC_SCATTER) through the
    // plugin registry: the builtin NCrystalFactory emits the same Abs/Scat
    // channels in the legacy order and each becomes a PluginModelAdapter.
    void cfgNCrystalViaPlugin(const std::string &cfgstr, double scatter_bias, double abs_bias);
    std::string m_name;
    SingletonPTRand &m_rng;
    std::unique_ptr<ModelCollection> m_discretModels;
    double m_numdensity;
    bool m_absorp_in_weight; 
  };

}

#endif