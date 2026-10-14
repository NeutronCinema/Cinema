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

// StackManager on synthetic tracks: main/second stack placement of primaries
// and secondaries, the unweighted-particle bookkeeping that guards pop(),
// scalceSecondary weight correction, and normaliseSecondStack resizing.
// StackManager is a per-thread singleton, so every case drains both stacks
// first to stay independent of case order.

#include "../doctest.h"

#include "PTStackManager.hh"
#include "PTParticle.hh"
#include "PTNeutron.hh"
#include "PTException.hh"
#include "PTRandCanonical.hh"
#include "PTVector.hh"

#include <memory>
#include <vector>

namespace pt = Prompt;

namespace {

// Re-seed the shared prompt RNG (used by normaliseSecondStack shuffling).
void seedStackRng(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

// Drain both stacks; only valid when the unweighted counter is balanced,
// which every case below guarantees before returning.
void drainStacks(pt::StackManager &sm)
{
  while(!sm.empty())
    (void)sm.pop();
  if(sm.getNumParticleInSecondStack())
  {
    sm.swapStack(); // requires an empty main stack
    while(!sm.empty())
      (void)sm.pop();
  }
}

pt::StackManager &stack()
{
  return pt::Singleton<pt::StackManager>::getInstance();
}

std::unique_ptr<pt::Particle> makeParticle(double ekin, double weight)
{
  auto p = std::make_unique<pt::Particle>(ekin, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p->setWeight(weight);
  return p;
}

// Move the second stack into the main stack and collect the particle weights
// (the second stack has no direct element accessor).
std::vector<double> harvestSecondStack(pt::StackManager &sm)
{
  std::vector<double> weights;
  if(sm.getNumParticleInSecondStack())
  {
    REQUIRE(sm.empty());
    sm.swapStack();
  }
  while(!sm.empty())
  {
    auto p = sm.pop();
    REQUIRE(p != nullptr);
    weights.push_back(p->getWeight());
  }
  return weights;
}

bool oneOf(double w, const std::vector<double> &set)
{
  for(double s : set)
    if(w == doctest::Approx(s).epsilon(1e-12))
      return true;
  return false;
}

} // namespace

TEST_CASE("stackmanager_add_grows_main_stack")
{
  auto &sm = stack();
  drainStacks(sm);
  CHECK(sm.empty());
  sm.add(makeParticle(1., 1.));
  sm.add(makeParticle(2., 1.));
  sm.add(makeParticle(3., 1.));
  CHECK(sm.getNumParticleInStack() == 3u);
  CHECK_FALSE(sm.empty());
  // pop returns the most recently added particle first
  auto p = sm.pop();
  REQUIRE(p != nullptr);
  CHECK(p->getEKin() == doctest::Approx(3.).epsilon(1e-12));
  drainStacks(sm);
  CHECK(sm.empty());
  CHECK(sm.getUnweightedNum() == 0);
}

TEST_CASE("stackmanager_addsecondary_to_main_copies_and_counts")
{
  auto &sm = stack();
  drainStacks(sm);
  sm.add(makeParticle(10., 1.));
  pt::Particle proto(1.5, pt::Vector(0., 1., 0.), pt::Vector(1., 1., 1.));
  proto.setWeight(0.25);
  sm.addSecondary(proto, false);
  CHECK(sm.getNumParticleInStack() == 2u);
  CHECK(sm.getUnweightedNum() == 1);
  // the stored particle is a copy: later changes to the prototype do not leak
  proto.setWeight(9.);
  // popping is blocked while an uncorrected secondary exists
  CHECK_THROWS_AS(sm.pop(), pt::Error::CalcError);
  // correct the bookkeeping, then confirm the stored copy kept weight 0.25
  sm.scalceSecondary(0, 1.);
  CHECK(sm.getUnweightedNum() == 0);
  auto s = sm.pop();
  REQUIRE(s != nullptr);
  CHECK(s->getWeight() == doctest::Approx(0.25).epsilon(1e-12));
  drainStacks(sm);
  CHECK(sm.empty());
}

TEST_CASE("stackmanager_addsecondary_to_second_stack")
{
  auto &sm = stack();
  drainStacks(sm);
  sm.add(makeParticle(1., 1.));
  pt::Particle proto(0.5, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  proto.setWeight(0.1);
  sm.addSecondary(proto, true);
  sm.addSecondary(proto, true);
  CHECK(sm.getNumParticleInSecondStack() == 2u);
  CHECK(sm.getNumParticleInStack() == 1u);
  // second-stack entries carry no unweighted bookkeeping
  CHECK(sm.getUnweightedNum() == 0);
  drainStacks(sm);
  CHECK(sm.getNumParticleInSecondStack() == 0u);
}

TEST_CASE("stackmanager_scalce_secondary_weight_correction")
{
  auto &sm = stack();
  drainStacks(sm);
  // three weighted secondaries with distinct weights
  pt::Particle p1(1., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p1.setWeight(1.);
  pt::Particle p2(2., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p2.setWeight(2.);
  pt::Particle p3(3., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  p3.setWeight(3.);
  sm.addSecondary(p1, false);
  sm.addSecondary(p2, false);
  sm.addSecondary(p3, false);
  REQUIRE(sm.getUnweightedNum() == 3);
  // lastidx counts backwards from the most recent secondary
  sm.scalceSecondary(0, 2.); // p3: 3 -> 6
  CHECK(sm.getUnweightedNum() == 2);
  sm.scalceSecondary(1, 3.); // p2: 2 -> 6
  CHECK(sm.getUnweightedNum() == 1);
  sm.scalceSecondary(2, 0.5); // p1: 1 -> 0.5
  CHECK(sm.getUnweightedNum() == 0);
  // pop order is LIFO; verify the corrected weights come back out
  auto q3 = sm.pop();
  REQUIRE(q3 != nullptr);
  CHECK(q3->getWeight() == doctest::Approx(6.).epsilon(1e-12));
  auto q2 = sm.pop();
  REQUIRE(q2 != nullptr);
  CHECK(q2->getWeight() == doctest::Approx(6.).epsilon(1e-12));
  auto q1 = sm.pop();
  REQUIRE(q1 != nullptr);
  CHECK(q1->getWeight() == doctest::Approx(0.5).epsilon(1e-12));
  CHECK(sm.empty());
}

TEST_CASE("stackmanager_normalise_second_stack_resizes")
{
  auto &sm = stack();
  drainStacks(sm);
  seedStackRng(20260901); // normaliseSecondStack shuffles/picks with the shared RNG
  const std::vector<double> original = {1., 2., 3., 4., 5.};
  for(double w : original)
  {
    pt::Particle p(w, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    p.setWeight(w);
    sm.addSecondary(p, true);
  }
  REQUIRE(sm.getNumParticleInSecondStack() == 5u);
  // growing duplicates randomly chosen entries; weights are not rescaled
  sm.normaliseSecondStack(8);
  CHECK(sm.getNumParticleInSecondStack() == 8u);
  auto grown = harvestSecondStack(sm);
  REQUIRE(grown.size() == 8u);
  for(double w : grown)
    CHECK_MESSAGE(oneOf(w, original), "normaliseSecondStack must not rescale weights");
  CHECK(sm.empty());
  CHECK(sm.getNumParticleInSecondStack() == 0u);

  // shrinking keeps a random subset, again with unmodified weights
  for(double w : original)
  {
    pt::Particle p(w, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    p.setWeight(w);
    sm.addSecondary(p, true);
  }
  sm.normaliseSecondStack(3);
  CHECK(sm.getNumParticleInSecondStack() == 3u);
  auto shrunk = harvestSecondStack(sm);
  REQUIRE(shrunk.size() == 3u);
  for(double w : shrunk)
    CHECK(oneOf(w, original));
  CHECK(sm.empty());
  CHECK(sm.getUnweightedNum() == 0);
}

TEST_CASE("stackmanager_normalise_empty_second_stack_throws")
{
  auto &sm = stack();
  drainStacks(sm);
  REQUIRE(sm.getNumParticleInSecondStack() == 0u);
  CHECK_THROWS_AS(sm.normaliseSecondStack(4), pt::Error::CalcError);
  CHECK(sm.getNumParticleInSecondStack() == 0u);
}
