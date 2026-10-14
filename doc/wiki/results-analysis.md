# Analysing results: histograms, MCPL files and error propagation

This page covers the half of the workflow that comes *after* transport: getting data out of a
run, what lands on disk, how to read those files back, combine them, plot them and propagate
uncertainties. Scorer creation is covered in [Scoring](scorers); run execution (seeds, MPI) in
[Simulation lifecycle](simulation-lifecycle). Everything here is the Python API, documented
against Cinema 2.0.0a5. Runnable companions:
[`doc/example_basic.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py),
[`doc/example_sas.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_sas.py)
and the pure-analysis [`examples/example_1d_analysis.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/examples/example_1d_analysis.py)
/ [`examples/example_2d_analysis.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/examples/example_2d_analysis.py).

---

## 1. Getting data out of a run

There are four routes out of a simulation:

| Route | How | Output |
|---|---|---|
| In-session histogram | `hist = sim.gatherHistData('name')` | Merged `Hist1D`/`Hist2D`. With `PromptMPI` the destination rank receives an **independent clone** holding the reduced arrays — the live scorer histogram is never written, so use the return value (plain serial `Prompt` returns a live view of the scorer instead) |
| All scorers to disk | `sim.save_all_scorers(savepdf=False)` | One `<name>.h5` per scorer, written on rank 0; `savepdf=True` adds a `<name>.pdf` each |
| Histogram dump at end of run | `sim.simulate(gun, n, save2Disk=True)` (under MPI written on rank 0; silently ignored for `PythonGun` guns — see below) | `<internal name>_seed<seed>.mcpl.gz` + a ready-made `<internal name>_view.py` template (section 3) |
| Particle records | `MCPLOutHelper` scorer | One MCPL particle file per rank: `<name>_pro<rank>.mcpl.gz` (section 5) |

```python
sim.simulate(gun, 100000)
hist = sim.gatherHistData('TOF')
if sim.rank == 0:                 # MPI: data is valid on the destination rank only
    hist.save('tof.h5')           # HDF5
    hist.savefig('tof.png')       # quick matplotlib export
```

Class-specific restrictions, all verified in 2.0.0a5:

- **`save_all_scorers` is `PromptMPI`-only.** It reads `self.rank`, which plain `Prompt` does
  not define: on a serial `Prompt` object it raises `AttributeError: 'Prompt' object has no
  attribute 'rank'`. Derive from `PromptMPI`.
- **The `save2Disk=True` histogram dump under MPI is written by rank 0 only.** The
  `PromptMPI.simulate` signature is now `simulate(gun, num, timer=True, save2Disk=False)`:
  the root rank runs with your flags and writes the `<...>_seed<seed>.mcpl.gz` files, while
  non-root ranks never dump (their local histograms are reduced to the root afterwards) and
  never print the timer.
- **`save2Disk=True` is silently ignored for `PythonGun` guns.** Config-string and
  config-object guns (`UniModeratorGun`, ...) go through the launcher and dump normally,
  but a `PythonGun` subclass takes the `gun.generate()`/`simOneEvent` loop, which never
  reaches the dump code — measured: 100 events with `save2Disk=True` wrote no
  `Scorer*.mcpl.gz` and printed no warning. Workaround: call `sim.l.go(n, save2Disk=True)`
  directly (measured to dump), or save the gathered histograms yourself.
- With the defaults (`save2Disk=False`, no `save_all_scorers()`) a run writes **no files at
  all**; results live in memory until you gather them.

---

## 2. `Hist1D` and `Hist2D`

Both classes wrap a C++ histogram. They come back from `gatherHistData`, and can also be
created standalone to bin data yourself (e.g. post-processing MCPL files):

```python
from Cinema.Prompt.histogram import Hist1D, Hist2D

h1 = Hist1D(1e-5, 1., 100, linear=False)   # linear binning is the default; linear=False selects log bins
h2 = Hist2D(-10, 10, 100, -10, 10, 100)    # 2D axes are always linear
h1.fillmany(energies, weights)             # or h1.fill(x, w) scalars
```

The accessors you will actually use:

