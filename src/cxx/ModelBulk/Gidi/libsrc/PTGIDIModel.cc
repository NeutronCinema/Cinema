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

#include "PTGIDIModel.hh"
#include "PTGIDIFactory.hh"
#include <iostream>
#include <iomanip>
#include <functional>
#include "PTMaterialDecomposer.hh"

#include "PTNeutron.hh"
#include "PTPhoton.hh"

Prompt::GIDIModel::GIDIModel(int pgd, const std::string &name, std::shared_ptr<MCGIDI::Protare> mcprotare,
                             double temperature, 
                             double bias, double frac, double lowerlimt, double upperlimt)
:Prompt::DiscreteModel(name+"_Gidi_"+std::to_string(mcprotare->numberOfReactions()), pgd,
                      lowerlimt,
                      upperlimt, 
                      bias),
m_factory(Prompt::Singleton<Prompt::GIDIFactory>::getInstance()), 
m_launcher(Singleton<Launcher>::getInstance()),
m_mcprotare(mcprotare), 
m_urr_info(nullptr),
m_products(new MCGIDI::Sampling::StdVectorProductHandler()),
m_cacheEkin(0.), 
m_cacheGidiXS(0.),
m_temperature(temperature),
m_frac(frac),
m_input(new MCGIDI::Sampling::Input(false, MCGIDI::Sampling::Upscatter::Model::B) ),
m_hashIndex(0)
{ 

  MCGIDI::Vector<MCGIDI::Protare *> protares(1);
  protares[0]= m_mcprotare.get();
  m_urr_info = new MCGIDI::URR_protareInfos(protares);

  m_input->m_temperature = const_boltzmann*temperature/Unit::keV;   // In keV/k;

//     std::cout << "!!!!!!!!! m_input->m_temperature "  << m_input->m_temperature << std::endl;
// abort();
  int numberOfReactions = m_mcprotare->numberOfReactions();
  std::cout <<"Model " << m_modelName << " has " << numberOfReactions << " reactions"<< ". " ;
  std::cout <<"URR_domainMin " << m_mcprotare->URR_domainMin( )  << "MeV,  URR_domainMax " << m_mcprotare->URR_domainMax()<< "MeV.\n " ;

  for( int i = 0; i < numberOfReactions; ++i ) 
  {
    auto reaction =  m_mcprotare->reaction(i);
    // The type of ENDF_MT can be found at https://t2.lanl.gov/nis/endf/mts.html
    std::cout << "Reaction " << i << ", ENDF_MT=" << reaction->ENDF_MT()  << std::endl;
  }

  size_t totalBytes = m_mcprotare->memorySize();
  double sizeInMB = static_cast<double>(totalBytes)/(1024.0*1024.0);
  std::cout << "Estimated memory size of " << name << " instance: " << std::fixed << std::setprecision(5) << sizeInMB << " MB" << std::endl;

}

Prompt::GIDIModel::~GIDIModel()
{
  delete m_products;
  delete m_urr_info;
  delete m_input;
  
  std::cout << std::scientific;  
  std::cout<<"Destructing GIDIModel " << m_modelName << ", energy between [" << m_modelvalid.minEkin << ", " << m_modelvalid.maxEkin << "] eV";
  std::cout<< ", containing " << m_mcprotare->numberOfReactions() << " reactions" <<std::endl;
}



double Prompt::GIDIModel::getCrossSection(double ekin) const
{
  if(!m_modelvalid.ekinValid(ekin))
    return 0.;

  // ekin==m_cacheEkin is the case for thermal neutron elastic scattering 
  // or neutron crossing geometry to the volume of the same material
  if(ekin!=m_cacheEkin)
  {
    m_cacheEkin = ekin;
    double ekin_MeV = ekin*1e-6;
    m_hashIndex = m_factory.getHashID(ekin_MeV);
    if(m_mcprotare->hasURR_probabilityTables())  {
      if(ekin_MeV>m_mcprotare->URR_domainMin() && ekin_MeV<m_mcprotare->URR_domainMax()) 
      {
        m_urr_info->updateProtare(m_mcprotare.get(), ekin_MeV, getRandNumber, nullptr);
        m_cacheGidiXS = m_mcprotare->crossSection( *m_urr_info, m_hashIndex,  0, ekin_MeV );  
      }
      else
      {
        m_urr_info->updateProtare(m_mcprotare.get(), ekin_MeV, getZero, nullptr);
        m_cacheGidiXS = m_mcprotare->crossSection( *m_urr_info, m_hashIndex, m_input->m_temperature*1e-3, ekin_MeV );  
      }
    }
    else
      m_cacheGidiXS = m_mcprotare->crossSection( *m_urr_info, m_hashIndex, m_input->m_temperature*1e-3, ekin_MeV );  
  }
  return m_cacheGidiXS*m_bias*Unit::barn*m_frac;

}

double Prompt::GIDIModel::getCrossSection(double ekin, const Prompt::Vector &dir) const
{
  return getCrossSection(ekin);
}

