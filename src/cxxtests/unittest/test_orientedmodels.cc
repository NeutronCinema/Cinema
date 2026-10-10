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

#include <cmath>
#include <limits>
#include <memory>

#include "PTActiveVolume.hh"
#include "PTModelCollection.hh"
#include "PTRandCanonical.hh"

namespace pt = Prompt;

namespace {

constexpr double g_tol = 1e-15;

// Component-wise vector comparison with an absolute tolerance, mirroring the
// helper of test_geotranslator.cc (doctest::Approx has an absolute window
// which is useless for components expected to be near zero).
void checkVecNear(const pt::Vector& v, const pt::Vector& expect, double tol)
{
  CHECK(std::fabs(v.x() - expect.x()) <= tol);
  CHECK(std::fabs(v.y() - expect.y()) <= tol);
  CHECK(std::fabs(v.z() - expect.z()) <= tol);
}

// A fake discrete model which records the incident direction that
// sampleReaction (and the directional cross section) received, and echoes it
// as the outgoing direction. m_oriented is protected state of PhysicsBase, so
// the subclass decides the orientation flag directly.
class RecordingModel : public pt::DiscreteModel
{
public:
  RecordingModel(bool oriented)
   : pt::DiscreteModel("RecordingModel", 2112, 1e-6, 1e6)
  { m_oriented = oriented; }

  double getCrossSection(double) const override
  { return g_xs; }

  double getCrossSection(double, const pt::Vector &dir) const override
  {
    m_lastXsDir = dir;
    m_xsDirCalls++;
    return g_xs;
  }

  const pt::SampledResult& sampleReaction(double ekin, const pt::Vector &dir) const override
  {
    m_lastSampleDir = dir;
    m_sampleCalls++;
    m_res.final_ekin = ekin;
    m_res.final_dir = dir; //echo the received direction (in the received frame)
    return m_res;
  }

  mutable pt::Vector m_lastXsDir {0., 0., 0.};
  mutable pt::Vector m_lastSampleDir {0., 0., 0.};
  mutable unsigned m_xsDirCalls {0};
  mutable unsigned m_sampleCalls {0};

  static constexpr double g_xs = 1.0; //single-channel unit cross section
};

// A model whose cross section is NaN. The accumulated selection probability
// then stays NaN, no channel ever satisfies p > r1, and the selection loop
// runs one past the last index: a deterministic trigger of the out-of-bounds
// access the index clamp in pickAndSample guards against (the guard also
// covers the theoretical rounding-past-the-sum case, which no unit test can
// reach with a real random draw).
class NaNXsModel : public RecordingModel
{
public:
  NaNXsModel() : RecordingModel(false) {}

  double getCrossSection(double) const override
  { return std::numeric_limits<double>::quiet_NaN(); }

  double getCrossSection(double, const pt::Vector &dir) const override
  {
    m_lastXsDir = dir;
    m_xsDirCalls++;
    return std::numeric_limits<double>::quiet_NaN();
  }
};

// ModelCollection consults the ActiveVolume singleton's geo translator, so
// the tests install a known placement on it. getGeoTranslator() hands out a
// const ref only; the transform itself is mutable state of the singleton.
pt::GeoTranslator& activeVolTranslator()
{
  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();
  return const_cast<pt::GeoTranslator&>(activeVolume.getGeoTranslator());
}

// quarter-turn rotation about y: global +z becomes local -x
void installRoty90()
{
  activeVolTranslator().getTransformMatrix()
    .Set(vecgeom::Vector3D<double>(0., 1., 0.), 0.5 * M_PI);
}

void reseedRNG(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

} // namespace

TEST_CASE("modelcollection_oriented_sampling_receives_local_direction")
{
  installRoty90();
  // reference translator carrying the same placement, independent of the
  // collection under test
  pt::GeoTranslator ref;
  ref.getTransformMatrix().Set(vecgeom::Vector3D<double>(0., 1., 0.), 0.5 * M_PI);

  reseedRNG(2026u);

  auto model = std::make_shared<RecordingModel>(true);
  pt::ModelCollection coll(2112);
  coll.addPhysicsModel(model);

  const double ekin = 0.0253;
  const pt::Vector globalDir(0., 0., 1.);
  const pt::Vector expected(-1., 0., 0.);

  const double xs = coll.totalCrossSection(2112, ekin, globalDir);
  CHECK(xs == doctest::Approx(1.0)); //single channel with unit xs
  // anchor: the cross section path already converts to the local frame
  checkVecNear(model->m_lastXsDir, expected, g_tol);
  CHECK(model->m_xsDirCalls == 1u);

  auto &res = coll.pickAndSample(ekin, globalDir);

  REQUIRE(model->m_sampleCalls == 1u);
  // regression: sampleReaction must be handed the crystal-frame direction,
  // the same global2Local conversion the xs path applies
  checkVecNear(model->m_lastSampleDir, expected, g_tol);
  checkVecNear(model->m_lastSampleDir, ref.global2Local_direction(globalDir), g_tol);
  CHECK_FALSE(model->m_lastSampleDir == globalDir);
  // the echoed outgoing direction is mapped back to the global frame
  checkVecNear(res.final_dir, globalDir, g_tol);
}

TEST_CASE("modelcollection_nonoriented_sampling_receives_global_direction")
{
  // even with a rotated placement, an un-oriented model must see the global
  // direction untouched
  installRoty90();
  reseedRNG(7u);

  auto model = std::make_shared<RecordingModel>(false);
  pt::ModelCollection coll(2112);
  coll.addPhysicsModel(model);

  const double ekin = 0.02;
  const pt::Vector globalDir(1., 0., 0.);
  coll.totalCrossSection(2112, ekin, globalDir);
  auto &res = coll.pickAndSample(ekin, globalDir);

  REQUIRE(model->m_sampleCalls == 1u);
  CHECK(model->m_lastSampleDir == globalDir); //no conversion on the way in
  CHECK(res.final_dir == globalDir);          //nor on the way out
}

TEST_CASE("modelcollection_selection_clamps_past_the_summed_probability")
{
  reseedRNG(42u);

  auto good = std::make_shared<RecordingModel>(false);
  auto corrupt = std::make_shared<NaNXsModel>();
  pt::ModelCollection coll(2112);
  coll.addPhysicsModel(good);
  coll.addPhysicsModel(corrupt);

  const double ekin = 0.0253;
  const pt::Vector globalDir(0., 0., 1.);
  // caches a NaN total cross section, so no channel can satisfy p > r1
  coll.totalCrossSection(2112, ekin, globalDir);
  auto &res = coll.pickAndSample(ekin, globalDir);

  // the selection loop exits with i == m_models.size(); the clamp must land
  // the draw on the last channel instead of reading m_models[i] out of bounds
  REQUIRE(corrupt->m_sampleCalls == 1u);
  CHECK(good->m_sampleCalls == 0u);
  CHECK(res.final_dir == globalDir);
}
