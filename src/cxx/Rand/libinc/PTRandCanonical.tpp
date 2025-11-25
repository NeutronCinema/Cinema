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

namespace PT=Prompt;

template <class T>
inline double PT::RandCanonical<T>::generate() const
{
  return std::generate_canonical<double,
         std::numeric_limits<double>::digits>(*(m_generator.get()));
}

template <class T>
PT::RandCanonical<T>::RandCanonical(std::shared_ptr<T> gen)
:m_generator(gen), m_seed(5489u), m_seedIsSet(false)
{
}

template <class T>
PT::RandCanonical<T>::~RandCanonical() = default;


template <class T>
inline void PT::RandCanonical<T>::setSeed(uint64_t seed)
{
  if(m_seedIsSet)
    PROMPT_THROW(BadInput, "seed is already set")
  m_seed = seed;
  m_generator.get()->seed(seed);
  m_seedIsSet=true;
}

template <class T>
inline void PT::RandCanonical<T>::resetSeed()
{
  m_seedIsSet = false;
}
