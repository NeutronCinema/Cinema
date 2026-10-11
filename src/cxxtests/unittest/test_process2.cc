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

// Particle/Process/Surface coverage:
// - Particle state transitions (propagation recomputes speed after energy
//   changes, direction stays normalised through the transport transitions,
//   kill freezes the state instead of touching the weight),
// - split/kill weight invariants through ScorerSplit and the roulette,
// - StackManager ordering (second stack swap, batch adds, pop guards),
// - the Prompt::Error hierarchy (type traits, base catching, message round trip),
// - the EnergyReflector threshold law against exact counts,
// - the Mirror reflectivity against hand-computed McStas R(Q) values,
// - ParticleProcess step flow with mock physics models (exponential step
//   length statistics, cross-section proportional channel selection,
//   absorption via kill or survival probability).
// Geometry-loaded cases (EnergyReflector/Mirror) degrade to warnings when
// CINEMAPATH is not set, like test_mirrorsurface does.

#include <cmath>
#include <cstdlib>
#include <limits>
#include <memory>
#include <string>
#include <type_traits>
#include <vector>

#include "../doctest.h"

#include "PTActiveVolume.hh"
#include "PTDiscreteModel.hh"
#include "PTEnergyReflector.hh"
#include "PTException.hh"
#include "PTGeoLoader.hh"
#include "PTMath.hh"
#include "PTMirror.hh"
#include "PTModelCollection.hh"
#include "PTNeutron.hh"
#include "PTParticle.hh"
#include "PTParticleProcess.hh"
#include "PTPhysicsFactory.hh"
#include "PTRandCanonical.hh"
#include "PTScorerSplit.hh"
#include "PTStackManager.hh"
#include "PTUnitSystem.hh"

namespace pt = Prompt;

