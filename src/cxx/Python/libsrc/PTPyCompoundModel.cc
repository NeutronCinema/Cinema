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

#include "PTPython.hh"
#include "PTModelCollection.hh"
#include "PTParticleProcess.hh"

void* pt_makeModelCollection(const char * cfg)
{
  auto *proc = new Prompt::ParticleProcess(cfg);
  return static_cast<void *>(proc);
}


void pt_deleteModelCollection(void* obj)
{
  delete static_cast<Prompt::ParticleProcess *>(obj);
}

double pt_ModelCollection_getxs(void* obj, int pdg, double ekin)
{
  Prompt::Vector dir;
  return static_cast<Prompt::ParticleProcess *>(obj)
      ->getModelCollection()->totalCrossSection(pdg, ekin, dir)/Prompt::Unit::barn;
}

double pt_ModelCollection_generate(void* obj, double ekin, double dx, double dy, double dz)
{
  Prompt::Vector dir(dx, dy, dz);
  if(dir.isStrictNullVector())
    PROMPT_THROW2(BadInput, "null incident direction (direction sampler would loop forever)");

  auto *coll = static_cast<Prompt::ParticleProcess *>(obj)->getModelCollection();

  // Arm the cross-section cache with this exact (ekin, dir) inquiry before
  // sampling: pickAndSample declines to sample whenever the cache does not
  // match, so a cold generate() would silently return a dummy result without
  // sampling anything.
  coll->totalCrossSection(2112, ekin, dir);

  return coll->pickAndSample(ekin, dir).final_ekin;
}

// Checked variants (0 status + pt_last_error, the protocol of the
// Launcher/Volume/makeModelCollection_checked bridges), implemented in
// PTPythonResource.cc. Since the P2 lazy rewrite the deferred gidi build
// runs inside totalCrossSection on this offline path, so a data problem
// would otherwise surface here as a C++ exception crossing the raw ctypes
// boundary — aborting the interpreter — instead of the catchable error the
// eager build used to raise at configuration time.
extern "C" int pt_bridge_record_error();

int pt_ModelCollection_getxs_checked(void* obj, int pdg, double ekin, double *out)
{
  try {
    Prompt::Vector dir;
    *out = static_cast<Prompt::ParticleProcess *>(obj)
        ->getModelCollection()->totalCrossSection(pdg, ekin, dir)/Prompt::Unit::barn;
    return 0;
  } catch(...) { return pt_bridge_record_error(); }
}

int pt_ModelCollection_generate_checked(void* obj, double ekin, double dx, double dy, double dz, double *out)
{
  try {
    Prompt::Vector dir(dx, dy, dz);
    if(dir.isStrictNullVector())
      PROMPT_THROW2(BadInput, "null incident direction (direction sampler would loop forever)");

    auto *coll = static_cast<Prompt::ParticleProcess *>(obj)->getModelCollection();
    coll->totalCrossSection(2112, ekin, dir);
    *out = coll->pickAndSample(ekin, dir).final_ekin;
    return 0;
  } catch(...) { return pt_bridge_record_error(); }
}
