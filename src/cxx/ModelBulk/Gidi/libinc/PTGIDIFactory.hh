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
#include <functional>
#include <map>
#include <set>
#include <tuple>

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
  class ProtareSingle;
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
    // GidiSetting snapshots (enable/threshold) are taken by ParticleProcess at
    // material-configuration time; the heavy GNDS session (PoPI database, map,
    // particle lists, domain hash) is no longer paid in the constructor but on
    // first use, so merely touching the singleton stays free until gidi data
    // is actually needed (P2.1 idempotent lazy initialisation).
    void ensureInitialised() const;

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
    const PoPI::Database &getPoPs() const;
    inline bool NCrystal4Elastic(double ekin) const
    {
      return ekin < m_ctrdata.getGidiThreshold();
    };


  private:

    friend class Singleton<GIDIFactory>;
    GIDIFactory();
    ~GIDIFactory();

    std::shared_ptr<MCGIDI::ProtareSingle> cachedProtare(const std::string &name, const std::string &tempLabel,
                                                         const char *mode,
                                                         const std::function<std::shared_ptr<MCGIDI::ProtareSingle>()> &builder) const;

    // Cache key of a built MCGIDI::ProtareSingle: isotope name, the heated
    // cross-section label of the selected temperature (encodes both the file
    // and the temperature), and the reaction-exclusion mode ("elas" keeps
    // elastic, "nonelas" keeps non-elastic, "all" excludes nothing). Sharing
    // one ProtareSingle across repeated isotopes is safe for sampling: the
    // per-event URR probabilities are refreshed from (energy, temperature,
    // RNG) before every use, never carried across calls.
    using ProtareCacheKey = std::tuple<std::string, std::string, const char *>;

    GidiSetting &m_ctrdata;
    // mutable: the accessors are const but must be able to run the one-time
    // lazy initialisation; the factory is thread_local, so no locking.
    mutable PoPI::Database *m_pops;
    mutable GIDI::Map::Map *m_map;
    mutable GIDI::Transporting::Particles *m_particles;
    mutable GIDI::Construction::Settings *m_construction;
    mutable MCGIDI::DomainHash *m_domainHash;
    LUPI::StatusMessageReporting *m_smr1;
    mutable bool m_initialised;
    mutable std::map<ProtareCacheKey, std::shared_ptr<MCGIDI::ProtareSingle>> m_protareCache;

  };
}

#endif
