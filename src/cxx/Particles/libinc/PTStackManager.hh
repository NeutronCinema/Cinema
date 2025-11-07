#ifndef Prompt_SingletonStackManager_hh
#define Prompt_SingletonStackManager_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
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

#include "PTSingleton.hh"
#include "PromptCore.hh"
#include "PTParticle.hh"
#include <ostream>

namespace Prompt {

  // The mechanism for treating secondaries:
  // int m_unweighted is added as a member of StackManager. 
  // It is increasing with the times of calling addSecondary to indicate the number
  // of secondary particles have been added to stack. The weights of the particles are 
  // scaled by Prompt::ParticleProcess::sampleFinalState for the cross section biasing. 
  // Before the correction is complete, StackManager::pop will forbit the action of  
  // poping a particle from the stack. 

  class StackManager {
  public:
    void add(std::unique_ptr<Particle> aparticle);
    void add(const Particle& aparticle, unsigned number);
    void addSecondary(const Prompt::Particle& aparticle, bool tosecond=false);

    std::unique_ptr<Particle> pop();
    bool empty() const;
    int getUnweightedNum() const { return m_unweighted; };
    void scaleSecondary(int lastidx, double factor);

    void normaliseSecondStack(long unsigned num);
    void swapStack();

    size_t getNumParticleInStack() const { return m_stack.size(); }
    size_t getNumParticleInSecondStack() const { return m_stack_second.size(); }

    friend std::ostream& operator << (std::ostream &, const StackManager&);

  private:
    friend class Singleton<StackManager>;
    StackManager();
    ~StackManager() = default;
    int m_unweighted;
    std::vector<std::unique_ptr<Particle> > m_stack;
    std::vector<std::unique_ptr<Particle> > m_stack_second;
  };

  std::ostream& operator << (std::ostream &, const StackManager&);
}

#endif
