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

#include "PTScorerFactory.hh"
#include "PTUtils.hh"
#include "PTCfgParser.hh"

#include "PTScorerDeltaMomentum.hh"
#include "PTScorerPSD.hh"
#include "PTScorerESpectrum.hh"
#include "PTScorerTOF.hh"
#include "PTScorerVolFluence.hh"
#include "PTScorerMultiScat.hh"
#include "PTScorerRotatingObj.hh"
#include "PTScorerWlSpectrum.hh"
#include "PTScorerAngular.hh"
#include "PTScorerSplit.hh"
#include "PTScorerWlAngle.hh"

Prompt::ScorerFactory::ScorerFactory()
{}


Prompt::Scorer* Prompt::ScorerFactory::createScorer(const std::string &cfgstr, double vol)
{
  std::cout << "Parsing scorer with config string: \n";
  std::cout << cfgstr << "\n";
  //fixme check number of input config

  auto &ps = Singleton<CfgParser>::getInstance();
  auto cfg = ps.parse(cfgstr);
  std::cout << "Parsed cfg: \n";
  cfg.print();

  std::string ScorDef = cfg.find("Scorer");

  if(ScorDef.empty())
  {
    PROMPT_THROW2(BadInput, "Scorer config string " << cfgstr << " does not define the scorer by the key \"Scorer\" ")
  }
  else
  {

    if(ScorDef == "DeltaMomentum")
    {
      // example cfg
      // "Scorer=DeltaMomentum; name=SofQ;sample_pos=0,0,1;beam_dir=0,0,1;dist=-100;
      // ptstate=ENTRY;linear=yes;min=0.5;max=50;numbin=1000;Qtrue=yes;scatnum=-1"


      int parCount = 12;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      auto samplePos = string2vec(cfg.find("sample_pos", force));
      auto beamDir = string2vec(cfg.find("beam_dir", force));
      double moderator2SampleDist = ptstod(cfg.find("dist", force));
      double minQ = ptstod(cfg.find("min", force));
      double maxQ = ptstod(cfg.find("max", force));

      int numBin = 100;
      if(cfg.find("numbin")=="") 
        parCount--;
      else
      {
        numBin = ptstoi(cfg.find("numbin"));
      }
      
      // the optional parameters
      int method = 0;
      if(cfg.find("method")=="") 
        parCount--;
      else
      {
        int methodInInt = ptstoi(cfg.find("method"));
        if(methodInInt==0 || methodInInt==1)
        {
          method = methodInInt;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"method\" should either be 0 or 1");
        }
      }

      int scatnum = -1;
      if(cfg.find("scatnum")=="") 
        parCount--;
      else
      {
        int scatnumInInt = ptstoi(cfg.find("scatnum"));
        if(scatnumInInt>=-1 )
        {
          scatnum = scatnumInInt;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"scatnum\" should be an integer greater than or equal to -1");
        }
      }

      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
        ptstate = getPTS (ptstateInStr);
      }

      bool linear = true;
      std::string linearInStr = cfg.find("linear");
      if(linearInStr.empty())
        parCount--;
      else
      {
        if(linearInStr=="yes")
        {
          linear = true;
        }
        else if(linearInStr=="no")
          linear = false;
        else {
          PROMPT_THROW2(BadInput, "The value for \"linear\" should either be \"yes\" or \"no\"");
        }

      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type DeltaMomentum is missing or with extra config parameters " << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerDeltaMomentum(name, samplePos, beamDir, moderator2SampleDist, minQ, maxQ, numBin, const_neutron_pgd, ptstate, method, scatnum, linear);
    }
    if(ScorDef == "Angular")
    {
      // example cfg
      // "Scorer=Angular;name=ST_template;sample_pos=0,-1750,0;beam_dir=0,-1,0;
      //  dist=3650.;min=10.0;max=160;numbin=6000;ptstate=ENTRY;linear=yes"


      int parCount = 9;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      auto beamDir = string2vec(cfg.find("beam_dir", force));
      double angle_min = ptstod(cfg.find("min", force));
      double angle_max = ptstod(cfg.find("max", force));

      int numBin = 100;
      if(cfg.find("numbin")=="") 
        parCount--;
      else
      {
        numBin = ptstoi(cfg.find("numbin"));
      }
      

      // the optional parameters

      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
       ptstate = getPTS (ptstateInStr);
      }

      bool inDegree = true;
      std::string inDegreeStr = cfg.find("inDegree");
      if(inDegreeStr.empty())
        parCount--;
      else
      {
        if(inDegreeStr=="yes")
        {
          inDegree = true;
        }
        else if(inDegreeStr=="no")
          inDegree = false;
        else {
          PROMPT_THROW2(BadInput, "The value for \"inDegree\" should either be \"yes\" or \"no\"");
        }

      }


      bool linear = true;
      std::string linearInStr = cfg.find("linear");
      if(linearInStr.empty())
        parCount--;
      else
      {
        if(linearInStr=="yes")
        {
          linear = true;
        }
        else if(linearInStr=="no")
          linear = false;
        else {
          PROMPT_THROW2(BadInput, "The value for \"linear\" should either be \"yes\" or \"no\"");
        }

      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type Angular is missing or with extra config parameters " << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerAngular(name, angle_min, angle_max, numBin, const_neutron_pgd, beamDir, ptstate, inDegree);
    }

    else if(ScorDef == "PSD")
    {
      // PSD: position sensitive detector

      int parCount = 10;

      bool force = true;

      std::string name = cfg.find("name", force);
      double xmin = ptstod(cfg.find("xmin", force));
      double xmax = ptstod(cfg.find("xmax", force));
      double ymin = ptstod(cfg.find("ymin", force));
      double ymax = ptstod(cfg.find("ymax", force));

      int nxbins = 100;
      if(cfg.find("numbin_x")=="") 
        parCount--;
      else
      {
        nxbins = ptstoi(cfg.find("numbin_x"));
      }

      int nybins = 100;
      if(cfg.find("numbin_y")=="") 
        parCount--;
      else
      {
        nybins = ptstoi(cfg.find("numbin_y"));
      }

      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
        ptstate = getPTS (ptstateInStr);
      }

      ScorerPSD::PSDType type = ScorerPSD::PSDType::XY;
      std::string typeInStr = cfg.find("type");
      if(typeInStr.empty())
        parCount--;
      else
      {
        if(typeInStr=="XY")
        {
          type = ScorerPSD::PSDType::XY;
        }
        else if(typeInStr=="XZ")
        {
          type = ScorerPSD::PSDType::XZ;
        }
        else if(typeInStr=="YZ")
        {
          type = ScorerPSD::PSDType::YZ;
        }
        else {
          PROMPT_THROW(BadInput, "Scorer type can only be XY, XZ or YZ" );
        }
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type PSD is missing or with extra config parameters" << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerPSD(name, xmin, xmax, nxbins, ymin, ymax, nybins, const_neutron_pgd, ptstate,type);
    }

    else if(ScorDef == "ESpectrum")
    {
      // ESpectrum: energy spectrum
      // example cfg
      // "Scorer=ESD; name=detector; min=0.0; max=0.0253; numbin=100; ptstate=ENTRY"

      int parCount = 8;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      double minE = ptstod(cfg.find("min", force));
      double maxE = ptstod(cfg.find("max", force));

      bool scoreTransfer = false;
      std::string scoreTransferStr = cfg.find("scoreTransfer");
      if (scoreTransferStr=="1" || scoreTransferStr=="true")
        scoreTransfer = true;
      else if (scoreTransferStr=="0" || scoreTransferStr=="false");
      else if (scoreTransferStr.empty())
        parCount--;
      else
        {
          PROMPT_THROW2(BadInput, "Not recognized scoreTransfer input " << scoreTransferStr << ".");
        }

      int numBin = 100;
      if(cfg.find("numbin")=="") 
        parCount--;
      else
      {
        numBin = ptstoi(cfg.find("numbin"));
      }

      int pdg = const_neutron_pgd;
      if(cfg.find("particle")=="") 
        parCount--;
      else
      {
        pdg = ptstoi(cfg.find("particle"));
      }

      // if is an energy transfer scorer, force pts to EXIT
      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
      {
        if(scoreTransfer)
          ptstate = Scorer::ScorerType::EXIT;
        parCount--;
      }
      else
      {
        ptstate = getPTS (ptstateInStr);
        if(scoreTransfer && ptstate != Scorer::ScorerType::EXIT)
        {
          ptstate = Scorer::ScorerType::EXIT;
          printf("WARNING: input particle tracing state forced to EXIT when scoring energy transfer!\n");
        }
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type ESpectrum is missing or with extra config parameters" << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerESpectrum(name, scoreTransfer, minE, maxE, numBin, pdg, ptstate);
    }
    else if(ScorDef == "WlSpectrum")
    {
      // WlSpectrum: wavelength spectrum
      // example cfg
      // "Scorer=WlSpectrum; name=detector; min=0.0; max=0.0253; numbin=100; ptstate=ENTRY"

      int parCount = 6;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      double minWl = ptstod(cfg.find("min", force));
      double maxWl = ptstod(cfg.find("max", force));

      int numBin = 100;
      if(cfg.find("numbin")=="") 
        parCount--;
      else
      {
        numBin = ptstoi(cfg.find("numbin"));
      }

      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
        ptstate = getPTS (ptstateInStr);
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type WlSpectrum is missing or with extra config parameters" << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerWlSpectrum(name, minWl, maxWl, numBin, const_neutron_pgd, ptstate);
    }
    else if(ScorDef == "TOF")
    {
      // TOF: time-of-flight
      // example cfg
      // "Scorer=TOF; name=detector; min=0.0; max=0.5; numbin=1000; ptstate=ENTRY"

      int parCount = 6;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      double minT = ptstod(cfg.find("min", force));
      double maxT = ptstod(cfg.find("max", force));

      int numBin = 100;
      if(cfg.find("numbin")=="") 
        parCount--;
      else
      {
        numBin = ptstoi(cfg.find("numbin"));
      }

      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
        ptstate = getPTS (ptstateInStr);
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type TOF is missing or with extra config parameters" << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerTOF(name, minT, maxT, numBin, const_neutron_pgd, ptstate);
    }
    else if(ScorDef == "MultiScat")
    {
      // MultiScat: multiple scattering
      // example cfg
      // "Scorer=MultiScat; name=D2O; min=1; max=5; linear=yes"
      // the default value for linear is yes

      int parCount = 5;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      
      // the optional parameters
      int minNumber = 0;
      if(cfg.find("min")=="") 
        parCount--;
      else
      {
        int minNumberInInt = ptstoi(cfg.find("min"));
        if(minNumberInInt>=0 )
        {
          minNumber = minNumberInInt;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"min\" should be an integer greater than or equal to 0");
        }
      }

      int maxNumber = 5;
      if(cfg.find("max")=="") 
        parCount--;
      else
      {
        int maxNumberInInt = ptstoi(cfg.find("max"));
        if(maxNumberInInt>=0 )
        {
          maxNumber = maxNumberInInt;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"max\" should be an integer greater than or equal to 0");
        }
      }
      int numBin = maxNumber-minNumber+1;

      bool linear = true;
      std::string linearInStr = cfg.find("linear");
      if(linearInStr.empty())
        parCount--;
      else
      {
        if(linearInStr=="yes")
        {
          linear = true;
        }
        else if(linearInStr=="no")
          linear = false;
        else {
          PROMPT_THROW2(BadInput, "The value for \"linear\" should either be \"yes\" or \"no\"");
        }
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type MultiScat is missing or with extra config parameters" << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      auto multiscat = new ScorerMultiScat(name, minNumber-0.5, maxNumber+0.5, numBin, const_neutron_pgd, Scorer::ScorerType::PROPAGATE_POST, linear);
      m_multiScatcorers.insert({name, multiscat});
      return multiscat;
    }
    else if(ScorDef == "VolFluence")
    {
      // VolFluence: volume flux

      int parCount = 7;

      bool force = true;
      std::string name = cfg.find("name", force);
      double xmin = ptstod(cfg.find("min", force));
      double xmax = ptstod(cfg.find("max", force));

      int nxbins = 100;
      if(cfg.find("numbin")=="") 
        parCount--;
      else
      {
        nxbins = ptstoi(cfg.find("numbin"));
      }

      Scorer::ScorerType ptstate = Scorer::ScorerType::PEA_PRE;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
        ptstate = getPTS (ptstateInStr);
      }

      bool linear = true;
      std::string linearInStr = cfg.find("linear");
      if(linearInStr.empty())
        parCount--;
      else
      {
        if(linearInStr=="yes")
        {
          linear = true;
        }
        else if(linearInStr=="no")
          linear = false;
        else {
          PROMPT_THROW2(BadInput, "The value for \"linear\" should either be \"yes\" or \"no\"");
        }

      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type VolFluence is missing or with extra config parameters" << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      return new ScorerVolFluence(name, xmin, xmax, nxbins, vol, const_neutron_pgd, ptstate, linear);

    }
    else if(ScorDef == "Split")
    {
      std::string name = cfg.find("name", true);
      int split = ptstoi(cfg.find("split", true));
      return new ScorerSplit(name, split, const_neutron_pgd);
    }
    else if(ScorDef == "RotatingObj")
    {
      // "Scorer=RotatingObj;name=ro1;rotation_axis=0,1,0;point_on_axis=0,0,0;rot_fre=100;type=Entry or Proprogate or Exit"/

      int parCount = 5;
      bool force = true;

      std::string name = cfg.find("name", force);
      auto rotAxis = string2vec(cfg.find("rotation_axis", force));
      auto pointAxis = string2vec(cfg.find("point_on_axis", force));
      double rotFreq = ptstod(cfg.find("rot_fre", force));
      return new ScorerRotatingObj(name, rotAxis, pointAxis, rotFreq, const_neutron_pgd);
    }
    else if(ScorDef == "WlAngle")
    {
      // example cfg
      // "Scorer=WlAngle; name=wl_angle;sample_pos=0,0,0;beam_dir=0,0,1;dist=1000;
      // ptstate=ENTRY;wl_min=0.5;wl_max=5;numbin_wl=1000;angle_min=-3;angle_max=3;numbin_angle=1000;method=0"

      int parCount = 15;

      // The mandatory parameters
      bool force = true;
      std::string name = cfg.find("name", force);
      auto samplePos = string2vec(cfg.find("sample_pos", force));
      auto beamDir = string2vec(cfg.find("beam_dir", force));
      double moderator2SampleDist = ptstod(cfg.find("dist", force));
      double wl_min = ptstod(cfg.find("wl_min", force));
      double wl_max = ptstod(cfg.find("wl_max", force));
      double angle_min = ptstod(cfg.find("angle_min", force));
      double angle_max = ptstod(cfg.find("angle_max", force));

      // the optional parameters
      int numbin_wl = 100;
      if(cfg.find("numbin_wl")=="") 
        parCount--;
      else
      {
        numbin_wl = ptstoi(cfg.find("numbin_wl"));
      }

      int numbin_angle = 100;
      if(cfg.find("numbin_angle")=="") 
        parCount--;
      else
      {
        numbin_angle = ptstoi(cfg.find("numbin_angle"));
      }
      
      int method = 0;
      if(cfg.find("method")=="") 
        parCount--;
      else
      {
        int methodInInt = ptstoi(cfg.find("method"));
        if(methodInInt==0 || methodInInt==1)
        {
          method = methodInInt;
        }
        else {
          PROMPT_THROW2(BadInput, "The value for \"method\" should either be 0 or 1");
        }
      }

      Scorer::ScorerType ptstate = Scorer::ScorerType::ENTRY;
      std::string ptstateInStr = cfg.find("ptstate");
      if(ptstateInStr.empty())
        parCount--;
      else
      {
        ptstate = getPTS (ptstateInStr);
      }

      std::string msname="";
      if(cfg.find("msname")=="") 
        parCount--;
      else
      {
        msname = cfg.find("msname");
      }

      int scatnum = -2;
      if(cfg.find("scatnum")=="") 
        parCount--;
      else
      {
        scatnum = ptstoi(cfg.find("scatnum"));
      }

      if(parCount!=cfg.size())
      {
        PROMPT_THROW2(BadInput, "Scorer type WlAngle is missing or with extra config parameters " << ", " << cfg.size() << " are given, but there is " <<   parCount <<" known parameters"  );
      }

      auto wlscorer = new ScorerWlAngle(name, samplePos, beamDir, moderator2SampleDist, wl_min, wl_max, numbin_wl, angle_min, angle_max, numbin_angle, const_neutron_pgd, ptstate, method);
      if(!msname.empty())
      {
        auto it=m_multiScatcorers.find(msname);
        if(it==m_multiScatcorers.end())
          PROMPT_THROW2(BadInput, "MultiScat Scorer " << msname << " is not defined. ")
        wlscorer->addMultiScatter(dynamic_cast<Prompt::ScorerMultiScat*>(it->second), scatnum);
      }
      return wlscorer;
    }
    else
      PROMPT_THROW2(BadInput, "Scorer type " << ScorDef << " is not supported. ")
  }

}


Prompt::Scorer::ScorerType Prompt::ScorerFactory::getPTS(const std::string& ptstateInStr) const 
{
  if(ptstateInStr=="ENTRY")
  {
    return Scorer::ScorerType::ENTRY;
  }
  else if(ptstateInStr=="ABSORB")
  {
    return Scorer::ScorerType::ABSORB;
  }
  else if(ptstateInStr=="SURFACE")
  {
    return Scorer::ScorerType::SURFACE;
  }
  else if(ptstateInStr=="PROPAGATE_POST")
  {
    return Scorer::ScorerType::PROPAGATE_POST;
  }
  else if(ptstateInStr=="PROPAGATE_PRE")
  {
    return Scorer::ScorerType::PROPAGATE_PRE;
  }
  else if(ptstateInStr=="EXIT")
  {
    return Scorer::ScorerType::EXIT;
  }
  else if(ptstateInStr=="PEA_PRE")
  {
    return Scorer::ScorerType::PEA_PRE;
  }
  else if(ptstateInStr=="PEA_POST")
  {
    return Scorer::ScorerType::PEA_POST;
  }
  else {
    PROMPT_THROW2(BadInput, "ptstate does not support" << " " << ptstateInStr);
  }
}
