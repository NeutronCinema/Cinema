#ifndef Prompt_GidiSetting_hh
#define Prompt_GidiSetting_hh

// #ifdef ENABLE_GIDI

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

namespace Prompt
{
  //fixme: add locker to disable modification when MC loop starts 
  class GidiSetting {
  public:
    double getGidiThreshold() const { return m_gidithreshold; };
    void setGidiThreshold(double t ) { m_gidithreshold = t; };

    bool getGidiSampleNTP() const { return m_gidiSampleNonTransportingParticles; };
    void setGidiSampleNTP(bool t ) { m_gidiSampleNonTransportingParticles = t; };

    bool getGammaTransport() const { return m_gidiEnableGamma; }
    void setGammaTransport(bool t) { m_gidiEnableGamma=t; }

    bool getEnableGidi() const { return m_enablegidi; }
    void setEnableGidi(bool t) { m_enablegidi=t; }

    bool getEnableGidiPowerIteration() const { return m_gidiPowerIteration; }
    void setEnableGidiPowerIteration(bool t) { m_gidiPowerIteration=t; }

    std::string getGidiPops() const {return m_gidipops;};
    std::string getGidiMap() const {return m_gidimap;};
    
    void setGidiPops(const std::string &s ) { m_gidipops = s; };
    void setGidiMap(const std::string &s ) { m_gidimap = s; };

    std::string getDataPath() const {
      const char* envVar = std::getenv("CINEMAPATH");
      if (envVar!= nullptr) {
          std::string cinemaPath(envVar);
          cinemaPath += "/external/ptdata/";
          std::cout << "getDataPath" << cinemaPath << std::endl;
          return cinemaPath;
      } else 
          return "";
    }

  private:
    friend class Singleton<GidiSetting>;
    GidiSetting();
    ~GidiSetting();

    bool m_enablegidi;
    double m_gidithreshold;
    bool m_gidiSampleNonTransportingParticles;
    bool m_gidiEnableGamma;
    bool m_gidiPowerIteration;
    std::string m_gidipops, m_gidimap;    
  };


}
#endif
// #endif