| Call | Meaning |
|---|---|
| `getWeight()` / `getWW()` | Per-bin weight sums ("the spectrum") and the raw per-bin Σw² array |
| `getHit()` | Per-bin entry counts |
| `getSdev()` | Per-bin `sqrt(Σw²)` — the standard uncertainty estimate (section 8) |
| `getAccWeight()` / `getTotalHit()` | Weight/hit sums over in-range bins (computed from the arrays) |
| `getTotalWeight()` | A C++-side scalar accumulator, over/underflow included (gotcha 4) |
| `getOverflow()` / `getUnderflow()` | Weight that fell outside the scored range — always check after changing a range |
| `getEdges()` / `getCentre()` / `getMean()` | Bin edges (`nbins+1`), centres, weighted mean |
| `scale(f)` / `reset()` / `addNote(s)` / `getNote()` | Rescale (content and totals by f, Σw² by f², so `getSdev()` by \|f\|; hits are fill counts and stay), start over, free-form metadata — checked by `Hist1D.merge` only, ignored by `Hist2D.merge` |
| `fill(x, w)` / `fillmany(x, w)` | Fill (1D; `Hist2D.fill(x, y, w)`) |
| `toArrayXY()` (1D) | Convert to an error-propagating `CinemaXY` array (section 8) |

Plotting: `Hist1D.plot(show=False, label=None, title=None, log=False, sigma=1, ax=None)`
draws an errorbar plot with `yerr = sigma * getSdev()`; `log=True` switches **both** axes to
log scale, `log=[xlog, ylog]` sets them independently. With no `ax` argument the method
creates and returns a new `Figure`; given an `ax` it returns that axes. `Hist2D.plot(...,
log=True, dynrange=1e-3)` draws a log-colour `pcolormesh`; `savefig(fname,
title='Histogram', log=...)` writes a 300-dpi PNG/PDF.

> **Compatibility note.** The file is written first and is always complete. On some existing
> 2.0.0a5 installs `savefig` prints `AttributeError: 'Figure' object has no attribute 'close'`
> afterwards — harmless; wrap the call in `try/except AttributeError` if it bothers you.
> Current builds return cleanly.

`hist1.merge(hist2)` combines two histograms of the same geometry; for `Hist1D` the `note`
strings must also match (tag 1D runs with `addNote` to keep them distinguishable). The two
guards fail very differently:

- **Note mismatch (`Hist1D` only)** raises an ordinary, catchable `RuntimeError`.
- **Geometry mismatch — different xmin/xmax or bin count (2D: also the y axis) — aborts the
  interpreter; it does not raise.** The C++ side throws `CalcError`, but `merge` is a raw
  ctypes call and the exception is never converted to a Python one: `std::terminate` fires and
  the process dies with SIGABRT (measured: `Hist1D(0,10,10).merge(Hist1D(0,20,10))` prints
  `terminate called after throwing an instance of 'Prompt::Error::CalcError'`; even
  `except BaseException` cannot catch it). To fail gracefully, compare `getXMin()`/`getXMax()`
  and `numbin` (2D: `ymin`/`ymax`, `xNumBin`/`yNumBin`) in Python *before* calling `merge`.

**`Hist2D.merge` overrides `merge` and never checks notes**: two 2D histograms with
different notes merge silently, keeping the first note (measured: weights 2+3 summed, note
`runA` kept) — notes do not keep two PSD-map runs apart; tag 2D runs by file name instead
(gotcha 6). Weights, hits **and** the Σw² arrays are summed, so the merged `getSdev()` =
`sqrt(Σ(Σw²))` is exactly the quadrature of the per-run uncertainties. Measured: a bin with
weight 5, Σw²=13 merged with weight 1, Σw²=1 gives weight 6 and `getSdev()` ≈ 3.742
(= `sqrt(14)`); two *independent single-fill* runs with weights 2 and 3 merge to sdev 3.606
= `sqrt(2² + 3²)`, the statistically correct value. `merge` and the MPI reduce (which also
sums Σw²) agree; for file-based multi-run averaging use `McplAnalysor.getHistMany`
(gotcha 6).

---

