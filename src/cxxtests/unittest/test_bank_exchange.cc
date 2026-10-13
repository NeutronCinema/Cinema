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

#include <cstring>
#include <string>
#include <vector>

#include "../doctest.h"

#include "PTSingleton.hh"
#include "PTStackManager.hh"
#include "PTRandCanonical.hh"

namespace pt = Prompt;

namespace {

pt::StackManager &g_stack = pt::Singleton<pt::StackManager>::getInstance();

// A valid header for a zero-particle bank (the import path requires the
// magic even for an empty exchange, so "clear the bank" goes through it).
std::vector<char> emptyBankBlob()
{
  std::vector<char> b(12, 0); // magic + uint64 count
  memcpy(b.data(), "PKB1", 4);
  return b;
}

// A bank with every record field non-trivial: two neutrons and a photon,
// distinct directions (already unit, as transport leaves them), positions,
// energies, times, weights and survival probabilities.
void fillBank()
{
  g_stack.importSecondStack(emptyBankBlob(), 0); // start from an empty bank
  pt::Particle p1(1.234, pt::Vector(0.6, 0.8, 0.0), pt::Vector(1.5, -2.0, 3.25));
  p1.setTime(1e-5);
  p1.setWeight(1.0);
  p1.scaleSurviveP(0.75);
  pt::Particle p2(5e6, pt::Vector(0.0, -1.0, 0.0), pt::Vector(0.0, 0.0, 0.0));
  p2.setTime(2.5e-6);
  p2.setWeight(0.5);
  p2.scaleSurviveP(1.0);
  pt::Particle g(2.0, pt::Vector(-0.28, -0.96, 0.0), pt::Vector(4.0, 4.0, 0.0), 22);
  g.setTime(7.0e-6);
  g.setWeight(2.0);
  g.scaleSurviveP(0.25);
  g_stack.addSecondary(p1, true);
  g_stack.addSecondary(p2, true);
  g_stack.addSecondary(g, true);
}

} // namespace

TEST_CASE("bank roundtrip is byte-identical and field-faithful")
{
  fillBank();
  CHECK(g_stack.getNumParticleInSecondStack() == 3);

  std::vector<char> blob1 = g_stack.dumpSecondStack();
  REQUIRE(blob1.size() == 12 + 3 * 84u); // header + 3 packed records

  g_stack.importSecondStack(blob1, 3);
  std::vector<char> blob2 = g_stack.dumpSecondStack();
  CHECK(blob1 == blob2);

  // the bank lives in the second stack, which has no per-particle accessor;
  // swap it into the transport stack to inspect entries through pop()
  g_stack.swapStack();

  // pop is LIFO, so the first particle back out is the photon added last,
  // all fields verbatim
  std::unique_ptr<pt::Particle> p = g_stack.pop(); // own it: pop hands over the unique_ptr
  CHECK(p->getPDG() == 22);
  CHECK(p->getEKin() == doctest::Approx(2.0).scale(0.));
  CHECK(p->getTime() == doctest::Approx(7.0e-6).scale(0.));
  CHECK(p->getWeight() == doctest::Approx(2.0).scale(0.));
  CHECK(p->getSurviveP() == doctest::Approx(0.25).scale(0.));
  CHECK(p->getDirection() == pt::Vector(-0.28, -0.96, 0.0));
  CHECK(p->getPosition() == pt::Vector(4.0, 4.0, 0.0));
  // the bank had three particles; two remain (now in the transport stack;
  // swapStack refuses a non-empty transport stack, so they stay there —
  // later cases only inspect the second stack)
  CHECK(g_stack.getNumParticleInStack() == 2);
}

TEST_CASE("bank import truncates an oversized pool to the requested share")
{
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();
  g_stack.importSecondStack(blob, 1); // pooled exchange normalises to the local share
  CHECK(g_stack.getNumParticleInSecondStack() == 1);
}

TEST_CASE("a concatenated pool of per-rank blobs imports as the union")
{
  // rank A banks 3 particles, rank B banks 2; the python side joins the
  // raw dumps, each of which carries its own header
  fillBank();
  std::vector<char> pool = g_stack.dumpSecondStack();

  g_stack.importSecondStack(emptyBankBlob(), 0);
  pt::Particle p(0.5, pt::Vector(1.0, 0.0, 0.0), pt::Vector(0.1, 0.2, 0.3));
  g_stack.addSecondary(p, true);
  pt::Particle q(0.7, pt::Vector(0.0, 1.0, 0.0), pt::Vector(0.4, 0.5, 0.6));
  g_stack.addSecondary(q, true);
  std::vector<char> blob2 = g_stack.dumpSecondStack();
  pool.insert(pool.end(), blob2.begin(), blob2.end());

  g_stack.importSecondStack(pool, 5); // union of both banks, then normalise
  CHECK(g_stack.getNumParticleInSecondStack() == 5);
}