namespace {

constexpr double g_ekin = 0.0253; // [eV] thermal neutron probe energy

// Seeded singleton RNG. resetSeed() is needed since setSeed() throws
// BadInput if a seed was already set on the singleton.
void reseedRNG(uint64_t seed)
{
  auto &rng = pt::Singleton<pt::SingletonPTRand>::getInstance();
  rng.resetSeed();
  rng.setSeed(seed);
}

// Load the small all-vacuum demo geometry once for the navigation singleton.
bool initGeometry()
{
  static bool done = false;
  if (done)
    return true;
  const char *path = std::getenv("CINEMAPATH");
  if (!path)
  {
    WARN("CINEMAPATH is not set, cannot load the test geometry");
    return false; // every geometry case retries; cheap and side-effect free
  }
  // the demo materials live under $CINEMAPATH/ncmat; the Python package
  // exports the same variable on import, a plain ctest run has to do it here
  std::string dataPath = std::string(path) + "/ncmat";
  const char *existing = std::getenv("NCRYSTAL_DATA_PATH");
  if (existing && *existing)
    dataPath += ":" + std::string(existing);
  setenv("NCRYSTAL_DATA_PATH", dataPath.c_str(), 1);
  pt::Singleton<pt::GeoLoader>::getInstance().initFromGDML(
      std::string(path) + "/gdml/simple_geo.gdml");
  done = true; // latched only after a clean load: never reload live singletons
  return true;
}

// Locate a neutron just inside the +z world face with a grazing flight
// direction chosen such that the elastic momentum transfer equals qWanted.
// The face normal is returned for checking the specular reflection.
pt::Neutron makeNeutronAtQ(double qWanted, double ekin, pt::Vector &normal)
{
  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();
  const pt::Vector pos(0., 0., 300. * pt::Unit::mm); // inside the world box
  REQUIRE_FALSE(activeVolume.locateActiveVolume(pos));
  activeVolume.getNormal(pos, normal);

  const double k0 = pt::neutronEKin2k(ekin);
  const double c = qWanted / (2. * k0); // |cos| between flight and normal
  REQUIRE(c <= 1.);

  pt::Vector tangent(1., 0., 0.);
  tangent = tangent - normal * tangent.dot(normal);
  tangent.normalise();
  pt::Vector dir = tangent * std::sqrt(1. - c * c) + normal * c;
  dir.normalise();
  return pt::Neutron(ekin, dir, pos);
}

// Reference implementation of the McStas mirror reflectivity with the
// constants fixed in the Mirror constructor (R0=0.99, Qc=0.0219 [1/Aa],
// alpha=6.07, W=0.003 [1/Aa]), written independently of the production
// code including the negative-band clamp.
double referenceReflectivity(double m, double Q)
{
  constexpr double R0 = 0.99;
  constexpr double Qc = 0.0219;
  constexpr double alpha = 6.07;
  constexpr double W = 0.003;
  if (Q < Qc)
    return R0;
  const double raw = 0.5 * R0 * (1. - std::tanh((Q - m * Qc) / W)) * (1. - alpha * (Q - Qc));
  return raw > 0. ? raw : 0.;
}

// Drain both stacks; only valid when the unweighted counter is balanced,
// which every case below guarantees before returning.
void drainStacks(pt::StackManager &sm)
{
  REQUIRE(sm.getUnweightedNum() == 0);
  while (!sm.empty())
    (void)sm.pop();
  if (sm.getNumParticleInSecondStack())
  {
    sm.swapStack(); // requires an empty main stack
    while (!sm.empty())
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

// Mock scatterer: constant cross section, elastic no-op reaction, counts
// the sampleReaction calls so the channel selection can be verified.
class DummyScatterModel : public pt::DiscreteModel
{
public:
  DummyScatterModel(double xs, unsigned gdp = pt::const_neutron_pgd)
      : pt::DiscreteModel("DummyScatter", gdp, 0., std::numeric_limits<double>::max(), 1.0),
        m_xs(xs), m_calls(0)
  {
  }

  double getCrossSection(double) const override { return m_xs; }
  double getCrossSection(double, const pt::Vector &) const override { return m_xs; }

  const pt::SampledResult &sampleReaction(double ekin, const pt::Vector &dir) const override
  {
    ++m_calls;
    m_res.final_ekin = ekin;
    m_res.final_dir = dir;
    m_res.deposition = 0.;
    m_res.dispeared = false;
    return m_res;
  }

  unsigned long long calls() const { return m_calls; }

private:
  double m_xs;
  mutable unsigned long long m_calls;
};

// Mock absorber: registers as the disappearing reaction model of its
// collection and deposits a fixed energy when sampled.
class DummyAbsorbModel : public pt::DiscreteModel
{
public:
  DummyAbsorbModel(double xs, unsigned gdp = pt::const_neutron_pgd)
      : pt::DiscreteModel("DummyAbsorb", gdp, 0., std::numeric_limits<double>::max(), 1.0),
        m_xs(xs)
  {
    m_res.dispeared = true; // make isDispearingReaction() true from birth
  }

  double getCrossSection(double) const override { return m_xs; }
  double getCrossSection(double, const pt::Vector &) const override { return m_xs; }

  const pt::SampledResult &sampleReaction(double ekin, const pt::Vector &dir) const override
  {
    ++m_calls;
    m_res.final_ekin = ekin;
    m_res.final_dir = dir;
    m_res.deposition = 0.25;
    m_res.dispeared = true;
    return m_res;
  }

  unsigned long long calls() const { return m_calls; }

private:
  double m_xs;
  mutable unsigned long long m_calls = 0;
};

} // namespace

TEST_CASE("process_particle_propagate_recomputes_speed_after_energy_change")
{
  const double ekin = g_ekin;
  pt::Neutron p(ekin, pt::Vector(1., 2., 2.), pt::Vector(1., 2., 3.));
  // the constructor normalised the direction to (1,2,2)/3
  const double speed = p.calcSpeed();
  CHECK(speed == doctest::Approx(std::sqrt(2. * ekin / pt::const_neutron_mass_evc2)).epsilon(1e-12));

  p.moveForward(9.); // moves by 9*(1,2,2)/3 = (3,6,6)
  CHECK(p.getPosition().x() == doctest::Approx(4.).epsilon(1e-12));
  CHECK(p.getPosition().y() == doctest::Approx(8.).epsilon(1e-12));
  CHECK(p.getPosition().z() == doctest::Approx(9.).epsilon(1e-12));
  CHECK(p.getStep() == 9.);
  CHECK(p.getTime() == doctest::Approx(9. / speed).epsilon(1e-12));

  // quadruple the energy: the speed doubles and the next leg takes half the time
  p.setEKin(4. * ekin);
  CHECK(p.getEnergyChange() == doctest::Approx(-3. * ekin).epsilon(1e-12));
  CHECK(p.calcSpeed() == doctest::Approx(2. * speed).epsilon(1e-12));

  p.moveForward(9.);
  CHECK(p.getPosition().x() == doctest::Approx(7.).epsilon(1e-12));
  CHECK(p.getPosition().y() == doctest::Approx(14.).epsilon(1e-12));
  CHECK(p.getPosition().z() == doctest::Approx(15.).epsilon(1e-12));
  CHECK(p.getTime() == doctest::Approx(9. / speed + 9. / (2. * speed)).epsilon(1e-12));
  CHECK(p.getStep() == 9.);
}

TEST_CASE("process_particle_direction_stays_unit_through_transitions")
{
  pt::Neutron p(1., pt::Vector(0., 3., 4.), pt::Vector(0., 0., 0.));
  CHECK(p.getDirection().x() == doctest::Approx(0.).epsilon(1e-12));
  CHECK(p.getDirection().y() == doctest::Approx(0.6).epsilon(1e-12));
  CHECK(p.getDirection().z() == doctest::Approx(0.8).epsilon(1e-12));

  // propagation and energy changes leave the normalised direction alone
  p.moveForward(2.5);
  p.setEKin(1e-6);
  CHECK(p.getDirection().mag2() == doctest::Approx(1.).epsilon(1e-12));

  // reflecting about the z plane like a surface process must stay normalised
  const pt::Vector d = p.getDirection();
  const pt::Vector normal(0., 0., 1.);
  const pt::Vector refl = d - normal * (2. * d.dot(normal));
  p.setDirection(refl);
  CHECK(p.getDirection().z() == doctest::Approx(-d.z()).epsilon(1e-12));
  CHECK(p.getDirection().mag2() == doctest::Approx(1.).epsilon(1e-12));

  // the setter stores verbatim: normalisation is the constructor's contract
  // and models are expected to hand over unit vectors
  p.setDirection(pt::Vector(3., 4., 0.));
  CHECK(p.getDirection().x() == 3.);
  CHECK(p.getDirection().y() == 4.);
  CHECK(p.getDirection().z() == 0.);
  CHECK(p.getDirection().mag2() == doctest::Approx(25.).epsilon(1e-9));
}

TEST_CASE("process_particle_kill_records_type_and_freezes_state")
{
  const double ekin = g_ekin;
  const pt::Particle::KillType types[] = {
      pt::Particle::KillType::ABSORB, pt::Particle::KillType::BIAS,
      pt::Particle::KillType::SCORE, pt::Particle::KillType::RT_ABSORB};
  for (auto t : types)
  {
    pt::Neutron p(ekin, pt::Vector(0., 0., 1.), pt::Vector(1., 1., 1.));
    p.setWeight(0.25);
    p.moveForward(3.);
    p.setDeposition(1.5);
    REQUIRE(p.isAlive());

    p.kill(t);
    // the transport removes the particle: the state is frozen as it was,
    // in particular the weight is not zeroed ("absorbed as is" semantics)
    CHECK_FALSE(p.isAlive());
    CHECK(p.getKillType() == t);
    CHECK(p.getWeight() == doctest::Approx(0.25).epsilon(1e-12));
    CHECK(p.getEKin() == doctest::Approx(ekin).epsilon(1e-12));
    CHECK(p.getDeposition() == doctest::Approx(1.5).epsilon(1e-12));
    CHECK(p.getPosition().z() == doctest::Approx(4.).epsilon(1e-12));
  }
}

TEST_CASE("process_split_scorer_halves_weight_exactly")
{
  auto &sm = stack();
  drainStacks(sm);

  { // split=2: the incoming weight halves and one copy keeps the event alive
    pt::ScorerSplit s2("half", 2, pt::const_neutron_pgd);
    pt::Neutron p(1., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    p.setWeight(1.);
    s2.score(p);
    CHECK(p.getWeight() == 0.5); // exact halving (scaleWeight(1./2))
    CHECK(sm.getNumParticleInStack() == 1u);
    CHECK(sm.getUnweightedNum() == 0); // batch adds carry no correction bookkeeping
    // the histogram recorded exactly one entry with the pre-split weight
    REQUIRE(s2.getHist() != nullptr);
    CHECK(s2.getHist()->getTotalHit() == 1.);
    CHECK(s2.getHist()->getAccWeight() == doctest::Approx(1.).epsilon(1e-12));

    // rescoring the same event is a no-op (event id dedup)
    s2.score(p);
    CHECK(p.getWeight() == 0.5);
    CHECK(sm.getNumParticleInStack() == 1u);
    CHECK(s2.getHist()->getTotalHit() == 1.);

    // another particle object of the same event id is deduped too
    pt::Neutron q(1., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    s2.score(q);
    CHECK(q.getWeight() == 1.);
    CHECK(sm.getNumParticleInStack() == 1u);

    // the stacked copy carries the halved weight: total weight is conserved
    auto copy = sm.pop();
    REQUIRE(copy != nullptr);
    CHECK(copy->getWeight() == 0.5);
    CHECK(copy->getEKin() == doctest::Approx(1.).epsilon(1e-12));
    CHECK(copy->getEventID() == p.getEventID());
    CHECK(copy->getWeight() + p.getWeight() == 1.);
    CHECK(sm.empty());
  }

  { // split=3: same division as the implementation, so equality is exact
    pt::ScorerSplit s3("third", 3, pt::const_neutron_pgd);
    pt::Neutron p(2., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    p.setWeight(1.);
    s3.score(p);
    CHECK(p.getWeight() == 1. / 3.);
    CHECK(sm.getNumParticleInStack() == 2u);
    auto c1 = sm.pop();
    auto c2 = sm.pop();
    REQUIRE(c1 != nullptr);
    REQUIRE(c2 != nullptr);
    CHECK(c1->getWeight() == 1. / 3.);
    CHECK(c2->getWeight() == 1. / 3.);
    CHECK(c1->getWeight() + c2->getWeight() + p.getWeight() ==
          doctest::Approx(1.).epsilon(1e-15).scale(0.));
  }

  { // split=1 records the entry but does not split
    pt::ScorerSplit s1("one", 1, pt::const_neutron_pgd);
    pt::Neutron p(1., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    s1.score(p);
    CHECK(p.getWeight() == 1.);
    CHECK(sm.getNumParticleInStack() == 0u);
    CHECK(s1.getHist()->getTotalHit() == 1.);
  }

  drainStacks(sm);
  CHECK(sm.empty());
}

TEST_CASE("process_stack_secondaries_swap_ordering")
{
  auto &sm = stack();
  drainStacks(sm);

  // keep the main stack non-empty to exercise the swap guard
  sm.add(makeParticle(10., 1.));
  pt::Particle b(2., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  b.setWeight(0.2);
  pt::Particle c(3., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  c.setWeight(0.3);
  sm.addSecondary(b, true);
  sm.addSecondary(c, true);
  CHECK(sm.getNumParticleInSecondStack() == 2u);
  CHECK(sm.getNumParticleInStack() == 1u);
  CHECK(sm.getUnweightedNum() == 0); // second-stack entries carry no bookkeeping

  // swapping while the main stack holds particles is refused loudly
  CHECK_THROWS_AS(sm.swapStack(), pt::Error::CalcError);
  CHECK(sm.getNumParticleInSecondStack() == 2u); // the refused swap changed nothing

  (void)sm.pop(); // drain the main stack
  REQUIRE(sm.empty());
  sm.swapStack();
  CHECK(sm.getNumParticleInSecondStack() == 0u);
  // LIFO: the last-added secondary comes back first, copied by value
  auto pc = sm.pop();
  REQUIRE(pc != nullptr);
  CHECK(pc->getEKin() == doctest::Approx(3.).epsilon(1e-12));
  CHECK(pc->getWeight() == doctest::Approx(0.3).epsilon(1e-12));
  auto pb = sm.pop();
  REQUIRE(pb != nullptr);
  CHECK(pb->getEKin() == doctest::Approx(2.).epsilon(1e-12));
  CHECK(pb->getWeight() == doctest::Approx(0.2).epsilon(1e-12));
  CHECK(sm.empty());

  drainStacks(sm);
}

TEST_CASE("process_stack_batch_add_and_depth_guards")
{
  auto &sm = stack();
  drainStacks(sm);

  pt::Particle proto(5., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  proto.setWeight(0.5);
  // zero-length batch is refused by the always-on assertion
  CHECK_THROWS_AS(sm.add(proto, 0), pt::Error::LogicError);
  CHECK(sm.empty()); // the refused call added nothing

  sm.add(proto, 4);
  CHECK(sm.getNumParticleInStack() == 4u);
  CHECK(sm.getUnweightedNum() == 0); // batch adds are not tracked as secondaries

  // an uncorrected secondary on top blocks pop until it is corrected
  pt::Particle s(7., pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  s.setWeight(0.5);
  sm.addSecondary(s, false);
  CHECK(sm.getUnweightedNum() == 1);
  CHECK_THROWS_AS(sm.pop(), pt::Error::CalcError);
  sm.scalceSecondary(0, 2.);
  CHECK(sm.getUnweightedNum() == 0);

  // LIFO: the secondary first (scaled to weight 1), then the four verbatim
  // batch copies (weight 0.5)
  auto top = sm.pop();
  REQUIRE(top != nullptr);
  CHECK(top->getEKin() == doctest::Approx(7.).epsilon(1e-12));
  CHECK(top->getWeight() == doctest::Approx(1.).epsilon(1e-12));
  for (unsigned i = 0; i < 4; ++i)
  {
    auto cp = sm.pop();
    REQUIRE(cp != nullptr);
    CHECK(cp->getEKin() == doctest::Approx(5.).epsilon(1e-12));
    CHECK(cp->getWeight() == doctest::Approx(0.5).epsilon(1e-12));
  }
  CHECK(sm.empty());
}

// Throw-and-catch round trip through the common base for one error type.
template <class ErrT>
void checkErrorRoundtrip(const std::string &msg)
{
  try
  {
    throw ErrT(msg, __FILE__, __LINE__);
    CHECK_MESSAGE(false, "the exception must escape");
  }
  catch (const pt::Error::Exception &e)
  {
    CHECK(std::string(e.what()).find(msg) != std::string::npos);
    CHECK(std::string(e.what()).size() > 0);
    CHECK(std::string(e.getTypeName()) != "");
    CHECK(std::string(e.getFile()).find("test_process2.cc") != std::string::npos);
    CHECK(e.getLineNo() > 0);
  }
}

TEST_CASE("process_exception_traits_and_hierarchy")
{
  static_assert(std::is_base_of<std::runtime_error, pt::Error::Exception>::value,
                "Prompt errors must be runtime errors");
  static_assert(std::is_base_of<pt::Error::Exception, pt::Error::BadInput>::value,
                "concrete errors must derive from the base");
  static_assert(std::is_nothrow_destructible<pt::Error::BadInput>::value,
                "destructors are declared throw()");
  static_assert(std::is_nothrow_destructible<pt::Error::CalcError>::value,
                "destructors are declared throw()");
  static_assert(std::is_nothrow_copy_constructible<pt::Error::BadInput>::value,
                "copying is declared throw()");
  static_assert(std::is_nothrow_move_constructible<pt::Error::BadInput>::value,
                "copy is nothrow, so the implicit move is too");

  // every registered error type round trips through the base handler
  checkErrorRoundtrip<pt::Error::FileNotFound>("no such file");
  checkErrorRoundtrip<pt::Error::DataLoadError>("corrupt payload");
  checkErrorRoundtrip<pt::Error::MissingInfo>("key absent");
  checkErrorRoundtrip<pt::Error::CalcError>("negative length");
  checkErrorRoundtrip<pt::Error::LogicError>("unreachable branch");
  checkErrorRoundtrip<pt::Error::BadInput>("bad cfg value");
  checkErrorRoundtrip<pt::Error::NotImplemented>("todo");

  // the throwing macro produces the concrete type, catchable as the base
  CHECK_THROWS_AS([] { PROMPT_THROW(BadInput, "thrown by macro"); }(),
                  pt::Error::BadInput);
  CHECK_THROWS_AS([] { PROMPT_THROW(BadInput, "thrown by macro"); }(),
                  pt::Error::Exception);
  CHECK_THROWS_AS([] { PROMPT_THROW(BadInput, "thrown by macro"); }(),
                  std::runtime_error);
}

TEST_CASE("process_exception_std_base_and_empty_message")
{
  // catching through std::exception keeps the composed message
  try
  {
    PROMPT_THROW(BadInput, "cfg parse failed at token 3");
    CHECK_MESSAGE(false, "the exception must escape");
  }
  catch (const std::exception &e)
  {
    CHECK(std::string(e.what()).size() > 0);
    CHECK(std::string(e.what()).find("cfg parse failed") != std::string::npos);
  }

  // an empty message is legal; the type name still identifies the error
  try
  {
    PROMPT_THROW(NotImplemented, "");
    CHECK_MESSAGE(false, "the exception must escape");
  }
  catch (const pt::Error::Exception &e)
  {
    CHECK(e.what() == std::string(""));
    CHECK(std::string(e.getTypeName()) == "NotImplemented");
  }

  // the streaming macro composes the exact message
  try
  {
    PROMPT_THROW2(CalcError, "step " << 3 << " of " << 7.5);
    CHECK_MESSAGE(false, "the exception must escape");
  }
  catch (const pt::Error::Exception &e)
  {
    CHECK(e.what() == std::string("step 3 of 7.5"));
  }

  // a handler may translate one error into another while unwinding
  try
  {
    try
    {
      PROMPT_THROW(FileNotFound, "missing.ncmat");
      CHECK_MESSAGE(false, "the inner exception must escape");
    }
    catch (const pt::Error::FileNotFound &)
    {
      PROMPT_THROW(DataLoadError, "while reading missing.ncmat");
    }
    CHECK_MESSAGE(false, "the outer exception must escape");
  }
  catch (const pt::Error::Exception &e)
  {
    CHECK(std::string(e.getTypeName()) == "DataLoadError");
    CHECK(std::string(e.what()).find("missing.ncmat") != std::string::npos);
  }
}

TEST_CASE("process_energyreflector_threshold_law_exact_counts")
{
  if (!initGeometry())
    return;

  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();
  const pt::Vector pos(0., 0., 300. * pt::Unit::mm);
  REQUIRE_FALSE(activeVolume.locateActiveVolume(pos));
  pt::Vector normal;
  activeVolume.getNormal(pos, normal);

  const double thr = 1.0;
  pt::EnergyReflector lt(thr, true);  // reflect ekin <= thr
  pt::EnergyReflector gt(thr, false); // reflect ekin > thr

  const double energies[] = {0.25, 0.5, 0.99, 1.0, 1.01, 2.0};
  unsigned nReflectedLT = 0, nReflectedGT = 0;
  for (double e : energies)
  {
    // fresh particle per branch, same incident direction
    const pt::Vector indir(0.6, 0., 0.8);
    const pt::Vector expectRefl = indir - normal * (2. * indir.dot(normal));

    pt::Neutron p(e, indir, pos);
    lt.sampleFinalState(p);
    const bool didLT = p.getDirection().dot(normal) * indir.dot(normal) < 0.;
    if (e <= thr)
    {
      CHECK(didLT); // the boundary energy belongs to the "<=" branch
      ++nReflectedLT;
    }
    else
      CHECK_FALSE(didLT);
    // reflected: exact specular direction; passed: untouched direction
    if (didLT)
    {
      CHECK(p.getDirection().x() == doctest::Approx(expectRefl.x()).epsilon(1e-12));
      CHECK(p.getDirection().y() == doctest::Approx(expectRefl.y()).epsilon(1e-12));
      CHECK(p.getDirection().z() == doctest::Approx(expectRefl.z()).epsilon(1e-12));
    }
    else
      CHECK(p.getDirection() == indir);
    CHECK(p.isAlive()); // the reflector never kills
    CHECK(p.getWeight() == 1.);

    pt::Neutron q(e, indir, pos);
    gt.sampleFinalState(q);
    const bool didGT = q.getDirection().dot(normal) * indir.dot(normal) < 0.;
    if (e > thr)
    {
      CHECK(didGT);
      ++nReflectedGT;
    }
    else
      CHECK_FALSE(didGT);
    CHECK(q.isAlive());
  }
  // exact analytic fractions: 4 of the 6 energies are <= thr
  CHECK(nReflectedLT == 4u);
  CHECK(nReflectedGT == 2u);
}

TEST_CASE("process_energyreflector_grid_half_reflected")
{
  if (!initGeometry())
    return;

  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();
  const pt::Vector pos(0., 0., 300. * pt::Unit::mm);
  REQUIRE_FALSE(activeVolume.locateActiveVolume(pos));
  pt::Vector normal;
  activeVolume.getNormal(pos, normal);

  // 1000 energies uniform in (0,2): exactly half of them below the threshold
  pt::EnergyReflector lt(1.0, true);
  const pt::Vector indir(0.6, 0., 0.8);
  const pt::Vector expectRefl = indir - normal * (2. * indir.dot(normal));
  unsigned reflected = 0;
  constexpr unsigned N = 1000;
  for (unsigned i = 0; i < N; ++i)
  {
    const double e = 2. * (i + 0.5) / N;
    pt::Neutron p(e, indir, pos);
    lt.sampleFinalState(p);
    if (e < 1.0)
    {
      ++reflected;
      CHECK(p.getDirection().z() == doctest::Approx(expectRefl.z()).epsilon(1e-12));
    }
    else
      CHECK(p.getDirection() == indir);
    CHECK(p.isAlive());
    CHECK(p.getWeight() == 1.);
  }
  CHECK(reflected == N / 2); // exact 500/500 split, no statistics involved
}

TEST_CASE("process_energyreflector_always_mode_and_factory")
{
  if (!initGeometry())
    return;

  auto &activeVolume = pt::Singleton<pt::ActiveVolume>::getInstance();
  const pt::Vector pos(0., 0., 300. * pt::Unit::mm);
  REQUIRE_FALSE(activeVolume.locateActiveVolume(pos));
  pt::Vector normal;
  activeVolume.getNormal(pos, normal);
  const pt::Vector indir(0.6, 0., 0.8);

  { // ekin=-1 is the reflect-everything mode regardless of the flag
    pt::EnergyReflector always(-1., false);
    const double energies[] = {1e-6, 0.5, 1.0, 100.};
    for (double e : energies)
    {
      pt::Neutron p(e, indir, pos);
      always.sampleFinalState(p);
      CHECK(p.getDirection().dot(normal) * indir.dot(normal) < 0.);
      CHECK(p.isAlive());
    }
  }

  auto &factory = pt::Singleton<pt::PhysicsFactory>::getInstance();
  auto lt = std::dynamic_pointer_cast<pt::EnergyReflector>(
      factory.createSurfaceProcess("physics=EnergyReflector;ekin=0.5;islessthan=1"));
  REQUIRE(lt);
  auto gt = std::dynamic_pointer_cast<pt::EnergyReflector>(
      factory.createSurfaceProcess("physics=EnergyReflector;ekin=0.5;islessthan=0"));
  REQUIRE(gt);

  // boundary energy: owned by the "<=" branch only
  pt::Neutron atBoundary(0.5, indir, pos);
  lt->sampleFinalState(atBoundary);
  CHECK(atBoundary.getDirection().dot(normal) * indir.dot(normal) < 0.);
  pt::Neutron atBoundary2(0.5, indir, pos);
  gt->sampleFinalState(atBoundary2);
  CHECK(atBoundary2.getDirection() == indir);

  // above the threshold the branches swap
  pt::Neutron above(0.75, indir, pos);
  lt->sampleFinalState(above);
  CHECK(above.getDirection() == indir);
  pt::Neutron above2(0.75, indir, pos);
  gt->sampleFinalState(above2);
  CHECK(above2.getDirection().dot(normal) * indir.dot(normal) < 0.);

  // a bad flag value is rejected loudly
  CHECK_THROWS_AS(factory.createSurfaceProcess("physics=EnergyReflector;ekin=1;islessthan=2"),
                  pt::Error::BadInput);
}

TEST_CASE("process_mirror_rq_values_hand_computed")
{
  if (!initGeometry())
    return;
  reseedRNG(20261011); // the threshold=0 path never draws, seed for hygiene

  // the in-file reference formula reproduces the hand-computed values
  CHECK(referenceReflectivity(1., 0.03) ==
        doctest::Approx(0.004232452849452832).epsilon(1e-12));
  CHECK(referenceReflectivity(1., 0.025) ==
        doctest::Approx(0.10916182692447148).epsilon(1e-12));
  CHECK(referenceReflectivity(1., 0.05) ==
        doctest::Approx(6.0066621859289426e-09).epsilon(1e-12));
  CHECK(referenceReflectivity(2., 0.025) ==
        doctest::Approx(0.9713676687256865).epsilon(1e-12));

  auto &factory = pt::Singleton<pt::PhysicsFactory>::getInstance();
  auto mirror = std::dynamic_pointer_cast<pt::Mirror>(
      factory.createSurfaceProcess("physics=Mirror;m=1;threshold=0"));
  auto mirror2 = std::dynamic_pointer_cast<pt::Mirror>(
      factory.createSurfaceProcess("physics=Mirror;m=2;threshold=0"));
  auto mirror5 = std::dynamic_pointer_cast<pt::Mirror>(
      factory.createSurfaceProcess("physics=Mirror;m=5;threshold=0"));
  auto mirror10 = std::dynamic_pointer_cast<pt::Mirror>(
      factory.createSurfaceProcess("physics=Mirror;m=10;threshold=0"));
  REQUIRE(mirror);
  REQUIRE(mirror2);
  REQUIRE(mirror5);
  REQUIRE(mirror10);

  pt::Vector normal;

  // below the critical momentum the full R0 is applied
  pt::Neutron below = makeNeutronAtQ(0.02, g_ekin, normal);
  mirror->sampleFinalState(below);
  CHECK(below.isAlive());
  CHECK(below.getWeight() == doctest::Approx(0.99).epsilon(1e-12));
  CHECK(mirror->getEventWeight() == doctest::Approx(0.99).epsilon(1e-12));

  // m=1 formula values at several Q above Qc, against the hand-computed
  // McStas expression (hard-coded literals, see the reference check above)
  pt::Neutron q1 = makeNeutronAtQ(0.025, g_ekin, normal);
  mirror->sampleFinalState(q1);
  CHECK(q1.getWeight() == doctest::Approx(0.10916182692447148).epsilon(1e-9).scale(0.));

  pt::Neutron q2 = makeNeutronAtQ(0.03, g_ekin, normal);
  mirror->sampleFinalState(q2);
  CHECK(q2.getWeight() == doctest::Approx(0.004232452849452832).epsilon(1e-9).scale(0.));
  CHECK(mirror->getEventWeight() ==
        doctest::Approx(0.004232452849452832).epsilon(1e-9).scale(0.));

  // deep in the tail the weight is tiny but positive and still exact
  pt::Neutron q3 = makeNeutronAtQ(0.05, g_ekin, normal);
  mirror->sampleFinalState(q3);
  CHECK(q3.isAlive());
  CHECK(q3.getWeight() == doctest::Approx(6.0066621859289426e-09).epsilon(1e-7).scale(0.));

  // the m value stretches the plateau: same Q, doubled m keeps near-unity R
  pt::Neutron q4 = makeNeutronAtQ(0.025, g_ekin, normal);
  mirror2->sampleFinalState(q4);
  CHECK(q4.getWeight() == doctest::Approx(0.9713676687256865).epsilon(1e-9).scale(0.));
  CHECK(q4.getWeight() > q1.getWeight());
  pt::Neutron q5 = makeNeutronAtQ(0.03, g_ekin, normal);
  mirror2->sampleFinalState(q5);
  CHECK(q5.getWeight() == doctest::Approx(0.9412295687273845).epsilon(1e-9).scale(0.));

  // clamp band: the raw McStas expression turns negative beyond Qc+1/alpha
  // (or in the m-shifted negative band); the clamp keeps the surface a
  // mirror at weight exactly zero, not a window, and the neutron still
  // specularly reflects with weight 0 (no roulette with threshold=0)
  const double clampQs[] = {0.2, 0.25};
  for (double q : clampQs)
  {
    pt::Neutron n1 = makeNeutronAtQ(q, g_ekin, normal);
    const pt::Vector in1 = n1.getDirection();
    mirror->sampleFinalState(n1);
    CHECK(n1.isAlive());
    CHECK(n1.getWeight() == 0.);
    CHECK(mirror->getEventWeight() == 0.);
    CHECK(n1.getDirection().dot(normal) == doctest::Approx(-in1.dot(normal)).epsilon(1e-10));

    pt::Neutron n5 = makeNeutronAtQ(q, g_ekin, normal);
    mirror5->sampleFinalState(n5);
    CHECK(n5.isAlive());
    CHECK(n5.getWeight() == 0.);
    CHECK(mirror5->getEventWeight() == 0.);

    pt::Neutron n10 = makeNeutronAtQ(q, g_ekin, normal);
    mirror10->sampleFinalState(n10);
    CHECK(n10.isAlive());
    CHECK(n10.getWeight() == 0.);
    CHECK(mirror10->getEventWeight() == 0.);
  }
}

TEST_CASE("process_mirror_reflectivity_monotone_in_q")
{
  if (!initGeometry())
    return;

  // below Qc the reflectivity is the R0 plateau, above it the McStas falloff
  // is the product of two decreasing factors, so R(Q) must never increase
  pt::Mirror mirror(1.0, 0.);
  pt::Vector normal;
  constexpr unsigned N = 30;
  double prev = std::numeric_limits<double>::max();
  unsigned belowQc = 0;
  for (unsigned i = 1; i <= N; ++i)
  {
    const double q = 0.005 * i;
    pt::Neutron n = makeNeutronAtQ(q, g_ekin, normal);
    mirror.sampleFinalState(n);
    const double w = n.getWeight();
    CHECK(n.isAlive());
    CHECK(w <= prev); // monotone non-increasing over the whole sweep
    if (q < 0.0219)
    {
      CHECK(w == doctest::Approx(0.99).epsilon(1e-12)); // plateau value
      ++belowQc;
    }
    prev = w;
  }
  CHECK(belowQc == 4u); // 0.005, 0.01, 0.015, 0.02 lie below Qc
  CHECK(prev < 0.98);   // the sweep left the plateau for good
}

TEST_CASE("process_pp_step_length_exponential_statistics")
{
  reseedRNG(20261011);

  // 1 barn ideal scatterer at 1 atom/Aa^3, plus a 4 barn mock scatterer:
  // the macroscopic cross section is then exactly 5 barn/Aa^3
  pt::ParticleProcess proc("physics=idealElaScat;xs_barn=1;density_per_aa3=1;", pt::const_neutron_pgd);
  CHECK(proc.getNumDensity() == doctest::Approx(1. / pt::Unit::Aa3).epsilon(1e-12));
  auto dummy = std::make_shared<DummyScatterModel>(4. * pt::Unit::barn);
  proc.getModelCollection()->addPhysicsModel(dummy);
  CHECK(proc.getModelCollection()->getModels().size() == 2u);

  pt::Neutron probe(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
  double mxs = 0.;
  (void)proc.sampleStepLength(probe, mxs);
  // load-bearing pin: 5 barn over 1/Aa^3, expressed through the unit system
  const double expectedMxs = (1. * pt::Unit::barn + 4. * pt::Unit::barn) / pt::Unit::Aa3;
  CHECK(mxs == doctest::Approx(expectedMxs).epsilon(1e-12));

  constexpr unsigned N = 100000;
  double sum = 0.;
  unsigned nPositive = 0, nBelowMedian = 0;
  for (unsigned i = 0; i < N; ++i)
  {
    pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    double m2 = 0.;
    const double len = proc.sampleStepLength(p, m2);
    if (len > 0.)
      ++nPositive;
    sum += len;
    if (len < std::log(2.) / expectedMxs)
      ++nBelowMedian;
    CHECK(m2 == mxs); // identical inquiry, so the cached cross section repeats
  }
  const double mean = sum / N;
  const double expectedMean = 1. / expectedMxs;
  // exponential distribution: mean mfp and std mfp, so the SEM is mfp/sqrt(N)
  const double sem = expectedMean / std::sqrt((double)N);
  CHECK(nPositive == N);
  CHECK(std::fabs(mean - expectedMean) < 5. * sem);
  // the median of the exponential is ln(2)/macxs: half the samples below it
  const double median = 0.5;
  const double sigmaMedian = std::sqrt(median * (1. - median) / N);
  CHECK(std::fabs(nBelowMedian / (double)N - median) < 5. * sigmaMedian);
}

TEST_CASE("process_pp_mock_scatter_model_flow")
{
  reseedRNG(20261012);

  // the mock model gets 4 of the 5 barns: P(mock channel) = 0.8 exactly
  pt::ParticleProcess proc("physics=idealElaScat;xs_barn=1;density_per_aa3=1;", pt::const_neutron_pgd);
  auto dummy = std::make_shared<DummyScatterModel>(4. * pt::Unit::barn);
  proc.getModelCollection()->addPhysicsModel(dummy);

  auto &sm = stack();
  drainStacks(sm);

  constexpr unsigned N = 1000;
  unsigned interacted = 0;
  for (unsigned i = 0; i < N; ++i)
  {
    pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
    double mxs;
    const double len = proc.sampleStepLength(p, mxs);
    CHECK(len > 0.);
    // the step length query caches the (ekin,dir) inquiry that pickAndSample
    // expects: this is the production step flow
    if (proc.sampleFinalState(p, len, false))
      ++interacted;
    // elastic scatter with unit weights: alive, weight and energy unchanged
    CHECK(p.isAlive());
    CHECK(p.getWeight() == 1.);
    CHECK(p.getEKin() == 1.0);
    CHECK(p.getDeposition() == 0.);
    CHECK(p.getDirection().mag2() == doctest::Approx(1.).epsilon(1e-12));
  }
  CHECK(interacted == N); // a scatter never makes the particle disappear here

  // channel selection is proportional to cross section:
  // Binomial(N, 0.8), six sigma window around the analytic mean
  const unsigned calls = static_cast<unsigned>(dummy->calls());
  const double expectedCalls = 0.8 * N;
  const double sigma = std::sqrt(N * 0.8 * 0.2);
  CHECK(std::fabs((double)calls - expectedCalls) < 6. * sigma);
  CHECK(calls > 0);
  CHECK(calls <= N);

  drainStacks(sm);
  CHECK(sm.empty());
}

TEST_CASE("process_pp_absorbing_mock_model_and_survivep")
{
  reseedRNG(20261013);

  auto &sm = stack();
  drainStacks(sm);

  // the absorber holds 4 of the 5 barns, so its channel fires in 80% of the
  // trials; the kill/deposition bookkeeping is pinned per outcome and the
  // channel fraction against the analytic binomial
  { // default handling: a disappeared reaction kills the particle
    pt::ParticleProcess proc("physics=idealElaScat;xs_barn=1;density_per_aa3=1;",
                             pt::const_neutron_pgd);
    auto absorber = std::make_shared<DummyAbsorbModel>(4. * pt::Unit::barn);
    proc.getModelCollection()->addPhysicsModel(absorber);

    constexpr unsigned N = 1000;
    unsigned killed = 0, survived = 0;
    for (unsigned i = 0; i < N; ++i)
    {
      pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
      double mxs;
      const double len = proc.sampleStepLength(p, mxs);
      CHECK(mxs == doctest::Approx(5. * pt::Unit::barn / pt::Unit::Aa3).epsilon(1e-12));
      const bool scat = proc.sampleFinalState(p, len, false);
      if (!p.isAlive())
      {
        ++killed;
        CHECK_FALSE(scat);
        CHECK(p.getKillType() == pt::Particle::KillType::ABSORB);
        // the disappeared state stays frozen at the incident values, but the
        // model's deposition is still recorded
        CHECK(p.getEKin() == 1.0);
        CHECK(p.getDirection() == pt::Vector(0., 0., 1.));
        CHECK(p.getDeposition() == doctest::Approx(0.25).epsilon(1e-12));
        CHECK(p.getWeight() == 1.);
        CHECK(p.getSurviveP() == 1.);
      }
      else
      {
        ++survived;
        CHECK(scat);
        CHECK(p.getDeposition() == 0.);
        CHECK(p.getSurviveP() == 1.); // no survival biasing in this mode
      }
    }
    CHECK(killed + survived == N);
    CHECK(static_cast<unsigned long long>(absorber->calls()) == killed);
    const double sigma = std::sqrt(N * 0.8 * 0.2);
    CHECK(std::fabs((double)killed - 0.8 * N) < 6. * sigma);
  }

  { // absorp_in_weight: the kill is replaced by a survival probability
    pt::ParticleProcess proc("physics=idealElaScat;xs_barn=1;density_per_aa3=1;",
                             pt::const_neutron_pgd, /*absorp_in_weight=*/true);
    auto absorber = std::make_shared<DummyAbsorbModel>(4. * pt::Unit::barn);
    proc.getModelCollection()->addPhysicsModel(absorber);

    constexpr unsigned N = 1000;
    const double absxs = 4. * pt::Unit::barn / pt::Unit::Aa3;
    unsigned absorbedChannel = 0;
    for (unsigned i = 0; i < N; ++i)
    {
      pt::Neutron p(1.0, pt::Vector(0., 0., 1.), pt::Vector(0., 0., 0.));
      double mxs;
      const double len = proc.sampleStepLength(p, mxs);
      const bool scat = proc.sampleFinalState(p, len, false);
      // nobody dies in this mode, whatever channel fired (the kill type is
      // only meaningful after kill(); a never-killed particle reads garbage)
      CHECK(p.isAlive());
      CHECK(p.getWeight() == 1.);
      // the survival probability is scaled on every step, channel independent
      CHECK(p.getSurviveP() == doctest::Approx(std::exp(-absxs * len)).epsilon(1e-12));
      // scat reports whether the particle survived the sampled reaction,
      // i.e. whether the absorber channel did not fire
      if (p.getDeposition() != 0.)
      {
        ++absorbedChannel;
        CHECK(p.getDeposition() == doctest::Approx(0.25).epsilon(1e-12));
        CHECK_FALSE(scat);
      }
      else
        CHECK(scat);
    }
    CHECK(static_cast<unsigned long long>(absorber->calls()) == absorbedChannel);
    const double sigma = std::sqrt(N * 0.8 * 0.2);
    CHECK(std::fabs((double)absorbedChannel - 0.8 * N) < 6. * sigma);
  }

  drainStacks(sm);
  CHECK(sm.empty());
}
