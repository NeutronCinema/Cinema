#ifndef Prompt_HDF5BinaryWrite_hh
#define Prompt_HDF5BinaryWrite_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  You may not use this file except in compliance with the License.          //
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
#include "hdf5.h"
#include <vector>
#include <string>
#include <map>

namespace Prompt {

class Particle;

class HDF5BinaryWrite {
public:
    HDF5BinaryWrite(const std::string& filename, bool compress=true);
    virtual ~HDF5BinaryWrite();
    
    void init(const std::string& dataSourceName);
    void addHeaderComment(const std::string& comment);
    
    // Write particle data with additional custom fields
    void write(const Particle& particle, int scatterNumber);
    
    // Add custom fields to the dataset
    void addCustomField(const std::string& fieldName, hid_t dataType);
    
private:
    std::string m_filename;
    hid_t m_file_id;
    hid_t m_dataset_id;
    hid_t m_dataspace_id;
    hid_t m_plist_id;
    bool m_compress;
    
    // Dataset dimensions
    hsize_t m_current_size;
    hsize_t m_max_size;
    hsize_t m_chunk_size;
    
    // Field definitions
    std::vector<std::string> m_field_names;
    std::vector<hid_t> m_field_types;
    std::vector<size_t> m_field_offsets;
    size_t m_particle_size;
    
    // Buffer for storing particles
    std::vector<char> m_particle_buffer;
    size_t m_buffer_position;
    
    hid_t createCompoundType();
    void extendDataset();
    void flushBuffer();
    void writeBufferToFile();
};

} // namespace Prompt

#endif