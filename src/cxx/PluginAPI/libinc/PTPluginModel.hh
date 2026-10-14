#ifndef Prompt_PluginModel_hh
#define Prompt_PluginModel_hh

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

#include "PTPluginTypes.hh"

// THE stable surface of the cinema physics-model plugin ABI: one abstract
// base for scattering physics (Prompt::Plugin::ScatterModel) and its
// per-collision contract. Freeze this interface across a minor release
// series; bump PROMPT_PLUGIN_ABI (PTPluginTypes.hh) on any change.
//
// Ownership and threading rules for plugin authors:
//   - ModelFactory objects are stateless and const; they may be called from
//     several threads at once (one produce() per thread_local universe).
//   - A ScatterModel instance is owned by exactly one thread's universe for
//     its whole life, so mutable per-thread scratch members are fine. Static
//     or global mutable state is NOT: it would race across threads.
//   - produce() must be deterministic from the cfg string alone: the host
//     deduplicates materials by cfg string and shares one model set between
//     all volumes configured identically.

namespace Prompt::Plugin {

class ScatterModel {
public:
  virtual ~ScatterModel() = default;

  // ---- metadata (queried once, at produce time) -------------------------

  // atoms/A^3. Return <= 0 if the model is naturally macroscopic: then
  // crossSection()/absorptionCrossSection() are read as macroscopic mm^-1
  // instead of microscopic mm^2, and the host cfg key density=D is rejected.
  virtual PluginNumDensity numberDensity() const = 0;

  // Valid open energy interval in eV. Outside it the host will not call the
  // model (the transport skips or errors before crossing the boundary).
  virtual PluginEkin emin() const { return 0.0; }
  virtual PluginEkin emax() const { return 1e30; }

  // true if crossSection depends on the incident direction. Oriented models
  // pay a direction transform per collision on the host side.
  virtual bool oriented() const { return false; }

  // true if this model IS an absorption channel (it terminates particles and
  // its absorptionCrossSection is meaningful). Exactly one declaring model is
  // allowed per material; it is elected for the absorp_in_weight host mode.
  virtual bool declaresAbsorption() const { return false; }

  virtual bool producesSecondaries() const { return false; }

  // ---- per-collision surface --------------------------------------------

  // Microscopic cross section in mm^2 (macroscopic mm^-1 when
  // numberDensity() <= 0), incident energy in eV, dir may be null for
  // non-oriented models. Called only inside [emin, emax).
  virtual PluginXs crossSection(PluginEkin ekin, const double* dir) const = 0;

  // Absorption cross section, same units; only called when
  // declaresAbsorption() is true. Bias is applied by the host.
  virtual PluginXs absorptionCrossSection(PluginEkin ekin, const double* dir) const
  {
    (void)ekin; (void)dir;
    return 0.0;
  }

  // Sample one collision: write the outcome into out and push secondaries
  // into sink (which may be null). sink->add may be called any number of
  // times; the host owns the particles afterwards. Random numbers come ONLY
  // from rng, never from an engine the plugin seeds itself.
  virtual void sample(PluginEkin ekin, const double* dir, Rng& rng,
                      SampleResult& out, SecondarySink* sink) = 0;
};

}

#endif
