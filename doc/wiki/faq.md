# Frequently asked questions

Answers to the questions that actually come up, in the form
**question → symptom (verbatim error where possible) → cause → fix**. This page
documents Cinema **2.0.0a5**; error messages and measured values were verified
live against that version. Each entry links to the deep-dive page instead of
duplicating it.

> **Legacy notice.** Everything on this page concerns the Python API
> (`Cinema.Prompt`). Defining simulations through GDML input files
> (`prompt -g file.gdml`) is legacy v1 functionality — it is not covered by
> this FAQ and must not be used for new work (see the notice on
> [Installation and environments](install)).

---

## 1. Installation and environment

### Nothing imports in a fresh shell

- **Symptom:** `ModuleNotFoundError: No module named 'Cinema'`; `cimbuild`
  prints `Error: CINEMAPATH environment variable is not set.`; loading the core
  fails with `IOError: CINEMAPATH enviroment need to be configured`.
- **Cause:** `env.sh` is environment setup *and* a lazy builder of the external
  libraries; nothing is installed system-wide, so every new shell must re-source it.
- **Fix:** `. env.sh` in every shell you work in (then re-apply the plugin-list
  fix below — re-sourcing rebuilds the broken value). Smoke test:
  `python3 -c "from Cinema.Prompt import PromptMPI; print('ok')"`.
  Details: [Installation and environments](install).

### Every simulation aborts right after `Configuring physics model: ...`

- **Symptom:** the process dies with
  `terminate called after throwing an instance of 'NCrystal::Error::BadInput'` /
  `what(): Could not find dynamic plugin shared library: .../libNCPlugin_....so;`
  (trailing `;`) — even without plugin materials, since the list loads when
  NCrystal initialises for the first volume.
- **Cause:** `install.sh` joins `ncrystal-pluginmanager` output lines carrying a
  trailing `;` into `NCRYSTAL_PLUGIN_LIST`; NCrystal then loads the literal name.
- **Fix:** after **every** `. env.sh` (re-sourcing rebuilds the broken value):
  `export NCRYSTAL_PLUGIN_LIST="$(printf '%s' "$NCRYSTAL_PLUGIN_LIST" | tr -d ';')"`
  — or export the absolute plugin `.so` paths by hand ([Installation and environments](install)).

### A newly installed plugin material is not found

- **Symptom:** NCrystal rejects a material that needs the freshly installed
  plugin (e.g. the `@CUSTOM_...` section it provides), although
  `ncrystal-pluginmanager --test <Plugin>` succeeds inside the conda env.
- **Cause:** a non-empty `NCRYSTAL_PLUGIN_LIST` **replaces** (does not extend)
  NCrystal's automatic plugin discovery — only the libraries listed in it are
  ever loaded.
- **Fix:** re-source `env.sh` after installing a plugin (the list is rebuilt
  from the pluginmanager of the conda env owning NCrystal), or add the new
  plugin's `.so` to the exported list by hand — keeping **all** plugins you
  use. See [Materials and physics](materials-physics), [SANS tutorial](tutorial-sans).

### CMake suddenly cannot find HDF5 or libxml2

- **Symptom:** configure errors about HDF5/libxml2 after moving, renaming or
  recreating the conda env — although the same checkout built fine before.
- **Cause:** `env.sh` caches its detection results (`PROMPT_LIBXML2_LIB`,
  `PROMPT_HDF5_*`) in `<cinema-checkout>/cinemabin/envCache.txt` and trusts
  that file blindly on the next source.
- **Fix:** delete `cinemabin/envCache.txt` and re-source `env.sh`.
  See [Installation and environments](install).

### A rebuild silently loses GIDI/CATIMA support

- **Symptom:** GIDI-based materials stop working after an ordinary rebuild,
  and `GidiSetting().isCompiled` is `False`.
- **Cause:** the first configure — the one `env.sh` runs for you — defaults
  `ENABLE_GIDI`/`ENABLE_CATIMA` to ON, but `cimbuild` passes them as OFF
  unless you ask. No warning is printed.
- **Fix:** rebuild with `cimbuild -r --enablegidi --enablecatima`, then check
  `GidiSetting().isCompiled` (import it as
  `from Cinema.Prompt.GidiSetting import GidiSetting` — the module path, not
  `from Cinema.Prompt import ...`). Details:
  [Installation and environments](install).

### GIDI material setup dies with "Cannot read from HDF5 file"

- **Symptom:** building a GIDI-enabled world aborts with
  `terminate called after throwing an instance of 'GIDI::Exception'` /
  `what(): parseValuesOfDoubles: Cannot read from HDF5 file as GIDI+ was
  compiled without HDF5 support.`