## 3. Output artefacts and naming

All files land in the current working directory.

| File | Written by | Content |
|---|---|---|
| `<name>.h5` | `save_all_scorers()` (rank 0) | HDF5 with gzip-compressed datasets `center` (or `xcenter`/`ycenter`), `edge` (or `xedge`/`yedge`), `weight`, `hit`, `sdev` plus the scalar strings `note` and `type` (the C++ class, e.g. `ScorerESpectrum`). This is what `ptplot` and `CinemaXY.from_hdf5` read. |
| `<name>.pdf` | `save_all_scorers(savepdf=True)` (rank 0) | Quick-look plot per scorer, alongside the `.h5`. |
| `<internal name>_seed<seed>.mcpl.gz` | `simulate(..., save2Disk=True)`, serial mode | Despite the extension this MCPL container carries the **histogram** as header blobs: `content`, `hit`, `edge` (`xedge`/`yedge` for 2D), `overflow`, `underflow`; header comments record scorer name, type, total hit, integral/accumulated weight, overflow and underflow. A ready-made plotting template `<internal name>_view.py` (base name without the `_seed<seed>` part) is written next to it — run `python3 <internal name>_view.py` for a quick look. |
| `<name>_pro<rank>.mcpl.gz` (particle records) | `MCPLOutHelper` scorers | One MCPL particle file per rank, section 5. The helper also dumps its internal counter histogram (fixed range −2.5..100.5) as `KillerMCPL_<name>_pro<rank>_seed<seed>.mcpl.gz` + `_view.py` — it counts scored particles, not a spectrum. |

Names: `.h5`/`.pdf` files use the **user scorer name** (`TOFHelper("TOF")` → `TOF.h5`),
while the `save2Disk` dump uses the **internal histogram name** `Scorer<Type>_<user name>`
→ `ScorerESpectrum_espec_seed5489.mcpl.gz` for `ESpectrumHelper('espec', ...)`.

**The seed in the file name is not your constructor seed.** The name embeds the C++ RNG seed
*at the moment the scorer is created*, i.e. during `makeWorld`, before `setWorld` applies the
constructor seed ([Simulation lifecycle](simulation-lifecycle)). Measured with
`ESpectrumHelper('espec')`, constructor seed 4096: a first `makeWorld` in a fresh process
writes `ScorerESpectrum_espec_seed5489.mcpl.gz` (5489 = library default, regardless of the
constructor seed); after `sim.clear()` + a second `makeWorld()` the next dump lands in
`ScorerESpectrum_espec_seed4096.mcpl.gz`, **added next to** the first file. So fresh-process
reruns **overwrite** the `_seed5489` file no matter which seed you pass, while rebuild loops
in one process accumulate files — treat the suffix as provenance, not a safety net; move or
rename outputs you want to keep.

> **Legacy notice.** Runs driven through the old GDML input path of the `prompt` command
> produce the same `<name>_seed<seed>.mcpl.gz` histogram dumps (their only output route).
> GDML input is legacy; the Python API with `save_all_scorers()` is the supported workflow.

---

## 4. `ptplot`: plotting `.h5` (and MCPL) files from the command line

`ptplot` is installed with the package (entry point
`Cinema.Prompt.cli.ptplotcli:main`): it loads each file into a `CinemaXY` array (section 8),
prints shape/weight/sdev ranges and draws errorbar plots.

```bash
ptplot tof.h5                      # single file, interactive window
ptplot *.h5                        # glob: ALL matched files combined into ONE figure
ptplot monitor1.h5+monitor2.h5     # "+" group: both curves in ONE figure
ptplot -d runs/*.h5                # -d downbins once (pairwise merging), -dd twice, ...
ptplot --ylin spectrum.h5          # linear y axis (log is the default)
ptplot data/*.h5 -o plots/ --no-show   # -o: existing output dir (or a file path)
ptplot x -s                        # list every parameter/unit pair understood below
```

Notes from the implementation, verified in 2.0.0a5:

- `-d/--downbinning` is a counter flag: each `-d` merges neighbouring bin pairs
  (`d[::2] + d[1::2]`), halving the bin count — handy for noisy spectra.
