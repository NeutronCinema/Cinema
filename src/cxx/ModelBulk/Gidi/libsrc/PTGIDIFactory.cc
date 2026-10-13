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
#include "GIDI.hpp"

#include "LUPI.hpp"
#include "MCGIDI.hpp"
#include "MCGIDI_sampling.hpp"
#include <limits>

#include <iostream>
#include <iomanip>
#include <functional>
#include "PTMaterialDecomposer.hh"
#include "PTGIDIModel.hh"

#include "PTGIDIFactory.hh"

Prompt::GIDIFactory::GIDIFactory()
:m_ctrdata(Singleton<Prompt::GidiSetting>::getInstance()),
m_pops(nullptr), m_map(nullptr), m_particles(nullptr), m_construction(nullptr),
m_constructionPhotonNuclear(nullptr), m_constructionPhotonAtomic(nullptr),
m_domainHash(nullptr), m_smr1(nullptr), m_initialised(false), m_photonParticleAdded(false)
{}

void Prompt::GIDIFactory::ensureInitialised() const
{
  if( m_initialised )
    return;

  m_pops = new PoPI::Database( m_ctrdata.getGidiPops());
  m_map = new GIDI::Map::Map( m_ctrdata.getGidiMap(), *m_pops );
  m_particles = new GIDI::Transporting::Particles();
  m_construction = new GIDI::Construction::Settings ( GIDI::Construction::ParseMode::all,
                                                GIDI::Construction::PhotoMode::nuclearAndAtomic );
  // the photon isotope pass wants photonuclear data only and the element
  // pass photo-atomic data only: one pass each keeps the atomic cross
  // section registered exactly once (a nuclearAndAtomic isotope pass plus
  // an element pass double-counts it)
  m_constructionPhotonNuclear = new GIDI::Construction::Settings ( GIDI::Construction::ParseMode::all,
                                                GIDI::Construction::PhotoMode::nuclearOnly );
  m_constructionPhotonAtomic = new GIDI::Construction::Settings ( GIDI::Construction::ParseMode::all,
                                                GIDI::Construction::PhotoMode::atomicOnly );
  m_domainHash = new MCGIDI::DomainHash ( 4000, 1e-8, 20 );

  GIDI::Transporting::Particle neutron(PoPI::IDs::neutron, GIDI::Transporting::Mode::MonteCarloContinuousEnergy);
  m_particles->add(neutron);

  m_initialised = true;
}

void Prompt::GIDIFactory::ensurePhotonParticle() const
{
  ensureInitialised();
  if( m_photonParticleAdded )
    return;

  GIDI::Transporting::Particle photon( PoPI::IDs::photon, GIDI::Transporting::Mode::MonteCarloContinuousEnergy );
  m_particles->add( photon );
  m_photonParticleAdded = true;
}

Prompt::GIDIFactory::~GIDIFactory()
{
  delete m_pops;
  delete m_map;
  delete m_particles;
  delete m_construction;
  delete m_constructionPhotonNuclear;
  delete m_constructionPhotonAtomic;
  delete m_domainHash;
}

int Prompt::GIDIFactory::getHashID(double energy) const
{
  ensureInitialised();
  return m_domainHash->index(energy);
}

bool Prompt::GIDIFactory::available() const
{
  return true;
}

const PoPI::Database &Prompt::GIDIFactory::getPoPs() const
{
  ensureInitialised();
  return *m_pops;
}

