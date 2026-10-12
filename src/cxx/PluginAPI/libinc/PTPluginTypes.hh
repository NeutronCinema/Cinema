#ifndef Prompt_PluginTypes_hh
#define Prompt_PluginTypes_hh

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

#include <cstdint>
#include <string>
#include "PTCfgParser.hh"

// Value types of the cinema physics-model plugin ABI.
//
// UNITS ARE LOAD-BEARING (the mm/cm benchmark incident proved it):
//   - energies are eV everywhere (transport asserts Unit::eV == 1),
//   - microscopic cross sections are mm^2 (barn-scaled; Unit::barn = 1e-28 m^2),
//   - number densities are atoms/A^3 at the plugin boundary (the same unit as
//     NCrystal's Info::numberDensity and the user key density_per_aa3); the
//     host converts to atoms/mm^3 before multiplying xs to macroscopic mm^-1,
//   - positions are mm, directions are unit vectors in the global frame,
//   - times are ms (the internal transport unit).
// The typed aliases below exist so a plugin author signing a signature with
// the wrong unit at least sees it in review.

namespace Prompt::Plugin {

using PluginEkin = double;        // eV
using PluginXs = double;          // mm^2 (microscopic) unless documented otherwise
using PluginNumDensity = double;  // atoms/A^3

// Bump on ANY change of the plugin-facing headers (PTPluginTypes.hh,
// PTPluginModel.hh, PTPluginFactory.hh). The loader refuses a plugin whose
// cinplugin_abi() differs, turning "mysterious crash after a cinema upgrade"
// into "rebuild your plugin".
#define PROMPT_PLUGIN_ABI 1

// Outcome of one sampled collision. Plain POD, returned through the out
// parameter of ScatterModel::sample.
struct SampleResult {
  double final_ekin;    // eV, post-collision energy of the primary
  double deposition;    // eV, energy deposited locally
  double final_dir[3];  // unit vector, post-collision direction (global frame)
  bool   absorbed;      // true => the primary terminates at this collision
};

// Random service handed to sample(). One method; the host binds it to the
// shared transport RNG stream, so plugin sampling is reproducible with the
// same seed exactly like the builtin models.
class Rng {
public:
  virtual double next() = 0;
protected:
  ~Rng() = default;
};

// A secondary the plugin wants to push onto the transport stack. Positions in
// mm, energy in eV, time in ms. NOTE: the host overrides pos with the current
// particle's position (a plugin cannot know it); pos exists in the struct to
// keep the layout stable for future offline-sampling hosts.
struct SecondarySpec {
  int    pdg;
  double ekin;
  double pos[3];
  double dir[3];
  double time;
  double weight;
};

// Host-implemented sink receiving secondaries during sample(). May be null:
// a plugin whose producesSecondaries() is false never receives one.
class SecondarySink {
public:
  virtual void add(const SecondarySpec&) = 0;
protected:
  ~SecondarySink() = default;
};

// Parsed key=value view of ONE cfg string, following the grammar of
// Prompt::CfgParser: sections split on ';', each 'key=value', single-quoted
// spans may contain ';'. Host-reserved keys (physics, scatter_bias, abs_bias,
// absorp_in_weight, density) are consumed by the host and never surface here.
class CfgView {
public:
  explicit CfgView(std::string raw);

  bool        has(const char* key) const;
  std::string str(const char* key) const;                // throws BadInput if missing
  std::string strOr(const char* key, const char* dflt) const;
  double      number(const char* key) const;             // throws BadInput if missing/not numeric
  std::vector<std::string> keys() const;                 // all keys except the host-reserved ones
  std::string ns() const { return m_ns; }                // value of the host physics= key
  std::string raw() const { return m_raw; }

private:
  std::string m_raw;
  std::string m_ns;
  // mutable: CfgParser::StringCfg's accessors predate const correctness,
  // while CfgView's plugin-facing surface must be const.
  mutable CfgParser::StringCfg m_parsed;
};

}

#endif
