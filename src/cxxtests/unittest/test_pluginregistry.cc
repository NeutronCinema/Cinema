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

#include "../doctest.h"

#include "PTPluginModel.hh"
#include "PTPluginRegistry.hh"
#include "PTException.hh"

#include <cstdlib>
#include <iostream>
#include <memory>
#include <utility>
#include <vector>

namespace pt = Prompt;

// The plugin binaries are built as MODULE libraries next to the tests; their
// paths are passed through the environment by CMakeLists (see the
// CINPLUGIN_TEST_* properties there).
static std::string envPath(const char* name)
{
  const char *v = std::getenv(name);
  return (v && *v) ? std::string(v) : std::string();
}

TEST_CASE("test_pluginregistry")
{
  auto helloPath = envPath("CINPLUGIN_TEST_HELLO");
  auto badabiPath = envPath("CINPLUGIN_TEST_BADABI");
  REQUIRE_MESSAGE(!helloPath.empty(), "CINPLUGIN_TEST_HELLO not set by the build");
  REQUIRE_MESSAGE(!badabiPath.empty(), "CINPLUGIN_TEST_BADABI not set by the build");

  auto &reg = pt::Plugin::PluginRegistry::instance();

  // A wrong-ABI plugin is refused with a diagnostic, before any registration.
  CHECK_THROWS_AS(reg.loadFile(badabiPath), pt::Error::BadInput);

  // The good plugin loads, registers, and serves its namespace.
  reg.loadFile(helloPath);
  const auto *factory = reg.lookup("hello");
  REQUIRE(factory != nullptr);
  CHECK(std::string(factory->ns()) == "hello");
  CHECK(std::string(factory->description()).find("constant-xs") != std::string::npos);

  // list() exposes the namespace for the future python-side listing.
  bool found = false;
  for(auto &pr : reg.list())
    found |= (pr.first == "hello");
  CHECK(found);

  // produce() validates keys and builds a working model.
  auto model = factory->produce(pt::Plugin::CfgView("physics=hello;xs=2.5"));
  REQUIRE(model != nullptr);
  CHECK(model->numberDensity() == doctest::Approx(0.01));
  CHECK(model->crossSection(1.0, nullptr) == doctest::Approx(2.5));

  // A bad key must name the namespace and the key (no parCount boilerplate).
  CHECK_THROWS_AS(factory->produce(pt::Plugin::CfgView("physics=hello;nonsense=1")),
                  pt::Error::BadInput);

  // sample() runs end-to-end through the ABI surfaces: a valid unit outcome,
  // random numbers drawn only from the injected Rng.
  class FixedRng final : public pt::Plugin::Rng {
  public:
    double next() override { return 0.25; }
  } rng;
  pt::Plugin::SampleResult out{};
  double dir[3] = {0.0, 0.0, 1.0};
  model->sample(2.0, dir, rng, out, nullptr);
  CHECK(out.final_ekin == doctest::Approx(2.0));
  CHECK(out.absorbed == false);

  // Loading the same plugin file again is a duplicate-name error.
  CHECK_THROWS_AS(reg.loadFile(helloPath), pt::Error::BadInput);

  // A multi-model factory emits its set in registration order, each emission
  // tagged with the role that selects the host bias key, and applies the
  // host's channel-enablement semantics (non-positive role bias skips the
  // emission). This is the shape that keeps a plugin Abs+Scat pair
  // byte-identical to the builtin paths.
  const auto *pairFactory = reg.lookup("hellopair");
  REQUIRE(pairFactory != nullptr);
  pt::Plugin::CfgView pairCfg("physics=hellopair;xs_a=1.5;xs_s=4.0");
  pt::Plugin::HostBias bothOn;
  std::vector<std::pair<pt::Plugin::ModelRole, double>> emitted;
  pairFactory->produceAll(pairCfg, bothOn,
    [&emitted](std::unique_ptr<pt::Plugin::ScatterModel> m, pt::Plugin::ModelRole role)
    { emitted.emplace_back(role, m->crossSection(1.0, nullptr)); });
  REQUIRE(emitted.size() == 2);
  CHECK(emitted[0].first == pt::Plugin::ModelRole::Scatter);
  CHECK(emitted[0].second == doctest::Approx(4.0));
  CHECK(emitted[1].first == pt::Plugin::ModelRole::Absorption);
  CHECK(emitted[1].second == doctest::Approx(1.5));

  // A skipped channel is never constructed: zero scatter bias leaves only
  // the absorption emission.
  emitted.clear();
  pt::Plugin::HostBias scatOff;
  scatOff.scatter = 0.0;
  pairFactory->produceAll(pairCfg, scatOff,
    [&emitted](std::unique_ptr<pt::Plugin::ScatterModel> m, pt::Plugin::ModelRole role)
    { emitted.emplace_back(role, m->crossSection(1.0, nullptr)); });
  REQUIRE(emitted.size() == 1);
  CHECK(emitted[0].first == pt::Plugin::ModelRole::Absorption);

  // The absorbing emission terminates particles and deposits its full energy.
  std::unique_ptr<pt::Plugin::ScatterModel> absModel;
  pt::Plugin::SampleResult absOut{};
  pairFactory->produceAll(pairCfg, bothOn,
    [&](std::unique_ptr<pt::Plugin::ScatterModel> m, pt::Plugin::ModelRole role)
    { if(role == pt::Plugin::ModelRole::Absorption) absModel = std::move(m); });
  REQUIRE(absModel != nullptr);
  CHECK(absModel->declaresAbsorption());
  absModel->sample(3.0, dir, rng, absOut, nullptr);
  CHECK(absOut.absorbed == true);
  CHECK(absOut.deposition == doctest::Approx(3.0));

  // Single-model factories default to exactly one Scatter-role emission.
  emitted.clear();
  factory->produceAll(pt::Plugin::CfgView("physics=hello;xs=2.5"), bothOn,
    [&emitted](std::unique_ptr<pt::Plugin::ScatterModel> m, pt::Plugin::ModelRole role)
    { emitted.emplace_back(role, m->crossSection(1.0, nullptr)); });
  REQUIRE(emitted.size() == 1);
  CHECK(emitted[0].first == pt::Plugin::ModelRole::Scatter);
  CHECK(emitted[0].second == doctest::Approx(2.5));

  // The pair factory's plain produce() is a deliberate error: the namespace
  // only makes sense as a model set.
  CHECK_THROWS_AS(pairFactory->produce(pairCfg), pt::Error::BadInput);

  // Unknown namespaces look up to null with a clean error path elsewhere.
  CHECK(reg.lookup("no_such_namespace") == nullptr);
}
