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

#include "PTPhysicsFactory.hh"
#include "PTUtils.hh"
#include "PTCfgParser.hh"
#include "PTMirror.hh"
#include "PTDiskChopper.hh"
#include "PTEnergyReflector.hh"

// NCrystal for MatCfg/createInfo in nccalNumDensity/showNCComposition; the
// concrete model classes used to live here too but moved behind the plugin
// registry (ModelBulk/NCrystal + builtins), so the host no longer links them
#include "NCrystal/NCrystal.hh"

bool Prompt::PhysicsFactory::rawNCrystalCfg(const std::string &cfgstr)
{
  try
  {
    auto &ps = Singleton<CfgParser>::getInstance();
    CfgParser::StringCfg cfg = ps.parse(cfgstr);
  }
  catch (Prompt::Error::BadInput& e)
  {
    return true;
  }
  return false;

}




double Prompt::PhysicsFactory::nccalNumDensity(const std::string &cfgstr)
{
  std::string nccfgstr = cfgstr;
  if(!rawNCrystalCfg(cfgstr))
  {
    CfgParser::StringCfg cfg = Singleton<CfgParser>::getInstance().parse(cfgstr);
    if(!cfg.getStringIfExist("nccfg", nccfgstr))
      PROMPT_THROW(BadInput, "NCrystal cfg string is not found");
  }

  // fixme: encounter what():  Assertion failure: isSingleIsotope() from NCrystal::AtomData::A when 
  // the material is LiquidHeavyWaterD2O_T293.6K.ncmat
  // showNCComposition(nccfgstr); 

  // FIXME: issue #41
  NCrystal::MatCfg matcfg(nccfgstr);
  auto info = NCrystal::createInfo(matcfg);
  if(info->hasNumberDensity())
    return info->getNumberDensity().get() / Unit::Aa3;
  else
  {
    PROMPT_THROW2(CalcError, "material has no number density " << nccfgstr);
    return 0.;
  }
}

void Prompt::PhysicsFactory::showNCComposition(const std::string &nccfgstr)
{
  NCrystal::MatCfg matcfg(nccfgstr);
  auto info = NCrystal::createInfo(matcfg);
  const NCrystal::Info::Composition & comp = info->getComposition();


  for(const NCrystal::Info::CompositionEntry &v : comp)
  {
    double frac = v.fraction;
    const auto& atom = v.atom.data();
    std::cout << atom.elementName() << ": A " << atom.A() << ", Z " << atom.Z() << ", fraction " << frac << std::endl;
  }

}


std::shared_ptr<Prompt::SurfaceProcess> Prompt::PhysicsFactory::createSurfaceProcess(const std::string &cfgstr)
{
  std::cout << "Parsing config string for a physics model: \n";

  auto &ps = Singleton<CfgParser>::getInstance();
  auto cfg = ps.parse(cfgstr);
  std::cout << "Parsed cfg: \n";
  cfg.print();

  std::string physDef = cfg.find("physics");

  if(physDef.empty())
  {
    PROMPT_THROW2(BadInput, "Config string " << cfgstr << " does not define the scorer by the key \"physics\" ")
  }
  else
  {
    std::shared_ptr<SurfaceProcess> phy;

    if(physDef == "Mirror")
    {

      // example cfg
      // ""physics=Mirror; m=1.0; threshold=1e-5""

      // where the m value is 1 by default//
      // the default threshold for the Russian roulette biasing method to be activated

      int parCount = 3;

      // optional parameters
      double m = 1;
      if(!cfg.getDoubleIfExist("m", m))
        parCount--;

      double threshold =  1e-3;
      if(!cfg.getDoubleIfExist("threshold", threshold))
        parCount--;

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Cfgstr for a mirror physics is missing or with extra config parameters " << cfg.size() << " " << parCount );
      }

      phy = std::make_shared<Mirror>(m, threshold);
    }
    else if(physDef=="DiskChopper")
    {
      // DiskChopper(double centre_x_mm, double centre_y_mm,  
      //       double theta0_deg, double r_mm, double phase_deg, double rotFreq_Hz, unsigned n);
      int parCount = 6;

      // optional parameters
      // double centre_x_mm = 0;
      // if(!cfg.getDoubleIfExist("centre_x_mm", centre_x_mm))
      //   parCount--;

      // double centre_y_mm = 0;
      // if(!cfg.getDoubleIfExist("centre_y_mm", centre_y_mm))
      //   parCount--;
      double theta0_deg = 0;
      if(!cfg.getDoubleIfExist("theta0", theta0_deg))
        parCount--;

      double r_mm = 0;
      if(!cfg.getDoubleIfExist("r", r_mm))
        parCount--;

      double phase_deg = 0;
      if(!cfg.getDoubleIfExist("phase", phase_deg))
        parCount--;

      double rotFreq_Hz = 0;
      if(!cfg.getDoubleIfExist("rotFreq", rotFreq_Hz))
        parCount--;

      unsigned n = 0;
      if(!cfg.getUnsignedIfExist("n", n))
        parCount--;

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Cfgstr for a DiskChopper physics is missing or with extra config parameters " << cfg.size() << " " << parCount );
      }

      phy = std::make_shared<DiskChopper>(theta0_deg, r_mm, phase_deg, rotFreq_Hz, n);
    }
    else if(physDef=="EnergyReflector")
    {
      int parCount = 3;
      double ekin = -1.;
      if(!cfg.getDoubleIfExist("ekin", ekin))
        parCount--;
      
      std::string islessthan = "1";
      if(!cfg.getStringIfExist("islessthan", islessthan))
        parCount--;

      if(islessthan!="0" && islessthan!="1")
        PROMPT_THROW2(BadInput, "'islessthan' should be \"0\" or \"1\". ");

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Cfgstr for a EnergyReflector physics is missing or with extra config parameters " << cfg.size() << " " << parCount );
      }

      bool b_lt = (islessthan=="1"); 
      phy = std::make_shared<EnergyReflector>(ekin, b_lt);
    }


    if(phy)
    {
      return phy;
    }
    else
      PROMPT_THROW2(BadInput, "Physics type " << physDef << " is not supported. ")
  }

}


Prompt::PhysicsFactory::PhysicsType Prompt::PhysicsFactory::checkPhysicsType(const std::string &cfgstr) const
{
  CfgParser::StringCfg cfg;
  // test if the cfg is a raw NCrystal cfg string
  try
  {
    auto &ps = Singleton<CfgParser>::getInstance();
    cfg = ps.parse(cfgstr);
  }
  catch (Prompt::Error::BadInput& e)
  {
    return PhysicsType::NC_RAW;
  }

  std::string physName;
  if( ! cfg.getStringIfExist("physics", physName))
      PROMPT_THROW(BadInput, "\"physics\" keyword is not defined. ")

  // ncrystal keeps a host branch (its cfg carries the NCrystal material, the
  // host computes the number density and gidi remains legacy there); every
  // other parsed namespace is the generic plugin route - unknown namespaces
  // surface as "unknown physics" from the registry lookup in ParticleProcess
  if(physName=="ncrystal")
    return PhysicsType::NC_SCATTER;
  return PhysicsType::PLUGIN;

}