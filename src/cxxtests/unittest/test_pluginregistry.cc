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

  // Unknown namespaces look up to null with a clean error path elsewhere.
  CHECK(reg.lookup("no_such_namespace") == nullptr);
}
