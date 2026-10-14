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

template <typename T>
void Prompt::NumpyWriter::writeNumpyFile(const std::string &filename, const std::vector<T> &data, Prompt::NumpyWriter::NPDataType type,
                  const std::vector<uint64_t> &shape) const
{
  std::string serialised;
  makeNumpyArr(data, type, shape, serialised);
  std::ofstream outfile(filename, std::ofstream::binary);
  outfile << serialised;
  outfile.close();
}

template <typename T>
void Prompt::NumpyWriter::makeNumpyArr(const std::vector<T> &data, Prompt::NumpyWriter::NPDataType type,
                              const std::vector<uint64_t> &shape, std::string &npArr) const
{
  makeNumpyArrFromUChar( reinterpret_cast<const uint8_t*>(data.data()),
                data.size()*sizeof(T), type, shape , npArr );
}

template <typename T>
void Prompt::NumpyWriter::makeNumpyArr(const T *data, size_t datasize, Prompt::NumpyWriter::NPDataType type,
                              const std::vector<uint64_t> &shape, std::string &npArr) const
{
  makeNumpyArrFromUChar( reinterpret_cast<const uint8_t*>(data), datasize*sizeof(T), type, shape , npArr );
}
