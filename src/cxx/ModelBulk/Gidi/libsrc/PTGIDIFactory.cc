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
m_pops(new PoPI::Database( m_ctrdata.getGidiPops())),
m_map (new GIDI::Map::Map( m_ctrdata.getGidiMap(), *m_pops )),
m_particles(new GIDI::Transporting::Particles()),
m_construction(new GIDI::Construction::Settings ( GIDI::Construction::ParseMode::all, 
                                              GIDI::Construction::PhotoMode::nuclearAndAtomic )),
m_domainHash(new MCGIDI::DomainHash ( 4000, 1e-8, 20 ) ),
m_smr1()
{ 
 
  GIDI::Transporting::Particle neutron(PoPI::IDs::neutron, GIDI::Transporting::Mode::MonteCarloContinuousEnergy);
  m_particles->add(neutron);
  if(m_ctrdata.getGammaTransport())
  {
    GIDI::Transporting::Particle photon( PoPI::IDs::photon, GIDI::Transporting::Mode::MonteCarloContinuousEnergy );
    m_particles->add( photon );
  }

  // m_pops->print(true);
  // m_pops->isMetaStableAlias();

  // std::cout << "!!!!!!!!!!!!!! "<<(*m_pops)["n"] << std::endl;
  // std::cout << (*m_pops)["He3"] << std::endl;
  // std::cout << (*m_pops)["O16"] << std::endl;
  // std::cout << (*m_pops)["O16"] << std::endl;

}

Prompt::GIDIFactory::~GIDIFactory()
{
  delete m_pops;
  delete m_map;
  delete m_particles;
  delete m_construction;
  delete m_domainHash;
}

int Prompt::GIDIFactory::getHashID(double energy) const
{
  return m_domainHash->index(energy);
}

bool Prompt::GIDIFactory::available() const
{
  return true;
}

// todo: fixme: factory should pass the shared pointer of ncrystal sca to the gidi model, alone with the elastic the hold. below the threslhold replace the xs of mt2, but cache the  total xs calculate by mt2 for sampling reaction. if mt2 is leaked at the end, use the mcstas for secondary.
// after that manager should cache all shared pointed gidi models. the isotope should be re used by a key name, the ncsca should be updated.

std::vector<std::shared_ptr<Prompt::GIDIModel>> Prompt::GIDIFactory::createNeutronGIDIModel(const std::vector<Prompt::IsotopeComposition> &vecComp, 
double temperature, double bias, double elasticThreshold, double minEKin, double maxEKin) const
{
  std::vector<std::shared_ptr<GIDIModel>> gidimodels;
  
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

   
    MCGIDI::Transporting::MC MC ( *m_pops, gidiprotare->projectile().ID(), 
                                  &gidiprotare->styles(), name, delay, 
                                  static_cast<GIDI::ProtareSingle const &>( *gidiprotare).projectileEnergyMax());
    // MC.setNuclearPlusCoulombInterferenceOnly( true );
    MC.sampleNonTransportingParticles( m_ctrdata.getGidiSampleNTP() );
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

      auto mcprotare = std::make_shared<MCGIDI::ProtareSingle>(*m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare), *m_pops, MC, 
                                                                  *m_particles, *m_domainHash, selectedTempinfo, nonElastic );
    // customize neutron index to consistent with pdg, neutron_pdg = 2112
      mcprotare->setUserParticleIndex(mcprotare->projectileIndex(), const_neutron_pgd);
      if(m_ctrdata.getGammaTransport())
        mcprotare->setUserParticleIndex(mcprotare->photonIndex(), const_photon_pgd);

      gidimodels.emplace_back(std::make_shared<GIDIModel>(const_neutron_pgd, "n_"+name+"_elas", mcprotare, selectedTemp_K, bias, frac, elasticThreshold, maxEKin));

      
      auto mcProtare_nonelastic = std::make_shared<MCGIDI::ProtareSingle>(*m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare), *m_pops, MC, 
                                                                  *m_particles, *m_domainHash, selectedTempinfo, elastic );

      mcProtare_nonelastic->setUserParticleIndex(mcProtare_nonelastic->projectileIndex(), const_neutron_pgd);
      if(m_ctrdata.getGammaTransport())
        mcProtare_nonelastic->setUserParticleIndex(mcProtare_nonelastic->photonIndex(), const_photon_pgd);

      gidimodels.emplace_back(std::make_shared<GIDIModel>(const_neutron_pgd, "n_"+name+"_nonelas", mcProtare_nonelastic, selectedTemp_K, bias, frac, 0, maxEKin));
    }
    else {
      GIDI::ExcludeReactionsSet excludeNone;
      auto mcprotare = std::make_shared<MCGIDI::ProtareSingle>(*m_smr1, static_cast<GIDI::ProtareSingle const &>( *gidiprotare), *m_pops, MC, 
                                                                  *m_particles, *m_domainHash, selectedTempinfo, excludeNone );
      mcprotare->setUserParticleIndex(mcprotare->projectileIndex(), const_neutron_pgd);
      if(m_ctrdata.getGammaTransport())
        mcprotare->setUserParticleIndex(mcprotare->photonIndex(), const_photon_pgd);
      gidimodels.emplace_back(std::make_shared<GIDIModel>(const_neutron_pgd, "n_"+name+"_all", mcprotare, selectedTemp_K, bias, frac, elasticThreshold>0. ? elasticThreshold: minEKin, maxEKin));

    }
    delete gidiprotare;
  }

  return std::move(gidimodels);
}



std::vector<std::shared_ptr<Prompt::GIDIModel>> Prompt::GIDIFactory::createPhotonGIDIModel(const std::vector<Prompt::IsotopeComposition> & vecComp, 
double bias, double minEKinElastic, double maxEKinElastic, double minEKinNonelastic, double maxEKinNonelastic) const
{
  std::vector<std::shared_ptr<GIDIModel>> gidimodels;

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
    auto *gidiprotare =  (GIDI::Protare *) m_map->protare( *m_construction, *m_pops, "photon", name, "", "", true, true ) ;
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
    MC.sampleNonTransportingParticles( m_ctrdata.getGidiSampleNTP() );
    // MC.set_ignoreENDF_MT5(true);
    MC.want_URR_probabilityTables(false);
    MC.setThrowOnError( false );

   
    // if( gidiprotare->protareType() != GIDI::ProtareType::single ) {
    //     PROMPT_THROW(CalcError, "ProtareType must be single");
    // }
    
    GIDI::ExcludeReactionsSet exc;
    int numberOfReactions = gidiprotare->numberOfReactions();
    std::cout <<"Isotope " << name << " has " << numberOfReactions << " reactions in total"<< "\n";

    auto g_mcProtare = std::make_shared<MCGIDI::ProtareComposite> ( *m_smr1, static_cast<GIDI::ProtareComposite const &>( *gidiprotare ), *m_pops, MC, 
                                                                *m_particles, *m_domainHash, temperatures, exc );
    // customize photon index to consistent with pdg, photon_pdg = 22
    g_mcProtare->setUserParticleIndex(g_mcProtare->photonIndex(), const_photon_pgd);
    gidimodels.emplace_back(std::make_shared<GIDIModel>(const_photon_pgd, "g_"+name, g_mcProtare, selectedTemp_K, bias, frac, minEKinNonelastic, maxEKinNonelastic));

    delete gidiprotare;
  }


  return std::move(gidimodels);
}

