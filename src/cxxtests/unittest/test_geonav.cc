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

#include "../doctest.h"

#include <iostream>
#include <memory>
#include "PTGeoLoader.hh"
#include "PTActiveVolume.hh"
#include "PTMath.hh"
#include "PTNeutron.hh"
#include "PTProgressMonitor.hh"

namespace pt = Prompt;

TEST_CASE("GeoLoader")
{
  //set the seed for the random generator
  pt::Singleton<pt::SingletonPTRand>::getInstance().setSeed(0);

  //load geometry
  auto &geoman = pt::Singleton<pt::GeoLoader>::getInstance();
  auto path = std::string(getenv("CINEMAPATH"));
  geoman.initFromGDML(path +"/gdml/first_geo.gdml");

  //create navigation manager
  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();


  size_t numBeam = 10;
  pt::ProgressMonitor moni("Prompt simulation", numBeam);

  for(size_t i=0;i<numBeam;i++)
  {
    std::cout << "i is " << i << std::endl;
    //double ekin, const Vector& dir, const Vector& pos
    pt::Neutron neutron(0.05 , {0.,0.,1.}, {0,0,-12000.*pt::Unit::mm});

    //! allocate the point in a volume
    activeVolume.locateActiveVolume(neutron.getPosition());
    while(!activeVolume.exitWorld() && neutron.isAlive())
    {
      //! first step of a particle in a volume
      // std::cout << activeVolume.getVolumeName() << " " << neutron.getPosition() << std::endl;
      activeVolume.setupVolPhysAndGeoTrans();

      //! the next while loop, particle should move in the same volume
      while(activeVolume.proprogateInAVolume(neutron))
      {
        if(neutron.isAlive())
          continue;
      }
    }
    moni.OneTaskCompleted();
  }
}
