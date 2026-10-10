#ifndef Prompt_GIDIFactory_hh
#define Prompt_GIDIFactory_hh

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
#include <memory>
#include <set>

#include "PromptCore.hh"
#include "PTDiscreteModel.hh"
#include "PTSingleton.hh"
#include "PTGidiSetting.hh"
#include "PTLauncher.hh"


namespace GIDI
{
  namespace Transporting
  {
    class Particles;
  }

  namespace Construction
  {
    class Settings;
  }
  
  namespace Map
  {
    class Map;
  }
}

namespace PoPI
{
  class Database;
}

namespace LUPI
{
  class StatusMessageReporting;
}

namespace MCGIDI
{
  class DomainHash;
  class Protare;
  class URR_protareInfos;
  namespace Sampling
  {
    class StdVectorProductHandler;
    class Input;
  }
}  

namespace Prompt {

  class IsotopeComposition;
  class GIDIModel;

  class GIDIFactory {
  public:
    std::vector<std::shared_ptr<GIDIModel>> createNeutronGIDIModel(const std::vector<IsotopeComposition>& iso,  double temperature,
                            double bias=1. , 
                            double elasticThreshold=0,
                            double minEKin=0, double maxEKin=std::numeric_limits<double>::max()) const;

    std::vector<std::shared_ptr<GIDIModel>> createPhotonGIDIModel(const std::vector<IsotopeComposition>& iso,  double bias=1. , 
                            double minEKinElastic=0, double maxEKinElastic=std::numeric_limits<double>::max(),
                            double minEKinNonelastic=0, double maxEKinNonelastic=std::numeric_limits<double>::max()) const;


    int getHashID(double energy) const;
    bool available() const;
    GidiSetting &getGidiSetting() const {return m_ctrdata;};
    const PoPI::Database &getPoPs() const {return *m_pops;};
    inline bool NCrystal4Elastic(double ekin) const 
    {
      return ekin < m_ctrdata.getGidiThreshold();
    };


  private:
  
    friend class Singleton<GIDIFactory>;
    GIDIFactory();
    ~GIDIFactory();

    GidiSetting &m_ctrdata;
    PoPI::Database *m_pops;
    GIDI::Map::Map *m_map;
    GIDI::Transporting::Particles *m_particles;
    GIDI::Construction::Settings *m_construction;
    MCGIDI::DomainHash *m_domainHash;
    LUPI::StatusMessageReporting *m_smr1;

  };
}

#endif
