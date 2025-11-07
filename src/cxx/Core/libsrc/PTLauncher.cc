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

#include "PTLauncher.hh"

#include "PTGeoLoader.hh"
#include "PTActiveVolume.hh"
#include "PTStackManager.hh"
#include "PTMath.hh"
#include "PTParticle.hh"
#include "PTProgressMonitor.hh"
#include "PTIsotropicGun.hh"
#include "PTNeutron.hh"
#include "PTGunFactory.hh"
#include "PTPythonGun.hh"
#include "NCrystal/NCrystal.hh"

class SingletonPTRandWrapper : public NCrystal::RNGStream{
public:
  SingletonPTRandWrapper()
  :NCrystal::RNGStream(), m_ptrng(Prompt::Singleton<Prompt::SingletonPTRand>::getInstance())
  {}
  virtual ~SingletonPTRandWrapper() override {}

  double actualGenerate() override {return m_ptrng.generate(); }

  //For the sake of example, we wrongly claim that this generator is safe and
  //sensible to use multithreaded (see NCRNG.hh for how to correctly deal with
  //MT safety, RNG states, etc.):
  bool useInAllThreads() const override { return true; }
private:
  Prompt::SingletonPTRand &m_ptrng;
};

   
Prompt::Launcher::Launcher()
: m_stackManager(Singleton<StackManager>::getInstance()),
m_activeVolume(Singleton<ActiveVolume>::getInstance())
{
  //This checks that the included NCrystal headers and the linked NCrystal
  //library are from the same release of NCrystal:
  NCrystal::libClashDetect();

  //set the generator for ncrystal
  NCrystal::setDefaultRNG(NCrystal::makeSO<SingletonPTRandWrapper>());
}


Prompt::Launcher::~Launcher()
{
  printLogo();
}

void Prompt::Launcher::setSeed(uint64_t seed) 
{ 
  Singleton<SingletonPTRand>::getInstance().setSeed(seed);
}


void Prompt::Launcher::loadGeometry(const std::string &geofile)
{
  //load geometry
  auto &geoman = Singleton<GeoLoader>::getInstance();
  geoman.initFromGDML(geofile.c_str());
  if(geoman.m_gun.use_count())
    m_gun = geoman.m_gun;
}

void Prompt::Launcher::setGun(const char* cfg)
{
  m_gun = Singleton<GunFactory>::getInstance().createGun(std::string(cfg));
}



void Prompt::Launcher::simOneEvent(bool recordTrj)
{
      //add a primary particle into the stack
    while(!m_stackManager.empty())
    {
      m_curParicle = m_stackManager.pop();
      auto *particle = m_curParicle.get();

      #ifdef DEBUG_PTS
        std::cout << "------ Start of event " << particle->getEventID() << " ------" << std::endl;
      #endif

      bool isFirstStep(true);

      // allocate the point in a volume,
      // returns ture when the particle is outside the world
      if(m_activeVolume.locateActiveVolume(particle->getPosition()))
        continue;

      if(recordTrj)
      {
        std::vector<Vector> tmp;
        tmp.reserve(m_trajectory.size());
        m_trajectory.swap(tmp);
      } 


      
      while(!m_activeVolume.exitWorld() && particle->isAlive() )
      {
        if(recordTrj)
        {
          m_trajectory.push_back(particle->getPosition());
        }

        m_activeVolume.setupVolPhysAndGeoTrans();
        // if it is not the first step, the particle should be at a boundary of a volume
        // do not consider the surface related scorers   
        if(!isFirstStep)
        {
          //fixme BUG: energy deposition and alike scores should be forbidden for surface type 
          m_activeVolume.scoreSurface(*particle);
          //if reflected, absorbed, transmitted
          if(m_activeVolume.surfaceReaction(*particle))
          {
            // std::cout << "reflection weight " << particle->getWeight() << "\n";
          }
          #ifdef DEBUG_PTS
            std::cout << "Entering volume " << m_activeVolume.getVolume()->GetName() 
            << " at " << particle->getPosition() 
            << " with energy " << particle->getEKin() << ";"
            << " weight " << particle->getWeight() << ";"
            << std::endl;
          #endif
          m_activeVolume.scoreEntry(*particle);
        }
        else {  //particle is initialised in this volume, but not penetrate the boundary to reach here 
        }

        //! within the next while loop, the particle is moving in the same volume
        while(m_activeVolume.proprogateInAVolume(*particle) )
        {
          // std::cout << "Tracing Volume ID " << m_activeVolume.getVolumeName() << std::endl;
          // score if any scorer is available
          // if(particle->isAlive() && m_activeVolume.hasPropagateScorer())
          // {
          //   #ifdef DEBUG_PTS
          //     std::cout << "Propagating in volume " << m_activeVolume.getVolumeName() << std::endl;
          //   #endif
          //   m_activeVolume.scorePropagate(*particle);
          // }
          if(recordTrj)
            m_trajectory.push_back(particle->getPosition());
        }
        // particle is moved
        isFirstStep=false; //set to false, so the surfaceReaction() can be triggered everytime particle reaching a boundary 

        // if(particle->isAlive())
        //   m_activeVolume.scoreExit(*particle);
      }

      if(!particle->isAlive())
      {
        if(particle->getKillType()==Particle::KillType::ABSORB)
        {
          #ifdef DEBUG_PTS
            std::cout << "Absorb in volume " << m_activeVolume.getVolume()->GetName() 
            << " at " << particle->getPosition() << ";"
            << " with energy " << particle->getEKin() << ";"
            << " weight " << particle->getWeight() << ";"
            << std::endl;
            std::cout << " " << std::endl;
          #endif
          m_activeVolume.scoreAbsorb(*particle);
        }
      }

      if(recordTrj)
      {
        m_trajectory.push_back(particle->getPosition());
      }
    }
}

size_t Prompt::Launcher::goWithSecondStack(uint64_t numParticle)
{
  m_stackManager.normaliseSecondStack(numParticle);
  m_stackManager.swapStack();
  std::cout << "Simulating " << m_stackManager.getNumParticleInStack()<< " particles using the swapped secondary stack.\n";
  simOneEvent(false);
  return m_stackManager.getNumParticleInSecondStack();
}

void Prompt::Launcher::go(uint64_t numParticle, double printPrecent, bool recordTrj, bool timer, bool save)
{
  // fixme: recordTrj should be done in the particle class with an optional switch.
  // to save 1. particle id, event id, the volume id, the physical id

  if(!m_gun.use_count())
  {
    std::cout << "PrimaryGun is not set, fallback to the neutron IsotropicGun\n";
    m_gun = std::make_shared<IsotropicGun>(Neutron(), 0.0253, Vector{0,0,0});
  }

  ProgressMonitor *moni=nullptr;
  if(timer)
    moni = new ProgressMonitor("Prompt simulation", numParticle, printPrecent);
  
  for(size_t i=0;i<numParticle;i++)
  {
    //add a primary particle into the stack
    m_stackManager.add(m_gun->generate());
    simOneEvent(recordTrj);
    if(timer)
      moni->OneTaskCompleted();
  }

  if(timer)
  {   
    delete moni;
  }

  if(save)
      Singleton<ResourceManager>::getInstance().writeScorer2Disk();

}


