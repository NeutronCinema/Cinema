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

#include "PTUtils.hh"
#include <algorithm>

std::vector<std::string> Prompt::split(const std::string& text, char delimiter)
{
  std::vector<std::string> words;
  std::stringstream sstream(text);
  std::string word;
  while (std::getline(sstream, word, delimiter))
  {
    word.erase(std::remove_if(word.begin(), word.end(),
                            [](char c) {
                                return (c == ' ' || c == '\n' || c == '\r' ||
                                        c == '\t' || c == '\v' || c == '\f');
                            }),
                            word.end());
    if(!word.empty())
      words.push_back(word);
  }


  return words;
}

Prompt::Vector Prompt::string2vec(const std::string& text, char delimiter)
{
  auto subs = split(text, delimiter);
  if(subs.size()!=3)
    PROMPT_THROW2(BadInput, "string2vec failed to create a vector from the input string " << text);
  return Vector{ptstod(subs[0]), ptstod(subs[1]), ptstod(subs[2]) };
}

int Prompt::ptstoi(const std::string& text)
{
  try
  {
    return std::stoi(text);
  }
  catch(...)
  {
    // std::invalid_argument, std::out_of_range
    PROMPT_THROW2(BadInput, "ptstod failed to convert an int from the input string " << text);
  }
}

int Prompt::ptstou(const std::string& text)
{
  try
  {
    return std::stol(text);
  }
  catch(...)
  {
    // std::invalid_argument, std::out_of_range
    PROMPT_THROW2(BadInput, "ptstou failed to convert an unsigned from the input string " << text);
  }
}



double Prompt::ptstod(const std::string& text)
{
  try
  {
    return std::stod(text);
  }
  catch(...)
  {
    // std::invalid_argument, std::out_of_range
    PROMPT_THROW2(BadInput, "ptstod failed to convert a double from the input string " << text);
  }
}

//Reversing CRC--Theory and Practice, HU Berlin Public Report, SAR-PR-2006-05.
//constants are used in functions crc32,crc32_magic,crc32_append_6chars, and getFileCRC32.
unsigned Prompt::crc32(const char * buffer , int length)
{
  const unsigned CRCPOLY = 0xEDB88320;
  const unsigned INITXOR = 0xFFFFFFFF;
  const unsigned FINALXOR = 0xFFFFFFFF;
  int i , j;
  unsigned int crcreg = INITXOR ;
  for (j = 0; j < length ; ++ j ) {
    char b  = (buffer [ j ]);
    for (i = 0; i < 8; ++ i) {
      if (( crcreg ^ b ) & 1) {
        crcreg = ( crcreg >> 1) ^ CRCPOLY ;
      } else {
        crcreg >>= 1;
      }
      b >>= 1;
    }
  }
  return crcreg ^ FINALXOR ;
}


unsigned Prompt::crc32(const std::string& str)
{
  return crc32(str.c_str(),str.size());
}

#include <cxxabi.h> //__cxa_demangle
std::string Prompt::getTypeName(const std::type_info& ti)
{
  // see https://panthema.net/2008/0901-stacktrace-demangled/cxa_demangle.html and
  // https://gcc.gnu.org/onlinedocs/libstdc++/manual/ext_demangling.html

  std::string tname (abi::__cxa_demangle(ti.name(), nullptr, nullptr, nullptr));

  std::string substr = "Prompt::";
  std::string::size_type i = tname.find(substr);
  if (i != std::string::npos)
     tname.erase(i, substr.length());

  return std::move(tname);
}
