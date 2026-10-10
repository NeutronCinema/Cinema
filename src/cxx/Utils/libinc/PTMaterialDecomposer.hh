#ifndef Prompt_MaterialDecomposer_hh
#define Prompt_MaterialDecomposer_hh

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
#include <memory>
#include <map>
#include <iostream>
#include <algorithm>

#include "PromptCore.hh"
#include "PTSingleton.hh"

namespace Prompt {

    struct IsotopeComposition {
    unsigned Z;
    unsigned A;
    double frac;;
    std::string name;

    friend std::ostream& operator<<(std::ostream& os, const IsotopeComposition& self)
    {
      os << self.Z << " " << self.A << " " << self.frac << " " << self.name;
      return os;
    }
  };

  std::vector<IsotopeComposition> shrink2element(const std::vector<IsotopeComposition> & isovec);
  
  class MaterialDecomposer {
  public:
    std::vector<IsotopeComposition> getComposition(int Z);
    std::vector<IsotopeComposition> decompose(const std::string & str, double &temperature);

  private:
  
    friend class Singleton<MaterialDecomposer>;
    MaterialDecomposer();
    ~MaterialDecomposer();

    std::map<int, std::vector<Prompt::IsotopeComposition>> m_natcomp;

  };
}

#endif
