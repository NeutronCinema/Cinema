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

#include "PTActiveVolume.hh"
#include <VecGeom/navigation/BVHNavigator.h>
#include <VecGeom/navigation/NewSimpleNavigator.h>
#include "PTMirror.hh"
#include "PTStackManager.hh"
#include "PTNeutron.hh"

Prompt::ActiveVolume::ActiveVolume()
:m_geo(vecgeom::GeoManager::Instance()), 
m_currState(vecgeom::NavigationState::MakeInstance(0)),
m_nextState(vecgeom::NavigationState::MakeInstance(0))
{}

Prompt::ActiveVolume::~ActiveVolume()
{
  delete m_currState;
  delete m_nextState;
  std::cout << "Destructed ActiveVolume" << std::endl;
}


void Prompt::ActiveVolume::setup()
{
  if(m_currState)
    delete m_currState;
  if(m_nextState)
    delete m_nextState;

  m_currState = vecgeom::NavigationState::MakeInstance(m_geo.getMaxDepth());
  m_nextState = vecgeom::NavigationState::MakeInstance(m_geo.getMaxDepth());
}

// Prompt::VolumePhysicsScorer *getLogicalVolumePhysicsScorer(const vecgeom::LogicalVolume &lv)
// {
//   return (Prompt::VolumePhysicsScorer *)lv.GetUserExtensionPtr();
// }

bool Prompt::ActiveVolume::locateActiveVolume(const Vector &p) const
{
  m_currState->Clear();
  m_nextState->Clear();

  auto pv = vecgeom::GlobalLocator::LocateGlobalPoint(m_geo.GetWorld(),
                          *reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&p), *m_currState, true);

  if(!pv)
    std::cout << "particle at " << p << " is outside the world" << std::endl;
  return exitWorld() || !pv;
} 

bool Prompt::ActiveVolume::exitWorld() const
{
  return m_currState->IsOutside();
}

void Prompt::ActiveVolume::setupVolPhysAndGeoTrans()
{
  // Find next step
  // m_currState->Top() gets the placed volume
  m_matphysscor = Singleton<ResourceManager>::getInstance().getVolumePhysicsScorer(getVolumeID());
  if(!m_matphysscor)
    PROMPT_THROW2(CalcError, "Volume with id " << getVolumeID() << " is not found in the resource manager");

  // auto &geo = Singleton<GeoManager>::getInstance();
  // m_matphysscor = geo.getVolumePhysicsScorer(getVolumeID())->second;

  makeGeoTranslator(); //set up the global to local translator for this volume
}

bool Prompt::ActiveVolume::surfaceReaction(Particle &particle) const
{
  if(hasBoundaryPhyiscs())
  {
    m_matphysscor->surfaceProcess->sampleFinalState(particle);
    return true;
  }
  else
    return false;
}

void Prompt::ActiveVolume::getNormal(const Vector& pos, Vector &normal) const
{
  const auto &vegpos = *reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&pos);
  auto &vegnormal = *reinterpret_cast<vecgeom::Vector3D<vecgeom::Precision>*>(&normal);
   m_currState->Top()->Normal(vegpos, vegnormal);
}


const Prompt::GeoTranslator& Prompt::ActiveVolume::getGeoTranslator() const
{
  return m_translator;
}

size_t Prompt::ActiveVolume::getVolumeID() const
{
  return  m_currState->Top()->GetLogicalVolume()->id();
}

size_t Prompt::ActiveVolume::numSubVolume() const
{
  return  m_currState->Top()->GetLogicalVolume()->GetNTotal();
}

double Prompt::ActiveVolume::distanceToOut(const Vector& loc_pos, const Vector &loc_dir) const
{
  return  m_currState->Top()->DistanceToOut(*reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&loc_pos),
                                 *reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&loc_dir));
}


std::string Prompt::ActiveVolume::getVolumeName() const
{
  return  m_currState->Top()->GetLogicalVolume()->GetName();
}

const vecgeom::VPlacedVolume *Prompt::ActiveVolume::getVolume() const
{
  return  m_currState->Top();
}


void Prompt::ActiveVolume::makeGeoTranslator()
{
  auto& trans = m_translator.getTransformMatrix();
  m_currState->DeltaTransformation(1, trans); //this is the difference between the volume and the world
}


void Prompt::ActiveVolume::scoreEntry(Prompt::Particle &particle)
{
  if(m_matphysscor->entry_scorers.size())
  {
    for(auto &v:m_matphysscor->entry_scorers)
    {
      v->score(particle);
    }
  }
}

void Prompt::ActiveVolume::scoreSurface(Prompt::Particle &particle)
{
  auto localposition = particle.getPosition();   
  if(m_matphysscor->surface_scorers.size())
  {
    for(auto &v:m_matphysscor->surface_scorers)
    {
      v->score(particle);
    }
  }
}

void Prompt::ActiveVolume::scoreAbsorb(Prompt::Particle &particle)
{
  if(m_matphysscor->absorb_scorers.size())
  {
    for(auto &v:m_matphysscor->absorb_scorers)
    {
      v->score(particle);
    }
  }
}

void Prompt::ActiveVolume::scorePropagatePre(Prompt::Particle &particle)
{
  if(m_matphysscor->propagate_pre_scorers.size())
  {
    for(auto &v:m_matphysscor->propagate_pre_scorers)
    {
      v->score(particle);
    }
  }
}

void Prompt::ActiveVolume::scorePropagatePost(Prompt::Particle &particle)
{
  if(m_matphysscor->propagate_post_scorers.size())
  {
    for(auto &v:m_matphysscor->propagate_post_scorers)
    {
      v->score(particle);
    }
  }
}

