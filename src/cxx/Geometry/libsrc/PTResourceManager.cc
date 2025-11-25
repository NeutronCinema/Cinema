#include "PTResourceManager.hh"
#include "PTScorerFactory.hh"
#include "PTPhysicsFactory.hh"
#include "PTRandCanonical.hh"

#include <VecGeom/management/GeoManager.h>


Prompt::ResourceManager::ResourceManager()
:  m_volumes(), m_globelPhysics(), m_globelScorers(), m_globelSurface()
{ }

Prompt::ResourceManager::~ResourceManager()
{ 
  // delete all scorers in m_globelScorers;


  auto iter = m_globelScorers.begin();
  while (iter != m_globelScorers.end()) {
    // std::cout << "[" << iter->first << "," << iter->second << "]\n";
    delete iter->second;
    ++iter;
  }


  // std::cout << "Simulation completed!\n";
  // std::cout << "Simulation created " << numParticleProcess() << " material physics\n";
  // std::cout << "There are " << numScorer() << " scorers in total\n";
}

void Prompt::ResourceManager::addNewVolume(size_t volID)
{
  if(hasVolume(volID))
    PROMPT_THROW2(CalcError, "volume ID " << volID << " already exist");

  auto vps = std::make_shared<VolumePhysicsScorer>();
  m_volumes.insert(std::make_pair(volID,  vps));
}

bool Prompt::ResourceManager::hasVolume(size_t volID) const
{
    return m_volumes.find(volID)==m_volumes.end() ? false : true;
}

const char* Prompt::ResourceManager::getLogicalVolumeMaterialName(unsigned volID) const
{
  std::string names;
  auto it = m_volumes.find(volID);
  if(it!=m_volumes.end())
  {
    return it->second->bulkMaterialProcess->getName().c_str();
  }
  return "";
}

std::string Prompt::ResourceManager::getLogicalVolumeScorerName(unsigned logid) const
{
  std::string names;
  auto it = m_volumes.find(logid);
  if(it!=m_volumes.end())
  {
    for(const auto &sc : it->second->scorers)
    {
      names += sc->getName() + " ";
    }
  }
  return names;
}

void Prompt::ResourceManager::eraseVolume(size_t volID, bool check)
{
  if(check)
  {
    if(!hasVolume(volID))
      PROMPT_THROW2(CalcError, "volume ID " << volID << " is not exist");
  }
  m_volumes.erase(volID);
}

std::shared_ptr<Prompt::VolumePhysicsScorer> Prompt::ResourceManager::getVolumePhysicsScorer(size_t volID) const
{
  auto it = m_volumes.find(volID);
  if(it != m_volumes.end())
  {
    return it->second;
  }
  else
  {
    return nullptr;
  }
}

bool Prompt::ResourceManager::hasScorer(const std::string& cfg) const
{
  return m_globelScorers.find(cfg) == m_globelScorers.end() ? false : true;
}

Prompt::CfgScorerMap::const_iterator Prompt::ResourceManager::findGlobalScorer(const std::string& cfg) const
{
  return m_globelScorers.find(cfg);
}

Prompt::CfgScorerMap::const_iterator Prompt::ResourceManager::endScorer() const
{
  return m_globelScorers.end();
}