- **Cause:** the gidiplus static library was compiled without its HDF5 reader.
  This happens when `make install4prompt` is invoked by hand without
  `HDF5_PATH` (the GNDS nuclear-data files under `external/ptdata/` are
  HDF5-backed, so without it every parse fails at runtime, not at link time).
- **Fix:** rebuild gidiplus with the HDF5 variables, exactly as `install.sh`
  does: `make realclean && make install4prompt HDF5_PATH=$PROMPT_HDF5_PATH
  HDF5_LIB=$PROMPT_HDF5_LIB HDF5_INCLUDE=$PROMPT_HDF5_HEADER` (plus
  `CXXFLAGS=-fPIC`), then rebuild Cinema with `cimbuild -r --enablegidi`.
  The HDF5 symbols themselves are resolved from Cinema's own link line.
  See [Installation and environments](install).

### conda wants to downgrade libxml2 (or refuses to)

- **Symptom:** while sourcing `env.sh`, conda resolves a `libxml2=2.9.3`
  install that conflicts with or downgrades other packages in the env.
- **Cause:** KDSource is pinned to libxml2 **2.9.3**; `install.sh` installs
  that exact version into an active conda env, or falls back to a cached
  source build if the resolver balks.
- **Fix:** accept the pin (or let the fallback source build run). Do not
  "upgrade away" the pin afterwards — KDSource may fail to link or load.
  See [Installation and environments](install).

### The first `. env.sh` hangs or fails on downloads

- **Symptom:** the first run sits for a long time cloning or downloading, or
  fails with a network error during the external-build step.
- **Cause:** the first run clones and compiles MCPL, libxml2, xerces-c,
  VecGeom, KDSource and gidiplus into `<cinema-checkout>/external/` — that
  needs network access to the project hosting plus fallback download sites
  for hdf5 and libxml2.
- **Fix:** run it once on a network-connected machine; later sources skip
  everything already built. See [Installation and environments](install).

### `PromptMPI` raises `ImportError` about mpi4py (or mpi4py failed to install)

- **Symptom:** `import Cinema.Prompt` and plain serial `Prompt` runs work, but
  constructing `PromptMPI` raises
  `ImportError: PromptMPI requires the mpi4py package ...`.
- **Cause:** `mpi4py` is an optional dependency: `promptCore.py` guards its
  import and only the `PromptMPI` subclass needs it, so serial runs have no
  mpi4py dependency. The `requirement` file lists mpi4py, but in an env where
  that one line failed to build (it needs MPI headers) the package is missing.
- **Fix:** once per venv: `cinemavirenv/bin/python3 -m pip install mpi4py`
  (needs MPI headers — the apt route's `libopenmpi-dev` or conda
  `openmpi`/`mpi4py` provide them), or stay with the serial `Prompt` class.
  See [Installation and environments](install).

---

## 2. Runtime surprises

### Rebuilding a world in the same process raises `World exist already`

- **Symptom:** a second `sim.makeWorld()` — or any second `setWorld` — raises
  `RuntimeError: World exist already: only one world can be set per process ...`.
- **Cause:** the world and its seed are one-shot per process (the `Launcher` is a
  singleton), and the guard is shared by every `Prompt` instance in the process —
  constructing a second `Simulation()` trips it on its first `setWorld` too.
- **Fix:** call `sim.clear()` before building again: it resets the C++
  resource manager, the world flag and the scorer registry, and the next
  `setWorld` re-applies the seed. For genuinely separate worlds, use separate
  processes (one script or `mpirun` rank each). See
  [The Simulation class](simulation-lifecycle).

### My "empty" world is full of hydrogen

- **Symptom:** a `Volume` created without `matCfg` configures the physics
  `freegas::H1/1e-26kgm3/H_is_1_H1`.
- **Cause:** `matCfg=None` does **not** mean vacuum — the default is a very
  dilute free-gas hydrogen, conventionally used as "vacuum".
- **Fix:** for a true void, set `void.ncmat` explicitly
  (`Volume("world", Box(...), "void.ncmat")`); otherwise name the material.
  The dilute gas is usually negligible, but absorption/scattering tallies and
  normalisation sums see it. See [Geometry](geometry) and
  [Materials and physics](materials-physics).

### A single-crystal config aborts: `Must set all or none of mos, dir1 and dir2 parameters`

- **Symptom:** uncatchable abort while the volume physics is configured, e.g.
  for `'Ge_sg227.ncmat;mos=0.0267deg'`.
- **Cause:** an oriented crystal is defined by the mosaic spread **plus two**
  crystal-plane-to-lab-direction mappings; NCrystal rejects partial specs.
