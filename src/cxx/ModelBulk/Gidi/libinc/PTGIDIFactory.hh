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

    // gammaTransport and sampleNTP are the configuration-time snapshots
    // carried by the caller's PendingGidi (P2.2) — never read from the live
    // GidiSetting here, or a setting changed between configuration and the
    // first transport event would silently rebuild different physics.
    std::vector<std::shared_ptr<GIDIModel>> createNeutronGIDIModel(const std::vector<IsotopeComposition>& iso,  double temperature,
                            double bias=1. ,
                            double elasticThreshold=0,
                            bool gammaTransport=false, bool sampleNTP=true,
                            double minEKin=0, double maxEKin=std::numeric_limits<double>::max()) const;

    // atomicPass selects the photo-atomic-only Construction: the isotope pass
    // runs photoMode nuclearOnly (photonuclear data per isotope), the element
    // pass runs atomicOnly (photo-atomic data per element, via shrink2element).
    // One pass each => the atomic cross section is registered exactly once.
    // CAVEAT: the gidiplus map lookup matches by target string and ignores
    // the entry's interaction attribute, so nuclearOnly handed a bare element
    // name ("Pb") silently serves the photo-atomic entry. This stays safe
    // because the material decomposer emits nuclide names ("Pb208") and only
    // the element pass carries element names; do not feed it element symbols.
    std::vector<std::shared_ptr<GIDIModel>> createPhotonGIDIModel(const std::vector<IsotopeComposition>& iso,  double bias=1. ,
                            bool gammaTransport=true, bool sampleNTP=true,
                            double minEKinElastic=0, double maxEKinElastic=std::numeric_limits<double>::max(),
                            double minEKinNonelastic=0, double maxEKinNonelastic=std::numeric_limits<double>::max(),
                            bool atomicPass=false) const;


    int getHashID(double energy) const;
    bool available() const;
    // Number of distinct MCGIDI protares currently cached. Test hook for the
    // data-reuse invariant: building the same nuclide through a second
    // material must not grow this.
    size_t protareCacheSize() const { return m_protareCache.size(); }
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

    std::shared_ptr<MCGIDI::Protare> cachedProtare(const std::string &name, const std::string &label,
                                                   const char *mode, bool gammaTransport, bool sampleNTP,
                                                   const std::function<std::shared_ptr<MCGIDI::Protare>()> &builder) const;

    // The photon transport particle is registered into the shared particle
    // list on demand: at init time no snapshot exists yet, so the first
    // build that wants photons adds it, once, before its protares.
    void ensurePhotonParticle() const;

    // Cache key of a built MCGIDI protare. The identity is CANONICAL, not
    // lexical: the PoPI-resolved (Z, A, metastable index) — so the same
    // nuclide reached under different names or aliases collapses onto one
    // entry (photo-atomic element targets carry A == 0). Alongside it: the
    // heated/gridded cross-section label (encodes both the data file and the
    // temperature), the reaction-exclusion mode ("elas" keeps elastic,
    // "nonelas" keeps non-elastic, "all" excludes nothing, "nuclear" /
    // "atomic" for the two photon passes), and the two build-time flags the
    // protare bakes in (gamma index mapping and non-transporting-particle
    // sampling). Sharing one protare across repeated isotopes is safe for
    // sampling: the per-event URR probabilities are refreshed from (energy,
    // temperature, RNG) before every use, never carried across calls.
    struct ProtareCacheKey {
      int Z, A, metastableIndex;
      std::string label, mode;
      bool gammaTransport, sampleNTP;
      bool operator<(ProtareCacheKey const &o) const {
        return std::tie(Z, A, metastableIndex, label, mode, gammaTransport, sampleNTP)
             < std::tie(o.Z, o.A, o.metastableIndex, o.label, o.mode, o.gammaTransport, o.sampleNTP);
      }
    };

    GidiSetting &m_ctrdata;
    // mutable: the accessors are const but must be able to run the one-time
    // lazy initialisation; the factory is thread_local, so no locking.
    mutable PoPI::Database *m_pops;
    mutable GIDI::Map::Map *m_map;
    mutable GIDI::Transporting::Particles *m_particles;
    mutable GIDI::Construction::Settings *m_construction;
    mutable GIDI::Construction::Settings *m_constructionPhotonNuclear; // PhotoMode::nuclearOnly, isotope pass
    mutable GIDI::Construction::Settings *m_constructionPhotonAtomic;  // PhotoMode::atomicOnly,  element pass
    mutable MCGIDI::DomainHash *m_domainHash;
    LUPI::StatusMessageReporting *m_smr1;
    mutable bool m_initialised;
    mutable bool m_photonParticleAdded;
    mutable std::map<ProtareCacheKey, std::shared_ptr<MCGIDI::Protare>> m_protareCache;

  };
}

#endif
