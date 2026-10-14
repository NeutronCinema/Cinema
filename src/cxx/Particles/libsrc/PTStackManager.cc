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

#include "PTStackManager.hh"
#include "PTRandCanonical.hh"
#include <bits/stdc++.h>

namespace {
  // Fission-bank record: the phase-space state a source site needs on
  // another rank. Everything else in Particle is either derived from these
  // (rest mass from pdg, via the normal constructors), per-process
  // bookkeeping (event/id/parentid, kill type, scratch counters), or fixed
  // at creation for bank particles (alive). The second stack only ever
  // holds plain Particle objects (addSecondary copies through the base
  // class), so the flat layout is lossless for every banked particle.
  //
  // dir/pos are stored as-is; import assigns them through setDirection()
  // instead of the normalising constructor path so that a dump-import-dump
  // roundtrip is byte-identical (the 4-arg constructor would re-normalise
  // an already unit direction and drift by an ulp).
#pragma pack(push, 1)
  struct BankRecord
  {
    double dir[3];
    double pos[3];
    double ekin;
    double time;
    double weight;
    double surviveP;
    int32_t pdg;
  };
#pragma pack(pop)
  static_assert(sizeof(BankRecord) == 10 * 8 + 4, "unexpected padding in BankRecord");

  const char BANK_MAGIC[4] = {'P', 'K', 'B', '1'};
  constexpr size_t BANK_HEADER = sizeof(BANK_MAGIC) + sizeof(uint64_t);
}

std::ostream& Prompt::operator << (std::ostream &o, const StackManager&s)
{
  o<<"********StackManager*****************\n";

  for(auto it=s.m_stack.begin();it!=s.m_stack.end();++it)
  {
    o<< *it->get() << std::endl;
    o<<"*************************\n";
  }
  return o;
}

Prompt::StackManager::StackManager(): m_unweighted(0)
{

}

void Prompt::StackManager::add(std::unique_ptr<Prompt::Particle> aParticle)
{
  m_stack.emplace_back(std::move(aParticle));
}

void Prompt::StackManager::addSecondary(const Prompt::Particle& aparticle, bool tosecond)
{
  if(tosecond)
  {
    //fixme it is here breaks the xs biasing mechanism and the weight is not corrected 
    m_stack_second.emplace_back(std::make_unique<Particle>(aparticle));
  }
  else
  {
    m_stack.emplace_back(std::make_unique<Particle>(aparticle));
    m_unweighted++;
  }
}
    
void Prompt::StackManager::scalceSecondary(int lastidx, double factor)
{
  m_stack[m_stack.size()-1-lastidx]->scaleWeight(factor);
  m_unweighted--;
}

void Prompt::StackManager::normaliseSecondStack(long unsigned num)
{
  if(m_stack_second.empty())
    PROMPT_THROW(CalcError, "secondary stack is empty");
  // num reaches here from public python bridges (goWithSecondStack,
  // importSecondStack), so bound it before any arithmetic: the unsigned
  // difference must not be truncated into a smaller int (a ~2**32 request
  // would otherwise resize down to its low 32 bits, silently, or allocate
  // tens of GB of null particles)
  if(num > 1000000000ul)
    PROMPT_THROW2(CalcError, "normaliseSecondStack: requested bank size " << num << " is unreasonably large");
  std::cout << "Normalising second stack (containing " << m_stack_second.size() << " particle )\n";
  ptrdiff_t toAdd = ptrdiff_t(num) - ptrdiff_t(m_stack_second.size());

  auto gen = Singleton<SingletonPTRand>::getInstance().getGenerator();


  if(toAdd < 0) // deleting
  {
    std::shuffle(m_stack_second.begin(), m_stack_second.end(), *gen);
    m_stack_second.resize(num);
  }
  else if(toAdd > 0)// adding random neutrons
  {

    std::uniform_int_distribution<> distrib(0, m_stack_second.size()-1);

    for(ptrdiff_t i=0;i<toAdd;i++)
    {
      Particle ap = *m_stack_second[distrib(*gen)].get();
      m_stack_second.emplace_back(std::make_unique<Particle>(ap) );
    }
  }
  
  std::cout << "Done normalisation\n";
}

