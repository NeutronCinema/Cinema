#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
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

import json
import os

from Cinema.Interface.Utils import findData

# Location of the raw runs' data: '<host>/<root>/<run-dir>'. Host and archive
# root are site-specific, so they come from the environment and default to
# empty - the data_path entries below then stay run-relative neutral paths.
MPI2022_DATA_HOST = os.environ.get('MPI2022_DATA_HOST', '')
MPI2022_DATA_ROOT = os.environ.get('MPI2022_DATA_ROOT', '')

def mpi2022DataPath(rel):
    # Join the configured host and archive root with a run's relative path,
    # skipping the empty parts.
    parts = [p.strip('/') for p in (MPI2022_DATA_HOST, MPI2022_DATA_ROOT, rel) if p]
    return '/'.join(parts)

MPIRuns={}

MPIRuns['Background_NoAu'] = {'run': 'run17261', 'data_path':mpi2022DataPath('da/mpi_data/17261')}
MPIRuns['Vholder_NoAu_1'] = {'run': 'run17262', 'estimated_height(mm)': 90.0, 'estimated_dmin(mm)': 8.9517, 'estimated_dmax(mm)': 9.5317, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017262')}
MPIRuns['Vholder_NoAu_2'] = {'run': 'run17282', 'estimated_height(mm)': 90.0, 'dmin(mm)': 8.9517, 'dmax(mm)': 9.5317, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017282')}
MPIRuns['Vholder&Vstick_NoAu'] = {'run': 'run17327', 'Vstick_height(mm)': 30.04, 'Vstick_d(mm)': 8.84, 'estimated_dmin(mm)': 8.9517, 'estimated_dmax(mm)': 9.5317, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017327')}
MPIRuns['D2O_NoAu'] = {'run': 'run17672', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017672')}
MPIRuns['H2O_NoAu'] = {'run': 'run17673', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017673')}
MPIRuns['NaH2PO4_D2O_NoAu'] = {'run': 'run17674', 'volume(ml)': 0.9, 'height_sample(mm)': 14.2419, 'dmin(mm)': 8.97, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017674')}
MPIRuns['NaH2PO4_H2O_NoAu'] = {'run': 'run17675', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7367, 'dmin(mm)': 8.98, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017675')}
MPIRuns['CuSO4_D2O_NoAu'] = {'run': 'run17676', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3056, 'dmin(mm)': 8.95, 'dmax(mm)': 9.54, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017676')}
MPIRuns['CuSO4_H2O_NoAu'] = {'run': 'run17677', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7899, 'dmin(mm)': 8.93, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017677')}

MPIRuns['D2O_Au'] = {'run': 'run17678', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017678')}
MPIRuns['H2O_Au'] = {'run': 'run17679', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017679')}
MPIRuns['NaH2PO4_D2O_Au'] = {'run': 'run17680', 'volume(ml)': 0.9, 'height_sample(mm)': 14.2419, 'dmin(mm)': 8.97, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017680')}
MPIRuns['NaH2PO4_H2O_Au'] = {'run': 'run17681', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7367, 'dmin(mm)': 8.98, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017681')}
MPIRuns['CuSO4_D2O_Au'] = {'run': 'run17682', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3056, 'dmin(mm)': 8.95, 'dmax(mm)': 9.54, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017682')}
MPIRuns['CuSO4_H2O_Au'] = {'run': 'run17683', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7899, 'dmin(mm)': 8.93, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017683')}

MPIRuns['D2O_Au_CCR05_roomtem'] = {'run': 'run17685', 'temperature': '293K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017685')}
MPIRuns['D2O_Au_CCR05_ice'] = {'run': 'run17686', 'temperature': '243K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017686')}
MPIRuns['H2O_Au_CCR05_roomtem1'] = {'run': 'run17687', 'temperature': '293K±3K', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017687')}
MPIRuns['H2O_Au_CCR05_roomtem2'] = {'run': 'run17689', 'temperature': '293K±3K', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017689')}
MPIRuns['H2O_Au_CCR05_ice'] = {'run': 'run17690', 'temperature': '243K±3K', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017690')}

MPIRuns['Background_NoAu_CCR05_roomtem'] = {'run': 'run17381', 'data_path':mpi2022DataPath('da/mpi_data/17381')}
MPIRuns['Vstick_NoAu_CCR05_roomtem'] = {'run': 'run17382', 'Vstick_height(mm)': 30.04, 'Vstick_d(mm)': 8.84, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017382')}
MPIRuns['Vholder_NoAu_CCR05_roomtem'] = {'run': 'run17383', 'estimated_height(mm)': 90.0, 'estimated_dmin(mm)': 8.9517, 'estimated_dmax(mm)': 9.5317, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017383')}
MPIRuns['H2O_NoAu_CCR05_roomtem'] = {'run': 'run17693', 'temperature': '293K±3K', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017693')}
MPIRuns['H2O_NoAu_CCR05_ice1'] = {'run': 'run17694', 'temperature': '243K±3K', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017694')}
MPIRuns['H2O_NoAu_CCR05_ice2'] = {'run': 'run17695', 'temperature': '213K±3K', 'volume(ml)': 0.3, 'height_sample(mm)': 4.7792, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017695')}
MPIRuns['D2O_NoAu_CCR05_roomtem1'] = {'run': 'run17696', 'temperature': '293K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017696')}
MPIRuns['D2O_NoAu_CCR05_roomtem2'] = {'run': 'run17699', 'temperature': '293K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017699')}
MPIRuns['D2O_NoAu_CCR05_ice'] = {'run': 'run17700', 'temperature': '213K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017700')}

MPIRuns['Background_NoAu_CCR06_roomtem'] = {'run': 'run17337', 'data_path':mpi2022DataPath('da/mpi_data/17337')}
MPIRuns['Vstick_NoAu_CCR06_roomtem'] = {'run': 'run17338', 'Vstick_height(mm)': 30.04, 'Vstick_d(mm)': 8.84, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017338')}
MPIRuns['Vholder_NoAu_CCR06_roomtem'] = {'run': 'run17339', 'estimated_height(mm)': 90.0, 'estimated_dmin(mm)': 8.9517, 'estimated_dmax(mm)': 9.5317, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017339')}
MPIRuns['D2O_NoAu_CCR06_roomtem'] = {'run': 'run17701', 'temperature': '302K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017701')}
MPIRuns['D2O_NoAu_CCR06_ice1'] = {'run': 'run17702', 'temperature': '50K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017702')}
MPIRuns['D2O_NoAu_CCR06_ice2'] = {'run': 'run17703', 'temperature': '12.8K±3K', 'volume(ml)': 0.9, 'height_sample(mm)': 14.3376, 'dmin(mm)': 8.94, 'dmax(mm)': 9.53, 'data_path':mpi2022DataPath('mpiexp2022/RUN0017703')}

ModuleCorner_Exp={}
with open('%s'%findData('MPI2022Exp/moduleCornerDetector_Exp.json')) as jsonFile:
    ModuleCorner_Exp=json.load(jsonFile)  
# print(ModuleCorner_Exp['module10802']['left_bottom']['pos']) 
