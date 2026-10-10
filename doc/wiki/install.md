# Installation and environments

This page covers the ways to install Cinema/Prompt, what the `env.sh` environment
script actually does, the NCrystal environment policy, and the known build and
environment gotchas. It documents Cinema **2.0.0a5** (`Cinema.__version__`, which is
authoritative for packages; the `Version` file in the repo says `v2.0.0`).

This wiki uses the Python API (`Cinema.Prompt`, `Simulation`) as the supported way to
define simulations everywhere. See [First simulation](first-simulation) for the
tutorial and [Home](home) for the project overview.

## 1. Which route should I choose?

| Route | How | Choose this if | Effort | Notes |
|---|---|---|---|---|
| **Conda package** | `conda install csns::cinema-prompt` | You want to run simulations, not develop Cinema | None (no build) | Linux, recommended quickstart; pre-built on x86-64 and arm64 by CI from the separate `cinema-prompt-feedstock` repo |
| **Source build, apt prerequisites** | `. env.sh && cimbuild -r` | You develop Cinema on Ubuntu and do not use conda | Medium; the first `. env.sh` downloads and compiles all external libraries (needs network) | The README path; viz needs the `libgl1` apt package |
| **Source build, conda prerequisites** | `conda create -n pt ...` then `. env.sh` | You develop Cinema and want the unified NCrystal environment (`pt`) | Medium | The `pt` env is also where NCrystal and its C++ plugins live (see section 6) |
| **Docker image `cinema:0.1`** | `docker/build.sh` | Only legacy QE/Tak-side workflows | Legacy, stale | Not the recommended path (section 11) |

For beamline-side usage the conda package is enough. Development and running the
test suite need a source build. Plugins are easiest with a source build, but a
conda install can also load plugins pip-installed into the same conda environment
(section 6).

## 2. Conda quickstart

On Linux:

```bash
conda install csns::cinema-prompt
```

This installs the `prompt` and `ptplot` console commands and the `Cinema.Prompt`
Python package with its bundled core library — no build step. Smoke test:

```bash
prompt --help                                                  # legacy CLI entry point exists
python -c "from Cinema.Prompt import PromptMPI; print('ok')"   # loads the core library
```

Expected output of the second command is a single `ok`.

> **Legacy notice — GDML input.** The `prompt` command dates from the v1 era where
> simulations were defined by GDML files (`prompt -g file.gdml`). GDML input is
> **legacy**: it still works and old examples depend on it, but it is not the
> recommended way to define new simulations. The supported path is the Python API
> (`Cinema.Prompt`), see [First simulation](first-simulation). The same `prompt`
> command also launches Python-API scripts (`prompt -g yourscript.py`); the CLI is
> described on the [CLI](cli) page.

The project metadata name is `neutron-cinema` (`pyproject.toml`); `requires-python`
is `>=3.8`, and in practice Python **3.10** is what the recipes and the
development environment use.

## 3. Source build with apt prerequisites (Ubuntu)

This is the README path:

```bash
sudo apt install g++ cmake python3-dev python3-pip python3-venv \
                 libxml2-dev libhdf5-dev libfftw3-dev libopenmpi-dev libgl1
git clone https://code.ihep.ac.cn/cinema-developers/cinema.git
cd cinema
. env.sh          # creates cinemavirenv, pip-installs the python requirements,
                  # downloads and builds all external libraries (first run: long, needs network)
cimbuild -r       # cmake Release build into <cinema-checkout>/cinemabin
```

Notes:

- `libgl1` is needed for off-screen VTK rendering (pyvista visualisation). Without it,
  visualisation-dependent examples fail at import. On the conda route the equivalent
  comes from the `pyvista`/`vtk=*=qt*` packages instead.
- The **first** `. env.sh` run clones and compiles MCPL, xerces-c, VecGeom, KDSource
  and gidiplus into `<cinema-checkout>/external/` (hdf5 only if no usable one is
  found).
  This is long and needs network access to the project hosting (`code.ihep.ac.cn`)
  plus fallback download sites for hdf5 and libxml2.
- Subsequent `. env.sh` runs skip everything that is already built.

`cimbuild` (a wrapper script placed on `PATH` by `env.sh`) is the daily build driver:

| Flag | Meaning |
|---|---|
| `-r` | Release build (`-DCMAKE_BUILD_TYPE=Release`) |
| `-d` | Debug build (`-g -O0`); mutually exclusive with `-r` |
| `-c` | `make clean` before building |
| `-t` | Run the tests: `ctest -j<N/2>` (C++ tests plus the registered `python-tests`, which run `pytest --forked` over `src/pythontests/`) followed by a pytest tree summary (`scripts/pytest_tree.py`) |
| `--enablegidi` | Pass `-DENABLE_GIDI=ON` (see the gotcha in section 7) |
| `--enablecatima` | Pass `-DENABLE_CATIMA=ON` (see the gotcha in section 7) |
| `--debugpts` | Pass `-DDEBUG_PTS=ON` (extra debug printout) |

