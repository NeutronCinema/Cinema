#ifndef Prompt_GIDI_hh
#define Prompt_GIDI_hh

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

#include <string>
#include <memory>
#include <set>

#include "PromptCore.hh"
#include "PTDiscreteModel.hh"
#include "PTSingleton.hh"
#include "PTGidiSetting.hh"
#include "PTLauncher.hh"


namespace MCGIDI
{
  class Protare;
  class URR_protareInfos;
  namespace Sampling
  {
    class StdVectorProductHandler;
    class Input;
  }
}  

namespace Prompt {
  class GIDIFactory;

  class GIDIModel  : public DiscreteModel {
  public:
    GIDIModel(int pgd, const std::string &name, std::shared_ptr<MCGIDI::Protare> mcprotare,
              double temperature, double bias=1.0, double frac=1.0, double lowerlimt = 0., double upperlimt = std::numeric_limits<double>::max());
    virtual ~GIDIModel();

    virtual double getCrossSection(double ekin) const override;
    virtual double getCrossSection(double ekin, const Vector &dir) const override;
    virtual const SampledResult& sampleReaction(double ekin, const Vector &dir) const override;

  protected:

    const GIDIFactory &m_factory;
    Launcher &m_launcher; 
    std::shared_ptr<MCGIDI::Protare> m_mcprotare;
    MCGIDI::URR_protareInfos *m_urr_info;
    mutable MCGIDI::Sampling::StdVectorProductHandler *m_products;
    //In fact, the xs is cached in the compoundmodel as well. But gidiplus need the un-biased xs to sample reaction MT,
    // hence cached here as well.
    mutable double m_cacheEkin, m_cacheGidiXS;  
    const double m_temperature, m_frac;
    MCGIDI::Sampling::Input *m_input;
    mutable int m_hashIndex;
  };

  
}

#endif