- `-s/--show` lists the tunable `para=...;unit=...` pairs (`time`, `ekin`, `x`, `y`, `z`,
  ...) but still requires the positional file argument: pass a dummy (`ptplot x -s`); the
  file is never touched. `-o` must be an **existing** directory (or a full file path);
  plots are named after the input (`combined_tof+monitor1.png` for a `+` group).
- MCPL files are also supported through a config-string syntax, evaluated with
  `Cinema.analysis` (section 7) — so the unit trap of that section applies here too:

```bash
ptplot "det_pro0.mcpl.gz;para=ekin;unit=eV;binmin=0;binmax=0.01;binnum=50"
ptplot "det_scat_*_pro0.mcpl.gz;para=scattering_angle;unit=deg;binmin=0;binmax=180;binnum=1800;incident_params=[incident_wavelength_A=4;incident_direction=(0,0,1)]"
```

The full command-line surface of `prompt` and `ptplot` lives on the [CLI](cli) page.

---

## 5. MCPL particle files: `MCPLOutHelper` and `PTMCPL`

`MCPLOutHelper` is not a histogram: it writes every scored particle to an MCPL file.

```python
from Cinema.Prompt.scorer import MCPLOutHelper
dump = MCPLOutHelper('det', kill=False)   # kill=True: particle removed after scoring
dump.make(detVol)                          # useful as an absorbing world boundary
```

`compress=True` (default) gzips the file to `.mcpl.gz`. A `_pro<rank>` suffix is appended in
the constructor whenever `mpi4py` is importable — which, in a working installation, is
*always*: serial runs write `det_pro0.mcpl.gz`, an N-rank run produces `det_pro0.mcpl.gz`
... `det_proN-1.mcpl.gz`; iterate them all (or merge with the `mcpl` tools) when analysing.
The helper also owns an internal counter histogram which `save_all_scorers()` writes as
`det.h5` — counts scored particles, not a spectrum.

**Field reuse.** MCPL has no place for Cinema's biasing bookkeeping, so spare standard fields
carry it. The particle fields themselves are stored in the MCPL standard units the metadata
claims (cm/MeV/ms — the writer applies the x0.1/x1e-6/x1e3 conversions; files written by
Cinema v2.0.1a1 through v2.1.0 carried the internal eV/s/mm unconverted):

| MCPL field | Stored quantity | Units on disk |
|---|---|---|
| `userflags` | event ID | — |
| `polarisation[0]` | survival probability | — |
| `polarisation[1]` | scattering number | count; **−3 when no `MultiScatCounter` is attached** |
| `polarisation[2]` | energy loss ΔE = E₀ − E | MeV |
| `ekin` | kinetic energy | MeV |
| `time` | time of flight | ms |
| `position` | position | cm |

Measured (2000 events, seed 4096, 1 meV neutrons flying 999 mm through void to the scorer):
`ekin 1e-9`, `time 2.28`, `z −0.1`, `pol (1.0, −3.0, 0.0)`, `userflags` 1, 2, 3, ...
so every standard-conforming reader — the `mcpl` tools, `MCPLGun`, `Cinema.analysis` —
sees the same numbers the simulation held (section 7 covers the pre-2.1.0 exception).
`PTMCPL` (exported from `Cinema.Prompt`) decodes the reused fields for you:

```python
from Cinema.Prompt import PTMCPL
from Cinema.Prompt.histogram import Hist1D
file = PTMCPL('det_pro0.mcpl.gz')
hist = Hist1D(1e-12, 4e-8, 500)            # MeV axis: values on disk are MeV
for pb in file.particle_blocks:
    hist.fill(pb.differential_energy, pb.survival_probability * pb.weight)
```

Per block (`PTParticleBlock`, a numpy-vectorised view of many particles):

