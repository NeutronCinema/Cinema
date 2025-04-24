################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2024 Prompt developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################

project(prompt_core)

find_package(HDF5 REQUIRED COMPONENTS C)
message(STATUS "FOUND HDF5:  ${HDF5_INCLUDE_DIR}")

# Add an option to enable/disable GIDI
option(ENABLE_GIDI "Enable the GIDI module" ON)

# Add an option to enable/disable  Catima
option(ENABLE_CATIMA "Enable the  Catima module" ON)

option(DEBUG_PTS "Enable the GIDI module" OFF)

option(BUILD_WITH_OPENMP "Build OpenMP" ON)
find_package(OpenMP REQUIRED)

#add source
file(GLOB COR_SRC "${PROJECT_SOURCE_DIR}/Core/libsrc/*.cc")
file(GLOB RND_SRC "${PROJECT_SOURCE_DIR}/Rand/libsrc/*.cc")
file(GLOB UTL_SRC "${PROJECT_SOURCE_DIR}/Utils/libsrc/*.cc")
file(GLOB ANA_SRC "${PROJECT_SOURCE_DIR}/Ana/libsrc/*.cc")
file(GLOB PAR_SRC "${PROJECT_SOURCE_DIR}/Particles/libsrc/*.cc")
file(GLOB BUK_SRC "${PROJECT_SOURCE_DIR}/ModelBulk/libsrc/*.cc")
file(GLOB RTR_SRC "${PROJECT_SOURCE_DIR}/ModelRayTracing/libsrc/*.cc")
file(GLOB SUR_SRC "${PROJECT_SOURCE_DIR}/ModelSurface/libsrc/*.cc")
file(GLOB GEO_SRC "${PROJECT_SOURCE_DIR}/Geometry/libsrc/*.cc")
file(GLOB GUN_SRC "${PROJECT_SOURCE_DIR}/Gun/libsrc/*.cc")
file(GLOB MAT_SRC "${PROJECT_SOURCE_DIR}/Material/libsrc/*.cc")
file(GLOB PYN_SRC "${PROJECT_SOURCE_DIR}/Python/libsrc/*.cc")
file(GLOB RAC_SRC "${PROJECT_SOURCE_DIR}/Process/libsrc/*.cc")
file(GLOB TRJ_SRC "${PROJECT_SOURCE_DIR}/Trj/libsrc/*.cc")
file(GLOB MCPL_SRC "${PROJECT_SOURCE_DIR}/MCPL/libsrc/*.cc" )
file(GLOB NC_SRC "${PROJECT_SOURCE_DIR}/ModelBulk/NCrystal/libsrc/*.cc")
file(GLOB CT_SRC "${PROJECT_SOURCE_DIR}/ModelBulk/Catima/libsrc/*.cc")
file(GLOB GD_SRC "${PROJECT_SOURCE_DIR}/ModelBulk/Gidi/libsrc/*.cc")

ADD_LIBRARY(${PROJECT_NAME} SHARED ${MCPL_SRC} ${COR_SRC} ${RAC_SRC} ${SUR_SRC} ${RND_SRC} 
                                ${UTL_SRC} ${RTR_SRC} ${ANA_SRC} ${PAR_SRC} ${BUK_SRC} 
                                ${GEO_SRC} ${MAT_SRC} ${PYN_SRC} ${GUN_SRC} ${TRJ_SRC} 
                                ${NC_SRC} ${CT_SRC} ${GD_SRC}) 

# Add the definition based on the option value for the library target
if(ENABLE_CATIMA)
    target_compile_definitions(${PROJECT_NAME} PUBLIC ENABLE_CATIMA)
endif()

if(ENABLE_GIDI)
    target_compile_definitions(${PROJECT_NAME} PUBLIC ENABLE_GIDI)
endif()

if(DEBUG_PTS)
    target_compile_definitions(${PROJECT_NAME} PUBLIC DEBUG_PTS)
endif()

find_package(Python REQUIRED COMPONENTS Interpreter)

FIND_LIBRARY(mcpl mcpl ${KDS_LIB})
FIND_LIBRARY(kdsource kdsource ${KDS_LIB})

# FIND_LIBRARY(gidiplus gidiplus ${GIDIPLUS_LIB})


target_link_libraries(${PROJECT_NAME} PUBLIC ${GIDIPLUS_LIB}/libgidiplus.a NCrystal::NCrystal VecGeom::vecgeom VecGeom::vgdml fftw3 ${HDF5_LIBRARIES} OpenMP::OpenMP_CXX  ${mcpl} ${kdsource})

#fixme remove openmp
target_include_directories( ${PROJECT_NAME}
    PUBLIC
    ${PROJECT_SOURCE_DIR}/Core/libinc
    ${PROJECT_SOURCE_DIR}/Rand/libinc
    ${PROJECT_SOURCE_DIR}/Utils/libinc
    ${PROJECT_SOURCE_DIR}/Ana/libinc
    ${PROJECT_SOURCE_DIR}/Particles/libinc
    ${PROJECT_SOURCE_DIR}/ModelBulk/NCrystal/libinc
    ${PROJECT_SOURCE_DIR}/ModelBulk/Catima/libinc
    ${PROJECT_SOURCE_DIR}/ModelBulk/Gidi/libinc
    ${PROJECT_SOURCE_DIR}/ModelBulk/libinc
    ${PROJECT_SOURCE_DIR}/ModelRayTracing/libinc
    ${PROJECT_SOURCE_DIR}/ModelSurface/libinc
    ${PROJECT_SOURCE_DIR}/Geometry/libinc
    ${PROJECT_SOURCE_DIR}/Material/libinc
    ${PROJECT_SOURCE_DIR}/Gun/libinc
    ${PROJECT_SOURCE_DIR}/Process/libinc
    ${PROJECT_SOURCE_DIR}/Python/libinc
    ${PROJECT_SOURCE_DIR}/Trj/libinc
    ${PROJECT_SOURCE_DIR}/MCPL/libinc
    ${VECGEOM_INCLUDE_DIRS}
    ${NCrystal_INCDIR}
    ${HDF5_INCLUDE_DIR}
    ${MCPL_INCDIR} #KDSource files are in this DIR as well
    # PRIVATE
    ${GIDIPLUS_INCDIR}
)
