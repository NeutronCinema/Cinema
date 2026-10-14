#ifndef Prompt_Scorer_hh
#define Prompt_Scorer_hh

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

#include "PromptCore.hh"
#include "PTParticle.hh"
#include "PTHist1D.hh"
#include "PTHist2D.hh"

namespace Prompt {
  class ActiveVolume;
  class Scorer {
  public:
    // PEA, PROPAGATE-EXIT-ABSORB, to account for everything inside a volume
    // PROPAGATE_PRE & PROPAGATE_POST for particle state before and after interaction, respectively
    enum class ScorerType {SURFACE, ENTRY, PROPAGATE_PRE, PROPAGATE_POST, EXIT, PEA_PRE, PEA_POST, ABSORB};
  public:
    Scorer(const std::string& name, ScorerType type, unsigned int pdg, int groupid=0) ;  
    virtual ~Scorer() {std::cout<<"Destructing Scorer " << m_name <<std::endl;};
    const std::string &getName() const { return m_name; }
    ScorerType getType() const { return m_type; }
    virtual void score(Particle &particle) = 0;
    virtual void save_mcpl() = 0;
    virtual const HistBase* getHist() const = 0 ; 

    /**
     * @brief Check if the arriving particle matches the particle type that the scorer desired.
     * 
     * @param particle arriving particle 
     * @return true if match. Note: if particle pdg set as 0, always true, meaning that all particles that arrives are counted.
     * @return false if not match.
     */
    inline bool rightParticle(const Particle &particle) const; 
    inline bool rightGroup() const;
    virtual bool rightScorer(const Particle &particle) const {return rightParticle(particle) &&  rightGroup();};

  protected:
    const std::string m_name;
    const ScorerType m_type;
    const int m_groupid;
    ActiveVolume &m_activeVolume; 
    const unsigned m_pdg;
    
    int getVolumeGroupID() const;
    
  };

  class ScorerWithoutMixin : public Scorer {
  public:
    ScorerWithoutMixin(const std::string& name, Scorer::ScorerType type, std::unique_ptr<Hist1D> hist, unsigned int pdg, int groupid=0)
    : Scorer(name, type, pdg, groupid), m_hist(std::move(hist)) {};
    virtual ~ScorerWithoutMixin() {  }
    void save_mcpl() override { m_hist->save(m_name); }
    const HistBase* getHist() const override  { return dynamic_cast<const HistBase*>(m_hist.get()); }
  protected:
    std::unique_ptr<Hist1D> m_hist;
  };

}

#include "PTScorer.icc"


#endif