`cimbuild` requires `CINEMAPATH` to be set — i.e. `env.sh` must have been sourced in
that shell — and always builds in `<cinema-checkout>/cinemabin`.

## 4. Source build with conda prerequisites

Instead of apt, let conda provide the compiler and libraries:

```bash
conda create -n pt python=3.10
conda activate pt
conda install cxx-compiler=1.10 cmake make=4.3 fftw unzip openmpi libxml2 \
              xerces-c=3.2.4 mpi4py hdf5=1.12 matplotlib pyvista vtkbool vtk=*=qt*
. env.sh
```

This conda env (typically named `pt`) is not just a build prerequisite provider: it is
**also the environment that owns NCrystal** and its C++ plugins (section 6). If you
plan to use plugin materials (e.g. the SasCSNS small-angle-scattering plugin), use
this route.

The C++ build finds NCrystal through `ncrystal-config --show cmakedir` and requires
**NCrystal >= 4.0.0**, so keep the `pt` env active (or at least its `bin` on `PATH`)
when the CMake configure step runs.

## 5. What `. env.sh` actually does

`env.sh` parses a few flags; the two that matter here are `-d` (docker mode) and
`-o` (also install OpenMC alongside — an extra not needed for anything in this
wiki) — and then it sources `install.sh` from the repo root. Sourcing it has the following effects **in every shell**:

1. **Prunes** entries belonging to a previously sourced Cinema environment from
   `PATH`, `LD_LIBRARY_PATH`, `PYTHONPATH`, `NCRYSTAL_PLUGIN_LIST` and
   `NCRYSTAL_DATA_PATH`, so re-sourcing does not grow the variables without bound.
2. Exports **`CINEMAPATH`** (the repo root). `cimbuild` refuses to run without it.
3. **Python environment**: activates `<cinema-checkout>/cinemavirenv` if it exists,
   otherwise creates that venv and runs `pip install -r <cinema-checkout>/requirement`
   (the answer prompt is hard-wired to yes). The venv holds only the light Python
   dependencies (mcpl, scipy, h5py, gvar, psutil, tqdm); **Cinema itself is
   not pip-installed there** — it is found via `PYTHONPATH`. Note that the
   `requirement` file has its NCrystal and visualisation lines commented out on
   purpose (section 6), and its `mpi4py` line is commented out too. That omission
   matters: `promptCore.py` imports mpi4py at module level, so a venv created this
   way cannot import `Cinema.Prompt` at all until mpi4py is installed (`pip install
   mpi4py` — the apt route's `libopenmpi-dev` prerequisite supplies what it needs —
   or take mpi4py from conda). The existing `cinemavirenv` on the development
   machine this wiki was written on carries mpi4py 4.1.1.
4. **Builds missing C++ externals into `<cinema-checkout>/external/`** (skipped when
   already present): MCPL, libxml2 **2.9.3** (pinned for KDSource), KDSource
   (default branch, currently `master`), xerces-c **v3.2.3** (shared libs, GDML parser dependency), VecGeom (branch
   `cinema` of the project's VecGeom fork, static library, built with GDML +
   navigation-index + built-in VecCore), hdf5 (**1.12.2** preferred), gidiplus
   (branch `pt`, `make install4prompt`), the SSSP pseudopotentials (BzScope/DFT side
   only — BzScope was formerly named PiXiu; the in-repo package directory is still
   `Cinema/PiXiu`) and the `ptgeo` git submodule.
5. **Exports the daily-use environment**:
   - `PYTHONPATH` = `<cinema-checkout>/src/python`, its `ptgeo/python` subtree, and
     `<cinema-checkout>` itself;
   - `LD_LIBRARY_PATH` += `<cinema-checkout>/cinemabin` (where `libprompt_core.so`
     is built);
   - `PATH` += the ptgeo examples dir, `cinemabin/bin`, and `<cinema-checkout>/scripts`
     (this is what puts `prompt`, `ptplot` and `cimbuild` on your command line);
   - `NCRYSTAL_DATA_PATH` = `<cinema-checkout>/ncmat` (the NCMAT files shipped in the
     repo; append your own directories colon-separated if needed);
   - `NCRYSTAL_PLUGIN_LIST`, resolved from the `ncrystal-pluginmanager` command of the
     conda env that owns the plugins (section 6);
   - `PROMPT_LIBXML2_LIB` / `PROMPT_HDF5_*` detection results.
