#ifndef Prompt_Utils_hh
#define Prompt_Utils_hh

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
#include <typeinfo> //getTypeName

namespace Prompt {
  std::vector<std::string> split(const std::string& text, char delimiter);
  Vector string2vec(const std::string& text, char delimiter=',');
  double ptstod(const std::string& text);
  int ptstoi(const std::string& text);
  int ptstou(const std::string& text);
  unsigned crc32(const char * buffer , int length);
  unsigned crc32(const std::string& str);
  std::string getTypeName(const std::type_info& ti);

}

#endif