- **Fix:** give all of them, as in
  `nccfg = 'Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'`:
  with `dir1`/`dir2` the cross sections depend on flight direction; without
  them the model is an unoriented powder. Canonical example:
  [Your first simulation](first-simulation); details:
  [Materials and physics](materials-physics).

### Do I have to wrap an NCrystal string in `Material()`?

- **Symptom:** mistakes inside an NCrystal material string — a missing or
  misspelled `.ncmat` file, an unknown key, an incomplete crystal spec — raise
  a normal, catchable Python `ValueError` ("NCrystal rejected the material
  config '...': ... This pre-check avoids an uncatchable process abort inside
  NCrystal."), whether the string is raw or wrapped in `Material()`.
- **Cause:** configs are pre-checked in Python before they ever reach the C++
  core — the data files are looked up (`_validateNccfgFiles`) and the content
  is round-tripped through the real NCrystal parser — precisely because a C++
  exception crossing the ctypes boundary would terminate the process.
  Wrapping in `Material()` adds no validation of its own. A raw string that
  carries parameters (contains `;` but no `physics=`) is accepted but emits a
  `RuntimeWarning` and is auto-wrapped into the canonical
  `physics=ncrystal;nccfg='...'` form, because only that form can carry the
  bias keys.
- **Fix:** wrap in `Material(...)` when you want bias factors
  (`setBiasScat`/`setBiasAbsp`/`setAbsorpInWeight` — a raw string cannot carry
  them), or write the explicit `physics=ncrystal;nccfg='...'` form when
  writing bias keys by hand. Typos now fail fast with a `ValueError` instead
  of killing the run. See [Materials and physics](materials-physics).

### My GIDI settings are silently ignored

- **Symptom:** `GidiSetting().setEnableGidi(True)`, threshold, PoPs/map paths —
  all set, yet the run transports plain NCrystal physics.
- **Cause:** the GIDI values are read once, when a volume's physics is
  configured; anything set **after** the first `Volume`/`Material` creation
  has no effect.
- **Fix:** configure `GidiSetting` before building any volume or material, and
  confirm the library was built with GIDI (`GidiSetting().isCompiled` — see the
  GIDI/CATIMA entry in section 1). Prefer the checked front-end API:
  `GidiSetting().enable()` warns when GIDI is not compiled in and refuses with
  `ValueError` when the data files are missing, instead of failing this quietly.
  See [Materials and physics](materials-physics).

### gidi.enable() raises ValueError about missing data files

- **Symptom:** `GidiSetting().enable()` refuses with a `ValueError` naming a
  `pops.xml` or `all.map` path that "is missing or unreadable".
- **Cause:** compiled-in is not the same as runtime-usable — the GIDI data
  package (pops database + map + ENDF files) is optional and not installed (or
  the configured paths point elsewhere). The refusal is deliberate: an enable
  that cannot be honoured must never degrade silently into "looks like GIDI
  but is not".
- **Fix:** install the GIDI data under the cinema data path, or point at an
  existing installation with `GidiSetting().setGidiPops(...)` /
  `.setGidiMap(...)` before `enable()`. Probe a build without side effects
  with `GidiSetting().available()`, e.g. `if gidi.available(): gidi.enable()`.
  Users who never enable GIDI are unaffected either way — the default path
  never reads the data. See [Materials and physics](materials-physics).

### A scorer returns another scorer's numbers

- **Symptom:** `sim.gatherHistData('tof')` returns data that cannot belong to
  `'tof'` — and no warning is printed anywhere.
- **Cause:** duplicate scorer names alias silently. Two scorers registered
  under the same name leave a single entry in `Volume.scorer_dict`, and lookups
  by name return one of them.
- **Fix:** keep scorer names unique (the rename helper `scorerNameConfig` is
  dead code — do not rely on it). After `makeWorld()`, check `sim.scorer`: it
  should list every scorer exactly once. See [Scoring](scorers).

### The `prompt` CLI fails and I cannot see where

- **Symptom:** one line `PromptCLI Error: <message>` plus the help text, then
  exit code 1.
- **Cause:** by default the CLI swallows the traceback.
- **Fix:** re-run with `--debug` — Python-level exceptions then print a full
  traceback (verified in 2.0.0a5). A C++ abort (SIGABRT, e.g. from a bad gun
  or material config) can never produce a Python traceback; debug such cases
  by running the script directly with `python3 myscript.py`.
  See [The command line](cli).

### A list-typed CLI parameter aborts the process

- **Symptom:** `prompt -g myscript.py --gun MyGun ...` dies with an
  uncatchable `Prompt::Error::BadInput` from the gun factory — also under
  `--debug`, because it is a C++ abort, not a Python exception.
- **Cause:** a constructor parameter annotated `src_whz: list = None` degrades
  to `Optional[list]` (a missing annotation degrades further); the type no
  longer compares equal to `list`, so the raw string goes through unconverted.
- **Fix:** annotate list parameters as plain `list` with a non-`None` default,
  e.g. `def __init__(self, src_whz: list = [10, 10, -20], ...):` — conventions
  in [Your first simulation](first-simulation), [The command line](cli), [Guns](guns).

---

## 3. Results puzzles

### Output files are named `..._seed5489...` and my rerun overwrote them

- **Symptom:** `Prompt.simulate(..., save2Disk=True)` writes
  `ScorerTOF_TOF_seed5489.mcpl.gz` no matter which seed you passed, and a
  second run with a different `-s` or constructor seed replaces the first
  file. Under MPI the same dump comes from rank 0 only.
- **Cause:** the file name embeds the C++ RNG seed
  current when the **scorer is created** — inside `makeWorld`, before
  `setWorld` applies your constructor seed. On the first build in a process
  this is the library default `5489`, so fresh-process runs collide
  (measured 2026-10: seeds 4096 and 777, 2000 events each — same name).
- **Fix:** one directory per seed. Only `clear()`-and-rebuild cycles within
  one process produce distinct names; the `.h5` files of
  `save_all_scorers()` have no seed component at all. See
  [Analysing results](results-analysis), [Running at scale](mpi-scale).

### MPI: wrong or double-counted histograms

- **Symptom:** on a rank other than 0 the histogram returned by
  `gatherHistData` holds that rank's local counts, not the total (measured on
  two ranks, seed 4096, 20000 events: rank 1 got 139, rank 0 the merged 313);
  calling `gatherHistData` and then `save_all_scorers()` inflates totals
  (same run: the `.h5` came out with 452 absorbed instead of 313).
