#ifndef Prompt_ActiveVolume_hh
#define Prompt_ActiveVolume_hh

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
#include <map>
#include "PromptCore.hh"
#include "PTSingleton.hh"
#include "PTParticle.hh"
#include <VecGeom/management/GeoManager.h>
#include "PTGeoLoader.hh"
#include "PTGeoTranslator.hh"
#include "PTScorer.hh"

namespace Prompt {

  class ActiveVolume  {
  public:
    void setup();
    
    // return false if the particle leaving a volume 
    // the current NavigationState is updated 
    bool proprogateInAVolume(Particle &particle);

    //locate the active volume, returns false if is outside the world
    bool locateActiveVolume(const Vector &p) const;
    bool exitWorld() const;
    void setupVolPhysAndGeoTrans();
    size_t getVolumeID() const;
    std::string getVolumeName() const;
    const vecgeom::VPlacedVolume *getVolume() const;

    void scoreEntry(Particle &particle);
    void scorePropagatePre(Particle &particle);
    void scorePropagatePost(Particle &particle);
    void scoreExit(Particle &particle);
    void scoreSurface(Particle &particle);
    void scoreAbsorb(Particle &particle);

    // It seems that the scorePropagate function have the same test as the following line, so commented
    // bool hasPropagateScorer() {return m_matphysscor->propagate_scorers.size(); };

    bool hasBoundaryPhyiscs() const;
    bool surfaceReaction(Particle &particle) const;

    //geotranslator and normal
    const GeoTranslator& getGeoTranslator() const;
    void makeGeoTranslator();

    // calculate the normal on the surface of the current vol;ume
    void getNormal(const Vector& pos, Vector &normal) const;
    const Scorer::ScorerType getCurrentTracingState(){return m_currentTracingState;}
    // return the number of subvolumes in the current physical volume
    size_t numSubVolume() const;

    // return the the distanceToOut 
    double distanceToOut(const Vector& loc_pos, const Vector &loc_dir) const;

  private:
    friend class Singleton<ActiveVolume>;
    ActiveVolume();
    ~ActiveVolume();

    void setCurrentTracingState(Scorer::ScorerType state);
    vecgeom::GeoManager &m_geo;
    std::shared_ptr<VolumePhysicsScorer> m_matphysscor;
    // NavigationState is NavStateIndex when VECGEOM_USE_NAVINDEX is enabled
    // It is NavStatePath otherwise
    vecgeom::NavigationState *m_currState, *m_nextState;
    GeoTranslator m_translator;
    Scorer::ScorerType m_currentTracingState;
  };

}

#endif