TEST_CASE("bank rejects foreign magic, short blobs and lying counts")
{
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();

  std::vector<char> foreign = blob;
  foreign[2] = 'X';
  CHECK_THROWS_AS(g_stack.importSecondStack(foreign, 1), pt::Error::DataLoadError);

  std::vector<char> short_(blob.begin(), blob.begin() + 8);
  CHECK_THROWS_AS(g_stack.importSecondStack(short_, 1), pt::Error::DataLoadError);

  std::vector<char> lying = blob;
  uint64_t inflated = 1000;
  memcpy(lying.data() + 4, &inflated, sizeof(inflated));
  CHECK_THROWS_AS(g_stack.importSecondStack(lying, 1), pt::Error::DataLoadError);

  // a failed import must leave the previous bank untouched
  CHECK(g_stack.getNumParticleInSecondStack() == 3);
}

TEST_CASE("empty bank roundtrip and the no-births-anywhere case")
{
  g_stack.importSecondStack(emptyBankBlob(), 0);
  std::vector<char> blob = g_stack.dumpSecondStack();
  CHECK(blob.size() == 12u);
  g_stack.importSecondStack(blob, 0); // legal: nothing was born on any rank
  CHECK(g_stack.getNumParticleInSecondStack() == 0);

  // mirroring the serial normaliseSecondStack: a real target on an empty
  // bank is the same CalcError the serial path raises
  CHECK_THROWS_AS(g_stack.importSecondStack(blob, 5), pt::Error::CalcError);
}

TEST_CASE("import with normaliseTo == 0 replaces the bank verbatim")
{
  // the nearest-neighbour exchange hands back an already exactly-sized
  // bank: normaliseTo == 0 must not resample (and not wipe, as a plain
  // resize-to-zero normalisation would)
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();
  g_stack.importSecondStack(emptyBankBlob(), 0);
  CHECK(g_stack.getNumParticleInSecondStack() == 0);
  g_stack.importSecondStack(blob, 0);
  CHECK(g_stack.getNumParticleInSecondStack() == 3);
}

TEST_CASE("absurd normalise targets are rejected, not truncated")
{
  // normaliseSecondStack subtracts the current bank size from the request;
  // a request near 2**32 truncated into int used to flip the sign (delete
  // branch, ~GB resize) or silently wrap (2**32+13 normalising to 13).
  // Both must now raise before any arithmetic.
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();
  CHECK_THROWS_AS(g_stack.importSecondStack(blob, (1ul << 31) + 100), pt::Error::CalcError);
  CHECK_THROWS_AS(g_stack.importSecondStack(blob, (1ul << 32) + 13), pt::Error::CalcError);
  CHECK_THROWS_AS(g_stack.importSecondStack(blob, 2000000000ul), pt::Error::CalcError);
  // the bank is untouched by the failed calls and a normal import still works
  CHECK(g_stack.getNumParticleInSecondStack() == 3);
  g_stack.importSecondStack(blob, 3);
  CHECK(g_stack.getNumParticleInSecondStack() == 3);
}

TEST_CASE("exact-size import is a resampling no-op: zero random draws")
{
  // the parallel exchange relies on this: after the pooled import the next
  // goWithSecondStack entry sees an already correct-sized bank and must
  // not perturb the transport RNG stream
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();
  auto *gen = pt::Singleton<pt::SingletonPTRand>::getInstance().getGenerator();
  auto state_before = *gen; // mt19937_64 is copyable and comparable
  g_stack.importSecondStack(blob, 3); // pool of 3, share of 3
  CHECK(*gen == state_before);

  g_stack.importSecondStack(blob, 2); // a real resample must consume draws
  CHECK_FALSE(*gen == state_before);
}

