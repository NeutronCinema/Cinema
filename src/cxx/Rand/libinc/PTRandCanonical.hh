#ifndef Prompt_RandCanonical_hh
#define Prompt_RandCanonical_hh

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

#include <functional>
#include <vector>
#include <memory>
#include <random>
#include <limits>

#include "PromptCore.hh"
#include "PTSingleton.hh"

//fixme: use ncrystal internal random generator
namespace Prompt {

  template <class T>
  class RandCanonical {
  public:
    RandCanonical(std::shared_ptr<T> gen);
    ~RandCanonical();
    double generate() const;
    void setSeed(uint64_t seed);
    T*  getGenerator() { return m_generator.get(); }
    uint64_t getSeed() { return m_seed; };
    void resetSeed();

  private:
    std::shared_ptr<T> m_generator;
    uint64_t m_seed;
    bool m_seedIsSet;
  };

  class SingletonPTRand : public RandCanonical<std::mt19937_64>  {
  private:
    friend class Singleton<SingletonPTRand>;
    SingletonPTRand(): RandCanonical<std::mt19937_64>(std::make_shared<std::mt19937_64>()) {}
    ~SingletonPTRand() {};
  };

}
#include "PTRandCanonical.tpp"


inline double getRandNumber(void *obj) 
{
  return Prompt::Singleton<Prompt::SingletonPTRand>::getInstance().generate();
}

inline double getZero(void *obj) 
{
  return 0.;
}




#endif