6. **Caches** the libxml2/hdf5 detection results in
   `<cinema-checkout>/cinemabin/envCache.txt` and re-reads that file on the next
   source to skip re-detection. If the conda env is moved or rebuilt, the cache goes
   stale — delete the file (section 10).

**Re-source `env.sh` in every new shell.** It is both environment setup *and* a lazy
builder of `external/`; nothing is installed system-wide. In a fresh shell without it,
`import Cinema` fails and `cimbuild` exits with `CINEMAPATH is not set`.

## 6. The NCrystal-on-conda rule

NCrystal provides the neutron scattering physics and the NCMAT material format; see
[Materials and physics](materials-physics). The environment policy (introduced when
the build was unified on conda) is:

- **Never pip-install NCrystal or NCrystal C++ plugins into Cinema's own Python
  environment.** Two NCrystal sources loaded into one process break in subtle ways.
  The `requirement` file documents this inline; its NCrystal lines are commented out
  on purpose — do not "restore" them.
- NCrystal (Python + C++ library; **4.2.12** and CMake requirement `>= 4.0.0` on the
  development machine this wiki was written on) lives in the **conda env**, e.g. `pt`.
- NCrystal C++ plugins are pip packages installed **into that same conda env**:

  ```bash
  conda activate pt
  pip install ncplugin-sascsns/                                                  # local plugin checkout (SasCSNS SANS plugin)
  pip install git+https://code.ihep.ac.cn/cinema-developers/ncplugin-bzscope     # BzScope plugin
  pip install git+https://github.com/highness-eu/ncplugin-SANSND.git             # SANSND plugin
  ncrystal-pluginmanager --test SasCSNS                                          # verify (from the activated conda env)
  ```

- Plugin discovery: NCrystal finds plugins via the `ncrystal-pluginmanager` command of
  the Python env they were installed into. Because Cinema's `cinemavirenv` deliberately
  has no NCrystal, that command is usually **not** on `PATH` when only `env.sh` is
  sourced. `install.sh` therefore resolves the plugin list itself and exports
  **`NCRYSTAL_PLUGIN_LIST`** (the plugin `.so` paths, colon-separated, with the
  `:DATA:` rows filtered out). The script falls back to a hard-coded
  developer-machine path for the pluginmanager when the command is not found — on
  other hosts, have the conda env active when sourcing `env.sh` (so the command is on
  `PATH`), or edit that fallback in `install.sh`.
- **A non-empty `NCRYSTAL_PLUGIN_LIST` replaces (does not extend) automatic plugin
  discovery.** It must therefore contain *all* plugin libraries you want to use.
- **Known bug — trailing semicolon.** `install.sh` builds the list by joining the
  pluginmanager output lines, but that output carries a trailing `;` on each library
  entry (verified: the exported value ends in `...so;`). NCrystal then tries to
  `dlopen` the literal filename ending in `;`, which fails with a `BadInput` error and
  aborts the process the moment a volume's material physics is configured — i.e. every
  simulation using an NCrystal material dies. Workaround, applied **after each
  `. env.sh`** (re-sourcing rebuilds the broken value):

  ```bash
  export NCRYSTAL_PLUGIN_LIST="$(printf '%s' "$NCRYSTAL_PLUGIN_LIST" | tr -d ';')"
  ```

  Alternatively export the list by hand: the absolute paths of all plugin `.so` files,
  colon-separated, without semicolons.

## 7. `cimbuild` feature-flag gotcha

The CMake options default to **ON** (`option(ENABLE_GIDI ... ON)` and
`option(ENABLE_CATIMA ... ON)` in `src/cxx/CMakeLists.txt`), and the first configure —
the one `env.sh` runs for you — passes no `-D` flags, so a fresh build has GIDI
(ENDF-based transport) and CATIMA enabled.

However, `cimbuild` always passes `-DENABLE_GIDI=OFF -DENABLE_CATIMA=OFF
-DDEBUG_PTS=OFF` unless you give the corresponding flags. So a plain

```bash
cimbuild -r
```

after a fresh `env.sh` build **silently reconfigures and rebuilds without GIDI and
CATIMA**. To keep feature parity with the initial build, use:

```bash
cimbuild -r --enablegidi --enablecatima
```

Python code can detect whether GIDI was compiled in via `GidiSetting().isCompiled`
(import it as `from Cinema.Prompt.GidiSetting import GidiSetting`, as in
[Materials and physics](materials-physics) — plain `from Cinema.Prompt import
GidiSetting` yields the module, not the class).
GIDI-dependent material models require the flag to have been ON for the
`libprompt_core.so` you actually run. Mixed rebuilds produce libraries with different
capabilities from the same checkout.

