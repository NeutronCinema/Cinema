#ifndef Prompt_ModelCollection_hh
#define Prompt_ModelCollection_hh

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

#include <string>
#include <memory>
#include "PromptCore.hh"
#include "PTVector.hh"
#include "PTRandCanonical.hh"
#include "PTDiscreteModel.hh"


namespace Prompt {

  class PhysicsModel;

  struct XSCache {
    double ekin;
    Vector dir;
    std::vector<double> cache_xs;
    std::vector<double> bias;
    double selectedBias;
    double tot;
  };

  // This class is used to represent a collection of models.
  // The upstream should make should it is the right one for the material
  // Only discrete models for now.
  // This class processes the biasing factor

  class ModelCollection  {
  public:
    ModelCollection(int gpd);
    virtual ~ModelCollection();

    void addPhysicsModel(std::shared_ptr<DiscreteModel> model);
    const std::vector<std::shared_ptr<DiscreteModel>>& getModels() const 
    { return m_models; }

    double totalCrossSection(int pdg, double ekin, const Vector &dir) const;

    // fixme: absorptionCrossSection is very very slow 
    double absorptionCrossSection(int pdg, double ekin) const;
    double calculateWeight(double lengthRho, bool hitWall);
    const SampledResult&  pickAndSample(double ekin, const Vector &dir) const;
    int getSupportedGPD() const { return m_forgpd; }
    bool containOriented() const { return m_containsOriented; }

  private:
    bool sameInquiryAsLastTime(double ekin, const Vector &dir) const;

    std::vector<std::shared_ptr<DiscreteModel> > m_models;
    mutable XSCache m_cache;
    bool m_containsOriented;
    int m_forgpd;
    mutable Vector m_localdir;
    mutable SampledResult m_res;

    SingletonPTRand &m_rng;
  };
}

inline bool Prompt::ModelCollection::sameInquiryAsLastTime(double ekin, const Vector &dir) const
{
  return m_containsOriented ? (m_cache.ekin==ekin && m_cache.dir == dir) : m_cache.ekin==ekin;
}

#endif