TEST_CASE("a pool of an empty and a non-empty blob upsamples to the share")
{
  g_stack.importSecondStack(emptyBankBlob(), 0);
  pt::Particle p(0.5, pt::Vector(1.0, 0.0, 0.0), pt::Vector(0.1, 0.2, 0.3));
  g_stack.addSecondary(p, true);
  std::vector<char> pool = emptyBankBlob(); // e.g. a rank that banked nothing
  std::vector<char> blob1 = g_stack.dumpSecondStack();
  pool.insert(pool.end(), blob1.begin(), blob1.end());
  g_stack.importSecondStack(pool, 3); // one real site, resampled to 3
  CHECK(g_stack.getNumParticleInSecondStack() == 3);
}

TEST_CASE("extractSecondStack picks records by local index, order preserved")
{
  // drain what earlier cases left in the transport stack so swapStack is
  // allowed again
  g_stack.importSecondStack(emptyBankBlob(), 0);
  while(g_stack.getNumParticleInStack())
    g_stack.pop();
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();

  // record 2 is the photon, record 0 the first neutron: the extracted
  // order {2, 0} round-trips verbatim, LIFO pops record 0 first
  std::vector<char> sub = g_stack.extractSecondStack(blob, {2, 0});
  REQUIRE(sub.size() == 12 + 2 * 84u);
  g_stack.importSecondStack(sub, 0);
  g_stack.swapStack();
  std::unique_ptr<pt::Particle> p = g_stack.pop();
  CHECK(p->getPDG() == 2112); // const_neutron_pgd
  CHECK(p->getEKin() == doctest::Approx(1.234).scale(0.));
  CHECK(p->getPosition() == pt::Vector(1.5, -2.0, 3.25));
  p = g_stack.pop(); // record 2: the photon
  CHECK(p->getPDG() == 22);
}

TEST_CASE("extractSecondStack concatenation, duplicates and empty selection")
{
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();

  // an extract of {2, 0} carries the singleton extracts' records, in the
  // index order, behind its own single header (each extract is a complete
  // blob, so the comparison is over the 84-byte record payloads)
  std::vector<char> sub = g_stack.extractSecondStack(blob, {2, 0});
  std::vector<char> s2 = g_stack.extractSecondStack(blob, {2});
  std::vector<char> s0 = g_stack.extractSecondStack(blob, {0});
  REQUIRE(sub.size() == 12 + 2 * 84u);
  CHECK(memcmp(sub.data() + 12, s2.data() + 12, 84) == 0);
  CHECK(memcmp(sub.data() + 12 + 84, s0.data() + 12, 84) == 0);

  // a duplicate index duplicates the record (with-replacement sampling)
  std::vector<char> dup = g_stack.extractSecondStack(blob, {1, 1});
  std::vector<char> s1 = g_stack.extractSecondStack(blob, {1});
  REQUIRE(dup.size() == 12 + 2 * 84u);
  CHECK(memcmp(dup.data() + 12, s1.data() + 12, 84) == 0);
  CHECK(memcmp(dup.data() + 12 + 84, s1.data() + 12, 84) == 0);

  // an empty selection is the valid 12-byte empty bank
  CHECK(g_stack.extractSecondStack(blob, {}) == emptyBankBlob());
}

TEST_CASE("extractSecondStack rejects bad blobs and out-of-range indices")
{
  fillBank();
  std::vector<char> blob = g_stack.dumpSecondStack();

  CHECK_THROWS_AS(g_stack.extractSecondStack(blob, {3}), pt::Error::DataLoadError);

  std::vector<char> pool = blob; // a concatenated two-blob pool has no
  pool.insert(pool.end(), blob.begin(), blob.end()); // meaningful local index
  CHECK_THROWS_AS(g_stack.extractSecondStack(pool, {0}), pt::Error::DataLoadError);

  std::vector<char> foreign = blob;
  foreign[2] = 'X';
  CHECK_THROWS_AS(g_stack.extractSecondStack(foreign, {0}), pt::Error::DataLoadError);

  std::vector<char> short_(blob.begin(), blob.begin() + 8);
  CHECK_THROWS_AS(g_stack.extractSecondStack(short_, {0}), pt::Error::DataLoadError);

  // count no longer matching the buffer size (a 3-record blob declaring 2)
  std::vector<char> lying = blob;
  uint64_t shrunk = 2;
  memcpy(lying.data() + 4, &shrunk, sizeof(shrunk));
  CHECK_THROWS_AS(g_stack.extractSecondStack(lying, {0}), pt::Error::DataLoadError);
}
