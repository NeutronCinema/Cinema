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

#include "PTStackManager.hh"
#include "PTRandCanonical.hh"
#include <bits/stdc++.h> 

std::ostream& Prompt::operator << (std::ostream &o, const StackManager&s)
{
  o<<"********StackManager*****************\n";

  for(auto it=s.m_stack.begin();it!=s.m_stack.end();++it)
  {
    o<< *it->get() << std::endl;
    o<<"*************************\n";
  }
  return o;
}

Prompt::StackManager::StackManager(): m_unweighted(0)
{

}

void Prompt::StackManager::add(std::unique_ptr<Prompt::Particle> aParticle)
{
  m_stack.emplace_back(std::move(aParticle));
}

void Prompt::StackManager::addSecondary(const Prompt::Particle& aparticle, bool tosecond)
{
  if(tosecond)
  {
    //fixme it is here breaks the xs biasing mechanism and the weight is not corrected 
    m_stack_second.emplace_back(std::make_unique<Particle>(aparticle));
  }
  else
  {
    m_stack.emplace_back(std::make_unique<Particle>(aparticle));
    m_unweighted++;
  }
}
    
void Prompt::StackManager::scaleSecondary(int lastidx, double factor)
{
  m_stack[m_stack.size()-1-lastidx]->scaleWeight(factor);
  m_unweighted--;
}

void Prompt::StackManager::normaliseSecondStack(long unsigned num)
{
  if(m_stack_second.empty())
    PROMPT_THROW(CalcError, "secondary stack is empty");
  std::cout << "Normalising second stack (containing " << m_stack_second.size() << " particle )\n";
  int toAdd = num - m_stack_second.size();

  auto gen = Singleton<SingletonPTRand>::getInstance().getGenerator();

  
  if(toAdd < 0) // deleting
  {
    std::shuffle(m_stack_second.begin(), m_stack_second.end(), *gen);
    m_stack_second.resize(num);
  }
  else if(toAdd > 0)// adding random neutrons
  {

    std::uniform_int_distribution<> distrib(0, m_stack_second.size()-1);

    for(int i=0;i<toAdd;i++)
    {
      Particle ap = *m_stack_second[distrib(*gen)].get();
      m_stack_second.emplace_back(std::make_unique<Particle>(ap) );
    }
  }
  
  std::cout << "Done normalisation\n";
}

void Prompt::StackManager::swapStack()
{
  if(!m_stack.empty())
    PROMPT_THROW2(CalcError, "stack must be empty when swaping with the secondary stack");
  m_stack.swap(m_stack_second);
}


void Prompt::StackManager::add(const Prompt::Particle& aparticle, unsigned number)
{
  pt_assert_always(number);
  for(unsigned i=0;i<number;i++)
  {
    auto np = std::make_unique<Particle>(aparticle);
    m_stack.emplace_back(std::move(np));
  }
}


std::unique_ptr<Prompt::Particle> Prompt::StackManager::pop()
{
  if(m_unweighted)
  {
    PROMPT_THROW2(CalcError, "The weight of " << m_unweighted << " particles in the particle stack are not corrected");
  }
  auto p = std::move(m_stack.back());
  m_stack.pop_back();
  return std::move(p);
}


bool Prompt::StackManager::empty() const
{
  return m_stack.empty();
}
