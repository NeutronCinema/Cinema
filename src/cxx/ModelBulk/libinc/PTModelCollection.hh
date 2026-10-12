#ifndef Prompt_ModelCollection_hh
#define Prompt_ModelCollection_hh

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
#include "PromptCore.hh"
#include "PTVector.hh"
#include "PTRandCanonical.hh"
#include "PTDiscreteModel.hh"
#ifdef ENABLE_GIDI
#include "PTMaterialDecomposer.hh"
#endif


namespace Prompt {

  class PhysicsModel;

  struct XSCache {
    double ekin;
    Vector dir;
    std::vector<double> cache_xs;
    std::vector<double> bias;
    double selectedBias;
    double tot;
  };

#ifdef ENABLE_GIDI
  // The settings of a gidi material, frozen at configuration time (P2.2):
  // everything the deferred GNDS build needs, so that later changes of the
  // global GidiSetting cannot alter an already-configured material.
  struct PendingGidi {
    std::vector<IsotopeComposition> isotopes;
    double temperature;
    double bias;            // neutron interaction bias
    double elasticThreshold;
    bool photon;            // snapshot of gammaTransport at configuration time
  };
#endif

  // This class is used to represent a collection of models.
  // The upstream should make should it is the right one for the material
  // Only discrete models for now.
  // This class processes the biasing factor

  class ModelCollection  {
  public:
    ModelCollection(int gpd);
    virtual ~ModelCollection();

    void addPhysicsModel(std::shared_ptr<DiscreteModel> model);
    const std::vector<std::shared_ptr<DiscreteModel>>& getModels() const
    { return m_models; }

#ifdef ENABLE_GIDI
    // Defer the gidi models of this material: register the frozen settings
    // now, build nothing (P2.1). Entries materialise in registration order.
    void registerPendingGidi(std::vector<IsotopeComposition> isotopes, double temperature,
                             double bias, double elasticThreshold, bool photon);

    // Hold back an already-built model so that prepareGidi() can append it
    // AFTER the deferred gidi models — preserving the eager model order of
    // the physics=ncrystal configuration (gidi first, NCrystal second).
    void registerDeferredModel(std::shared_ptr<DiscreteModel> model);

    // The single materialization point: build all pending gidi models of this
    // collection. Consumes no random numbers, so the RNG stream is untouched.
    void prepareGidi();

    // prepareGidi() for every live collection; called once at the top of each
    // transport entry (Launcher::simOneEvent covers go, goWithSecondStack and
    // the python-gun loop).
    static void prepareAllGidi();
#endif

    double totalCrossSection(int pdg, double ekin, const Vector &dir) const;

    double unbiasedAbsorptionCrossSection(int pdg, double ekin) const;
    double calculateWeight(double lengthRho, bool hitWall);
    SampledResult&  pickAndSample(double ekin, const Vector &dir) const;
    int getSupportedGPD() const { return m_forgpd; }
    bool containOriented() const { return m_containsOriented; }

  private:
    bool sameInquiryAsLastTime(double ekin, const Vector &dir) const;

    std::vector<std::shared_ptr<DiscreteModel> > m_models;
    mutable XSCache m_cache;
    bool m_containsOriented;
    int m_forgpd;
    mutable Vector m_localdir;
    mutable SampledResult m_res;

    // Cache for disappearing reaction models to optimize absorptionCrossSection
    mutable std::shared_ptr<DiscreteModel> m_disappearingModel;

    SingletonPTRand &m_rng;

#ifdef ENABLE_GIDI
    std::vector<PendingGidi> m_pendingGidi;
    std::vector<std::shared_ptr<DiscreteModel> > m_deferredModels;
#endif
  };
}

inline bool Prompt::ModelCollection::sameInquiryAsLastTime(double ekin, const Vector &dir) const
{
  return m_containsOriented ? (m_cache.ekin==ekin && m_cache.dir == dir) : m_cache.ekin==ekin;
}

#endif