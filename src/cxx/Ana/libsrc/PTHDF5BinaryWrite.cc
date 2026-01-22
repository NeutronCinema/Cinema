#include "PTHDF5BinaryWrite.hh"
#include "PTParticle.hh"
#include "hdf5.h"
#include <iostream>
#include <cstring>

namespace Prompt {

HDF5BinaryWrite::HDF5BinaryWrite(const std::string& filename, bool compress) 
    : m_filename(filename), m_compress(compress), m_current_size(0), m_max_size(10000), 
      m_chunk_size(1000), m_buffer_position(0) {
    
    // Create file with H5F_ACC_TRUNC to overwrite existing files
    m_file_id = H5Fcreate(m_filename.c_str(), H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    if (m_file_id < 0) {
        throw std::runtime_error("Failed to create HDF5 file: " + m_filename);
    }
    
    // Initialize default fields
    m_field_names = {"position_x", "position_y", "position_z", 
                     "direction_x", "direction_y", "direction_z",
                     "energy", "time", "weight", "pdgcode",
                     "survive_probability", "scatter_number", "energy_loss"};
    
    m_field_types = {H5T_NATIVE_DOUBLE, H5T_NATIVE_DOUBLE, H5T_NATIVE_DOUBLE,
                     H5T_NATIVE_DOUBLE, H5T_NATIVE_DOUBLE, H5T_NATIVE_DOUBLE,
                     H5T_NATIVE_DOUBLE, H5T_NATIVE_DOUBLE, H5T_NATIVE_DOUBLE, H5T_NATIVE_INT,
                     H5T_NATIVE_DOUBLE, H5T_NATIVE_INT, H5T_NATIVE_DOUBLE};
    
    // Calculate offsets and total size
    m_particle_size = 0;
    for (size_t i = 0; i < m_field_names.size(); ++i) {
        m_field_offsets.push_back(m_particle_size);
        m_particle_size += H5Tget_size(m_field_types[i]);
    }
    
    // Create compound type
    hid_t compound_type = createCompoundType();
    
    // Create dataset creation property list
    m_plist_id = H5Pcreate(H5P_DATASET_CREATE);
    hsize_t chunk_dims[1] = {m_chunk_size};
    H5Pset_chunk(m_plist_id, 1, chunk_dims);
    
    if (m_compress) {
        H5Pset_deflate(m_plist_id, 6); // Compression level 6
    }
    
    // Create dataspace for extendable dataset
    hsize_t dims[1] = {0};
    hsize_t max_dims[1] = {H5S_UNLIMITED};
    m_dataspace_id = H5Screate_simple(1, dims, max_dims);
    
    // Create dataset
    m_dataset_id = H5Dcreate2(m_file_id, "particles", compound_type, m_dataspace_id, 
                             H5P_DEFAULT, m_plist_id, H5P_DEFAULT);
    
    H5Tclose(compound_type);
    
    // Initialize buffer
    m_particle_buffer.resize(m_particle_size * m_chunk_size);
    m_buffer_position = 0;
}

HDF5BinaryWrite::~HDF5BinaryWrite() {
    flushBuffer(); // Write any remaining particles in buffer
    
    if (m_dataset_id >= 0) H5Dclose(m_dataset_id);
    if (m_dataspace_id >= 0) H5Sclose(m_dataspace_id);
    if (m_plist_id >= 0) H5Pclose(m_plist_id);
    if (m_file_id >= 0) H5Fclose(m_file_id);
}

void HDF5BinaryWrite::init(const std::string& dataSourceName) {
    // Add data source as attribute
    hid_t attr_space = H5Screate(H5S_SCALAR);
    hid_t attr_type = H5Tcopy(H5T_C_S1);
    H5Tset_size(attr_type, dataSourceName.size());
    
    hid_t attr_id = H5Acreate2(m_file_id, "data_source", attr_type, attr_space, 
                              H5P_DEFAULT, H5P_DEFAULT);
    H5Awrite(attr_id, attr_type, dataSourceName.c_str());
    
    H5Aclose(attr_id);
    H5Tclose(attr_type);
    H5Sclose(attr_space);
}

void HDF5BinaryWrite::addHeaderComment(const std::string& comment) {
    // Store comments in a string dataset
    hid_t str_type = H5Tcopy(H5T_C_S1);
    H5Tset_size(str_type, H5T_VARIABLE);
    
    hid_t space_id = H5Screate(H5S_SCALAR);
    hid_t attr_id = H5Acreate2(m_file_id, "header_comment", str_type, space_id, 
                              H5P_DEFAULT, H5P_DEFAULT);
    
    const char* temp = comment.c_str();
    H5Awrite(attr_id, str_type, &temp);
    
    H5Aclose(attr_id);
    H5Sclose(space_id);
    H5Tclose(str_type);
}

void HDF5BinaryWrite::write(const Particle& particle, int scatterNumber) {
    // Get buffer position for current particle
    char* particle_data = m_particle_buffer.data() + m_buffer_position * m_particle_size;
    
    // Write particle data to buffer
    size_t offset = 0;
    
    // Position (convert from cm to m)
    const Vector& pos = particle.getPosition();
    double pos_arr[3] = {pos.x(), pos.y() , pos.z()};
    memcpy(particle_data + offset, pos_arr, 3 * sizeof(double));
    offset += 3 * sizeof(double);
    
    // Direction
    const Vector& dir = particle.getDirection();
    double dir_arr[3] = {dir.x(), dir.y(), dir.z()};
    memcpy(particle_data + offset, dir_arr, 3 * sizeof(double));
    offset += 3 * sizeof(double);
    
    // Energy (convert from meV to eV)
    double energy = particle.getEKin();
    memcpy(particle_data + offset, &energy, sizeof(double));
    offset += sizeof(double);
    
    // Time (convert from ms to s)
    double time = particle.getTime();
    memcpy(particle_data + offset, &time, sizeof(double));
    offset += sizeof(double);
    
    // Weight
    double weight = particle.getWeight();
    memcpy(particle_data + offset, &weight, sizeof(double));
    offset += sizeof(double);
    
    // PDG code
    int pdgcode = particle.getPDG();
    memcpy(particle_data + offset, &pdgcode, sizeof(int));
    offset += sizeof(int);
    
    // Custom fields
    double sp = particle.getSurviveP();
    memcpy(particle_data + offset, &sp, sizeof(double));
    offset += sizeof(double);
    
    memcpy(particle_data + offset, &scatterNumber, sizeof(int));
    offset += sizeof(int);
    
    double energyLoss = particle.getEKin0()-particle.getEKin();
    memcpy(particle_data + offset, &energyLoss, sizeof(double));
    offset += sizeof(double);
    
    m_buffer_position++;
    m_current_size++;
    
    // Flush buffer if full
    if (m_buffer_position >= m_chunk_size) {
        flushBuffer();
    }
}

void HDF5BinaryWrite::addCustomField(const std::string& fieldName, hid_t dataType) {
    // This method allows adding custom fields dynamically
    m_field_names.push_back(fieldName);
    m_field_types.push_back(dataType);
    m_field_offsets.push_back(m_particle_size);
    m_particle_size += H5Tget_size(dataType);
    
    // Need to recreate the dataset with new structure
    // For simplicity, this implementation uses fixed fields
}

hid_t HDF5BinaryWrite::createCompoundType() {
    hid_t compound_type = H5Tcreate(H5T_COMPOUND, m_particle_size);
    
    size_t current_offset = 0;
    for (size_t i = 0; i < m_field_names.size(); ++i) {
        H5Tinsert(compound_type, m_field_names[i].c_str(), current_offset, m_field_types[i]);
        current_offset += H5Tget_size(m_field_types[i]);
    }
    
    return compound_type;
}

void HDF5BinaryWrite::extendDataset() {
    hsize_t new_dims[1] = {m_current_size};
    H5Dset_extent(m_dataset_id, new_dims);
    
    hid_t file_space = H5Dget_space(m_dataset_id);
    H5Sclose(file_space);
}

void HDF5BinaryWrite::flushBuffer() {
    if (m_buffer_position == 0) return;
    
    extendDataset();
    
    // Select hyperslab for writing
    hsize_t start[1] = {m_current_size - m_buffer_position};
    hsize_t count[1] = {m_buffer_position};
    
    hid_t mem_space = H5Screate_simple(1, count, NULL);
    hid_t file_space = H5Dget_space(m_dataset_id);
    
    H5Sselect_hyperslab(file_space, H5S_SELECT_SET, start, NULL, count, NULL);
    
    // Write buffer to file
    hid_t compound_type = createCompoundType();
    H5Dwrite(m_dataset_id, compound_type, mem_space, file_space, H5P_DEFAULT, m_particle_buffer.data());
    
    H5Tclose(compound_type);
    H5Sclose(mem_space);
    H5Sclose(file_space);
    
    // Reset buffer
    m_buffer_position = 0;
}

void HDF5BinaryWrite::writeBufferToFile() {
    flushBuffer();
}

} // namespace Prompt