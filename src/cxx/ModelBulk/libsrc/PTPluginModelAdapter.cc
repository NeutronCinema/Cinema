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

#include "PTPluginModelAdapter.hh"
#include "PTUnitSystem.hh"

#include <iostream>

namespace pt = Prompt;

namespace {
std::atomic<unsigned> g_pluginModelCounter{0};
}

pt::PluginModelAdapter::PluginModelAdapter(std::unique_ptr<Plugin::ScatterModel> plugin,
                                           const std::string &ns, double bias)
: DiscreteModel(ns+"#"+std::to_string(++g_pluginModelCounter), const_neutron_pgd,
                plugin->emin(), plugin->emax(), bias),
                m_plugin(std::move(plugin)), m_ns(ns)
{
  m_rngView.rng = &m_rng;
  m_oriented = m_plugin->oriented();
  // Election snapshot for ModelCollection::addPhysicsModel: a plugin that
  // declares itself the absorption channel plays the role NCrystalAbs plays
  // for the builtin stack (its ctor set m_res.dispeared the same way).
  m_res.dispeared = m_plugin->declaresAbsorption();
}

pt::PluginModelAdapter::~PluginModelAdapter()
{
  std::cout<<"Destructing plugin physics model " << m_modelName << ", energy between ["
           << m_modelvalid.minEkin << ", " << m_modelvalid.maxEkin << "]" << std::endl;
}

double pt::PluginModelAdapter::getCrossSection(double ekin) const
{
  if( m_plugin->oriented() )
    PROMPT_THROW(CalcError, "direction should be provided for oriented material");
  return m_plugin->crossSection(ekin, nullptr)*m_bias;
}

double pt::PluginModelAdapter::getCrossSection(double ekin, const Vector &dir) const
{
  double d[3] = {dir.x(), dir.y(), dir.z()};
  return m_plugin->crossSection(ekin, d)*m_bias;
}

const pt::SampledResult& pt::PluginModelAdapter::sampleReaction(double ekin, const Vector &dir) const
{
  // Plugins normalise the incident direction internally like NCrystal does:
  // on a null vector that division yields NaN and their loops never end.
  if(dir.isStrictNullVector())
    PROMPT_THROW(BadInput, "null incident direction, plugin direction sampling would loop forever");

  Plugin::SampleResult out;
  out.final_ekin = ekin;
  out.deposition = 0.0;
  out.final_dir[0] = dir.x();
  out.final_dir[1] = dir.y();
  out.final_dir[2] = dir.z();
  out.absorbed = false;

  // own copy of the incident direction: plugins may write out.final_dir
  // while still reading dir, so the two must not alias
  double inidir[3] = {dir.x(), dir.y(), dir.z()};
  m_plugin->sample(ekin, inidir, m_rngView, out,
                   m_plugin->producesSecondaries() ? &m_sinkView : nullptr);

  m_res.final_ekin = out.final_ekin;
  m_res.deposition = out.deposition;
  m_res.final_dir = Vector{out.final_dir[0], out.final_dir[1], out.final_dir[2]};
  m_res.dispeared = out.absorbed;
  return m_res;
}

void pt::PluginModelAdapter::SinkView::add(const Plugin::SecondarySpec& spec)
{
  // Offline sampling runs without a current particle; a null m_curParicle
  // would segfault here, so fall back to a stub particle at the origin
  // (same guard as GIDIModel::sampleReaction).
  auto &launcher = Singleton<Launcher>::getInstance();
  Particle offlineStub(0., Vector{0., 0., 1.}, Vector{0., 0., 0.});
  const Particle &primary = launcher.hasCurrentParticle()
      ? launcher.getCurrentParticle() : offlineStub;

  Vector pos = primary.getPosition();
  Vector dir{spec.dir[0], spec.dir[1], spec.dir[2]};

  // The generic Particle ctor already assigns the rest mass per pdg
  // (neutron mass for 2112, zero otherwise - correct for photons), which is
  // all the concrete Neutron/Gamma wrappers add; keep one code path.
  Particle sec(spec.ekin, dir, pos, spec.pdg);
  sec.setTime(spec.time);
  sec.setWeight(spec.weight);

  Singleton<StackManager>::getInstance().addSecondary(sec, false);
}
