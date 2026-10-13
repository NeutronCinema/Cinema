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

#include "PromptCore.hh"
#include "PTLauncher.hh"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace pt = Prompt;

// These wrappers are bound from python by symbol name through ctypes, so
// they keep C linkage and are declared here directly. They used to be
// declared in PTPython.hh with void returns; that header is no longer
// included because the bridged subset below returns an int status instead
// (no other translation unit calls these functions from C++, so the stale
// declarations in PTPython.hh stay harmless).
//
// The error protocol is documented next to pt_last_error() in
// PTPythonResource.cc, which also implements pt_bridge_record_error: a
// bridged wrapper catches any escaping C++ exception, records its message in
// a thread-local buffer and returns a nonzero status (0 = ok, 1 =
// Prompt::Error::Exception, 2 = other std::exception or unknown) instead of
// letting the exception cross the extern "C" boundary into ctypes, where it
// would abort the whole python process with SIGABRT.
extern "C" {
double pt_rand_generate();
void* pt_Launcher_getInstance();
void pt_Launcher_setSeed(void* obj, uint64_t seed);
int pt_Launcher_loadGeometry(void* obj, const char* fileName);
size_t pt_Launcher_getTrajSize(void* obj);
void pt_Launcher_getTrajectory(void* obj, double *trj);
int pt_Launcher_go(void* obj, uint64_t numParticle, double printPrecent, bool recordTrj, bool timer, bool save2Disk);
int pt_Launcher_setGun(void *obj, const char* cfg);
int pt_Launcher_simOneEvent(void *obj, bool recordTrj);
int pt_Launcher_goWithSecondStack(void *obj, uint64_t numParticle, size_t *out);
int pt_Launcher_secondStackSize(void *obj, size_t *out);
int pt_Launcher_dumpSecondStack(void *obj, char *buf, size_t cap, size_t *written);
int pt_Launcher_loadSecondStack(void *obj, const char *data, size_t len, uint64_t normaliseTo);
int pt_Launcher_extractSecondStack(void *obj, const char *data, size_t len,
                                   const char *idxData, size_t nIdx,
                                   char *buf, size_t cap, size_t *written);

const char* pt_last_error();
int pt_bridge_record_error();
}

double pt_rand_generate()
{
  return pt::Singleton<pt::SingletonPTRand>::getInstance().generate();
}

void* pt_Launcher_getInstance()
{
  return static_cast<void *>(std::addressof(pt::Singleton<pt::Launcher>::getInstance()));
}

void pt_Launcher_setSeed(void* obj, uint64_t seed)
{
  std::cout << "set random seed: " << seed << std::endl;
  static_cast<pt::Launcher *>(obj)->setSeed(seed);
}

// Bridged: an unreadable or broken geometry file is reported as a nonzero
// status plus pt_last_error() instead of aborting the host process.
int pt_Launcher_loadGeometry(void* obj, const char* fileName)
{
  try {
    static_cast<pt::Launcher *>(obj)->loadGeometry(std::string(fileName));
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

size_t pt_Launcher_getTrajSize(void* obj)
{
  return static_cast<pt::Launcher *>(obj)->getTrajSize();
}

void pt_Launcher_getTrajectory(void* obj, double *trj)
{
  auto &trjv = static_cast<pt::Launcher *>(obj)->getTrajectory();
  for(const auto &v: trjv)
  {
    *(trj++) = v.x();
    *(trj++) = v.y();
    *(trj++) = v.z();
  }
}

// Bridged: a bad numParticle/printPrecent combination (e.g. go(0) with the
// timer enabled, rejected by ProgressMonitor) is reported as a nonzero
// status plus pt_last_error() instead of aborting the host process.
int pt_Launcher_go(void* obj, uint64_t numParticle, double printPrecent, bool recordTrj, bool timer, bool save2Disk)
{
  try {
    static_cast<pt::Launcher *>(obj)->go(numParticle, printPrecent, recordTrj, timer, save2Disk);
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

// Bridged: an unknown gun= key (or any other cfg rejection in the gun
// factory) is reported as a nonzero status plus pt_last_error() instead of
// aborting the host process.
int pt_Launcher_setGun(void *obj, const char* cfg)
{
  try {
    static_cast<pt::Launcher *>(obj)->setGun(cfg);
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

// Bridged: same reason as pt_Launcher_simOneEvent — the deferred gidi build
// runs inside the first event of the second-stack cycle.
int pt_Launcher_goWithSecondStack(void *obj, uint64_t numParticle, size_t *out)
{
  try {
    *out = static_cast<pt::Launcher *>(obj)->goWithSecondStack(numParticle);
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

// Bridged: the fission-bank exchange for the parallel power iteration.
// Two-step dump (query the blob size, then fill a caller-allocated buffer)
// follows the getTrajSize/getTrajectory idiom; the load validates the
// format, so a corrupted or foreign blob surfaces as DataLoadError through
// the bridge instead of crossing into ctypes.
int pt_Launcher_secondStackSize(void *obj, size_t *out)
{
  try {
    *out = static_cast<pt::Launcher *>(obj)->secondStackSize();
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

int pt_Launcher_dumpSecondStack(void *obj, char *buf, size_t cap, size_t *written)
{
  try {
    std::vector<char> blob = static_cast<pt::Launcher *>(obj)->exportSecondStack();
    if(blob.size() > cap)
      PROMPT_THROW2(CalcError, "second-stack blob needs " << blob.size() << " bytes, caller provided " << cap);
    memcpy(buf, blob.data(), blob.size());
    *written = blob.size();
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

int pt_Launcher_loadSecondStack(void *obj, const char *data, size_t len, uint64_t normaliseTo)
{
  try {
    std::vector<char> blob(data, data + len);
    static_cast<pt::Launcher *>(obj)->importSecondStack(blob, normaliseTo);
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}

// Bridged like loadSecondStack: record selection for the nearest-neighbour
// bank exchange. The indices arrive as a packed buffer of native-endian
// uint64 (python side passes a numpy uint64 array's bytes); the output
// buffer is sized exactly by the caller (12-byte header + 84 bytes per
// selected record, both fixed by the record layout in PTStackManager.cc).
int pt_Launcher_extractSecondStack(void *obj, const char *data, size_t len,
                                   const char *idxData, size_t nIdx,
                                   char *buf, size_t cap, size_t *written)
{
  try {
    std::vector<char> blob(data, data + len);
    std::vector<uint64_t> indices(nIdx);
    if(nIdx)
      memcpy(indices.data(), idxData, nIdx * sizeof(uint64_t));
    std::vector<char> out = static_cast<pt::Launcher *>(obj)->extractSecondStack(blob, indices);
    if(out.size() > cap)
      PROMPT_THROW2(CalcError, "second-stack extract needs " << out.size() << " bytes, caller provided " << cap);
    memcpy(buf, out.data(), out.size());
    *written = out.size();
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}


// Bridged: since the lazy gidi rewrite the first event builds the pending
// gidi models, and a data problem (DataLoadError) must surface as a nonzero
// status plus pt_last_error() instead of aborting the host process.
int pt_Launcher_simOneEvent(void *obj, bool recordTrj)
{
  try {
    static_cast<pt::Launcher *>(obj)->simOneEvent(recordTrj);
    return 0;
  }
  catch (...) {
    return pt_bridge_record_error();
  }
}