std::shared_ptr<MCGIDI::Protare>
Prompt::GIDIFactory::cachedProtare(const std::string &name, const std::string &label, const char *mode,
                                   bool gammaTransport, bool sampleNTP,
                                   const std::function<std::shared_ptr<MCGIDI::Protare>()> &builder) const
{
  // Identity is canonical, not lexical: PoPI resolves aliases (final) and
  // hands back the integer (Z, A, metastable index), so the same nuclide
  // reached under a different name still shares one entry instead of
  // duplicating the (large) MCGIDI tables. Ids PoPI does not know keep a
  // distinct, name-carrying entry (the builder below then reports them
  // missing). Note the Base overloads: the particleZ(Database, string)
  // convenience overload dynamic_casts to Particle and throws bad_cast for
  // chemical elements.
  int Z = -1, A = 0, ms = 0;
  if( m_pops->exists( name ) ) {
    PoPI::Base const &base = m_pops->get<PoPI::Base>( m_pops->final( name ) );
    Z = PoPI::particleZ( base );
    A = PoPI::particleA( base );
    ms = PoPI::particleMetaStableIndex( base );
  }
  ProtareCacheKey key{ Z, A, ms, label, mode, gammaTransport, sampleNTP };
  if( Z < 0 )
    key.label = name + "@" + label;
  auto iter = m_protareCache.find( key );
  if( iter != m_protareCache.end() ) {
    std::cout << "Reusing the cached MCGIDI tables for isotope " << name
              << " (" << mode << ", temperature label " << label << ")" << std::endl;
    return iter->second;
  }
  auto protare = builder();
  m_protareCache.emplace( std::move(key), protare );
  return protare;
}

// todo: fixme: factory should pass the shared pointer of ncrystal sca to the gidi model, alone with the elastic the hold. below the threslhold replace the xs of mt2, but cache the  total xs calculate by mt2 for sampling reaction. if mt2 is leaked at the end, use the mcstas for secondary.
// after that manager should cache all shared pointed gidi models. the isotope should be re used by a key name, the ncsca should be updated.

