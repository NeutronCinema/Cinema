#ifndef Prompt_MCPLGun_hh
#define Prompt_MCPLGun_hh

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

#include "PTPrimaryGun.hh"
#include "PTMCPLParticleReader.hh"
#include "PTMCPLBinaryWrite.hh"

class KDSource ;
namespace Prompt {
  class MCPLGun : public PrimaryGun {
  public:
    MCPLGun(const Particle &aParticle, const std::string &fn);

    virtual ~MCPLGun(); 
    virtual std::unique_ptr<Particle> generate() override;
    virtual void sampleEnergy(double &ekin) override;
    virtual void samplePosDir(Vector &pos, Vector &dir) override;
    virtual double getParticleWeight() override;
    virtual double getTime() override;

    private:
      std::unique_ptr <MCPLParticleReader>  m_mcplread;
      KDSource *kdsource;
      mcpl_particle_t *m_particle;
      int m_mode;
      double m_w_crit;
      // MCPLBinaryWrite m_writer; // for testing
  };
}


#endif