## 8. Verify your installation

```bash
# 1. Imports and version (after . env.sh, or in the conda env for a conda install)
python3 - <<'EOF'
import Cinema                                   # expected: 2.0.0a5
print(Cinema.__version__, Cinema.__file__)
from Cinema.Prompt import PromptMPI             # loads libprompt_core.so
print('Prompt core OK')
EOF
```

For a source install, `Cinema.__file__` points into
`<cinema-checkout>/src/python/Cinema`; for a conda install, into the env's
`site-packages`.

```bash
# 2. Legacy CLI entry point exists (GDML is legacy; see notice in section 2)
prompt --help

# 3. Full Python-API smoke test: Ge single-crystal slab + TOF scorer.
#    Source checkouts only — conda users: skip this step (the step-1 import
#    already exercised the core), or fetch doc/example_basic.py from the
#    repository link at the bottom of this page and run it.
#    Opens an interactive 3D viewer (needs a display and the viz dependencies);
#    comment out the sim.show(gun,100) line and uncomment the sim.simulate(...)
#    line inside for a non-interactive check.
python3 doc/example_basic.py
```

`doc/example_basic.py` is the reference Python-API script. On the development machine
this wiki was written on, its transport step costs about **0.4 s per 1e5 events**
(roughly 3 s process total including initialisation) — timings are for that example,
that event count, on that machine. The example is walked through line by line in
[First simulation](first-simulation).

```bash
# 4. NCrystal plugin (conda env that owns the plugins)
conda activate pt
ncrystal-pluginmanager --test SasCSNS           # expect: "All ok"

# 5. Source installs: C++ ctest suite + python pytest tree
cimbuild -t
```