- **Cause:** `gatherHistData` is collective — every rank must call it, in the
  same order — and merges into rank `dst` (default 0). Off rank `dst` the
  returned object still holds that rank's local, unmerged data — fine for a
  quick look at one rank, wrong for totals (it is the unused receive buffers
  that stay unfilled); on rank `dst`, the reduce *replaces* the arrays with
  merged sums, so a second gather re-sums them.
- **Fix:** gather once per scorer, plot/save only under `if sim.rank == 0:`,
  and take merged scalars from `getAccWeight()`/`getWeight().sum()`.
  See [Running at scale](mpi-scale), [Analysing results](results-analysis).

### Numbers read from an MCPL file do not match my scorer ranges

- **Symptom:** e.g. a TOF histogram binned over 0..40e-3 while the MCPL `time`
  field reads up to 40; energies off by a factor 1e6.
- **Cause:** the MCPL standard fixes the particle fields to position **cm**,
  kinetic energy **MeV**, time **ms**, and Cinema honours that on both
  sides — `MCPLGun` rescales when sampling, the analysers treat on-disk
  energies as MeV, and the writer (`MCPLOutHelper`, C++ `KillerMCPL`)
  converts on output. The exception is **files written by Cinema 2.1.0 or
  earlier**, whose particle records carry Prompt's internal mm / eV / s,
  unconverted. The `<name>_seed<seed>.mcpl.gz` dumps of `save2Disk=True` are
  a different container: they hold **no particle records at all**
  (`nparticles` is 0, measured on a 2.0.0a5 dump) — only histogram header
  blobs (`edge`, `content`, ...), plain arrays in internal units, with no
  time/ekin/position fields to convert or mis-convert.
- **Fix:** current files need no conversion anywhere — `MCPL_Analyzer_1D/2D`,
  `MCPLGun` and the `mcpl` tools read them correctly as written. For the old
  internal-unit files, convert at the boundary (the recipe is in [Units and
  conversions](units), section 2.1) or read them as mm/eV/s with `PTMCPL` or
  the `mcpl` package. Read the seed dumps only as histograms — with
  `PromptFileReader`, `McplAnalysor`, or the generated `_view.py` script.

### Are these error bars Poisson?

- **Symptom:** error bars that do not scale like 1/sqrt(N), or an `sdev` that
  comes out too small after merging independent runs.
- **Cause:** `getSdev()` returns `sqrt(Σw²)` per bin — the σ estimate of the
  bin's weighted sum for independent events, not a Poisson error. Estimator
  classes instead use the factor-10 heuristic `w/sqrt(hit/10)`, and the
  Python `Hist.merge` combines Σw² in quadrature, which *underestimates* the
  variance of merged independent runs (the MPI reduce sums Σw² correctly).
