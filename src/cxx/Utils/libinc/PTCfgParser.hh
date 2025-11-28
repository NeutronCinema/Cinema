#ifndef Prompt_CfgParser_hh
#define Prompt_CfgParser_hh

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

#include <string>
#include <map>
#include <iostream>
#include <algorithm>
#include "PTSingleton.hh"
#include "PTUtils.hh"

namespace Prompt {
  class CfgParser {
  public:
    struct StringCfg {
      std::string name;
      std::map<std::string, std::string> parameters;
      void print();
      std::string find(const std::string &key, bool force=false);
      bool contains(const std::string &key)
      {
        return find(key).empty() ? false : true;
      }
      size_t size()
      {
        return parameters.size();
      }

      bool getStringIfExist(const std::string &key, std::string& str)
      {
        std::string strAsStr = find(key);
        if(strAsStr.empty())
          return false;
        else
        {
          std::swap(str,strAsStr);
          return true;
        }
      }

      bool getDoubleIfExist(const std::string &key, double &vale)
      {
        std::string valueAsStr = find(key);
        if(!getStringIfExist(key, valueAsStr))
          return false;
        else
        {
          vale = ptstod(valueAsStr);
          return true;
        }
      }

      bool getUnsignedIfExist(const std::string &key, unsigned &vale)
      {
        std::string valueAsStr = find(key);
        if(!getStringIfExist(key, valueAsStr))
          return false;
        else
        {
          vale = ptstou(valueAsStr);
          return true;
        }
      }

      bool getIntIfExist(const std::string &key, int &vale)
      {
        std::string valueAsStr = find(key);
        if(!getStringIfExist(key, valueAsStr))
          return false;
        else
        {
          vale = ptstoi(valueAsStr);
          return true;
        }
      }

      bool getVectorIfExist(const std::string &key, Vector &vale)
      {
        std::string valueAsStr = find(key);
        if(!getStringIfExist(key, valueAsStr))
          return false;
        else
        {
          vale = string2vec(valueAsStr);
          return true;
        }
      }

      bool getBoolIfExist(const std::string &key, bool &value)
      {
        std::string valueAsStr = find(key);
        if(!getStringIfExist(key, valueAsStr))
          return false;
        else
        {
          // Convert string to boolean (case-insensitive)
          std::string lowerStr = valueAsStr;
          std::transform(lowerStr.begin(), lowerStr.end(), lowerStr.begin(), ::tolower);
          
          if (lowerStr == "true" || lowerStr == "1" || lowerStr == "yes") {
            value = true;
          } else if (lowerStr == "false" || lowerStr == "0" || lowerStr == "no") {
            value = false;
          } else {
            // If it's not a recognized boolean string, try to parse as double
            // and treat non-zero as true
            double numValue = ptstod(valueAsStr);
            value = (numValue != 0.0);
          }
          return true;
        }
      }

    };
  public:
    StringCfg parse(const std::string& cfgstr);
  private:
    friend class Singleton<CfgParser>;
    CfgParser();
    ~CfgParser() = default;
  };
}
#endif