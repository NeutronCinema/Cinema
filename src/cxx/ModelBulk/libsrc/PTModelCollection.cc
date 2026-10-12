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

#include "PTModelCollection.hh"
#include "PTNCrystalScat.hh"
#include "PTNCrystalAbs.hh"
#include "PTPhysicsModel.hh"
#include "PTActiveVolume.hh"
#include <algorithm>
#ifdef ENABLE_GIDI
#include "PTGIDIFactory.hh"
#include "PTGIDIModel.hh"
#endif

// Registry of every live collection on this thread (singletons are
// thread_local, so collections never cross threads). It lets the transport
// entries materialise all pending gidi models through one call without
// walking the geometry.
//
// The vector is heap-allocated on purpose. A function-local thread_local
// object would be destroyed before the thread_local singletons that own the
// collections registered here (TLS destructors run in reverse completion
// order, and ResourceManager completes before the first collection is
// constructed), so ~ModelCollection would deregister from an
// already-destroyed vector — a use-after-free on every normal process exit.
// A raw pointer has no TLS destructor: the vector outlives every owner, the
// deregistration stays exact, and the few-dozen-byte buffer is reclaimed
// with the thread.
namespace {
  std::vector<Prompt::ModelCollection*> &liveCollections()
  {
    static thread_local auto *s_live = new std::vector<Prompt::ModelCollection*>;
    return *s_live;
  }
}

Prompt::ModelCollection::ModelCollection(int gpd)
:m_cache({}), m_containsOriented(false), m_rng( Singleton<SingletonPTRand>::getInstance() ),
 m_forgpd(gpd), m_res(), m_disappearingModel(nullptr)
{
  liveCollections().push_back(this);
}

Prompt::ModelCollection::~ModelCollection()
{
  auto &live = liveCollections();
  live.erase( std::remove( live.begin(), live.end(), this ), live.end() );
}

#ifdef ENABLE_GIDI
void Prompt::ModelCollection::registerPendingGidi(std::vector<IsotopeComposition> isotopes, double temperature,
                                                  double bias, double elasticThreshold, bool photon, bool sampleNTP)
{
  PendingGidi pending;
  pending.isotopes = std::move(isotopes);
  pending.temperature = temperature;
  pending.bias = bias;
  pending.elasticThreshold = elasticThreshold;
  pending.photon = photon;
  pending.sampleNTP = sampleNTP;
  m_pendingGidi.push_back( std::move(pending) );
  std::cout << "GIDI models for this material are registered as pending"
            << " and will be built at the first transport event." << std::endl;
}

void Prompt::ModelCollection::registerDeferredModel(std::shared_ptr<DiscreteModel> model)
{
  m_deferredModels.push_back( std::move(model) );
}

void Prompt::ModelCollection::prepareGidi()
{
  if(m_pendingGidi.empty() && m_deferredModels.empty())
    return;

  auto &gidifactory = Singleton<GIDIFactory>::getInstance();
  // Consume every entry as it completes: if the build of entry k throws, the
  // earlier entries stay built exactly once, so a retry (next transport
  // event) only redoes the failed one instead of duplicating whole channels.
  while(!m_pendingGidi.empty())
  {
    PendingGidi pending( std::move(m_pendingGidi.front()) );
    m_pendingGidi.erase( m_pendingGidi.begin() );

    // same model order as the eager configuration used to produce:
    // neutron models first, then photon, then the atomic photon pass.
    // gamma/sampleNTP are the configuration-time snapshot, not the live
    // GidiSetting — the deferred build must not read changed globals.
    auto models = gidifactory.createNeutronGIDIModel(pending.isotopes, pending.temperature,
                                                     pending.bias, pending.elasticThreshold,
                                                     pending.photon, pending.sampleNTP);
    for(const auto &v : models)
      addPhysicsModel(v);

    if(pending.photon)
    {
      auto gmodels = gidifactory.createPhotonGIDIModel(pending.isotopes, 1.,
                                                       pending.photon, pending.sampleNTP);
      for(const auto &v : gmodels)
        addPhysicsModel(v);

      auto atomic_models = gidifactory.createPhotonGIDIModel(shrink2element(pending.isotopes), 1.,
                                                             pending.photon, pending.sampleNTP);
      for(const auto &v : atomic_models)
        addPhysicsModel(v);
    }
  }

  // held-back models land after the gidi ones, as in the eager layout
  while(!m_deferredModels.empty())
  {
    std::shared_ptr<DiscreteModel> model( std::move(m_deferredModels.front()) );
    m_deferredModels.erase( m_deferredModels.begin() );
    addPhysicsModel( model );
  }
}

void Prompt::ModelCollection::prepareAllGidi()
{
  for(auto *coll : liveCollections())
    coll->prepareGidi();
}
#endif


void Prompt::ModelCollection::addPhysicsModel(std::shared_ptr<Prompt::DiscreteModel> model)
{
  // Check if this is a disappearing reaction model
  if (model->isDispearingReaction()) {
    if (m_disappearingModel != nullptr) {
      // Multiple disappearing reaction models detected - this is an error
      PROMPT_THROW2(CalcError, 
        "Multiple disappearing reaction models detected in ModelCollection. "
        "Only one disappearing reaction model is allowed per collection.");
    }
    m_disappearingModel = model;
  }

  m_models.emplace_back(model);

  // cache_xs and bias will be updated once a calculation is required.
  // so the initial value can be arbitrary.
  m_cache.cache_xs.push_back(0.);
  m_cache.bias.push_back(1.); // to be update in totalCrossSection
  if(m_models.back()->isOriented())
    m_containsOriented = true;
}