- **Fix:** for multi-run statistics use the MPI reduce,
  `McplAnalysor.getHistMany()` or `ErrorPropagator`.
  The full picture: [Analysing results](results-analysis).

### A log-binned scorer rejects its range: `min ... must be positive for logarithmic binning`

- **Symptom:** constructing a scorer raises `ValueError`, e.g. with
  `ESpectrumHelper('e', 0., 1., 100)`.
- **Cause:** several scorers default to logarithmic binning
  (`ESpectrumHelper`, `WlSpectrumHelper`, `VolFluenceHelper`, `DirectSqHelper`),
  and log edges require strictly `0 < xmin < xmax` — the constructor validates
  this up front instead of failing later inside the C++ histogram.
- **Fix:** pass strictly positive edges, or request linear binning
  (`log=False`; `linear=True` still works as a deprecated alias). See
  [Scoring](scorers).

### Can I make a 2D histogram with logarithmic axes?

- **Symptom:** `Hist2D(1e-2, 1e2, ...)` comes out with linear bins.
- **Cause:** `Hist2D` edges are always built with `numpy.linspace` — the class
  has no log mode. (The `log=True` colour scale of `.plot()` is a different
  thing: it only affects the rendering.)
- **Fix:** bin a transformed variable yourself (fill with `log10(x)`), or bin
  linearly in the run and rebin to a log axis in post-processing. Note that
  `DirectSqwHelper(log=True)` warns that log-Q binning is not supported by the
  C++ scorer yet and keeps the axis linear.
  See [Analysing results](results-analysis).

---

## 4. Visualization

### `ImportError: pyvista is required to visualize.` on import

- **Symptom:** even `import Cinema.Prompt` fails — in a batch script that
  never calls `show()`.
- **Cause:** the import chain (`promptCore` → `geo` → `Mesh`) imports pyvista
  unconditionally; only the viewer *class* itself is loaded lazily inside
  `showWorld`.
- **Fix:** make pyvista (+VTK) importable: conda route `pyvista` and
  `vtk=*=qt*`; on the apt route additionally `libgl1` for off-screen GL.
  See [Installation and environments](install) and [Visualization](visualization).

### Boolean solids mesh slowly / `geoClip` kills the process

- **Symptom:** volumes built with `SolidUnion`/`SolidIntersection`/
  `SolidSubtraction` fall back to a slow point-cloud reconstruction with a
  warning; `show(..., geoClip=True)` prints
  `tetgen is required. Use 'pip install tetgen' to install.` and the process
  exits.
- **Cause:** meshing boolean solids needs `vtkbool`; the interactive clipping
  widget needs `tetgen`. The tetgen failure path calls `sys.exit` and is not
  caught by the clip fallback handler.
- **Fix:** `pip install vtkbool tetgen` into the environment that runs the
  script, or avoid `geoClip`. See [Visualization](visualization).

### A batch job hangs — or silently renders headless — at `show()`

- **Symptom:** an MPI job stalls; or stderr shows a warning that `DISPLAY` is
  set but unreachable within 2.0 s, "forcing headless rendering ...
  interactive show() is disabled", and `show()` returns without a window.
- **Cause:** `show()` opens an interactive pyvista window — rank 0 renders
  while all ranks wait at a barrier. On a node without a usable display it
  degrades to an off-screen render.
- **Fix:** never call `show()` in batch jobs or CI. For scripted screenshots
  and geometry inspection use the `Mesh` iterator, which builds meshes without
  a window. See [Visualization](visualization).

### My beamline looks like a toothpick

- **Symptom:** a metre-scale instrument with mm-scale detectors renders
  unreadable — one fat box and a needle.
- **Cause:** the viewer uses one scale for all axes; long, thin geometries are
  the classic victim.
- **Fix:** `show(gun, n, xscale=..., yscale=..., zscale=...)` — the axis
  scaling keywords (like `mergeMesh`, `byMat`, `addLegend`, `geoClip`) exist on
  both the serial and the MPI variant of `show`. Also useful for dense scenes:
  `geoClip`, and a direct `Visualiser` with `blacklist`/`nSegments`.
  See [Visualization](visualization).

---

## 5. Where to ask

Questions, problems and plugin requests: **cinema-users@outlook.com**.
The source lives at <https://code.ihep.ac.cn/cinema-developers/cinema>;
installation recipes on [Installation and environments](install), and the
worked examples on [Your first simulation](first-simulation) and the
[SANS tutorial](tutorial-sans) solve most first-week issues on their own.