const Prompt::SampledResult& Prompt::GIDIModel::sampleReaction(double ekin, const Vector &indir) const
{
  pt_assert_always(ekin==m_cacheEkin);
  const double ekin_MeV = ekin*1e-6;

  m_res.dispeared = false;

  std::vector<Particle> secondaries;

  int reactionIndex =  m_mcprotare->sampleReaction( *m_urr_info, m_hashIndex, m_input->m_temperature*1e-3, ekin_MeV, m_cacheGidiXS, getRandNumber, nullptr );

  MCGIDI::Reaction const *reaction = m_mcprotare->reaction( reactionIndex );
  pt_assert_always(m_mcprotare->threshold( reactionIndex ) < ekin_MeV);

  m_products->clear();
  reaction->sampleProducts( m_mcprotare.get(), ekin_MeV, *m_input, getRandNumber, nullptr, *m_products );
  pt_assert_always(m_input->m_reaction==reaction);

  double totalekin = 0;
  //   std::cout << "Reaction label: " << reaction->label().c_str() << " " << reaction->ENDF_MT()<<std::endl;
  for( std::size_t i = 0; i < m_products->size( ); i++ ) 
  {
    MCGIDI::Sampling::Product &aproduct = (*m_products)[i];
    // std::cout << reaction->ENDF_MT() << ", id " << i <<  ", aproduct " <<  aproduct.m_productIndex << ", " << aproduct.m_kineticEnergy*1e6;
    // std::cout << ", user product index: " << aproduct.m_userProductIndex << std::endl;
    if (aproduct.m_userProductIndex==const_neutron_pgd || aproduct.m_userProductIndex==const_photon_pgd) //neutron 11 or gamma 8
    {
     
      double gidi_ekin_ev = aproduct.m_kineticEnergy*1e6;
      Vector gidi_dir(aproduct.m_px_vx, aproduct.m_py_vy, aproduct.m_pz_vz);
      gidi_dir.normalise();

      totalekin += gidi_ekin_ev; // accumulate the energy that will be carried by a particle in the later simulation. 

      // make secondary
      const Particle & primary = m_launcher.getCurrentParticle(); 
      // m_launcher.copyCurrentParticle(primary); 
      if(aproduct.m_userProductIndex==const_neutron_pgd)
      {
        #ifdef DEBUG
          pt_assert_always(aproduct.m_productIndex==m_factory.getPoPs()["n"]);
        #endif
        Neutron sec(gidi_ekin_ev, gidi_dir, primary.getPosition());
        sec.setTime(primary.getTime() + aproduct.m_birthTimeSec);
        secondaries.push_back(sec);
      }
      else if(aproduct.m_userProductIndex==const_photon_pgd)
      {
        #ifdef DEBUG
          pt_assert_always(aproduct.m_productIndex==m_factory.getPoPs()["photon"]);
        #endif
        Photon sec(gidi_ekin_ev, gidi_dir, primary.getPosition());
        sec.setTime(primary.getTime() + aproduct.m_birthTimeSec);
        if(m_factory.getGidiSetting().getGammaTransport() )
        {
          secondaries.push_back(sec);
        }
      }
      else
        PROMPT_THROW(NotImplemented, "");
      
    }
    // if(m_input->m_frame == GIDI::Frame::centerOfMass && secondaries.size())
    //  std::cout << "ENDF MT" << reaction->ENDF_MT() <<  ", secondaries.size() " <<  secondaries.size() << ", ekin " << ekin << std::endl;
   
  }

  // correct for the directions
  if(secondaries.size())
  {
    double rotation_matrix[9];
    indir.findRotationMatrixFrom001(rotation_matrix);
    for(auto &sec: secondaries)
    {
      auto outdir = sec.getDirection().applyRotationMatrix(rotation_matrix);
      sec.setDirection(outdir);
      #ifdef DEBUG
        Vector temp{0,0,1};
        auto mu = temp.angleCos(sec.getDirection());
        pt_assert(indir.angleCos(outdir) == mu); 
      #endif
    }
  }

  
  // All secondary particles that are not simulated by prompt are contributed to the "energy deposition".
  // So, in the case that neutron is the only transporting particle, the energy deposition is calculated as incident neutorn kinetic energy 
  // plus Q and substrcut the total kinetic energy of all the tracking particles. 

  // printf("MT%d, deposition %e\n\n", reaction->ENDF_MT(), ekin+reaction->finalQ(ekin_MeV)*1e6-totalekin);

  m_res.deposition = ekin + reaction->finalQ(ekin_MeV)*1e6-totalekin;

  // Kill neutron in an absorption
  if(secondaries.empty())
  {
    // essentially killing the current active particle in the launcher
    m_res.dispeared = true;
  }
  else if(secondaries.size()==1 && secondaries[0].getPDG()==2112) /*If is neutron, treated as like the incoming neutron states changes*/
  {
    // essentially modifying the current active particle in the launcher
    //fixme: how about a reaction produce only one delayed particle? there is no way to treat the time in this function
    m_res.final_ekin = secondaries[0].getEKin();
    m_res.final_dir = secondaries[0].getDirection();
  }
  else
  {
    // essentially killing the current active particle in the launcher
    m_res.dispeared = true;

    for(const auto &p: secondaries)
    {
      if(m_factory.getGidiSetting().getEnableGidiPowerIteration() && p.getWeight()!=1.) 
      {
        PROMPT_THROW2(CalcError, "particle weight in gidi model is not unity.") 
      }
      if(m_factory.getGidiSetting().getGammaTransport() && p.getPDG()==22)
      {
        Singleton<StackManager>::getInstance().addSecondary(p, m_factory.getGidiSetting().getEnableGidiPowerIteration());
      }
      else if (p.getPDG()==2112)
      {
        Singleton<StackManager>::getInstance().addSecondary(p, m_factory.getGidiSetting().getEnableGidiPowerIteration());
      }
      
    }
  }
  return m_res;
}