void Prompt::StackManager::swapStack()
{
  if(!m_stack.empty())
    PROMPT_THROW2(CalcError, "stack must be empty when swaping with the secondary stack");
  m_stack.swap(m_stack_second);
}

std::vector<char> Prompt::StackManager::dumpSecondStack() const
{
  std::vector<char> blob(BANK_HEADER + m_stack_second.size() * sizeof(BankRecord));
  memcpy(blob.data(), BANK_MAGIC, sizeof(BANK_MAGIC));
  uint64_t count = m_stack_second.size();
  memcpy(blob.data() + sizeof(BANK_MAGIC), &count, sizeof(count));
  auto *rec = reinterpret_cast<BankRecord *>(blob.data() + BANK_HEADER);
  for(const auto &p : m_stack_second)
  {
    const Vector &d = p->getDirection();
    rec->dir[0] = d.x();
    rec->dir[1] = d.y();
    rec->dir[2] = d.z();
    const Vector &pos = p->getPosition();
    rec->pos[0] = pos.x();
    rec->pos[1] = pos.y();
    rec->pos[2] = pos.z();
    rec->ekin = p->getEKin();
    rec->time = p->getTime();
    rec->weight = p->getWeight();
    rec->surviveP = p->getSurviveP();
    rec->pdg = p->getPDG();
    ++rec;
  }
  return blob;
}

void Prompt::StackManager::importSecondStack(const std::vector<char> &blob, long unsigned normaliseTo)
{
  // The python side pools the banks of all ranks by plain byte
  // concatenation of their dumps, so the buffer may hold a sequence of
  // self-describing blobs, each with its own header. Pass 1 walks all the
  // headers first so a rejected import leaves the current bank untouched;
  // pass 2 materialises into a fresh vector that is swapped in only on
  // success — a record-level defect (e.g. a null direction, which the
  // Particle constructor rejects) must not destroy the previous bank either.
  if(blob.size() < BANK_HEADER)
    PROMPT_THROW(DataLoadError, "second-stack blob is shorter than its header");

  size_t off = 0;
  uint64_t total = 0;
  while(off < blob.size())
  {
    if(blob.size() - off < BANK_HEADER)
      PROMPT_THROW(DataLoadError, "trailing bytes where a second-stack blob header should be");
    if(memcmp(blob.data() + off, BANK_MAGIC, sizeof(BANK_MAGIC)))
      PROMPT_THROW(DataLoadError, "second-stack blob has a wrong magic (expected PKB1)");
    uint64_t count = 0;
    memcpy(&count, blob.data() + off + sizeof(BANK_MAGIC), sizeof(count));
    // the division doubles as the overflow guard: it caps count at what the
    // remaining bytes could hold, so count*sizeof below cannot wrap
    if(count > (blob.size() - off - BANK_HEADER) / sizeof(BankRecord))
      PROMPT_THROW2(DataLoadError, "second-stack sub-blob at offset " << off
                            << " declares " << count << " particles, more than the buffer holds");
    total += count;
    off += BANK_HEADER + count * sizeof(BankRecord);
  }

  std::vector<std::unique_ptr<Particle>> fresh;
  fresh.reserve(total);
  off = 0;
  while(off < blob.size())
  {
    uint64_t count = 0;
    memcpy(&count, blob.data() + off + sizeof(BANK_MAGIC), sizeof(count));
    const auto *rec = reinterpret_cast<const BankRecord *>(blob.data() + off + BANK_HEADER);
    for(uint64_t i = 0; i < count; ++i, ++rec)
    {
      // reject a null direction here with a blob-level message before the
      // constructor's "Can't scale null-vector" CalcError can surface one
      if(rec->dir[0] == 0. && rec->dir[1] == 0. && rec->dir[2] == 0.)
        PROMPT_THROW2(DataLoadError, "second-stack record at offset "
                              << off + BANK_HEADER + i * sizeof(BankRecord)
                              << " carries a null direction");
      // the 4-arg constructor derives rest mass from pdg and normalises the
      // direction; the stored direction is then assigned back verbatim so a
      // dump-import-dump roundtrip is byte-identical
      auto p = std::make_unique<Particle>(rec->ekin, Vector(rec->dir[0], rec->dir[1], rec->dir[2]),
                                          Vector(rec->pos[0], rec->pos[1], rec->pos[2]), rec->pdg);
      p->setDirection(Vector(rec->dir[0], rec->dir[1], rec->dir[2]));
      p->setTime(rec->time);
      p->setWeight(rec->weight);
      p->scaleSurviveP(rec->surviveP); // a fresh particle starts at 1.0, so this restores the value
      fresh.emplace_back(std::move(p));
    }
    off += BANK_HEADER + count * sizeof(BankRecord);
  }
  m_stack_second = std::move(fresh);

  // normaliseTo > 0 applies the same resampling (and the same RNG draws) as
  // the serial goWithSecondStack entry; normaliseTo == 0 means "replace the
  // bank verbatim": the nearest-neighbour exchange hands back an already
  // exactly-sized bank, so no resampling — and no RNG draws — may happen.
  // The pooled exchange relies on the CalcError of a real target on an empty
  // bank, mirroring the serial path.
  if(normaliseTo)
    normaliseSecondStack(normaliseTo);
}

