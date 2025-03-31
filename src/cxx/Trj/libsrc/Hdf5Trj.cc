#include "Hdf5Trj.hh"
#include <algorithm>
#include <utility>      // std::move

//FIXME: HDF5 is extremly slow to read subdataset, if it is no continuous.
//load the full trajectory as the workaround to deal with readAtomTrj

Hdf5Trj::Hdf5Trj(std::string fileName)
:Trajectory(fileName)
{
  m_file_id = H5Fopen (m_fileName.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);

  //species
  readDataset("particles/all/species/value", m_species);
  m_nAtom = m_species.dim[1];
  m_nFrame = m_species.dim[0];

  // //check position data are in 1d array
  // Data<double> pos;
  // // do not load data, only assign the shape
  // readDataset("particles/all/position/value", pos, false);
  // if(pos.dim[0]==m_nAtom*m_nFrame*3 && pos.dim[1]==1 && pos.dim[2]==1)
  // {
  //   std::cout << "atomic position data are in 1D format" << std::endl;
  // }
  // else if (pos.dim[0]==m_nFrame && pos.dim[1]==m_nAtom && pos.dim[2]==3)
  // {
  //   std::cout << "atomic position data will be formatted into 1D" << std::endl;
  //   //enable write
  //   H5Fclose(m_file_id);
  //   m_file_id = H5Fopen (m_fileName.c_str(),  H5F_ACC_RDWR, H5P_DEFAULT);
  //   hid_t dataset_id = H5Dopen2 (m_file_id, "particles/all/position/value", H5P_DEFAULT);
  //   hid_t memspace_id = H5Dget_space (dataset_id);
  //   hsize_t oneDSize[3]{3*m_nAtom*m_nFrame, 1, 1};
  //   H5Dset_extent(dataset_id, oneDSize);
  //   H5Fclose(m_file_id);
  //   //read only again
  //   m_file_id = H5Fopen (m_fileName.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT);
  //   H5Dclose(dataset_id);
  //   H5Sclose(memspace_id);
  // }
  // else
  // {
  //   throw std::runtime_error ("atomic position data are in a wrong shape " );
  // }


  if(!m_species.shrink2D())
    throw std::runtime_error ("unable to shirnk m_species");
  m_species.print("m_species");

  //find atom type and count
  auto temp(m_species.vec);
  std::sort(temp.begin(), temp.end());
  auto endOfUnique = std::unique(temp.begin(), temp.end());
  temp.erase(endOfUnique, temp.end());
  std::swap(m_atomType,temp);
  m_atomCount.resize(0);
  m_atomCount.resize(m_atomType.size(), 0.);

  for(unsigned i=0;i<m_atomType.size();i++)
  {
    for(auto v: m_species.vec)
    {
      if(v==m_atomType[i])
      {
        m_atomCount[i]++;
      }
    }
  }

  //find number of molecule
  m_nMolecule = gcd(m_atomCount);
  m_nAtomPerMole = m_nAtom/m_nMolecule;
  std::cout << "m_nMolecule " << m_nMolecule << std::endl;
  std::cout << m_nAtom << " atoms, " <<  m_nFrame << " frames. "<< std::endl;

  //time
  readDataset("particles/all/species/time", m_time);
  m_time.print("m_time");
  m_deltaT = (m_time.vec[1]- m_time.vec[0])*1e-15;
  std::cout << "m_deltaT " << m_deltaT << std::endl;

  //box
  readDataset("particles/all/box/edges/value", m_box);
  if(m_box.shrink2D())
    std::cout << "Simulation is found in fixed volume" << std::endl;
  m_box.print("m_box");

  double lengthSum(0.);
  for(auto v: m_box.vec)
    lengthSum += v;

  m_qResolution=2*M_PI/(lengthSum/m_box.vec.size());
  std::cout << "m_qResolution " << m_qResolution << std::endl;

  if(m_box.dim[0]==m_nFrame)
  {
    m_fixed_box_size = false;
  }
  else if(m_box.dim[0]==3)
  {
    m_fixed_box_size = true;
  }
  else {
    throw std::runtime_error ("Can not determine if the simulation box has a fixed size");
  }
}

Hdf5Trj::~Hdf5Trj()
{
  H5Fclose(m_file_id);
}

void Hdf5Trj::cacheAtomTrj()
{
  std::cout << "caching atomic trjectory " << std::endl;
  readDataset("particles/all/position/value", m_fullTrj);
  m_fullTrj.swapaxes3d();
  m_fullTrj.print("m_fullTrj");
}