| Accessor | Meaning |
|---|---|
| `event_id`, `survival_probability`, `scattering_number`, `differential_energy` | The four reused fields |
| `weight`, `ekin`, `position`, `time`, ... | Standard MCPL fields (forwarded) |
| `getSingleScatteringFlags()` / `getMultipleScatteringFlags()` | scattering number == 1 / > 1 |
| `getElasticFlags()` / `getInelasticFlags()` | ΔE == 0 / ΔE ≠ 0 |
| `getSingleElasticScatteringWeight()` | weight of single-elastic particles |
| `getSingleInelasticScatteringWeight()` | weight of single-inelastic particles |
| `getMultipleScatteringWeight()` | weight of multiply-scattered particles |

The raw field names (`polx`, `polarisation`, ...) are deliberately blocked — access raises
`AttributeError` pointing you to the named accessors.

The bookkeeping identity behind these accessors is the core of probability-conserving
variance reduction: **the physical contribution of a recorded particle is
`survival_probability × weight`**, and the flag accessors decompose a spectrum into
single-elastic / single-inelastic / multiple-scattering parts *post hoc* — the MCPL
equivalent of the `addScatterCounter` decomposition in [Scoring](scorers); biasing itself is
covered in [Materials and physics](materials-physics). The decomposition needs a
`MultiScatCounter` in the chain: without one the scattering-number field holds the sentinel
−3, single/multiple flags and weight accessors return 0 (measured above), while the
elastic/inelastic split (ΔE == 0) still works.

---

## 6. Reading results back

### Histogram blobs: `PromptFileReader`

```python
from Cinema.Prompt import PromptFileReader
f = PromptFileReader('ScorerESpectrum_espec_seed5489.mcpl.gz', dumpHeader=False)
x, y = f.getData('edge'), f.getData('content')   # numpy arrays from the blobs
print(list(f.dataKeys()), f.getComments())       # blob keys, header comment lines
```

`getData(k)` unpacks the named blob (`content`, `hit`, `edge`, `xedge`, `yedge`, `overflow`,
`underflow`); `getComments()` returns the statistics lines recorded at write time. The
`_view.py` file next to the dump shows the same reload plus a matplotlib plot (it divides by
the bin width — appropriate for log-binned spectra). `PromptFileReader` also exposes
`blockIterator()` for particle records, but **for particles use `PTMCPL`** (section 5):
its record helpers are keyed on a stale field map (gotcha 8).

### Multi-seed merging: `McplAnalysor`

`McplAnalysor` (same module) rebuilds an `ErrorPropagator` (section 8) from a histogram dump:

```python
from Cinema.Prompt.PromptFileReader import McplAnalysor
import matplotlib.pyplot as plt
ana = McplAnalysor('runs/ScorerESpectrum_espec_seed*.mcpl.gz', dumpHeader=False)
hist = ana.getHistMany()      # sums every matched file, errors in quadrature
x = hist.xcentre              # NB: this array actually holds the nbins+1 bin edges
plt.errorbar(x[:-1], hist.weight, yerr=hist.error, fmt='s-')
plt.show()
```

Do **not** call `hist.plot()` on the result: `getHist`/`getHistMany` build the
`ErrorPropagator` with the `nbins+1`-element **edge** array passed as `xcentre`, and its
`plot` then prints `'x' and 'y' must have the same size` and returns `None` — no figure, no
exception (measured). Plot from the arrays as above (the merge itself is unaffected).

`getHistMany(offset=0, num=None)` sorts the matched files by the **last integer in the file
name** and merges them one by one via `ErrorPropagator.__iadd__` (weights add, errors combine
in quadrature) — measured on two 3000-event dumps: merged total weight 6000. With a
single-file path, `getHist()` returns just that file. This is the reading half of the
independent-seed pattern on the [MPI at scale](mpi-scale) page.

---

## 7. Post-hoc analysis with units: `Cinema.analysis`

`Cinema.analysis` builds histograms *from MCPL particle files* with explicit unit handling.

- **Unit enums** (`TimeUnit`, `EnergyUnit`, `LengthUnit`, `AngleUnit`,
  `MomentumTransferUnit`, `WavelengthUnit`, `VelocityUnit`) each provide `.convert_to(value,
  target)` and a default. Defaults: **ms** (time), **MeV** (energy), **cm** (length), cosine
  (angle), Å⁻¹ (Q), Å (wavelength), **mm/s** (velocity) — MCPL-standard conventions, not
  Cinema's internal eV/s/mm (trap below). More conversions on the [Units](units) page.
