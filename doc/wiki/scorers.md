# Scoring: measuring particles

A **scorer** is the Cinema/Prompt equivalent of a detector or tally: it accumulates a
histogram (or an MCPL particle file) while neutrons are transported. Scorers are attached
to geometry volumes, and each one declares *what* it scores (energy, time, position, Q, ...)
and *when* it fires (the particle tracing state, `ptstate`).

This page documents the Python API (`Cinema.Prompt.scorer` helpers), which is the supported
path. Scorer configuration strings from the v1 era still work but are deprecated — see
[section 7](#7-legacy-scorer-configuration-strings-deprecated). Documented against Cinema
2.0.0a5; the authoritative source is
[`src/python/Cinema/Prompt/scorer.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/scorer.py).

The scoring loop fits in three lines:

```python
from Cinema.Prompt.scorer import TOFHelper

tof = TOFHelper("TOF", ptstate='ABSORB')  # 1. create, with a unique name
tof.make(vol)                             # 2. attach to a volume (mandatory)
...
hist = sim.gatherHistData('TOF')          # 3. retrieve by name after simulate()
hist.savefig('tof.png')
```

A complete runnable script is
[`doc/example_basic.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py),
walked through line by line in [First simulation](first-simulation).

---

## 1. The scorer model

Every scorer is a *helper* class from `Cinema.Prompt.scorer`. Three things define one:

1. **A unique name** — the key you later use to fetch results.
2. **Binning** — range and bin count (plus linear vs logarithmic where supported).
3. **A `ptstate`** — the particle tracing state that triggers the counting action (section 2).

The helper object alone does nothing. **`scorer.make(volume)` is mandatory**: it is the call
that creates the C++ scorer and registers it with the volume. A helper that is never
`make()`-ed scores nothing and does not appear in `sim.scorer`.

Internally, `make()` calls `Volume.addScorer(...)`, which records the scorer in the
class-level dictionary `Volume.scorer_dict`. The simulation exposes this dictionary as the
`sim.scorer` property, and `sim.gatherHistData(name)` looks the name up there to return the
live histogram. Because the registry is keyed by name, **scorer names must be unique** within
a simulation.

```python
tof.make(vol)        # registers 'TOF' in Volume.scorer_dict
print(sim.scorer)    # {'TOF': 'TOF', ...}  (name -> name for helper scorers; name -> config string only for legacy string scorers)
```

Two more consequences of the model, developed in [Geometry](geometry) and
[Simulation lifecycle](simulation-lifecycle):

- Scorers belong to **logical volumes**; a volume only exists in the world once it is
  `placeChild`-ed, and `setWorld` closes the geometry. Build volumes and attach scorers
  inside `makeWorld()`, before `setWorld`.
- Re-running a second simulation in the same process requires `sim.clear()`, which resets
  the C++ scorer store *and* `Volume.scorer_dict`.

For a custom quantity you can derive your own helper from `ScorerHelper` (1D) or
`ScorerHelper2D`; see the class docstrings in
[`scorer.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/scorer.py).

---

## 2. When a scorer fires: the `ptstate` table

`ptstate` (class `ParticleTracingState`) defines the interaction type of the
particle–volume system that triggers the counting. Accepted values, with their numeric
codes:

| Value | Name             | Fires when |
|------:|------------------|------------|
| 0     | `SURFACE`        | An interaction at the volume *surface*, e.g. surface transmission or optics physics (mirror, chopper). |
| 1     | `ENTRY`          | The particle enters the volume (state *before* any physics happens in it). |
| 2     | `PROPAGATE_PRE`  | Immediately *before* a bulk-scattering interaction in the volume. |
| 3     | `PROPAGATE_POST` | Immediately *after* the bulk scattering — energy and momentum are already updated. |
| 4     | `EXIT`           | The particle exits the volume. |
| 5     | `PEA_PRE`        | Fires on propagate_pre, exit **or** absorb — the pre-hit "account for everything in this volume" variant. |
| 6     | `PEA_POST`       | The same trio (propagate_post, exit, absorb), post-hit variant. |
| 7     | `ABSORB`         | The particle is absorbed by *real* physics in the volume. |

`PEA_PRE`/`PEA_POST` exist so a single scorer can count every particle passing through a
volume regardless of whether it scattered, exited or was absorbed — use them for fluence-like
quantities. `ABSORB` fires only on genuine absorption, which is what makes the
`TOFHelper(..., ptstate='ABSORB')` absorber-channel TOF of `doc/example_basic.py` work.

Helpers accept either the enum member (`ParticleTracingState.EXIT`) or the **exact** string
(`'EXIT'`), see [gotcha 2](#8-gotchas).

### Nested volumes and double counting

`ENTRY` and `EXIT` fire at *every* boundary crossing. If a volume is nested inside another
volume, one traversal of the outer volume enters and exits the inner one too, so both
scorers count twice. The regression test
[`test_prompt_ptstate.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_scorers/test_prompt_ptstate.py)
makes this explicit: with a void sphere placed inside a void box, every history enters and
exits the box twice, and the `ENTRY` scorer records `2 x (number of histories)` hits
(verified at 1e4 events with tolerance 10%).

For counts that must not depend on how many boundaries were crossed, score on
`ABSORB`/`SURFACE`, or keep the scored volume free of nested daughters (flat geometry — the
pattern of every regression test that asserts one count per history). **`PEA_PRE`/`PEA_POST`
do not avoid the double counting**: they fire once per propagate/exit/absorb event, so in
nested volumes they count exactly like `ENTRY`/`EXIT`. Measured with the sphere-in-box
geometry above (1e4 MaxwellianGun events, seed 4096, scorers on the outer box), all four
states record 20000 hits — twice the number of histories — while the flat box without the
nested sphere records 10000. The role of the `PEA_*` states is counting every passing
particle whether it scattered, exited or was absorbed (fluence-like quantities), not
one-count-per-particle.

---

## 3. Scorer catalogue

All helpers live in `Cinema.Prompt.scorer`. Units are Cinema units: **eV** for energy,
**Å** for wavelength, **s** for time, **mm** for lengths, **Å⁻¹** for momentum transfer
(see [Geometry](geometry) for the coordinate conventions). `pdg=2112` (neutron) everywhere
by default.

| Helper | Scores (unit) | Default range and binning | Fires (default `ptstate`) | Notes |
|---|---|---|---|---|
| `ESpectrumHelper` | Kinetic energy (eV); energy transfer if `energyTransfer=True` | 1e-5..1 eV, 100 bins, **log** | `ENTRY` | `log=False` for linear bins |
| `WlSpectrumHelper` | Wavelength (Å) | 0.1..10 Å, 100 bins, **log** | `ENTRY` | |
| `TOFHelper` | Time-of-flight (s) | 0..40e-3 s, 100 bins, linear | `ENTRY` | |
| `PSDHelper` | 2D position (mm) | ±10 mm, 100x100 bins, linear | `ENTRY` | `psdtype` = `'XY'`/`'XZ'`/`'YZ'`; volume-local frame, global if `isGlobal=True` |
| `VolFluenceHelper` | Energy-resolved track-length fluence normalised by the volume capacity (1/mm²) | 1e-6..10 eV, 100 bins, **log** | fixed `PEA_PRE` | Divides by `vol.getCapacity()` (mm³) captured at `make()`; **invalid if particle weights change inside the volume** (gotcha 4) |
| `DirectSqHelper` | S(Q), momentum transfer Q (Å⁻¹) | none — `qmin`, `qmax`, `numbin` required, **log** | `ENTRY` | Requires `mod_smp_dist` (moderator-to-sample distance, mm); `refDir` incident direction, `samplePos`; `method=0` uses the real energy transfer, `method=1` the static approximation |
| `DirectSqwHelper` | S(Q,ω), Q (Å⁻¹) x energy transfer ω = E_final − E_initial (eV) | Q 0.1..10 Å⁻¹ in 50 bins; ω −0.1..0.1 eV in 30 bins | `ENTRY` | Requires `mod_smp_dist` (mm) and `mean_ekin` (eV); Q axis is always linearly binned for now (`log=True` warns) |
| `DepositionHelper` | Deposited energy spectrum, weighted by weight x survival probability | none — `min`, `max`, `numbin`, `pdg`, `ptstate` all required | user-set | |
| `MultiScatCounter` | Histogram of the number of scatterings per particle in the volume | fixed −2.5..100.5, 103 bins | fixed `PEA_POST` | See section 5 |
| `MCPLOutHelper` | Not a histogram: writes every scored particle to an MCPL file | — | fixed `ENTRY` | `kill=True` removes the particle after scoring (absorbing boundary) — since the scorer only fires at entry, it turns the volume surface into an absorbing front face; `compress=True` gzips; under MPI each rank writes `<name>_pro<rank>` |

Positions are scored in the volume-local frame by default (`PSDHelper(isGlobal=True)` for
the global frame), and `DirectSqHelper`/`DirectSqwHelper` need the moderator-to-sample
distance and beam direction because they reconstruct Q from the kinematics. For a worked
SANS example using `PSDHelper`, see
[`doc/example_sas.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_sas.py)
(a full walkthrough is on the [SANS with the SasCSNS plugin](tutorial-sans) page).

All histogram helpers except `MultiScatCounter` mix in `addScatterCounter` (section 5).

On binning keywords: `log` is the canonical flag (`log=True` for logarithmic bins) and
`linear=True`/`linear=False` remain as deprecated aliases that emit a `DeprecationWarning`;
passing both `log` and `linear` is an error. `DirectSqwHelper` is the 2-D exception: its
`logx` is a deprecated alias for `log`, and logarithmic Q binning is not supported by the
C++ scorer yet — `log=True` emits a `UserWarning` and the Q axis stays linearly binned, so
rebin in post-processing if you need log-Q.

---

## 4. One scorer, several placements: `scorerGroup` and `groupID`

A logical volume can be placed several times — an array of identical detectors is one
`Volume` placed at N transformations. `placeChild(..., scorerGroup=g)` tags each placement
with a group number, and a scorer with `groupID=g` only counts particles hitting placements
of the matching group. **`groupID=0` counts all placements.** (The placement transform
syntax is covered in [Geometry](geometry).)

The identity to remember:

```
groupID=0  ==  groupID=1 + groupID=2 + ...
```

The test
[`test_prompt_groupid.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_scorers/test_prompt_groupid.py)
verifies it end to end: one detector volume placed twice at ±45° (`scorerGroup=1` and
`scorerGroup=2`), three `ESpectrumHelper` scorers with `groupID` 0, 1, 2; at 1e6 events with
an `IsotropicGun` at 1 eV (seed 1010) the recorded hits are 128756 = 64291 + 64465.

```python
detector = Volume("detector", Box(100, 100, 1))
ESpectrumHelper('energy_gp0', 1e-6, 20e6, 100, groupID=0).make(detector)
ESpectrumHelper('energy_gp1', 1e-6, 20e6, 100, groupID=1).make(detector)
ESpectrumHelper('energy_gp2', 1e-6, 20e6, 100, groupID=2).make(detector)
world.placeChild('Dtt1', detector, trf_1, scorerGroup=1)
world.placeChild('Dtt2', detector, trf_2, scorerGroup=2)
```

This is an excerpt of the test's setup: `world` and the placement transforms
`trf_1`/`trf_2` (the two ±45° placements) are defined in the test linked above.

Caveat: `DirectSqHelper` accepts a `groupID` argument but does not forward it to the C++
scorer in this version — per-placement grouping is ineffective there (gotcha 7).

---

## 5. Multi-scattering decomposition

A common neutron-metrology task is separating the single-scattering signal from the
multiply-scattered background. The recipe uses two pieces:

1. A `MultiScatCounter` attached to the sample volume — it counts, per particle, how many
   scatterings happened there.
2. `scorer.addScatterCounter(counter, n)` on any other scorer — it restricts that scorer to
   particles whose scattering count satisfies `n`:

| `n` | Particles counted |
|----:|-------------------|
| `-2` (default) | all particles |
| `-1` | only particles that never entered the counter volume |
| `0` | entered the counter volume but did not scatter in it |
| `n > 0` | scattered exactly n times in the counter volume |

```python
from Cinema.Prompt.scorer import ESpectrumHelper, MultiScatCounter

counter = MultiScatCounter()          # name defaults to 'ScatterCounter'
counter.make(sample)                  # attach to the SAMPLE volume

det = Volume('det', Sphere(80, 80 + 1e-3))
for n in (-2, 0, 1, 2):
    s = ESpectrumHelper(f'ekin{n}', 1e-5, 1, 100)   # log E bins, 1e-5..1 eV
    s.make(det)                                      # attach to the DETECTOR volume
    s.addScatterCounter(counter, n)
```

Excerpt of [`test_prompt_multiScatMixin.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_scorers/test_prompt_multiScatMixin.py):
there, `sample` is a box volume placed directly in the world (no nested daughters).

One counter can be shared by many scorers with different `n` — that is the standard
single/multiple-scattering separation. With absorption disabled, the identities
`total(-2) == number of incoming particles` and `sum over n >= 0 == number of incoming
particles` are regression-tested at 1e5 events (seed 1010) in
[`test_prompt_multiScatMixin.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_scorers/test_prompt_multiScatMixin.py).

The counter's own histogram is also useful directly: bin index = scattering number + 2
(range −2..100), so `sim.gatherHistData('ScatterCounter').getWeight()[2]` is the weight of
particles that traversed the sample without scattering.

The biasing machinery records the per-particle scattering number into MCPL output files as
well, which allows the same decomposition *post hoc* — see [Analysing results](results-analysis).

---

## 6. Reading results in-session

After (or during) `simulate()`, results are fetched **by scorer name**:

```python
hist = sim.gatherHistData('TOF')   # Hist1D or Hist2D, live view of the C++ histogram
hist.savefig('tof.png')            # or hist.plot(show=True) for an interactive window
hist.save('tof.h5')                # HDF5 (weight/hit/sdev/edges)
xy = hist.toArrayXY()              # error-propagating 1D array
```

Equivalently, `scorer.getHistogram()` fetches the live histogram through the helper object.
`sim.save_all_scorers(savepdf=False)` loops over everything in `sim.scorer` and writes one
`<name>.h5` (plus `<name>.pdf` if `savepdf=True`) per scorer; under MPI it writes from rank 0
only.

The quick histogram API you will use most:

| Call | Meaning |
|---|---|
| `getWeight()` | per-bin weight sums ("the spectrum") |
| `getHit()` | per-bin entry counts |
| `getSdev()` | per-bin `sqrt(sum of w²)` — a heuristic uncertainty estimate |
| `getTotalWeight()` | sum of everything, **including** over/underflow |
| `getAccWeight()` / `getTotalHit()` | weight/hit sums over in-range bins only (excluding over/underflow) |
| `getEdges()` / `getCentre()` / `getMean()` | bin edges (`nbins+1`), centres, weighted mean |
| `getOverflow()` / `getUnderflow()` | summed weight of entries outside the scored range (equal to the particle count only for unit-weight particles) — always check these after changing a range |
| `plot(...)` / `savefig(fname)` | matplotlib output (2D plots use log colour scale) |
| `fill(x, w)` / `fillmany(x, w)` | fill your own `Hist1D`/`Hist2D` (e.g. when post-processing MCPL files) |

`Hist1D` and `Hist2D` can also be created standalone (`Hist1D(xmin, xmax, num)`) and merged
(`hist1.merge(hist2)`, which sums weights/hits and combines errors in quadrature); MPI result
reduction and multi-seed averaging use related machinery (`comm.Reduce` +
`setWeight`/`setHit`/`setWW`, and `McplAnalysor.getHistMany`) covered on the
[Analysing results](results-analysis) page.
A full treatment of histograms, MCPL particle files, the `ptplot` tool and error propagation
is on [Analysing results](results-analysis); unit conversion helpers are on the
[Units](units) page.

Under MPI, `PromptMPI.gatherHistData(name, dst=0)` sums the per-rank histograms to rank
`dst` (default 0); **only that rank receives valid data**, so gate any plotting/saving with
`if sim.rank == 0:`. MPI run semantics are covered in [Simulation lifecycle](simulation-lifecycle).

---

## 7. Legacy scorer configuration strings (deprecated)

> **Legacy.** The `ConfigString`-based scorer classes (`PSD`, `WlSpectrum`, `ESpectrum`,
> `TOF`, `VolFluence`), the `ScorerHelperV1` family (`ESpectrumHelperV1`,
> `WlSpectrumHelperV1`, `TOFHelperV1`, `VolFluenceHelperV1`) and the free function
> `makePSD` date from the v1 string-configuration era. They are invoked by passing a config
> string to `Volume.addScorer`, e.g.
> `vol.addScorer("Scorer=TOF; name=tof1; min=0.; max=0.04; numbin=100; ptstate=ENTRY")`.
> They still work but are marked in the source "to be reviewed and potentially deprecated",
> and constructing one now emits a `DeprecationWarning`.
> **Do not use them in new work** — use the helper classes of section 3, which construct the
> C++ scorers directly. The same applies to GDML-declared scorers of the legacy GDML input
> path; the Python API is the supported route.

---

## 8. Gotchas

1. **`make(volume)` is mandatory.** An un-`make()`-ed helper scores nothing and is absent
   from `sim.scorer`, so `gatherHistData` raises `KeyError` — the message now lists the
   registered scorer names (`no scorer named 'TOF'; registered scorers: [...]`), so a typo
   or a missing `make()` is visible at a glance.
2. **`ptstate` strings must match exactly.** `'PROPAGATE'` alone is invalid and raises
   `RuntimeError` when the scorer is created (`ptsNum`); the valid strings are exactly the
   eight names of section 2. Passing the enum member
   (`from Cinema.Prompt.scorer import ParticleTracingState`) removes the string risk.
   Note the base class itself has no default, so helper authors must pass one; at the user
   level every helper except `DepositionHelper` already sets one — `'ENTRY'` by default,
   with `VolFluenceHelper` fixed to `PEA_PRE`, `MultiScatCounter` fixed to `PEA_POST` and
   `MCPLOutHelper` fixed to `ENTRY` —
   so `ptstate` may simply be omitted unless you are using `DepositionHelper`.
3. **`ENTRY`/`EXIT` double count in nested volumes** (each boundary crossing fires) — see
   section 2 for the sphere-in-box example. `PEA_*` does not avoid this either: it fires per
   propagate/exit/absorb event, so it double-counts the same way.
4. **`VolFluenceHelper` is only valid where weights do not change.** It divides track length
   by the volume capacity and assumes unit biasing factor D inside the volume; if a particle
   weight changes inside the scored volume it throws a C++ `LogicError` ("The D value for
   the material ... should be unity"). Do not combine it with non-unity
   `scatter_bias`/`abs_bias` in that volume — see [Materials and physics](materials-physics).
5. **Log-binned scorers need positive edges.** `ESpectrumHelper`, `WlSpectrumHelper`,
   `VolFluenceHelper` and `DirectSqHelper` default to logarithmic bins (`log=True`); the
   constructor validates the range up front and raises `ValueError`
   ("min ... must be positive for logarithmic binning", or "range min ... must be smaller
   than max") instead of failing later inside the C++ histogram. Pass a positive range, or
   `log=False` for linear bins.
6. **Scorer names must be unique.** `Volume.scorer_dict` is keyed by name; a duplicate name
   silently collides in the registry. (A `scorerNameConfig` helper that renames duplicates
   with a trailing backtick exists but is never called automatically — do not rely on it.)
7. **`DirectSqHelper` ignores its `groupID`.** The argument is accepted but not forwarded to
   the C++ scorer in this version; per-placement grouping (section 4) does not apply to it.
8. **Check units before interpreting a histogram.** TOF is in seconds, energy in eV,
   wavelength in Å, Q in Å⁻¹, PSD in mm, distances in mm. MCPL *particle* files written by
   `MCPLOutHelper` carry the internal eV/s/mm values on disk even though their metadata
   claims cm/MeV/ms — see [Analysing results](results-analysis) and [Units](units) before
   feeding them to `MCPLGun`, `MCPL_Analyzer_*`, `ptplot`'s MCPL mode or any standard-unit
   reader. (Genuine MCPL-standard files from other codes are cm/MeV/ms.)
9. **MPI: only the destination rank has data.** `gatherHistData` reduces to rank 0 by
   default; on other ranks the returned object holds invalid data. Gate output with
   `if sim.rank == 0:`.
10. **Call `sim.clear()` between simulations in one process** — otherwise scorers and the
    old world leak into the next run (the test suite does this in every test).
11. **All-zero histograms with exit code 0 usually mean the gun is outside the world.** Every
    primary born outside the world volume is dropped before tracking starts and each one prints
    `particle at {...} is outside the world` to stdout; no scorer ever fires. Check the gun
    `position` against the world extent (see [Geometry](geometry), world-assembly rule 5) before
    suspecting the scorer setup.

---

## Where to go next

- [Geometry](geometry) — volume placement, `scorerGroup` and the coordinate conventions
- [Materials and physics](materials-physics) — biasing, and the weight-change caveat behind gotcha 4
- [Simulation lifecycle](simulation-lifecycle) — `clear()`/rebuild, seeds, MPI result reduction
- [Your first simulation](first-simulation) — line-by-line walkthrough of `doc/example_basic.py`
- [Analysing results](results-analysis) — the Histogram/MCPL material of section 6 in depth
- [Units](units) — unit conversions
- [SANS with the SasCSNS plugin](tutorial-sans) — step-by-step walkthrough of `doc/example_sas.py`
- [FAQ](faq) — common scoring puzzles

---

*Source files: [`scorer.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/scorer.py),
[`geo.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/geo.py) (`Volume.addScorer`, `placeChild`),
[`promptCore.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/promptCore.py) (`gatherHistData`, `save_all_scorers`),
scorer tests in [`src/pythontests/prompt_scorers/`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_scorers/).
Questions: cinema-users@outlook.com.*
