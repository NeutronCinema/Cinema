#ifndef Prompt_ScorerFactory_hh
#define Prompt_ScorerFactory_hh

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
#include "PTSingleton.hh"
#include "PTHist1D.hh"
#include "PTHist2D.hh"
#include "PTScorer.hh"
namespace Prompt {

  enum AnalysisType {
    POSXY,
    VOLUME_FLUX,
    SURFACE_FLUX,
    SURFACE_CURRENT
  };

  class ScorerFactory  {
  public:
    //used in GeoManager::initFromGDML
    Scorer * createScorer(const std::string &cfg);
  private:
    std::map<const std::string, Scorer*> m_multiScatcorers;
    friend class Singleton<ScorerFactory>;
    ScorerFactory();
    ~ScorerFactory() = default;
    Scorer::ScorerType getPTS(const std::string& ptstateInStr) const;

  };
}

#endif