- **`ParticleParameter`** names what to histogram. Direct parameters read MCPL fields
  (`TIME`, `KINETIC_ENERGY`, `X/Y/Z_POSITION`, `X/Y/Z_DIRECTION`, `PDG_CODE`, `WEIGHT`,
  `EVENT_ID`, ...); calculated parameters (`MOMENTUM_TRANSFER_Q`, `ENERGY_TRANSFER_OMEGA`,
  `SCATTERING_ANGLE`, `WAVELENGTH`, `VELOCITY`) are derived per particle. Only the first
  three require the matching `IncidentParameters` subclass (else `ValueError`);
  `WAVELENGTH`/`VELOCITY` derive from the outgoing ekin alone. Enum members and plain
  strings (`para='time'`) are both accepted.
- **`IncidentParameters(incident_energy_eV=...)` or `(incident_wavelength_A=...)`** (exactly
  one), optionally `incident_direction=(0,0,1)` and `sample_position=(0,0,0)`; subclasses
  `MomentumTransferQParameters`, `EnergyTransferOmegaParameters`,
  `ScatteringAngleParameters` (a config string is accepted too).
- **`MCPL_Analyzer_1D(para, unit, incident_params, binmin, binmax, binnum, linear,
  auto_range_file)`** is a `Hist1D` subclass: `analyze(filename)` streams the file and fills
  the histogram, converting units and computing derived quantities; `MCPL_Analyzer_2D` does
  the same per axis. `auto_range_file='<some file>'` pre-scans that file and sizes the bins
  to its range (min × 0.9 to max × 1.1, measured) — useful when the range is unknown.

```python
from Cinema.analysis import MCPL_Analyzer_1D, MomentumTransferQParameters
ana = MCPL_Analyzer_1D(para='momentum_transfer_q', unit='AA^-1',
                       incident_params=MomentumTransferQParameters(incident_wavelength_A=2.5),
                       binmin=0.01, binmax=3, binnum=100)
ana.analyze('det_scat_pro0.mcpl.gz')
ana.plot(show=True)
```

**The MCPL boundary-unit trap.** Every unit conversion in `Cinema.analysis` — and in the
`MCPLGun` source, [Guns](guns) — assumes the file is in MCPL standard units (cm/MeV/ms),
and current `MCPLOutHelper` files are (section 5): the writer applies the conversions, so
no action is needed for files written by this release. The trap remains for **files written
by Cinema v2.0.1a1 through v2.1.0**: their numbers on disk are eV/s/mm while the metadata claims
cm/MeV/ms, so `MCPL_Analyzer_1D(para='velocity')` lands the 1 meV / 999 mm particle of
section 5 in the ≈4.5×10⁸ mm/s bin — as if the particle had 1 keV; the 10⁶ energy misread
becomes a 10³ velocity error (v ∝ √E; true ≈4.4×10² m/s) — and `para='time'` stretches the
true 2.28 ms flight a thousandfold. `auto_range_file` picks up the misread scale, and
`ptplot`'s MCPL mode inherits the same assumption. Workarounds, in order of preference:

1. Read with `PTMCPL` and convert explicitly — old-file values are already in Cinema units
   (eV/s/mm), so usually *no* conversion is needed before filling your own histogram.
