import os
import numpy as np
from Cinema.Experiment.Analyser import PixelLocator, IDFLoader


# file = '<idf-dir>/module10702.txt'
# pxlID = np.loadtxt(file, dtype=int, usecols=(0))
# pxlPos = np.loadtxt(file, usecols=(1,2,3))*1e3 #meter to mm
# particlePos = np.array([-0.505989, -0.199400, -1.226291])*1e3 #meter to mm
# pixel = PixelLocator(pxlID, pxlPos)
# id, dist = pixel.locate(particlePos)
# print(id, dist)

# Directory with the MPI2022 IDF pixel-layout files: point CINEMA_MPI2022_DATA
# at a site-specific absolute location; the default is the relative path
# 'mpi_experiment_2022/idf' (resolved against the working directory).
idf_dir = os.environ.get('CINEMA_MPI2022_DATA')
if not idf_dir:
    print('Warning: CINEMA_MPI2022_DATA is not set - falling back to the '
          "relative default 'mpi_experiment_2022/idf'")
    idf_dir = 'mpi_experiment_2022/idf'
idf = IDFLoader(idf_dir)
tree = idf.query('module10701')
# Directory holding the pixel-wise '*.wgt' simulation outputs: point
# CINEMA_MPI2022_RUNDATA at it; when unset, fall back to the run-relative
# default with a warning.
rundata_dir = os.environ.get('CINEMA_MPI2022_RUNDATA')
if not rundata_dir:
    print('Warning: CINEMA_MPI2022_RUNDATA is not set - falling back to the '
          "relative default 'cinemaRunData/2022_6_02/HW_Num_4_10_10'")
    rundata_dir = 'cinemaRunData/2022_6_02/HW_Num_4_10_10'
dd = tree.generateDD(os.path.join(rundata_dir, '*300*.wgt'))
print(dd.dd[257].keys())