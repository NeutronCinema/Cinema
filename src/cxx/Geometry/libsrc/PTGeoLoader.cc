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

#include "PTGeoLoader.hh"

#include <VecGeom/base/Config.h>
#include <VecGeom/management/GeoManager.h>
#include <VecGeom/gdml/Middleware.h>
#include <VecGeom/gdml/Frontend.h>
#include <VecGeom/volumes/PlacedVolume.h>

#include "PTScorerFactory.hh"
#include "PTGunFactory.hh"
#include "PTPhysicsFactory.hh"

#include "PTUtils.hh"
#include "PTNeutron.hh"
#include "PTVecGeom.hh"

Prompt::GeoLoader::GeoLoader()
:m_gun(nullptr), m_resman(Singleton<ResourceManager>::getInstance() )
{
}

Prompt::GeoLoader::~GeoLoader()
{
}

void Prompt::GeoLoader::setupNavigator()
{
  pt_initNavigators(true);
}

void Prompt::GeoLoader::initFromGDML(const std::string &gdml_file)
{
  vgdml::Parser p;
  const auto loadedMiddleware = p.Load(gdml_file.c_str(), false, 1);


  setupNavigator();


  if (!loadedMiddleware) PROMPT_THROW(DataLoadError, "failed to load the gdml file ");

  const auto &aMiddleware = *loadedMiddleware;
  auto volumeMatMap   = aMiddleware.GetVolumeMatMap();

  // Get User info, which includes primary generator definition
  auto uinfo = aMiddleware.GetUserInfo();
  for(const auto& info : uinfo)
  {
    std::cout << "Processing userinfo \"" <<  info.GetType() << "\": " ;
    std::cout << info.GetValue() << std::endl;

    if(info.GetType()=="PrimaryGun")
    {
      m_gun = Singleton<GunFactory>::getInstance().createGun(info.GetValue());
    }
  }


  // Get the volume auxiliary info
  const std::map<int, std::vector<vgdml::Auxiliary>>& volAuxInfo = aMiddleware.GetVolumeAuxiliaryInfo();
  std::cout << "Geometry contains "
            << volAuxInfo.size() << " entries of volum auxiliary info\n";
  

  auto &scorerFactory = Singleton<ScorerFactory>::getInstance();
  auto &geoManager = vecgeom::GeoManager::Instance();

  //geoManager.GetLogicalVolumesMap() returens std::map<unsigned int, LogicalVolume *>
  for (const auto &item : geoManager.GetLogicalVolumesMap())
  {

    auto &volume   = *item.second;
    const size_t volID = volume.id();
    std::cout << "Processing volume " << volume.GetName() << ", logical ID " << volID << std::endl;

    m_resman.addNewVolume(volID);

    // std::shared_ptr<VolumePhysicsScorer> vps(nullptr);
    // if(m_logVolID2physcorer.find(volID)==m_logVolID2physcorer.end())
    // {
    //   m_logVolID2physcorer.insert(std::make_pair(volID,  std::make_shared<VolumePhysicsScorer>()));
    //   vps = m_logVolID2physcorer[volID];
    // }
    // else
    // {
    //   PROMPT_THROW2(CalcError, "volume ID " << volID << " appear more than once")
    // }

    // 1. filter out material-empty volume
    auto mat_iter = volumeMatMap.find(volID);
    if(mat_iter==volumeMatMap.end()) //union creates empty virtual volume
    {
      // m_logVolID2physcorer.erase(volID);
      m_resman.eraseVolume(volID);
      // PROMPT_THROW(CalcError, "empty volume ")
      continue;
    }

    // 2. setup scorers
    if(volAuxInfo.size())
    {
      auto volAuxInfo_iter = volAuxInfo.find(volID);

      if(volAuxInfo_iter != volAuxInfo.end()) //it volume contains an AuxInfo info
      {

        std::cout << volume.GetName()<< ", +++++++++++++ volID " << volID << " contains volAuxInfo\n";
        const std::vector<vgdml::Auxiliary> &volAuxInfoVec = (*volAuxInfo_iter).second;
        auto volAuxInfoSize = volAuxInfoVec.size();
        std::cout << "volAuxInfoSize " << volume.GetName()  << " "
              << volAuxInfoSize << std::endl;

        for(const auto& info : volAuxInfoVec)
        {
          if (info.GetType() == "Scorer")
          {
            std::string scorercfg = info.GetValue();
            m_resman.addScorer(volID, scorercfg);

            // std::shared_ptr<Prompt::Scorer> scor = getScorer(info.GetValue());

            // if(scor.use_count()) //this scorer exist
            // {
            //   vps->scorers.push_back(scor);
            // }
            // else
            // {
            //   scor = scorerFactory.createScorer(info.GetValue(), volume.GetUnplacedVolume()->Capacity() );
            //   m_globelScorers[info.GetValue()]=scor;
            //   vps->scorers.push_back(scor);
              std::cout << "Scorer for vol name " << volume.GetName() <<" capacity "<<  volume.GetUnplacedVolume()->Capacity()  << std::endl;

            // }
            std::cout << "vol name " << volume.GetName() <<" type "<< info.GetType() << " value " << info.GetValue() << std::endl;
          }
          else if(info.GetType() == "SurfaceProcess")
          {
            std::cout << "SurfaceProcess: vol name " << volume.GetName() <<" type "<< info.GetType() << " value " << info.GetValue() << std::endl;
            // vps->surfaceProcess = Singleton<PhysicsFactory>::getInstance().createSurfaceProcess(info.GetValue());
            std::string surfaceCfg = info.GetValue();
            m_resman.addSurface(volID, surfaceCfg);
            std::cout << "Added SurfaceProcess " <<  info.GetValue() << std::endl;
          }
        }
      }
    }

    // 3. setup physics model, if it is not yet set
    const vgdml::Material& mat = mat_iter->second;

    m_resman.cfgVolPhysics(volID, mat.attributes.find("atomValue")->second);

    // auto matphys = getParticleProcess(mat.attributes.find("atomValue")->second);


    // if(matphys) //m_logVolID2physcorer not exist
    // {
    //   vps->bulkMaterialProcess=matphys;
    //   std::cout << "Set model " << mat.name
    //             << " for volume " << volume.GetName() << std::endl;
    // }
    // else
    // {
    //   std::cout << "Creating model " << mat.name << ", "
    //             << mat.attributes.find("atomValue")->second << volume.GetName() << std::endl;
    //   std::shared_ptr<ParticleProcess> model = std::make_shared<ParticleProcess>("neutron bulk physics"); //it should be a dict later
    //   m_globelPhysics.insert( std::make_pair<std::string, std::shared_ptr<ParticleProcess>>(std::string(mat.name) , std::move(model) ) );

    //   auto theNewPhysics = getParticleProcess(mat.name);
    //   const std::string &cfg = mat.attributes.find("atomValue")->second;
    //   theNewPhysics->cfgPhysicsModel(cfg);
    //   vps->bulkMaterialProcess=theNewPhysics;
    // }
    std::cout << "done physics " << std::endl;

    // m_resman.sortScorers(volID);
    // std::cout << "done physics scorers" << std::endl;

    std::cout << "volume name " << volume.GetName() << " (id = " << volume.id() << "): material name " << mat.name << std::endl;
    if (mat.attributes.size()) std::cout << "  attributes:\n";
    for (const auto &attv : mat.attributes)
      std::cout << "    " << attv.first << ": " << attv.second << std::endl;
    if (mat.fractions.size()) std::cout << "  fractions:\n";
    for (const auto &attv : mat.fractions)
      std::cout << "    " << attv.first << ": " << attv.second << std::endl;
    if (mat.components.size()) std::cout << "  components:\n";
    for (const auto &attv : mat.components)
      std::cout << "    " << attv.first << ": " << attv.second << std::endl;
  }
}