void Hdf5Trj::clearCache()
{
  m_fullTrj.clear();
}



void Hdf5Trj::readFrame(unsigned frameID, std::vector<double> &frame) const
{
  hid_t dataset_id = H5Dopen2 (m_file_id, "particles/all/position/value", H5P_DEFAULT);
  hid_t memspace_id = H5Dget_space (dataset_id);
  hsize_t offset[3]{frameID,0,0}, count[3]{1,m_nAtom,3}, block[3]{1,1,1}, stride[3]{1,1,1};
  herr_t status = H5Sselect_hyperslab(memspace_id, H5S_SELECT_SET, offset, stride, count, block);
  hsize_t dims[3]{1,m_nAtom,3};
  hid_t mid = H5Screate_simple(3, dims, NULL);
  frame.resize(m_nAtom*3);
  status = H5Dread(dataset_id, H5T_NATIVE_DOUBLE, mid, memspace_id, H5P_DEFAULT, frame.data());

  H5Sclose(mid);
  H5Dclose(dataset_id);
  H5Sclose(memspace_id);
}


const double* const Hdf5Trj::readAtomTrj(unsigned atomOffset) const
{
  if(m_fullTrj.dim.size()!=3)//pre-loaded full trjectory
  {
    throw std::runtime_error("trajectory is not pre-loaded");
  }
  return m_fullTrj.vec.data() + atomOffset*m_nFrame*3;
}


void Hdf5Trj::readAtomTrj(unsigned atomOffset, std::vector<double> &atomTrj) const
{
  atomTrj.resize(m_nFrame*3);

  if(m_fullTrj.dim.size()==3)//pre-loaded full trjectory
  {
    std::copy(m_fullTrj.vec.data() + atomOffset*m_nFrame*3, m_fullTrj.vec.data()+(atomOffset+1)*m_nFrame*3, atomTrj.begin());
  }
  else
  {
    hid_t dataset_id = H5Dopen2 (m_file_id, "particles/all/position/value", H5P_DEFAULT);
    hid_t memspace_id = H5Dget_space (dataset_id);
    hsize_t offset[3]{0,atomOffset,0}, count[3]{m_nFrame,1,3}, block[3]{1,1,1}, stride[3]{1,1,1};
    // hsize_t offset[3]{0,atomOffset,0}, count[3]{m_nFrame,1,1}, block[3]{1,1,3}, stride[3]{1,1,1};

    herr_t status = H5Sselect_hyperslab(memspace_id, H5S_SELECT_SET, offset, stride, count, block);
    hsize_t dims[3]{m_nFrame,1,3};
    hid_t mid = H5Screate_simple(3, dims, NULL);
    atomTrj.resize(m_nFrame*3);
    status = H5Dread(dataset_id, H5T_NATIVE_DOUBLE, mid, memspace_id, H5P_DEFAULT, atomTrj.data());

    H5Sclose(mid);
    H5Dclose(dataset_id);
    H5Sclose(memspace_id);
  }
}

