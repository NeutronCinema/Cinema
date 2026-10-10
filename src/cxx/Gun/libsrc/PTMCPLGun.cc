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

#include "PTMCPLGun.hh"


#ifdef __cplusplus
extern "C" {
#endif

#include "kdsource.h"

#ifdef __cplusplus
}
#endif


#include <filesystem>
#include <chrono> // fixme: workaround for  srand(time(NULL));

Prompt::MCPLGun::MCPLGun(const Particle &aParticle, const std::string &fn)
: PrimaryGun(aParticle), m_mode(std::filesystem::path(fn).extension()==".xml" ? true : false),
m_particle((mcpl_particle_t*)malloc(sizeof(mcpl_particle_t))), m_w_crit(0.)//, m_writer("pt_resampled")
{ 
  if(m_mode)
  {
    srand(static_cast<unsigned int>(std::chrono::high_resolution_clock::now().time_since_epoch().count())); //  fixme: work around for now, should use the random number stream of prompt
    kdsource = KDS_open(fn.c_str());
    m_w_crit = KDS_w_mean(kdsource, 1000, NULL);
  }
  else
  {
    free(m_particle);
    m_mcplread = std::make_unique<MCPLParticleReader>(fn, true);
  }

}

Prompt::MCPLGun::~MCPLGun() 
{
  if(m_mode)
  {
    KDS_destroy(kdsource);
    free(m_particle);
  }
}

std::unique_ptr<Prompt::Particle> Prompt::MCPLGun::generate()
{
  // m_particle is read in different modes
  if(m_mode)
  {
    KDS_sample2(kdsource, m_particle, true, m_w_crit, NULL, 1);
  }
  else
  {
    if(! m_mcplread->readOneParticle())
      PROMPT_THROW(CalcError, "failed to read particle from the mcpl file");
    m_particle = m_mcplread->getParticle();      
  }

  if(getPDG() != m_particle->pdgcode)
    PROMPT_THROW2(CalcError, "sampled particle is not the same as type of the gun");

  //reading and converting unit 
  m_ekin = m_particle->ekin*Unit::MeV;
  m_ekin0 = m_ekin;

  m_pos.set(m_particle->position[0]*Unit::cm, 
            m_particle->position[1]*Unit::cm,
            m_particle->position[2]*Unit::cm);

  m_dir.set(m_particle->direction[0], 
             m_particle->direction[1],
             m_particle->direction[2]);
    
  m_eventid++;
  m_weight = m_particle->weight;
  m_alive = true;
  m_time = m_particle->time*Unit::ms;
  auto p = std::make_unique<Particle>(*this);
  // std::cout << *p.get() << std::endl;
  // m_writer.write(*p.get());

  return std::move(p);
}


void Prompt::MCPLGun::sampleEnergy(double &ekin)
{
  PROMPT_THROW(NotImplemented, "This method is forbidden in this class");
}

void Prompt::MCPLGun::samplePosDir(Vector &pos, Vector &dir) 
{
  PROMPT_THROW(NotImplemented, "This method is forbidden in this class");
}

double Prompt::MCPLGun::getParticleWeight()
{
  PROMPT_THROW(NotImplemented, "This method is forbidden in this class");
}

double Prompt::MCPLGun::getTime() 
{
  PROMPT_THROW(NotImplemented, "This method is forbidden in this class");
}



