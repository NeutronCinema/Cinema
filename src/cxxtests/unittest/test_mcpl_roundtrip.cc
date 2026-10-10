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

// MCPL write -> read round trip (complements the write-only test_mcpl.cc).
// The only test in this suite performing file IO: a small /tmp file (~5 ms per case).

#include "../doctest.h"

#include "PTMCPLBinaryWrite.hh"
#include "PTMCPLParticleReader.hh"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <sys/types.h>
#include <unistd.h>
#include <vector>

namespace pt = Prompt;

namespace {

// per-process name so parallel ctest invocations cannot collide on the same path;
// namespace-scope (not function-local) so that TempFileCleanup below can still read
// it during static destruction (destroyed after the cleanup guard, in reverse order)
const std::string kTestFileName = "/tmp/cinema_cxxtest_mcplrt_" + std::to_string(getpid()) + ".mcpl";

const std::string &testFileName() { return kTestFileName; }

// Write two well-separated neutrons with double precision and no gzip so that the
// reader can reopen exactly this path. Caller must re-write per test case.
void writeTwoParticles()
{
  pt::MCPLBinaryWrite w(testFileName(), /*enable_double=*/true, /*enable_extra3double=*/false,
                        /*enable_extraUnsigned=*/true, /*compress=*/false);
  pt::Particle p1(0.0253, pt::Vector(0, 0, 1), pt::Vector(1, 2, 3));
  p1.setTime(1e-7); // s, converted to ms by the writer
  pt::Particle p2(1.0, pt::Vector(1, 0, 0), pt::Vector(-4.5, 0.25, 100), pt::const_proton_pgd);
  p2.setWeight(0.5);
  p2.setTime(0.002); // s, converted to ms by the writer
  w.write(p1);
  w.write(p2);
  w.close(); // destructor must not close the file twice
}

bool contains(const char *haystack, uint32_t len, const char *needle)
{
  uint32_t nlen = std::strlen(needle);
  if (len < nlen)
    return false;
  for (uint32_t i = 0; i + nlen <= len; ++i)
    if (std::memcmp(haystack + i, needle, nlen) == 0)
      return true;
  return false;
}

// removes the round-trip file when the test binary exits
struct TempFileCleanup
{
  ~TempFileCleanup() { std::remove(kTestFileName.c_str()); }
};
const TempFileCleanup s_tempFileCleanup;

} // namespace

TEST_CASE("mcpl_roundtrip_count_and_flags")
{
  writeTwoParticles();
  pt::MCPLParticleReader r(testFileName());
  CHECK(r.particleCount() == 2u);
  // the double precision and userflag bits recorded in the file header
  mcpl_file_t f = mcpl_open_file(testFileName().c_str());
  REQUIRE(f.internal != 0);
  CHECK(mcpl_hdr_has_doubleprec(f) != 0);
  CHECK(mcpl_hdr_has_userflags(f) != 0);
  CHECK(mcpl_hdr_has_polarisation(f) == 0);
  mcpl_close_file(f);
}

TEST_CASE("mcpl_roundtrip_energy")
{
  writeTwoParticles();
  pt::MCPLParticleReader r(testFileName());
  // writer converts eV -> MeV, reader multiplies by Unit::MeV again
  CHECK(r.readOneParticle());
  CHECK(pt::floateq(r.getEnergy(), 0.0253, 1e-12, 1e-15));
  CHECK(r.readOneParticle());
  CHECK(pt::floateq(r.getEnergy(), 1.0, 1e-12, 1e-15));
}

TEST_CASE("mcpl_roundtrip_position_and_direction")
{
  writeTwoParticles();
  pt::MCPLParticleReader r(testFileName());
  CHECK(r.readOneParticle());
  pt::Vector pos, dir;
  r.getPosition(pos);
  r.getDirection(dir);
  // writer converts mm -> cm, reader multiplies by Unit::cm again
  CHECK(pt::floateq(pos.x(), 1.0, 1e-12, 1e-12));
  CHECK(pt::floateq(pos.y(), 2.0, 1e-12, 1e-12));
  CHECK(pt::floateq(pos.z(), 3.0, 1e-12, 1e-12));
  // direction is stored as a unit vector without conversion
  CHECK(pt::floateq(dir.x(), 0.0, 1e-12, 1e-12));
  CHECK(pt::floateq(dir.y(), 0.0, 1e-12, 1e-12));
  CHECK(pt::floateq(dir.z(), 1.0, 1e-12, 1e-12));
  CHECK(pt::floateq(dir.mag2(), 1.0, 1e-12, 1e-12));
  // second particle keeps a unit direction through the round trip as well
  CHECK(r.readOneParticle());
  r.getDirection(dir);
  CHECK(pt::floateq(dir.mag2(), 1.0, 1e-12, 1e-12));
  CHECK(pt::floateq(dir.x(), 1.0, 1e-12, 1e-12));
}

