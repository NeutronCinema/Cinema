#ifndef Prompt_ResourceManager_hh
#define Prompt_ResourceManager_hh

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
#include <map>
#include <unordered_map>
#include "PromptCore.hh"
#include "PTParticleProcess.hh"
#include "PTSurfaceProcess.hh"
#include "PTScorer.hh"
#include "PTSingleton.hh"
#include "PTHistBase.hh"
namespace Prompt {
    // A VolumePhysicsScorer should attach to a unique volume by volume idx
    // So VolMap is a map for all the volumes and its VolumePhysicsScorer 
    struct VolumePhysicsScorer { 
        //bulk physics
        std::shared_ptr<ParticleProcess> bulkMaterialProcess; 
        std::shared_ptr<SurfaceProcess> surfaceProcess; //surface physics
        std::vector< Scorer * >  scorers; /*Scorer*/

        std::vector< Scorer * >  surface_scorers;
        std::vector< Scorer * >  entry_scorers;
        std::vector< Scorer * >  propagate_pre_scorers;
        std::vector< Scorer * >  propagate_post_scorers;
        std::vector< Scorer * >  exit_scorers;
        std::vector< Scorer * >  absorb_scorers;
        
    };
    

    using VolMap = std::unordered_map<size_t, std::shared_ptr<VolumePhysicsScorer>>;
    using CfgPhysMap = std::unordered_map<std::string /*material name*/, std::shared_ptr<ParticleProcess> > ;
    using CfgScorerMap = std::unordered_map<std::string /*scorer name*/, Scorer * > ;
    using CfgSurfaceMap = std::unordered_map<std::string /*surface name*/, std::shared_ptr<SurfaceProcess> > ;

    class ResourceManager {
        public:
            void addNewVolume(size_t volID);
            bool hasVolume(size_t volID) const;
            void eraseVolume(size_t volID, bool check=true);

            std::shared_ptr<VolumePhysicsScorer> getVolumePhysicsScorer(size_t volID) const;
            std::string getLogicalVolumeScorerName(unsigned volID) const;
            const char* getLogicalVolumeMaterialName(unsigned volID) const;

            bool hasScorer(const std::string& cfg) const;
            CfgScorerMap::const_iterator findGlobalScorer(const std::string& cfg) const;
            CfgScorerMap::const_iterator endScorer() const;
            void addScorer(size_t volID, const std::string& cfg, Scorer *scorer=nullptr);
            void addSurface(size_t volID, const std::string& cfg);
            void cfgVolPhysics(size_t volID, const std::string& cfg);

            void clear();

            void writeScorer2Disk() const;
            Prompt::HistBase* getHist(const std::string& name); 

        private:
            friend class Singleton<ResourceManager>;
            ResourceManager();
            ~ResourceManager();

            VolMap m_volumes;
            CfgPhysMap m_globelPhysics;
            CfgScorerMap m_globelScorers;
            CfgSurfaceMap m_globelSurface;
    };

}
#endif
