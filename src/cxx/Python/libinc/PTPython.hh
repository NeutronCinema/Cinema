#ifndef Prompt_Python_hh
#define Prompt_Python_hh

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

bool pt_Gidi_compiled();

// Converters
double pt_eKin2k(double ekin);
double pt_angleCosine2Q(double anglecosine, double enin_eV, double enout_eV);
double pt_wl2ekin( double wl);
double pt_ekin2wl( double ekin) ;
double pt_ekin2speed( double ekin);
double pt_speed2ekin( double v);

// random
double pt_rand_generate();

// Prompt::Launcher
void* pt_Launcher_getInstance();
void pt_Launcher_setSeed(void* obj, uint64_t seed);
void pt_Launcher_loadGeometry(void* obj, const char* fileName);
size_t pt_Launcher_getTrajSize(void* obj);
void pt_Launcher_getTrajectory(void* obj, double *trj);
void pt_Launcher_go(void* obj, uint64_t numParticle, double printPrecent, bool recordTrj, bool timer, bool save2Disk);
void pt_Launcher_setGun(void *obj, const char* cfg);
void pt_Launcher_simOneEvent(void *obj, bool recordTrj);
size_t pt_Launcher_goWithSecondStack(void *obj, uint64_t numParticle);

// Prompt::HistBase
void pt_HistBase_merge(void* obj, void* obj2);
void pt_HistBase_setWeight(void *obj, double *data, size_t n);
void pt_HistBase_setHit(void *obj, double *data, size_t n);
void pt_HistBase_setWW(void *obj, double *data, size_t n);
double pt_HistBase_getXMin(void* obj);
double pt_HistBase_getXMax(void* obj);
double pt_HistBase_getTotalWeight(void* obj);
double pt_HistBase_getAccWeight(void* obj);
double pt_HistBase_getOverflow(void* obj);
double pt_HistBase_getUnderflow(void* obj);
double pt_HistBase_getTotalHit(void* obj);
size_t pt_HistBase_getDataSize(void* obj);
void pt_HistBase_scale(void* obj, double scale);
void pt_HistBase_reset(void* obj);
void pt_HistBase_getRaw(void* obj, double* data);
void pt_HistBase_getHit(void* obj, double* data);
void pt_HistBase_getww(void *obj, double *data);
void pt_HistBase_getww_2dalias(void *obj, double *data);

unsigned pt_HistBase_dimension(void* obj);
const char* pt_HistBase_getName(void* obj);


// Prompt::Hist1D
void* pt_Hist1D_new(double xmin, double xmax, unsigned nbins, bool linear);
void pt_Hist1D_delete(void* obj);
void pt_Hist1D_getEdge(void* obj, double* edge);
void pt_Hist1D_getWeight(void* obj, double* w);
void pt_Hist1D_getHit(void* obj, double* h);
unsigned pt_Hist1D_getNumBin(void* obj); 
void pt_Hist1D_fill(void* obj, double val, double weight);
void pt_Hist1D_fillmany(void* obj, size_t n, double* val, double* weight);

// Prompt::Est1D
void* pt_Est1D_new(double xmin, double xmax, unsigned nbins, bool linear);
void pt_Est1D_delete(void* obj);
void pt_Est1D_fill(void* obj, double val, double weight, double error);
void pt_Est1D_fillmany(void* obj, size_t n, double* val, double* weight, double* error);

// Prompt::Hist2D
void* pt_Hist2D_new(double xmin, double xmax, unsigned nxbins,
                    double ymin, double ymax, unsigned nybins);
void pt_Hist2D_delete(void* obj);
void pt_Hist2D_getWeight(void* obj, double* w);
void pt_Hist2D_getDensity(void* obj, double* d);
void pt_Hist2D_getHit(void* obj, double* h);
void pt_Hist2D_fill(void* obj, double xval, double yval, double weight);
void pt_Hist2D_fillmany(void* obj, size_t n, double* xval, double* yval, double* weight);
void pt_Hist2D_merge(void* obj, void* obj2);
double pt_Hist2D_getYMin(void* obj);
double pt_Hist2D_getYMax(void* obj);
unsigned  pt_Hist2D_getNBinX(void* obj);
unsigned  pt_Hist2D_getNBinY(void* obj);

// Prompt::MCPLBinaryWrite
#include "mcpl.h"
void* pt_MCPLBinaryWrite_new(const char *fn, bool enable_double=false, bool enable_extra3double=false, 
                bool enable_extraUnsigned=false);
void pt_MCPLBinaryWrite_delete(void* obj);
void pt_MCPLBinaryWrite_write(void* obj, mcpl_particle_t par);
void pt_MCPLBinaryWrite_close(void* obj);

// XS python interface
void* pt_makeModelCollection(const char * cfg);
void pt_deleteModelCollection(void* obj);
double pt_ModelCollection_getxs(void* obj, int pdg, double ekin);
double pt_ModelCollection_generate(void* obj, double ekin);

// Prompt::GidiSetting
void* pt_GidiSetting_getInstance();

double pt_GidiSetting_getGidiThreshold(void* obj);
void pt_GidiSetting_setGidiThreshold(void* obj, double t);

const char * pt_GidiSetting_getGidiPops(void* obj);
void pt_GidiSetting_setGidiPops(void* obj, const char *s);

const char * pt_GidiSetting_getGidiMap(void* obj);
void pt_GidiSetting_setGidiMap(void* obj, const char *s);

bool pt_GidiSetting_getEnableGidi(void* obj); 
void pt_GidiSetting_setEnableGidi(void* obj, bool t);

bool pt_GidiSetting_getEnableGidiPowerIteration(void* obj);
void pt_GidiSetting_setEnableGidiPowerIteration(void* obj, bool t);

bool pt_GidiSetting_getGammaTransport(void* obj);
void pt_GidiSetting_setGammaTransport(void* obj, bool t);

double pt_nccalNumDensity(const char *s);  

void pt_merge_mcpl(const char* file_output, unsigned nfiles, const char ** files);
#ifdef __cplusplus
}
#endif

#endif