Note that a subset of the Python tests is excluded by `src/pythontests/conftest.py`
and some golden-value tests are known-failing; see
[Running the test suite](#9-running-the-test-suite) before treating a red suite as a
broken install.

## 9. Running the test suite

`cimbuild -t` (after a build) runs everything, in two halves:

1. **C++ tests** — `ctest -j<n/2>` in `cinemabin/`: doctest-based unit tests
   (`src/cxxtests/`) plus one ctest entry per Python test file.
2. **Python tests** — `scripts/pytest_tree.py`: runs
   `pytest src/pythontests --forked` and prints the result as a tree.

Three prerequisites, or the suites fail for environment reasons rather than code
reasons:

- **Source `env.sh` in *this* shell first.** Without it, the Python tests die with
  `ModuleNotFoundError: No module named 'Cinema'` and some C++ tests abort on
  missing paths.
- **`pytest` must be in `cinemavirenv`.** It is not in the `requirement` file yet;
  install it once per checkout:
  `cinemavirenv/bin/python3 -m pip install pytest pytest-forked`.
- **Normalise `NCRYSTAL_PLUGIN_LIST`** (section 6 workaround) — the trailing
  semicolon makes every NCrystal-based test SIGABRT the process.

### Direct invocations (faster than a full `cimbuild -t`)

```bash
# Python suite only — the fast, authoritative check (~10 s):
cd cinemabin && ../cinemavirenv/bin/python3 -m pytest ../src/pythontests --forked --tb=line -q

# C++ suite only:
cd cinemabin && ctest -j$(($(nproc)/2))

# One C++ test:            ctest -R test_geonav -V
# One Python test:         pytest ../src/pythontests/test_prompt_hist.py -q
# The tree view cimbuild:  ../scripts/pytest_tree.py
```

### What a green suite looks like (2.0.0a5, measured 2026-10)

- **pytest: 44 passed, 9 skipped, 0 failed.** The 9 skips are environmental, not
  bugs: numba and `makeChopper` not installed, tests needing external gdml/mcpl
  data files, a broken `ParticleParameter` API, and three expected-value
  mismatches (`mirror`, `pythongun`, `scorerCfg`). The geometry solids
  expectations (Box/Cone/Orb/Tet/ellipsoid/...) all pass on the current VecGeom
  and are no longer excluded.
- **ctest: 68 entries — 64 pass.** The 4 permanent reds are the *same* files
  conftest.py excludes (`python-test_cinema_array_ops`, `python-test_prompt_chopper`,
  `python-test_tak_parfft`, `python-test_tak_trj`): ctest runs each file as a
  bare script and does not see conftest exclusions. Run ctest with
  `-E "^(python-test_cinema_array_ops|python-test_prompt_chopper|python-test_tak_parfft|python-test_tak_trj)$"`
  to match the pytest verdict.

Many Python tests are **golden-anchor** regressions: exact per-bin values at a
fixed seed (e.g. the expected wavelength spectrum in the solids tests). A red
anchor usually means transport behaviour genuinely changed — treat it as a
physics review item, not noise.

### Automatic tests on every push

The repo ships a pre-push hook that runs the suite (ctest with the 4 known-red
entries excluded, plus the full pytest run; it sources `env.sh` and normalises
`NCRYSTAL_PLUGIN_LIST` itself, so it works from any shell). Total cost: roughly
20-30 s.

```bash
git config core.hooksPath scripts/git-hooks   # activate, once per clone
git push                                       # tests run first; failure aborts the push
git push --no-verify                           # bypass for this push only
```

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `import Cinema` fails, or `cimbuild` errors with `CINEMAPATH is not set`, in a fresh shell | `env.sh` not sourced in *this* shell; nothing is installed system-wide | `. env.sh` again, in every new shell |
| HDF5/libxml2 CMake errors after moving or recreating the conda env | Stale `<cinema-checkout>/cinemabin/envCache.txt`; the cached `PROMPT_LIBXML2_LIB` / `PROMPT_HDF5_*` values are trusted blindly on the next source | Delete `cinemabin/envCache.txt` and re-source `env.sh` |
| conda resolver conflicts or downgrades around libxml2 | KDSource needs libxml2 **2.9.3**; `install.sh` runs `conda install libxml2=2.9.3` when a conda env is active and libxml2 is not already installed in it | Let it downgrade, or let the script fall back to the cached/source build path for libxml2 |
| Every NCrystal-material simulation aborts with a `BadInput` error mentioning a plugin path ending in `;` | The `NCRYSTAL_PLUGIN_LIST` trailing-semicolon bug (section 6) | Re-export the list without semicolons after each `. env.sh` (section 6 workaround) |
| Plugin material not found although the plugin is installed | `NCRYSTAL_PLUGIN_LIST` replaces automatic discovery and does not list the new plugin | Add the plugin `.so` to the exported list (colon-separated, no semicolons) or reinstall the plugin into the conda env and re-source |
| Rebuild loses GIDI/CATIMA support that the first build had | `cimbuild` passes `ENABLE_GIDI=OFF`/`ENABLE_CATIMA=OFF` by default, while the first configure defaults to ON (section 7) | `cimbuild -r --enablegidi --enablecatima` |
| `pip install .` in the repo deletes `build/` and `external/` | The hatchling build hook (`tools/scripts/build_tool/install_cdeps.py`) wipes and rebuilds both directories at the repo root | Do not run `pip install .` inside a working checkout; the packaging path is meant for the conda feedstock |
| First `. env.sh` hangs or fails on downloads | The first run clones/compiles all externals and needs network access to the project hosting plus fallback sites for hdf5/libxml2 | Run it on a network-connected machine once; later sources skip finished components |
| Visualisation-dependent examples fail at import | Missing VTK/GL stack | apt route: install `libgl1`; conda route: install `pyvista` and `vtk=*=qt*` as in the section 4 recipe |
| `ncrystal-pluginmanager` works only inside the conda env | By design: NCrystal and the plugins live in the conda env, not in `cinemavirenv` | `conda activate pt` for plugin management; `env.sh` handles the bridge for simulations (section 6) |

## 11. Legacy: docker image

> **Legacy.** The docker image is stale (Ubuntu 20.04 base, clones old upstream
> NCrystal/VecGeom trees that differ from the ones `env.sh` uses, strips the
> visualisation dependencies, and bakes all environment variables into the image
> instead of using `env.sh`). Its build context is the *parent* of the repo, so the
> checkout directory must be named `cinema`. It is retained for the QE/Tak-side
> workflows, not as a recommended way to install Prompt.

```bash
cd <cinema-checkout>/docker
./build.sh                                # builds image tag cinema:0.1
docker run -it --rm -v $(pwd):/data cinema:0.1
```

## Planned pages

The [CLI](cli), [FAQ](faq) and [Running at scale](mpi-scale) topics now have their own
pages. Environment-adjacent topics still planned as separate wiki pages (not yet
written): `ncrystal-plugins` (plugin details), `dev-notes` (test-suite notes and
known-failing tests) and `legacy-gdml` (the legacy GDML input path).

## Where to ask

Questions and problems: `cinema-users@outlook.com`. The source lives at
`https://code.ihep.ac.cn/cinema-developers/cinema`; the method paper is
[doi:10.1016/j.cpc.2023.109004](https://doi.org/10.1016/j.cpc.2023.109004).