std::vector<std::shared_ptr<Prompt::GIDIModel>> Prompt::GIDIFactory::createNeutronGIDIModel(const std::vector<Prompt::IsotopeComposition> &vecComp,
double temperature, double bias, double elasticThreshold, bool gammaTransport, bool sampleNTP,
double minEKin, double maxEKin) const
{
  std::vector<std::shared_ptr<GIDIModel>> gidimodels;

  ensureInitialised();
  if(gammaTransport)
    ensurePhotonParticle();

  // auto gdcomp = new GIDI::ProtareComposite( *m_construction);
  // auto mcpro_comp = new MCGIDI::ProtareComposite();

  // fixme: make shared pointer map to cache MCGIDI::ProtareSingle for repeated isotopes
  // the key should be the label (i.e. iter->heatedCrossSection()) plus the  isotope name
  for(const auto& isotope : vecComp)
  {
    //fixme:: factory that can cache the model from isotope info
    const std::string &name = isotope.name;
    double frac = isotope.frac;

    if(!m_map->isProtareAvailable( PoPI::IDs::neutron, name))
    {
      PROMPT_THROW2(DataLoadError, "GIDIFactory createNeutronGIDIModel failed to load data for " << name << ". ");
    }
    auto *gidiprotare =  (GIDI::Protare *) m_map->protare( *m_construction, *m_pops, "n", name, "", "", true, true ) ;
    // gdcomp->append(gidiprotare);

    // making sure the gidiprotare is single, so that projectileEnergyMax can be called
    pt_assert_always(gidiprotare->numberOfProtares()==1);

    std::cout << "Using data file " << gidiprotare->realFileName() << std::endl;

    auto delay = GIDI::Transporting::DelayedNeutrons::on;
    if( !gidiprotare->isDelayedFissionNeutronComplete() ) 
    {
        std::cout << "WARNING: delayed neutron data for "<< name<< " are incomplete and are not included." << std::endl;
        delay = GIDI::Transporting::DelayedNeutrons::off;
    }
    else
      std::cout << "Delayed neutron data for "<< name<< " are included." << std::endl;

    GIDI::Transporting::Settings incompleteParticlesSetting( gidiprotare->projectile().ID(),  delay);
    std::set<std::string> incompleteParticles;
    gidiprotare->incompleteParticles( incompleteParticlesSetting, incompleteParticles );
    std::cout << "# List of incomplete particles:";
    for( auto iter = incompleteParticles.begin(); iter != incompleteParticles.end(); ++iter ) {
        std::cout << " " << *iter;
    }
    std::cout << std::endl;

    GIDI::Styles::TemperatureInfos tempinfos = gidiprotare->temperatures();
    std::vector<double> availableTemp;
    for( GIDI::Styles::TemperatureInfos::const_iterator iter = tempinfos.begin(); iter != tempinfos.end(); ++iter ) {
      availableTemp.push_back(iter->temperature().value()*Unit::MeV / const_boltzmann);
      std::cout << "label = " << iter->heatedCrossSection() << "  temperature = " << availableTemp.back() << " Kelvin" << std::endl;
    }

    // find the nearest temperature 
    auto findNearestTemperatureIndex = [&](const std::vector<double>& availableTemp) {
        if (availableTemp.empty()) return static_cast<size_t>(-1);

        double minDiff = std::abs(availableTemp[0] - temperature);
        size_t nearestIndex = 0;

        for (size_t i = 0; i < availableTemp.size(); ++i) {
            double temp = availableTemp[i];
            double diff = std::abs(temp - temperature);
            if (diff < minDiff) {
                minDiff = diff;
                nearestIndex = i;
            }
        }
        return nearestIndex;
    };


    GIDI::Styles::TemperatureInfos selectedTempinfo;
    size_t nearestIndex = findNearestTemperatureIndex(availableTemp);
    selectedTempinfo.push_back(tempinfos[nearestIndex]);
    double selectedTemp_K = selectedTempinfo.back().temperature().value()*Unit::MeV / const_boltzmann;
    std::cout <<"The specified temperature is  " << temperature << " Kelvin, the selected data is at " << availableTemp[nearestIndex]  << " Kelvin\n";

    // The heated cross-section label pins the data file and temperature; it is
    // the cache key component that keeps two materials at different
    // temperatures from sharing the same MCGIDI tables.
    std::string selectedLabel( tempinfos[nearestIndex].heatedCrossSection() );

    MCGIDI::Transporting::MC MC ( *m_pops, gidiprotare->projectile().ID(),
                                  &gidiprotare->styles(), name, delay,
                                  static_cast<GIDI::ProtareSingle const &>( *gidiprotare).projectileEnergyMax());
    // MC.setNuclearPlusCoulombInterferenceOnly( true );
    MC.sampleNonTransportingParticles( sampleNTP );
    // MC.set_ignoreENDF_MT5(true);
    MC.want_URR_probabilityTables(true);
    MC.setThrowOnError( false );
    // MC.setZeroDepositionIfAllProductsTracked
    // MC.setWantTerrellPromptNeutronDistribution(true);
   

    if( gidiprotare->protareType() != GIDI::ProtareType::single ) {
        PROMPT_THROW(CalcError, "ProtareType must be single");
    }
    int numberOfReactions = gidiprotare->numberOfReactions();
    std::cout <<"Isotope " << name << " has " << numberOfReactions << " reactions in total"<< "\n";


    if(elasticThreshold>0.) {
      GIDI::ExcludeReactionsSet nonElastic, elastic;
      for( int i = 0; i < numberOfReactions; ++i )
      {
        // The type of ENDF_MT can be found at https://t2.lanl.gov/nis/endf/mts.html
        if(gidiprotare->reaction(i)->ENDF_MT()==2)
        {
          elastic.emplace(i);
          // break;
        }
        else
        {
          nonElastic.emplace(i);
        }
      }

      auto mcprotare = cachedProtare( name, selectedLabel, "elas", gammaTransport, sampleNTP, [&]() {
        auto protare = std::make_shared<MCGIDI::ProtareSingle>(*m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare), *m_pops, MC,
                                                                    *m_particles, *m_domainHash, selectedTempinfo, nonElastic );
        // customize neutron index to consistent with pdg, neutron_pdg = 2112
        protare->setUserParticleIndex(protare->projectileIndex(), const_neutron_pgd);
        if(gammaTransport)
          protare->setUserParticleIndex(protare->photonIndex(), const_photon_pgd);
        return protare;
      });

      gidimodels.emplace_back(std::make_shared<GIDIModel>(const_neutron_pgd, "n_"+name+"_elas", mcprotare, selectedTemp_K, bias, frac, elasticThreshold, maxEKin));


      auto mcProtare_nonelastic = cachedProtare( name, selectedLabel, "nonelas", gammaTransport, sampleNTP, [&]() {
        auto protare = std::make_shared<MCGIDI::ProtareSingle>(*m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare), *m_pops, MC,
                                                                    *m_particles, *m_domainHash, selectedTempinfo, elastic );
        protare->setUserParticleIndex(protare->projectileIndex(), const_neutron_pgd);
        if(gammaTransport)
          protare->setUserParticleIndex(protare->photonIndex(), const_photon_pgd);
        return protare;
      });

      gidimodels.emplace_back(std::make_shared<GIDIModel>(const_neutron_pgd, "n_"+name+"_nonelas", mcProtare_nonelastic, selectedTemp_K, bias, frac, 0, maxEKin));
    }
    else {
      auto mcprotare = cachedProtare( name, selectedLabel, "all", gammaTransport, sampleNTP, [&]() {
        GIDI::ExcludeReactionsSet excludeNone;
        auto protare = std::make_shared<MCGIDI::ProtareSingle>(*m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare), *m_pops, MC,
                                                                    *m_particles, *m_domainHash, selectedTempinfo, excludeNone );
        protare->setUserParticleIndex(protare->projectileIndex(), const_neutron_pgd);
        if(gammaTransport)
          protare->setUserParticleIndex(protare->photonIndex(), const_photon_pgd);
        return protare;
      });
      gidimodels.emplace_back(std::make_shared<GIDIModel>(const_neutron_pgd, "n_"+name+"_all", mcprotare, selectedTemp_K, bias, frac, elasticThreshold>0. ? elasticThreshold: minEKin, maxEKin));

    }
    delete gidiprotare;
  }

  return std::move(gidimodels);
}



