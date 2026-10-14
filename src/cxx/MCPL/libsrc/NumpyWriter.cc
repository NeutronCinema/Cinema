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

#include "NumpyWriter.hh"
#include <cstring>

Prompt::NumpyWriter::NumpyWriter()
{
  //fixme: make sure it is a little endian system
}

Prompt::NumpyWriter::~NumpyWriter()
{

}

void Prompt::NumpyWriter::makeNumpyArrFromUChar(const uint8_t *data, size_t len,
                  Prompt::NumpyWriter::NPDataType dtype, const std::vector<uint64_t> &shape, std::string &npArr)
{
  const std::string fixed_magic_string("\x93NUMPY");

  npArr.reserve(len + 128); //a guess of tot size

  npArr = fixed_magic_string +'\x01'+'\x00' + "  ";
  npArr += "{'descr': '" + U32toASCII(dtype).getTypeString() + "', 'fortran_order': False, 'shape': (" ;

  for(auto v:shape)
    npArr += std::to_string(v) + ",";
  if(shape.size()>1)
    npArr.pop_back();

  npArr += "), }";

  unsigned dict_size = npArr.size();
  if(dict_size>65535)
    throw std::length_error("header in npy 1.0 format can't be larger than 65535 bytes, see https://docs.scipy.org/doc/numpy-1.14.2/neps/npy-format.html");

  //total meta info size mush be evenly divisible by 64 for alignment purposes.
  //-1, because terminated by a newline '\n'
  unsigned tot = ((dict_size/64)+1)*64;

  //sizeof("\x93NUMPY\x01\00")+sizeof(HEADER_LEN)=10 bytes
  uint16_t header_len_with_padding = tot-10;

  npArr[8] = ( unsigned char ) (header_len_with_padding & 0xff) ;
  npArr[9] = ( unsigned char ) ((header_len_with_padding>>8) & 0xff);

  unsigned padding_size = tot - dict_size - 1;
  npArr.append(padding_size,'\x20');
  npArr += "\n";

  npArr.append(reinterpret_cast<const char* >(data),len);
}
