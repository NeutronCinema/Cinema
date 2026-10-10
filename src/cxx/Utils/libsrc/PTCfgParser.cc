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

#include "PTCfgParser.hh"
#include "PTUtils.hh" //split

void Prompt::CfgParser::StringCfg::print()
{
  std::cout << "StringCfg " << name << " of size " << size() << ":\n";
  for(auto it = parameters.begin(); it!=parameters.end();++it)
  {
    std::cout << "  [" << it->first << " = "
                << it->second << "]\n";
  }
}

std::string Prompt::CfgParser::StringCfg::find(const std::string &key, bool force)
{
  auto  it = parameters.find(key);
  std::string v =  it == parameters.end() ? "" : it->second;
  if(v.empty() && force)
    PROMPT_THROW2(BadInput, "cfg is missing the key \""<< key << "\"" );
  return v;
}

Prompt::CfgParser::CfgParser()
{
}

Prompt::CfgParser::StringCfg Prompt::CfgParser::parse(const std::string& cfgstrinput)
{
  std::string cfgstr = cfgstrinput; 
  //find this substrings inside ' '
  std::map<std::string, std::string> strRlcDict;
  std::vector<size_t> pos;
  size_t found = cfgstr.find(char(39)); //39 for '
  while(found!=std::string::npos)
  {
    pos.push_back(found);
    found = cfgstr.find(char(39), pos.back()+1);
  }
  if(pos.size()%2==1)
    PROMPT_THROW(BadInput, " bad input caused by '");

  
  for(size_t i= 0; i<pos.size();i=i+2)
  {
    std::string sub=cfgstr.substr(pos[i]+1,pos[i+1]-pos[i]-1);
    std::string magicstr = "magicsubstring"+std::to_string(i);
    cfgstr.replace(pos[i], pos[i+1]-pos[i]+1, magicstr);
    strRlcDict.emplace(magicstr, sub);
  }  

  auto strvec = split(cfgstr, ';');
  StringCfg cfg;
  cfg.name=strvec[0];
  for(const auto &s: strvec)
  {
    auto p = split(s, '=');
    if(p.size()!=2)
        PROMPT_THROW2(BadInput, " cfg section \""<< s << "\" is ill-defined (expected "
                      "key=value sections separated by ';'; if this is a gun definition, "
                      "the first section must be gun=<GunName>)" );
    cfg.parameters[p[0]] = p[1];
    // std::cout << s << std::endl;
  }

  for(auto it=cfg.parameters.begin();it!=cfg.parameters.end();++it)
  {
    auto itstr = strRlcDict.find(it->second);
    if(itstr!=strRlcDict.end())
      it->second = itstr->second;
  }

  return std::move(cfg);
}