std::vector<std::shared_ptr<Prompt::GIDIModel>> Prompt::GIDIFactory::createPhotonGIDIModel(const std::vector<Prompt::IsotopeComposition> & vecComp,
double bias, bool gammaTransport, bool sampleNTP,
double minEKinElastic, double maxEKinElastic, double minEKinNonelastic, double maxEKinNonelastic,
bool atomicPass) const
{
  std::vector<std::shared_ptr<GIDIModel>> gidimodels;

  ensureInitialised();
  if(gammaTransport)
    ensurePhotonParticle();

  // the isotope pass reads photonuclear data through the nuclearOnly
  // Construction, the element pass photo-atomic data through the atomicOnly
  // one (see the header); nuclearAndAtomic in a single pass would register
  // the atomic cross section twice (once per pass)
  GIDI::Construction::Settings &construction = atomicPass ? *m_constructionPhotonAtomic
                                                          : *m_constructionPhotonNuclear;

  // fixme: make shared pointer map to cache MCGIDI::ProtareSingle for repeated isotopes
  // the key should be the label (i.e. iter->heatedCrossSection()) plus the  isotope name
  for(const auto& isotope : vecComp)
  {
    const std::string &name = isotope.name; //.substr(0,1);
    double frac = isotope.frac;

    if(!m_map->isProtareAvailable( PoPI::IDs::photon, name))
    {

      std::cout << "WARNING: photon data for "<< name << " are are not found. The cross section for isotope: " << isotope << "\" is ignored.\n";
      continue;
      // PROMPT_THROW2(DataLoadError, "GIDIFactory createPhotonGIDIModel failed to load data for " << name);
    }
    auto *gidiprotare =  (GIDI::Protare *) m_map->protare( construction, *m_pops, "photon", name, "", "", true, true ) ;
    if(!gidiprotare)
    {
      // the map returns null when the half of the data this pass wants does
      // not exist (e.g. no photonuclear file for H1 in the isotope pass);
      // skipping keeps the rest of the material transportable
      std::cout << "WARNING: photon " << (atomicPass ? "atomic" : "nuclear") << " data for "
                << name << " could not be constructed. It is ignored.\n";
      continue;
    }
    std::cout << "Using data file " << gidiprotare->realFileName() << std::endl;
    auto delay = GIDI::Transporting::DelayedNeutrons::on;
    if( !gidiprotare->isDelayedFissionNeutronComplete() )
    {
        std::cout << "WARNING: delayed neutron fission data for "<< name<< " are incomplete and are not included." << std::endl;
        delay = GIDI::Transporting::DelayedNeutrons::off;
        pt_assert_always(false);
    }
    else
      std::cout << "Delayed neutron fission data for "<< name<< " are included." << std::endl;

    GIDI::Transporting::Settings incompleteParticlesSetting( gidiprotare->projectile().ID(),  delay);
    std::set<std::string> incompleteParticles;
    gidiprotare->incompleteParticles( incompleteParticlesSetting, incompleteParticles );
    std::cout << "# List of incomplete particles:";
    for( auto iter = incompleteParticles.begin(); iter != incompleteParticles.end(); ++iter ) {
        std::cout << " " << *iter;
    }
    std::cout << std::endl;

    GIDI::Styles::TemperatureInfos temperatures = gidiprotare->temperatures();
    for( GIDI::Styles::TemperatureInfos::const_iterator iter = temperatures.begin(); iter != temperatures.end(); ++iter ) {
      std::cout << "label = " << iter->heatedCrossSection() << "  temperature = " << iter->temperature().value() << std::endl;
    }


    // std::string label( temperatures[0].heatedCrossSection() ); // fixme: heated? gridded
    std::string label( temperatures[0].griddedCrossSection() );

    double selectedTemp_K = temperatures[0].temperature().value()*Unit::MeV / const_boltzmann;

    MCGIDI::Transporting::MC MC ( *m_pops, gidiprotare->projectile().ID(), &gidiprotare->styles(), label, delay, 150.0 );
    // MC.setNuclearPlusCoulombInterferenceOnly( true );
    MC.sampleNonTransportingParticles( sampleNTP );
    // MC.set_ignoreENDF_MT5(true);
    MC.want_URR_probabilityTables(false);
    MC.setThrowOnError( false );

    GIDI::ExcludeReactionsSet exc;
    int numberOfReactions = gidiprotare->numberOfReactions();
    std::cout <<"Isotope " << name << " has " << numberOfReactions << " reactions in total"<< "\n";

    // dispatch on the real type inside the cached build: the isotope pass
    // yields single photonuclear protares and the element pass single
    // photo-atomic protares, but a map entry may still hand back a composite.
    // Viewing a ProtareSingle as a ProtareComposite reference reads out of
    // bounds (the old segfault). The protare goes through the cache keyed by
    // the canonical (Z, A): two materials sharing an element share the one
    // set of photo-atomic tables instead of each building a copy.
    auto g_mcProtare = cachedProtare( name, label, atomicPass ? "atomic" : "nuclear",
                                      gammaTransport, sampleNTP, [&]() {
      std::shared_ptr<MCGIDI::Protare> protare;
      if( gidiprotare->protareType() == GIDI::ProtareType::composite )
        protare = std::make_shared<MCGIDI::ProtareComposite>( *m_smr1, static_cast<GIDI::ProtareComposite const &>( *gidiprotare ), *m_pops, MC,
                                                              *m_particles, *m_domainHash, temperatures, exc );
      else
      {
        pt_assert_always(gidiprotare->protareType() == GIDI::ProtareType::single);
        protare = std::make_shared<MCGIDI::ProtareSingle>( *m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare ), *m_pops, MC,
                                                           *m_particles, *m_domainHash, temperatures, exc );
      }
      // customize photon index to consistent with pdg, photon_pdg = 22
      protare->setUserParticleIndex(protare->photonIndex(), const_photon_pgd);
      return protare;
    });
    gidimodels.emplace_back(std::make_shared<GIDIModel>(const_photon_pgd, "g_"+name, g_mcProtare, selectedTemp_K, bias, frac, minEKinNonelastic, maxEKinNonelastic));

    delete gidiprotare;
  }


  return std::move(gidimodels);
}