double Prompt::ModelCollection::unbiasedAbsorptionCrossSection(int pdg, double ekin) const 
{
  // Use cached disappearing model if available
  if (m_disappearingModel != nullptr)
  {
    if (m_disappearingModel->isValid(pdg, ekin)) 
      return m_disappearingModel->getCrossSection(ekin)/m_disappearingModel->getBias();
  }
  pt_assert_always(m_disappearingModel != nullptr);
  
  return 0.;
  }

double Prompt::ModelCollection::totalCrossSection(int pdg, double ekin, const Vector &dir) const
{
  // offline callers (python xs(), unit tests) can reach the collection before
  // any transport entry ran; self-materialise the pending gidi models. No-op
  // once prepared, and the build consumes no random numbers.
#ifdef ENABLE_GIDI
  const_cast<ModelCollection*>(this)->prepareGidi();
#endif

  if(sameInquiryAsLastTime(ekin, dir))
  {
    return m_cache.tot;
  }
  else
  {
    double xs(0.);
    for(unsigned i=0;i<m_models.size();i++)
    {
      double channelxs(0);
      // if the model is valid for the particle
      if(m_models[i]->isValid(pdg, ekin))
      {
        if(m_models[i]->isOriented())
        {
          auto &activeVolume = Singleton<ActiveVolume>::getInstance();
          m_localdir =  activeVolume.getGeoTranslator().global2Local_direction(dir);
          channelxs = m_models[i]->getCrossSection(ekin, m_localdir) ;
        }
        else  {
          channelxs = m_models[i]->getCrossSection(ekin);
          // std::cout << "model name: " << m_models[i]->getName()
          // << ", ekin=" << ekin
          // << ", biasing=" << m_models[i]->getBias() << ", channelxs=" << channelxs << "\n\n";
        }
        m_cache.cache_xs[i] = channelxs;
        m_cache.bias[i] = m_models[i]->getBias();
        xs += channelxs;

      }  
      else
      {
        m_cache.cache_xs[i] = 0.;
        m_cache.bias[i] = m_models[i]->getBias();
      }
    }
    // std::cout << "total xs " << xs << "\n\n";

    m_cache.tot = xs;
    m_cache.ekin = ekin;
    m_cache.dir = dir;

    return xs;
  }
}

Prompt::SampledResult& Prompt::ModelCollection::pickAndSample(double ekin, const Vector &dir) const
{
  if(!sameInquiryAsLastTime(ekin, dir))
  {
    //fixme:!!
    printf("WARNING, sampling event with different incident energy and/or direction\n");
    m_res.final_ekin = ekin;
    m_res.final_dir = dir;
    return m_res;
  }

  //if xs is zero, do nothing
  if(!m_cache.tot)
  {
    m_res.final_ekin = ekin;
    m_res.final_dir = dir;
    return m_res;
  }

  double r1 =  m_rng.generate();
  unsigned i=0;
  double p(0.), i_tot(1./m_cache.tot);
  for(; i<m_cache.cache_xs.size(); i++) //fixme: this is only faster when the number of physics model is small
  {
    p += m_cache.cache_xs[i]*i_tot;
    if(p > r1)
      break;
  }
  if(i >= m_models.size()) //guard: the draw rounded past the summed probability
    i = m_models.size()-1;

  //oriented models sample in the local (crystal) frame: convert the incident
  //direction like totalCrossSection does, the sampled outgoing direction is
  //mapped back to the global frame below
  const Vector *sampledir = &dir;
  if(m_models[i]->isOriented())
  {
    auto &activeVolume = Singleton<ActiveVolume>::getInstance();
    m_localdir =  activeVolume.getGeoTranslator().global2Local_direction(dir);
    sampledir = &m_localdir;
  }

  m_res = m_models[i]->sampleReaction(ekin, *sampledir);

  if(m_models[i]->isOriented())
  {
    auto &activeVolume = Singleton<ActiveVolume>::getInstance();
    m_res.final_dir =  activeVolume.getGeoTranslator().local2Global_direction(m_res.final_dir);
  }

  m_cache.selectedBias = m_models[i]->getBias();

  return m_res;
}

//this shoule be called right after cross section is updated
double Prompt::ModelCollection::calculateWeight(double lengthRho, bool hitWall)
{
  double factor(1.);
  for(size_t i=0;i<m_models.size();i++)
  {
    double modbias(m_models[i]->getBias());
    if (modbias==1.) continue;
    //this factor contributed in this step of lengthRho by this model
    // printf("\nm_cache.bias[i]==%g\n", m_cache.bias[i]);
    pt_assert(m_cache.bias[i]>0);
    factor *= exp( (m_cache.bias[i]-1.)*lengthRho* m_cache.cache_xs[i]/m_cache.bias[i] );
  }
  // std::cout << "selectedBias " << m_cache.selectedBias << " factor " << factor
  // << std::endl;
  // assert(m_cache.selectedBias);
  return (m_cache.selectedBias!=0 && m_cache.selectedBias!=1. && !hitWall ) ?  (factor/m_cache.selectedBias) : factor;
}