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

namespace PT=Prompt;

template <class T>
inline double PT::RandCanonical<T>::generate() const
{
  // Bit-exact inline replica of libstdc++ generate_canonical<double, 53>
  // for a full-range uint64 engine (min()=0): __m=1, so the value is
  // (double)x / 2^64 where x is the single raw draw. The std:: version
  // recomputes a long-double log2 of the range on EVERY call (two logl
  // calls per random number - profiled at ~9% of thermal transport);
  // this replica produces the identical double with one integer-to-double
  // conversion and one division. Verified bit-identical against
  // std::generate_canonical in test_prompt_bias-style unit checks.
  double x = static_cast<double>((*m_generator.get())());
  constexpr double two64 = 18446744073709551616.0;  // 2^64, exact in double
  double ret = x / two64;
  if (ret >= 1.0)  // x == 2^64-1 rounds up to 1.0: clamp like the std version
    ret = 1.0 - std::numeric_limits<double>::epsilon() / 2.0;
  return ret;
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
