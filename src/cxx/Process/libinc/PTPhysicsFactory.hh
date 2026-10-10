#ifndef Prompt_PhysicsFactory_hh
#define Prompt_PhysicsFactory_hh

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

#include "PromptCore.hh"
#include "PTSingleton.hh"
#include "PTSurfaceProcess.hh"
#include "PTModelCollection.hh"

namespace Prompt {

  class PhysicsFactory  {
  public:
    enum class PhysicsType {
      SURFACE_PHYSICS,
      NC_SCATTER,
      NC_ABSORB,
      NC_SCATTER_ABSORB,
      NC_RAW,
      NC_IDEALSCAT,
      ENDF_SCATTER,
      ENDF_ABSORB
    };
  public:
    bool rawNCrystalCfg(const std::string &cfgstr);
    double nccalNumDensity(const std::string &nccfgstr); // ncrystal cfg string
    void showNCComposition(const std::string &nccfgstr);

    std::shared_ptr<SurfaceProcess> createSurfaceProcess(const std::string &cfgstr);

    std::shared_ptr<DiscreteModel> createIdealElaScat(const std::string &cfgstr);
    std::unique_ptr<ModelCollection> createParticleProcess(const std::string &cfgstr);
    PhysicsType checkPhysicsType(const std::string &cfgstr) const;

  private:
    friend class Singleton<PhysicsFactory>;
    PhysicsFactory() = default;
    ~PhysicsFactory() = default;
  };
}

#endif