2. To use `MCPL_Analyzer_*` (or `ptplot`'s MCPL mode) on an old file, convert it into
   standard units first — the `PTMCPL` + `MCPLBinaryWrite` recipe on the [Units](units)
   page does exactly that (`ekin × 1e-6` eV→MeV, `time × 1e3` s→ms, `position × 0.1`
   mm→cm) and is verified end-to-end.
3. Files from this release, or genuine standard-unit files from other codes, need none of
   this — `Cinema.analysis` is correct for them as documented.

---

## 8. Error propagation

Two uncertainty models coexist; know which one your numbers carry.

**Σw² (the transport histograms).** Every C++ histogram accumulates per-bin Σw²;
`getSdev()` returns `sqrt(Σw²)` — the standard error of the bin's weight sum for
independently sampled histories, and the meaningful estimate for scorer output — carried by
`Hist1D.plot`, the `.h5` files (`sdev` dataset) and `CinemaXY.from_hdf5`.

**The `hit/10` heuristic (read-back paths).** `ErrorPropagator(weight, xcentre, count=...)`
and `SpectrumEstimator` fall back to

```
err = w / sqrt(hit / 10)
```

when no explicit error is supplied. Measured: `SpectrumEstimator.fill(x=1, w=20, hit=1)` →
`getError()` = 63.25 = 20/sqrt(0.1); `ErrorPropagator` with `count=[10, 40]` on `w=[100,
200]` → `error=[100, 100]`. It is a rough per-bin relative-error guess assuming many
similarly weighted contributions, used wherever only weights and hits survive — notably
`McplAnalysor.getHist`/`getHistMany`, because the `.mcpl.gz` histogram blobs store `content`
and `hit` but no Σw². Caveats: blind to strongly weighted rare events (biasing!), and
zero-hit bins return **0** error, not NaN, so they plot as "precise zeros".

`ErrorPropagator` (in `Cinema.Experiment.Analyser`) supports `+=`, `-=`, `/=` and `.scale(f)`
with errors propagated in quadrature (measured: 100 ⊕ 5 → 100.12) and rejects incompatible
axes — the same quadrature convention as `Hist.merge` and the MPI reduce (gotcha 6). It is one
piece of the wider `Cinema.Experiment` toolbox for comparing simulated histograms with real
beamline data; the rest of it, and the research modules built around it, are described on
[Adjacent research modules](adjacent-research-modules).

**`CinemaXY` / `CinemaXYZ`** (`Cinema.array`, backed by `gvar`) turn histograms into arrays
that propagate errors through arithmetic:

```python
xy = hist.toArrayXY()          # or CinemaXY.from_hist1d(hist), CinemaXY.from_hdf5('tof.h5')
scaled = xy * 2                # mean doubles, sdev doubles (verified)
squared = xy ** 2              # relative errors double (verified)
fine = xy.interpolate(np.linspace(xmin, xmax, 200))   # needs an ARRAY of x values
```

- `xy.mean`, `xy.sdev`, `xy.x` are plain numpy views; `xy.plot(ax=...)` draws mean ± sdev.
  2D: `CinemaXYZ.from_hist2d(hist2d)`; `.plot(plot_errors=True)`, `.plot_surface()`,
  `.interpolate(new_x, new_y)` — feed it bin **centres** (`data.x`), not edges.
- `interpolate` rejects a scalar x (`TypeError`) and out-of-range points; not every numpy
  ufunc is guaranteed to exist on every build (`**2` and `np.exp` usually work; the in-repo
  examples wrap exotic operations in `try/except`). Treat `+ - * /`, scalar scaling and
  `interpolate` as the stable core.

---

## 9. Gotchas

1. **`save_all_scorers()` requires `PromptMPI`.** On plain `Prompt` it raises
   `AttributeError: 'Prompt' object has no attribute 'rank'` (section 1).
2. **Under MPI the `save2Disk=True` dump is rank-0 only** — non-root ranks never write the
   `<...>_seed<seed>.mcpl.gz` histogram files (section 1). Even in serial mode the flag is
   silently ignored for `PythonGun` guns: bypass `simulate` with `sim.l.go(n, save2Disk=True)`
   or save the histograms yourself (section 1).
3. **`gatherHistData` is collective — every rank calls it, in the same order.** The reduce
   result is written into an **independent clone** that is *returned* on rank `dst` (size-1
   MPI runs included; plain serial `Prompt` has nothing to reduce and returns the live view);
   the live scorer histogram keeps its rank-local content.
   Consequences: repeated gathers are idempotent (gathering for plotting and then calling
   `save_all_scorers()`, which gathers again, no longer over-counts the saved `.h5`), but the
   merged numbers exist **only in the returned clone** — code that ignores the return value
   still reads the rank-local scorer, and the C++ scalar getters stay rank-local even on the
   clone (gotcha 4).
4. **`getTotalWeight()`, `getOverflow()`, `getUnderflow()` are C++ scalars** and are not
   covered by the MPI reduce: after `gatherHistData` on rank `dst` they hold that rank's
   *local* values — on the returned clone as much as on the live scorer (measured:
   `getTotalWeight` 5000 with merged weight sum 10000). Use `getAccWeight()`,
   `getTotalHit()` or `getWeight().sum()` for merged numbers.
5. **File names embed the seed current at scorer creation** — the library default 5489 on the
   first build, not your constructor seed; fresh-process reruns overwrite, in-process rebuilds
   add files (section 3).
6. **Two error channels live in the histogram arrays — know which is which before merging.**
   `Hist1D`/`Hist2D` accumulate Σw² in the ww channel and keep entry counts in `hit`;
   `Est1D` is the opposite: its error estimate *is* the `hit` array (`getError()` returns it)
   and ww stays zero. Both merge correctly since the round-2 fix — `Hist.merge` sums the ww
   variances (errors of independent runs combine in quadrature through `getSdev()` =
   `sqrt(Σ(Σw²))`, section 2), and `Est1D` overrides the merge so its error channel also
   combines in quadrature (3+4 → 5, not 7) — but they are not interchangeable: `getSdev()`
   on an `Est1D` is always 0, use `getError()`. The note guard is `Hist1D`-only:
   `Hist1D.merge` raises `RuntimeError` on a note mismatch, but `Hist2D.merge` does not check
   notes and merges silently — keep 2D runs (e.g. PSD maps) distinguishable by file name, not
   `addNote` (section 2). That `RuntimeError` is the *only* catchable merge failure: a
   geometry mismatch aborts the interpreter, it does not raise (section 2).
7. **`ptplot -s` needs a dummy file argument**, and `-o` only accepts an existing directory
   or a file path (section 4).
8. **`PromptFileReader`'s particle-record helpers are stale.** Its module-level record map
   decodes an *older* polarisation convention (`q`→polx, `scatNum`→pdgcode, ...) that
   contradicts section 5's encoding. For particles use `PTMCPL`; `PromptFileReader`
   remains the tool for histogram blobs.
9. **MCPL particle files written by Cinema v2.0.1a1 through v2.1.0 carry internal units**
   (eV/s/mm) despite the standard-unit metadata; convert before feeding them to `MCPLGun`,
   `Cinema.analysis`, `ptplot`'s MCPL mode or any standard-unit reader (section 7). Files
   written by this release are in MCPL standard units and need no conversion. Without a
   `MultiScatCounter` the scattering-number field is the sentinel −3: single/multiple
   flags and weight accessors return zero; the ΔE==0 elastic/inelastic split still works.
10. **`McplAnalysor.getHist`/`getHistMany` results plot wrong out of the box** — `xcentre`
    holds bin *edges* (`nbins+1` values) and `plot()` prints a size mismatch, returning
    `None`. Plot from `hist.xcentre[:-1]`, `hist.weight`, `hist.error` (section 6).
11. **`CinemaXY.interpolate` needs an array** (`np.linspace(...)`); a scalar raises
    `TypeError`, as do out-of-range points. In 2D, interpolate on bin centres, not edges.
12. **`Hist.savefig` may print a harmless `AttributeError` after writing** on some 2.0.0a5
    installs — the PNG/PDF is complete (section 2).

---

## Where to go next

- [Scoring](scorers) — creating the scorers whose results are analysed here
- [Simulation lifecycle](simulation-lifecycle) — seeds, `clear()`/rebuild, MPI semantics
- [MPI at scale](mpi-scale) — independent-seed production and rank-gated I/O
- [Units](units) — conversions between eV, Å, ms and the MCPL conventions; [Materials and physics](materials-physics) — biasing behind the survival-probability bookkeeping

---

*Source files: [`Hist.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/histogram/Hist.py),
[`PromptFileReader.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/PromptFileReader.py),
[`mcpl.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/mcpl.py), [`analysis.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/analysis.py),
[`ptplotcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/ptplotcli.py). Questions: cinema-users@outlook.com.*
