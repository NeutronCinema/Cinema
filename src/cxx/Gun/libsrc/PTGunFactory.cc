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

#include "PTGunFactory.hh"
#include "PTUtils.hh"
#include "PTCfgParser.hh"

#include "PTNeutron.hh"

#include "PTMaxwellianGun.hh"
#include "PTSimpleThermalGun.hh"
#include "PTIsotropicGun.hh"
#include "PTUniModeratorGun.hh"
#include "PTMPIGun.hh"
#include "PTSANSGun.hh"
#include "PTMCPLGun.hh"
Prompt::GunFactory::GunFactory()
{}


std::shared_ptr<Prompt::PrimaryGun> Prompt::GunFactory::createGun(const std::string &cfgstr)
{
  std::cout << "Parsing config string for the particle gun: \n";
  std::cout << cfgstr << "\n";
  //fixme check number of input config

  auto &ps = Singleton<CfgParser>::getInstance();
  auto cfg = ps.parse(cfgstr);
  std::cout << "Parsed cfg: \n";
  cfg.print();

  std::string gunDef = cfg.find("gun");

  if(gunDef.empty())
  {
    PROMPT_THROW2(BadInput, "Scorer config string " << cfgstr << " does not define the scorer by the key \"Scorer\" ")
  }
  else
  {

    if(gunDef == "MaxwellianGun")
    {
      // example cfgstr:
      // gun=MaxwellianGun;src_w=100;src_h=50;src_z=-10;
      // slit_w=5;slit_h=10;slit_z=10;temperature=293.15;

      // temperature is optional with default value 293.15kelvin

      int parCount = 8;

      // The mandatory parameters
      bool force = true;
      double src_w = ptstod(cfg.find("src_w", force));
      double src_h = ptstod(cfg.find("src_h", force));
      double src_z = ptstod(cfg.find("src_z", force));
      double slit_w = ptstod(cfg.find("slit_w", force));
      double slit_h = ptstod(cfg.find("slit_h", force));
      double slit_z = ptstod(cfg.find("slit_z", force));

      // the optional parameters
      double temp = 293.15;
      std::string temperatureInStr = cfg.find("temperature");
      if(temperatureInStr.empty())
        parCount--;
      else
      {
        temp=ptstod(temperatureInStr);
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "MaxwellianGun is missing or with extra config parameters" << cfg.size() << " " << parCount );
      }

     return std::make_shared<MaxwellianGun>(Neutron(), temp,
          std::array<double, 6> {src_w, src_h, src_z,
                                 slit_w, slit_h, slit_z});
    }
    else if(gunDef == "SimpleThermalGun")
    {
      // example cfgstr:
      // gun=SimpleThermalGun;energy=0.0253;position=0,0,-500;direction=0,0,1

      // energy and direction are optional with default value 0 and 0,0,1 separately

      int parCount = 4;

      // The mandatory parameters
      bool force = true;
      Vector position = string2vec(cfg.find("position", force));

      // the optional parameters
      double energy = 0;
      if(cfg.find("energy")=="") 
        parCount--;
      else
      {
        double energyInDou = ptstod(cfg.find("energy"));
        if(energyInDou>=0 )
        {
          energy = energyInDou;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"energy\" should be greater than or equal to 0");
        }
      }

      Vector direction = Vector{0.,0.,1.};
      if(!cfg.getVectorIfExist("direction", direction))
        parCount--;

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "SimpleThermalGun is missing or with extra config parameters" << cfg.size() << " " << parCount );
      }

      return std::make_shared<SimpleThermalGun>(Neutron(), energy, position, direction);
    }
    else if(gunDef == "IsotropicGun")
    {
      // example cfgstr:
      // gun=IsotropicGun;energy=0.0253;position=0,0,-10

      // energy is optional with default value 0

      int parCount = 3;

      // The mandatory parameters
      bool force = true;
      Vector position = string2vec(cfg.find("position", force));

      // the optional parameters
      double energy = 0;
      if(cfg.find("energy")=="") 
        parCount--;
      else
      {
        double energyInDou = ptstod(cfg.find("energy"));
        if(energyInDou>=0 )
        {
          energy = energyInDou;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"energy\" should be greater than or equal to 0");
        }
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "IsotropicGun is missing or with extra config parameters" << cfg.size() << " " << parCount );
      }

      return std::make_shared<IsotropicGun>(Neutron(), energy, position);
    }
    else if(gunDef == "UniModeratorGun")
    {
      // example cfgstr:
      // gun=UniModeratorGun;mean_wl=3.39;range_wl=0.3;src_w=100;src_h=50;src_z=-400;
      // slit_w=5;slit_h=10;slit_z=1


      int parCount = 9;

      // The mandatory parameters
      bool force = true; 
      double src_w = ptstod(cfg.find("src_w", force));
      double src_h = ptstod(cfg.find("src_h", force));
      double src_z = ptstod(cfg.find("src_z", force));
      double slit_w = ptstod(cfg.find("slit_w", force));
      double slit_h = ptstod(cfg.find("slit_h", force));
      double slit_z = ptstod(cfg.find("slit_z", force));

      // the optional parameters
      double mean_wl = 1;
      if(cfg.find("mean_wl")=="") 
        parCount--;
      else
      {
        double mean_wlInDou = ptstod(cfg.find("mean_wl"));
        if(mean_wlInDou>0 )
        {
          mean_wl = mean_wlInDou;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"mean_wl\" should be positive");
        }
      }

      double range_wl = 0.0001;
      if(cfg.find("range_wl")=="") 
        parCount--;
      else
      {
        double range_wlInDou = ptstod(cfg.find("range_wl"));
        if(range_wlInDou>=0 )
        {
          range_wl = range_wlInDou;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"range_wl\" should be greater than or equal to 0");
        }
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "UniModeratorGun is missing or with extra config parameters" << cfg.size() << " " << parCount );
      }

      return std::make_shared<UniModeratorGun>(Neutron(), mean_wl, range_wl,
            std::array<double, 6> {src_w, src_h, src_z,
                                 slit_w, slit_h, slit_z});
    }
    else if(gunDef == "MPIGun")
    {
      // example cfgstr:
      // gun=MPIGun;src_w=100;src_h=50;src_z=-400;
      // slit_w=5;slit_h=10;slit_z=1

      int parCount = 7;

      // The mandatory parameters
      bool force = true;
      double src_w = ptstod(cfg.find("src_w", force));
      double src_h = ptstod(cfg.find("src_h", force));
      double src_z = ptstod(cfg.find("src_z", force));
      double slit_w = ptstod(cfg.find("slit_w", force));
      double slit_h = ptstod(cfg.find("slit_h", force));
      double slit_z = ptstod(cfg.find("slit_z", force));

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "MPIGun is missing or with extra config parameters" << cfg.size() << " " << parCount );
      }

      return std::make_shared<MPIGun>(Neutron(),
            std::array<double, 6> {src_w, src_h, src_z,
                                 slit_w, slit_h, slit_z});
    }
    else if(gunDef == "SANSGun")
    {
      int parCount = 7;

      // The mandatory parameters
      bool force = true;
      double src_w = ptstod(cfg.find("src_w", force));
      double src_h = ptstod(cfg.find("src_h", force));
      double src_z = ptstod(cfg.find("src_z", force));
      double slit_w = ptstod(cfg.find("slit_w", force));
      double slit_h = ptstod(cfg.find("slit_h", force));
      double slit_z = ptstod(cfg.find("slit_z", force));

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "SANSGun is missing or with extra config parameters" << cfg.size() << " " << parCount );
      }

      return std::make_shared<SANSGun>(Neutron(),
            std::array<double, 6> {src_w, src_h, src_z,
                                 slit_w, slit_h, slit_z});
    }
    else if(gunDef == "MCPLGun")
    {
      std::string fn = cfg.find("mcplfile", true);
      return std::make_shared<MCPLGun>(Neutron(), fn);
    }
    else
      PROMPT_THROW2(BadInput, "Gun " << gunDef << " is not supported. ")
  }
  pt_assert_always(false);
  //a return statement here to stop compiler warning, it should never reach here
  return std::make_shared<IsotropicGun>(Neutron(), 1, Vector{0,0,0});

}