TEST_CASE("mcpl_roundtrip_weight_time_pdg")
{
  writeTwoParticles();
  pt::MCPLParticleReader r(testFileName());
  CHECK(r.readOneParticle());
  CHECK(pt::floateq(r.getWeight(), 1.0, 1e-12, 1e-15));
  CHECK(pt::floateq(r.getTime(), 1e-7, 1e-12, 1e-15)); // s -> ms -> s
  CHECK(r.getPDG() == pt::const_neutron_pgd);
  CHECK(r.readOneParticle());
  CHECK(pt::floateq(r.getWeight(), 0.5, 1e-12, 1e-15));
  CHECK(pt::floateq(r.getTime(), 0.002, 1e-12, 1e-15));
  CHECK(r.getPDG() == pt::const_proton_pgd);
}

TEST_CASE("mcpl_roundtrip_repeat_rewinds")
{
  writeTwoParticles();
  pt::MCPLParticleReader r(testFileName()); // repeat = true by default
  // four reads from a two particle file: 1st, 2nd, 1st, 2nd again
  const double expected[] = {0.0253, 1.0, 0.0253, 1.0};
  const int32_t expectedPDG[] = {pt::const_neutron_pgd, pt::const_proton_pgd,
                                 pt::const_neutron_pgd, pt::const_proton_pgd};
  for (unsigned i = 0; i < 4; ++i) {
    CHECK(r.readOneParticle());
    CHECK(pt::floateq(r.getEnergy(), expected[i], 1e-12, 1e-15));
    CHECK(r.getPDG() == expectedPDG[i]);
  }
}

TEST_CASE("mcpl_roundtrip_no_repeat_eof_and_numpy_blobs")
{
  writeTwoParticles();
  {
    pt::MCPLParticleReader r(testFileName(), /*repeat=*/false);
    CHECK(r.readOneParticle());
    CHECK(r.readOneParticle());
    CHECK_FALSE(r.readOneParticle()); // end of file reported once
  }
  // numpy blobs stored in the header survive the round trip with their dtype strings
  {
    pt::MCPLBinaryWrite w(testFileName(), true, false, true, false);
    std::vector<double> dvec{1, 2};
    w.addHeaderData("npar_f8", dvec.data(), {2}, pt::NumpyWriter::NPDataType::f8);
    std::vector<float> fvec{1, 2, 3};
    w.addHeaderData("npar_f4", fvec.data(), {3}, pt::NumpyWriter::NPDataType::f4);
    std::vector<int32_t> ivec{1, 2, 3, 4};
    w.addHeaderData("npar_i4", ivec.data(), {4}, pt::NumpyWriter::NPDataType::i4);
    w.closeHeader();
    pt::Particle p(0.0253, pt::Vector(0, 0, 1), pt::Vector(0, 0, 0));
    w.write(p);
    w.close();
  }
  mcpl_file_t f = mcpl_open_file(testFileName().c_str());
  REQUIRE(f.internal != 0);
  REQUIRE(mcpl_hdr_nblobs(f) == 3);
  const char **keys = mcpl_hdr_blobkeys(f);
  CHECK(std::string(keys[0]) == "npar_f8");
  CHECK(std::string(keys[1]) == "npar_f4");
  CHECK(std::string(keys[2]) == "npar_i4");
  // npy v1.0 layout: 64-byte aligned header, then 8/4/4-byte items
  const uint32_t payload[] = {16, 12, 16};
  const char *types[] = {"<f8", "<f4", "<i4"};
  for (unsigned b = 0; b < 3; ++b) {
    uint32_t len = 0;
    const char *data = nullptr;
    REQUIRE(mcpl_hdr_blob(f, keys[b], &len, &data) != 0);
    CHECK(len % 64 == payload[b]);
    CHECK(contains(data, len, types[b]));
  }
  // the f8 payload tail is the last written double
  uint32_t len = 0;
  const char *data = nullptr;
  REQUIRE(mcpl_hdr_blob(f, "npar_f8", &len, &data) != 0);
  double last = 0.0;
  std::memcpy(&last, data + len - 8, 8);
  CHECK(pt::floateq(last, 2.0, 1e-12, 1e-15));
  mcpl_close_file(f);
}
