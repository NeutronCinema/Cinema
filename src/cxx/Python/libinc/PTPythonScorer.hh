#ifndef Prompt_PTPythonScorer_hh
#define Prompt_PTPythonScorer_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        //
//                                                                            //
//  Copyright 2021-2024 Prompt developers                                     //
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

#ifdef __cplusplus
extern "C" {
#endif

void* pt_ScorerDeposition_new(const char* name, double xmin, double xmax, unsigned nbins, unsigned pdg, int type, bool linear, int groupid);

void* pt_ScorerESpectrum_new(const char* name, bool scoreTransfer, double xmin, double xmax, unsigned nbins, unsigned pdg, int type, int groupid, bool linear);

void* pt_ScorerTOF_new(const char* name, double xmin, double xmax, unsigned nbins, unsigned pdg, int type, int groupid);

void* pt_ScorerWlSpectrum_new(const char* name, double xmin, double xmax, unsigned nxbins, unsigned int pdg, int type, int groupid, bool linear);

void* pt_ScorerVolFluence_new(const char* name, double xmin, double xmax, unsigned nbins, double volme, unsigned pdg, int type, bool linear, int groupid);

void* pt_ScorerMultiScat_new(const char* name, double xmin, double xmax, unsigned nbins, unsigned pdg, int type, int groupid);

void* pt_ScorerDeltaMomentum_new(const char* name,
    double sourceSampleDist, double qmin, double qmax, unsigned numbin, unsigned int pdg,
    double mean_incident_dir_x, double mean_incident_dir_y, double mean_incident_dir_z,
    double sample_position_x, double sample_position_y, double sample_position_z, int type, 
    int method, bool linear);
     
void* pt_ScorerDirectSqw_new(const char* name, double qmin, double qmax, unsigned xbin, 
                            double ekinmin, double ekinmax, unsigned nybins, unsigned int pdg, int group_id,
                            double mod_smp_dist, double mean_ekin,
                            double mean_incident_dir_x, double mean_incident_dir_y, double mean_incident_dir_z,
                            double sample_position_x, double sample_position_y, double sample_position_z, int type);

void* pt_ScorerPSD_new(const char* name, double xmin, double xmax, unsigned nxbins, 
                    double ymin, double ymax, unsigned nybins, unsigned pdg, int ptstype, int psdtype, int groupid, bool isGlobal);

void pt_addMultiScatter1D(void* scatter, void* espScorer, int scatNumReq);

void pt_addMultiScatter2D(void* scatter, void* espScorer, int scatNumReq);

void* pt_KillerMCPL_new(const char* name, unsigned pdg, int groupid, bool kill, bool compress, int type);

#ifdef __cplusplus
}
#endif

#endif