void Prompt::ResourceManager::addScorer(size_t volID, const std::string& cfg, Scorer *scorer)
{
  auto it_vol = m_volumes.find(volID);
  if(it_vol == m_volumes.end())
      PROMPT_THROW2(CalcError, "addScorer: volume ID " << volID << " is not exist");

  auto it = m_globelScorers.find(cfg);

  // not exist
  Scorer *sc(nullptr);
  if(it==m_globelScorers.end())
  {

    auto &geoManager = vecgeom::GeoManager::Instance();
    auto volume = geoManager.FindLogicalVolume(volID);
    double capacity = volume->GetUnplacedVolume()->Capacity();
    if(scorer==nullptr)
    {
      auto &scorerFactory = Singleton<ScorerFactory>::getInstance();
      sc = scorerFactory.createScorer(cfg, capacity );
      m_globelScorers[cfg] = sc;
    }
    else
    {
      sc = scorer; 
      m_globelScorers[cfg] = sc;
    }

  }
  else
  {
    sc = it->second;
  }

  it_vol->second->scorers.push_back(sc);

  auto type = sc->getType();
  if(type==Scorer::ScorerType::ENTRY)
  {
    it_vol->second->entry_scorers.push_back(sc);
    std::cout << "Added ENTRY type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::PROPAGATE_PRE)
  {
    it_vol->second->propagate_pre_scorers.push_back(sc);
    std::cout << "Added PROPAGATE_PRE type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::PROPAGATE_POST)
  {
    it_vol->second->propagate_post_scorers.push_back(sc);
    std::cout << "Added PROPAGATE_POST type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::EXIT)
  {
    it_vol->second->exit_scorers.push_back(sc);
    std::cout << "Added EXIT type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::SURFACE)
  {
    it_vol->second->surface_scorers.push_back(sc);
    std::cout << "Added SURFACE type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::ABSORB)
  {
    it_vol->second->absorb_scorers.push_back(sc);
    std::cout << "Added ABSORB type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::PEA_PRE)
  {
    it_vol->second->propagate_pre_scorers.push_back(sc);
    it_vol->second->exit_scorers.push_back(sc);
    it_vol->second->absorb_scorers.push_back(sc);
    std::cout << "Added PEA_PRE type scorer: " << sc->getName() << std::endl;
  }
  else if(type==Scorer::ScorerType::PEA_POST)
  {
    it_vol->second->propagate_post_scorers.push_back(sc);
    it_vol->second->exit_scorers.push_back(sc);
    it_vol->second->absorb_scorers.push_back(sc);
    std::cout << "Added PEA_POST type scorer: " << sc->getName() << std::endl;
  }
  else
    PROMPT_THROW2(BadInput, "unknown scorer type " << static_cast<int>(type) );

  std::cout << "Done scorer " << cfg << std::endl;
}


void Prompt::ResourceManager::addSurface(size_t volID, const std::string& cfg)
{
  auto it_vol = m_volumes.find(volID);
  if(it_vol == m_volumes.end())
      PROMPT_THROW2(CalcError, "addScorer: volume ID " << volID << " is not exist");

  auto it = m_globelSurface.find(cfg);

  std::shared_ptr<SurfaceProcess> sc(nullptr);
  // not exist
  if(it==m_globelSurface.end())
  {
    sc = Singleton<PhysicsFactory>::getInstance().createSurfaceProcess(cfg);
    m_globelSurface[cfg] = sc;
  }
  else
  {
    sc = it->second;
  }

  it_vol->second->surfaceProcess = sc;
}

void Prompt::ResourceManager::cfgVolPhysics(size_t volID, const std::string& cfg)
{
  auto it_vol = m_volumes.find(volID);
  if(it_vol == m_volumes.end())
      PROMPT_THROW2(CalcError, "cfgVolPhysics: volume ID " << volID << " is not exist");

  auto it = m_globelPhysics.find(cfg);
  std::shared_ptr<ParticleProcess> sc(nullptr);
  // not exist
  if(it==m_globelPhysics.end())
  {
    sc = std::make_shared<ParticleProcess>(cfg);
    m_globelPhysics[cfg] = sc;

  }
  else
  {
    sc = it->second;
  }

  it_vol->second->bulkMaterialProcess = sc;
}

#include <VecGeom/management/GeoManager.h>

void Prompt::ResourceManager::clear()
{
  m_volumes.clear();
  m_globelPhysics.clear();
  m_globelScorers.clear();
  m_globelSurface.clear();
  vecgeom::GeoManager::Instance().Clear();
  Singleton<SingletonPTRand>::getInstance().resetSeed();
}

void Prompt::ResourceManager::writeScorer2Disk() const
{  
  for(auto it=m_volumes.begin();it!=m_volumes.end();++it)
  {
    for(const auto &v : it->second->scorers)
    {
      v->save_mcpl();
    }
  }
}

Prompt::HistBase* Prompt::ResourceManager::getHist(const std::string& name)  
{
  auto item = m_globelScorers.find(name);
  if(item!=m_globelScorers.end())
  {
    auto it = dynamic_cast<const HistBase*>(item->second->getHist());
    return const_cast<HistBase*>(it);
  }
  else
  {
    PROMPT_THROW2(CalcError, "Histogram not found, name: " <<name);
    return nullptr;
  }
}



