#ifndef Prompt_PhysicsModel_hh
#define Prompt_PhysicsModel_hh

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

namespace Prompt {

  struct ModelValidity
  {
    int supportPGD;
    double minEkin, maxEkin;
    bool rightParticleType(int pgd) const
    {
      return supportPGD==pgd;
    }

    bool isValid(int pgd, double ekin) const
    {
      return pgd==supportPGD && (ekin > minEkin && ekin < maxEkin);
    }

    bool ekinValid(double ekin) const
    {
      return (ekin > minEkin && ekin < maxEkin);
    }

  };

  class PhysicsBase {
  public:
    PhysicsBase() = delete;
    PhysicsBase &operator = (const PhysicsBase&) = delete;

    PhysicsBase(const std::string &name, int gdp, double emin, double emax);
    virtual ~PhysicsBase() = default;
    const std::string &getName() { return m_modelName; }
    bool isOriented();
    bool isValid(int pdg, double ekin) {return m_modelvalid.isValid(pdg, ekin); }
    virtual double getCrossSection(double ekin) const ;
    virtual double getCrossSection(double ekin, const Vector &dir) const;

    Vector randIsotropicDirection() const;
    Vector randDirectionGivenScatterMu( double mu, const Vector& indir ) const;
  
  protected:
    std::string m_modelName;
    ModelValidity m_modelvalid;
    bool m_oriented;
    SingletonPTRand &m_rng;
  };

  struct SampledResult {
    double final_ekin;
    double deposition;
    Vector final_dir;
    bool dispeared;
    SampledResult() : final_ekin(0), deposition(0.0), final_dir{0.0, 0.0, 1.0}, dispeared(false) {}
  };

  class PhysicsModel : public PhysicsBase {
  public:
    PhysicsModel(const std::string &name);
    PhysicsModel(const std::string &name, unsigned gdp, double emin, double emax);
    virtual ~PhysicsModel() = default;

    bool isDispearingReaction() const
    { return m_res.dispeared; }


    virtual const SampledResult& sampleReaction(double ekin, const Vector &dir) const = 0;
  protected:
    mutable SampledResult m_res;
  };

}

#endif