void Prompt::ActiveVolume::scoreExit(Prompt::Particle &particle)
{
  if(m_matphysscor->exit_scorers.size())
  {
    for(auto &v:m_matphysscor->exit_scorers)
    {
      // to act along with the Prompt::ScorerRotatingObj::score method,
      // disable the effective energy and direction, by setting the direction to null
      if(particle.hasEffEnergy())
          particle.setEffDirection(Vector());
      else
      {
        v->score(particle);
      }
    }
  }
}

bool Prompt::ActiveVolume::hasBoundaryPhyiscs() const
{
  return m_matphysscor->surfaceProcess.use_count();
}

// Function to test if the ray intersects with the circular surface
bool intersec(const Prompt::Vector& pos, const Prompt::Vector& dir)
{
  const Prompt::Vector center{0,0,2200.}, nor{0,0,1}; 
  double m_r= 500;
  // Step 1: Calculate the dot product of the direction vector and the normal
  double dot = dir.dot(nor);

  // If the dot product is zero, the ray is parallel to the plane
  if (fabs(dot) < 1e-10) {
      return false; // No intersection since ray is parallel to the plane
  }

  // Step 2: Find the intersection point with the plane
  // The formula for t is (center - pos) dot nor / dir dot nor
  double t = (center - pos).dot(nor) / dot;

  // If t < 0, the intersection point is behind the ray's origin
  if (t < 0) {
      return false;
  }
    // Calculate the intersection point
  auto intersectionPoint = pos + dir * t;

  // Step 3: Check if the intersection point is within the circle radius
  // We project the intersection point onto the plane's circular area
  auto OC = intersectionPoint - center; // Vector from circle center to intersection point

  // Check if the distance from the center to the intersection point is within the radius
  return (OC.dot(OC) <= m_r * m_r);

}


bool Prompt::ActiveVolume::proprogateInAVolume(Particle &particle)
{
  if(!particle.isAlive())
    return false;
  
  const auto *p = reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&particle.getPosition());
  const auto *dir = reinterpret_cast<const vecgeom::Vector3D<vecgeom::Precision>*>(&particle.getDirection());
  double fmp(0.);
  double stepLength = m_matphysscor->bulkMaterialProcess->sampleStepLength(particle, fmp);

  //! updates m_nextState to contain information about the next hitting boundary:
  //!   - if a daugher is hit: m_nextState.Top() will be daughter
  //!   - if ray leaves volume: m_nextState.Top() will point to current volume
  //!   - if step limit > step: m_nextState == in_state
  //!   ComputeStep is essentialy equal to ComputeStepAndPropagatedState without the relaction part
  
  double step =  m_currState->Top()->GetLogicalVolume()
  ->GetNavigator()->ComputeStepAndPropagatedState(*p, *dir, stepLength, *m_currState, *m_nextState);

  bool sameVolume (m_currState->Top() == m_nextState->Top());
  
  if(stepLength < step)
    PROMPT_THROW2(CalcError, "stepLength < step " << stepLength << " " << step << "\n");

  const double resolution = 10*vecgeom::kTolerance; //this value should be in sync with the geometry tolerance

  // // Test if there is intersections
  // if(particle.getWeight()<1e-6)
  // {
  //   double targW = 1e-3;
  //   if(getRandNumber(nullptr)<targW)
  //   {
  //     particle.setWeight(targW);
  //   }
  //   else
  //   {
  //     particle.kill(Particle::KillType::BIAS);
  //     return false;
  //   }

  // }

  // if(particle.getDeposition() != -1. && particle.getPosition().mag()<70  && true && intersec(particle.getPosition(), particle.getDirection()))
  // {
  //   double distOut = distanceToOut(particle.getPosition(), particle.getDirection());

  //   // move neutron towards target by thr time of fmp, or to the boundary
  //   double thr = 3.;
  //   double moved_dist(0);
  //   if(distOut > thr*fmp)
  //   {
  //     // std::cout << "split " << particle << ", fmp " << fmp <<std::endl;
  //     double moved_dist = thr*fmp;
  //     auto ghost = Neutron(particle.getEKin(), particle.getDirection(), particle.getPosition());
  //     ghost.scaleWeight(particle.getWeight());
  //     if(fmp)
  //     {
  //       double scale = exp(-moved_dist/fmp);
  //       ghost.scaleWeight(scale);
  //       particle.scaleWeight(1-scale);
  //     }      
  //     ghost.moveForward(moved_dist);
  //     ghost.setDeposition(-1.); // hack for indicating this is just biased
  //     Singleton<StackManager>::getInstance().add(ghost, 2);
  //   }
  // }

  //Move next step
  particle.moveForward(sameVolume ? step : (step + resolution) );

  // Here is the state just before interaction
  scorePropagatePre(particle);

  m_matphysscor->bulkMaterialProcess->sampleFinalState(particle, step, !sameVolume);
  // #ifdef DEBUG_PTS
  //   std::cout << "Propagating in volume " << getVolumeName() << std::endl;
  // #endif

  scorePropagatePost(particle);
  
  
  if(!sameVolume)
  {
    #ifdef DEBUG_PTS
      std::cout << "Exiting volume " << getVolume()->GetName() 
      << " at " << particle.getPosition() 
      << " with energy " << particle.getEKin() << ";"
      << " weight " << particle.getWeight() << ";"
      << std::endl;
      std::cout << " " << std::endl;
    #endif
    scoreExit(particle);  //score exit before activeVolume changes, otherwise physical volume id and scorer id may be inconsistent.
    particle.moveForward(0); // clear step length in the particle, so that the next entry event with zero length
    std::swap(m_currState, m_nextState);
  }

  //sample the interaction at the location
  return sameVolume;

}