template <class T>
void Hdf5Trj::readDataset(const std::string &name, Data<T> &vec, bool loadData) {
    // Open the dataset within the HDF5 file
    hid_t dataset_id = H5Dopen2(m_file_id, name.c_str(), H5P_DEFAULT);
    if (dataset_id < 0) {
        // If dataset opening fails, throw an appropriate error
        throw std::runtime_error("Failed to open dataset: " + name);
    }

    // Get the dataspace associated with the dataset
    hid_t memspace_id = H5Dget_space(dataset_id);
    if (memspace_id < 0) {
        // In case getting the dataspace fails, close the dataset and throw an error
        H5Dclose(dataset_id);
        throw std::runtime_error("Failed to get dataspace for dataset: " + name);
    }

    // Get the rank (number of dimensions) of the dataspace
    int rank = H5Sget_simple_extent_ndims(memspace_id);
    if (rank < 0) {
        // If getting the rank fails, close the dataset and dataspace, then throw an error
        H5Dclose(dataset_id);
        H5Sclose(memspace_id);
        throw std::runtime_error("Failed to get rank of dataspace for dataset: " + name);
    }

    // Resize the dimension container of 'vec' based on the rank
    vec.dim.resize(rank);
    // Get the dimensions of the dataspace and store them in 'vec.dim'
    // Here, make sure the type of vec.dim elements is compatible with hsize_t
    // If there's a type mismatch error like before, check the type of vec.dim
    if (H5Sget_simple_extent_dims(memspace_id, vec.dim.data(), NULL) < 0) {
        H5Dclose(dataset_id);
        H5Sclose(memspace_id);
        throw std::runtime_error("Failed to get dimensions for dataset: " + name);
    }

    // Calculate the total number of elements in the dataset (number of points)
    hsize_t numPoints = H5Sget_simple_extent_npoints(memspace_id);
    if (numPoints < 0) {
        H5Dclose(dataset_id);
        H5Sclose(memspace_id);
        throw std::runtime_error("Failed to get number of points in dataset: " + name);
    }

    // Resize the data container 'vec.vec' based on the number of points
    vec.vec.resize(numPoints);

    // Only read the data if loadData is true
    if (loadData) {
        // Get the datatype of the dataset
        hid_t datatype = H5Tcopy(H5Dget_type(dataset_id));
        if (datatype < 0) {
            H5Dclose(dataset_id);
            H5Sclose(memspace_id);
            throw std::runtime_error("Failed to copy datatype for dataset: " + name);
        }

        // Based on the type T, use the appropriate HDF5 read function
        if constexpr (std::is_same_v<T, double>) {
            if (H5Dread(dataset_id, H5T_NATIVE_DOUBLE, H5S_ALL, H5S_ALL, H5P_DEFAULT, vec.vec.data()) < 0) {
                H5Tclose(datatype);
                H5Dclose(dataset_id);
                H5Sclose(memspace_id);
                throw std::runtime_error("Failed to read dataset as double type: " + name);
            }
        } else if constexpr (std::is_same_v<T, int>) {
            if (H5Dread(dataset_id, H5T_NATIVE_INT, H5S_ALL, H5S_ALL, H5P_DEFAULT, vec.vec.data()) < 0) {
                H5Tclose(datatype);
                H5Dclose(dataset_id);
                H5Sclose(memspace_id);
                throw std::runtime_error("Failed to read dataset as int type: " + name);
            }
          } else if constexpr (std::is_same_v<T, unsigned int>) {
            if (H5Dread(dataset_id, H5T_NATIVE_UINT, H5S_ALL, H5S_ALL, H5P_DEFAULT, vec.vec.data()) < 0) {
                H5Tclose(datatype);
                H5Dclose(dataset_id);
                H5Sclose(memspace_id);
                throw std::runtime_error("Failed to read dataset as int type: " + name);
            }
        } else {
            // For other types not explicitly handled yet, close relevant resources and throw an error
            H5Tclose(datatype);
            H5Dclose(dataset_id);
            H5Sclose(memspace_id);
            throw std::runtime_error("Unsupported data type for reading dataset: " + name);
        }

        // Close the copied datatype
        H5Tclose(datatype);
    }

    // Close the dataset and dataspace identifiers to release resources
    H5Dclose(dataset_id);
    H5Sclose(memspace_id);
}

void* Hdf5Trj_new(const char* fileName)
{
  return static_cast<void *>(new Hdf5Trj (std::string(fileName)));
}

double Hdf5Trj_getDeltaT(void* self)
{
  return static_cast<Hdf5Trj *>(self)->getDeltaT();
}

double Hdf5Trj_getQResolution(void* self)
{
  return static_cast<Hdf5Trj *>(self)->getQResolution();
}

void Hdf5Trj_delete(void* self)
{
  delete static_cast<Hdf5Trj *>(self);
}

void Hdf5Trj_frequency(void* self, void *fre )
{
  Data<double> temp = static_cast<Hdf5Trj *>(self)->unweightedFrequency();
  auto freCase = static_cast< Data<double> *>(fre);
  *freCase = std::move(temp);
}

void Hdf5Trj_vDosSqw(void* self, unsigned firstAtomPos,void *vdos,
               void *Q , void *omega,
               void* sqw)
{
  static_cast<Hdf5Trj *>(self)->vDosSqw(firstAtomPos,  *static_cast< Data<double> *>(vdos),  *static_cast< Data<double> *>(omega),
  *static_cast< std::vector<double>  *>(Q),  *static_cast< Data<double> *>(sqw) );
}

void Hdf5Trj_structFactSqw(void* self, unsigned qSize ,
                void *structFact, void *scl)
{
  static_cast<Hdf5Trj *>(self)->structFactSqw(qSize, *static_cast< Data<double> *>(structFact),
  						 *static_cast< std::vector<double>  *>(scl) );
}