size_t Prompt::StackManager::secondStackBlobSize() const
{
  return BANK_HEADER + m_stack_second.size() * sizeof(BankRecord);
}

std::vector<char> Prompt::StackManager::extractSecondStack(const std::vector<char> &blob,
                                                           const std::vector<uint64_t> &localIndices) const
{
  // nearest-neighbour exchange helper: pick records out of one dump by
  // local index and return them as a fresh self-describing blob. Only a
  // single-sub-blob buffer is addressable: a concatenated pool has no
  // meaningful "local index".
  if(blob.size() < BANK_HEADER)
    PROMPT_THROW(DataLoadError, "second-stack blob is shorter than its header");
  if(memcmp(blob.data(), BANK_MAGIC, sizeof(BANK_MAGIC)))
    PROMPT_THROW(DataLoadError, "second-stack blob has a wrong magic (expected PKB1)");
  uint64_t count = 0;
  memcpy(&count, blob.data() + sizeof(BANK_MAGIC), sizeof(count));
  // the division doubles as the overflow guard, as in importSecondStack
  if(count > (blob.size() - BANK_HEADER) / sizeof(BankRecord)
     || blob.size() != BANK_HEADER + count * sizeof(BankRecord))
    PROMPT_THROW(DataLoadError, "second-stack blob count does not match its size "
                                "(multi-blob pools are not addressable by local index)");

  std::vector<char> out(BANK_HEADER + localIndices.size() * sizeof(BankRecord));
  memcpy(out.data(), BANK_MAGIC, sizeof(BANK_MAGIC));
  uint64_t outCount = localIndices.size();
  memcpy(out.data() + sizeof(BANK_MAGIC), &outCount, sizeof(outCount));
  const auto *src = reinterpret_cast<const BankRecord *>(blob.data() + BANK_HEADER);
  auto *dst = reinterpret_cast<BankRecord *>(out.data() + BANK_HEADER);
  for(uint64_t idx : localIndices)
  {
    if(idx >= count)
      PROMPT_THROW2(DataLoadError, "second-stack record index " << idx
                            << " out of range (bank holds " << count << ")");
    *dst++ = src[idx]; // byte copy: a duplicate index duplicates the record
  }
  return out;
}


void Prompt::StackManager::add(const Prompt::Particle& aparticle, unsigned number)
{
  pt_assert_always(number);
  for(unsigned i=0;i<number;i++)
  {
    auto np = std::make_unique<Particle>(aparticle);
    m_stack.emplace_back(std::move(np));
  }
}


std::unique_ptr<Prompt::Particle> Prompt::StackManager::pop()
{
  if(m_unweighted)
  {
    PROMPT_THROW2(CalcError, "The weight of " << m_unweighted << " particles in the particle stack are not corrected");
  }
  auto p = std::move(m_stack.back());
  m_stack.pop_back();
  return std::move(p);
}


bool Prompt::StackManager::empty() const
{
  return m_stack.empty();
}
