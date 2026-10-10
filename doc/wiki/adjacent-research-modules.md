# Adjacent research modules

Three modules ship in the repository alongside the Prompt transport core that are
*research tools, not products*: `Cinema.Tak` (molecular-dynamics trajectories to
scattering kernels), `Cinema.PiXiu` (DFT phonons to scattering kernels; the published
name of this pipeline is **BzScope (formerly PiXiu)**) and `Cinema.Experiment`
(comparing simulations with beamline data). They are maintained best-effort. This page
says honestly what each one is for, gives a minimal usage sketch, and lists the caveats
you will hit. It documents Cinema 2.0.0a5. Sources of truth, given as repo-relative
paths in the `Cinema` source repository (browsing the project forge requires an IHEP
account): `src/python/Cinema/Tak/analysor.py`,
`src/python/Cinema/PiXiu/AtomInfo.py`,
`src/python/Cinema/Experiment/Analyser/DataLoader.py`
and the kernel writers in
`src/python/Cinema/Interface/helper.py`.

## 1. Where they sit

All three live *around* the physics core described in [Materials and physics](materials-physics),
which is a pure NCrystal config-string workflow. Tak and BzScope are pre-processing:
they manufacture thermal-scattering data for materials whose dynamics are not covered by
the NCMAT files that NCrystal ships. `Experiment.Analyser` is post-processing: it reads
real detector data in the same shape a simulation produces, so histograms can be compared.

```text
 Tak (MD trajectory)  ─┐
                       ├─> S(Q,omega) grid ─> NCMAT v2 @DYNINFO file ─> nccfg string
 BzScope (DFT phonons) ─┘        (HDF5)            (Interface/helper)    │
                                                                        v
                                              Prompt transport (materials-physics)
                                                                        │
     Experiment.Analyser  <───────── detector histograms ────────────────┘
```

| Module | Direction | Status |
|:---|:---|:---|
| `Cinema.Tak` | MD trajectory -> S(Q), VDOS, MSD, S(Q,omega) -> NCMAT | Best-effort; the most usable of the three, but see its numba caveat |
| `Cinema.PiXiu` (BzScope) | crystal structure -> QE/phonopy -> one-phonon S(Q,omega) -> NCMAT | Maintainer-only; use the plugin repository as the supported entry |
| `Cinema.Experiment` | CSNS-format beamline data <-> simulation histograms | Internal, shaped by one campaign; expect to adapt |

**When to prefer a plain NCrystal config string.** If NCrystal's standard material
library or the repository `ncmat/` files already describe your material — free gases,
VDOS phonons, S(alpha,beta) tables, single crystals — do not reach for these modules at
all: a one-line `nccfg` (section 3 of [Materials and physics](materials-physics)) is
faster, tested and supported. Tak and BzScope exist for the case where you must
*generate* the scattering law yourself, from a trajectory or from first-principles
phonons.

Two shared facts before the details:

1. Every module imports `Cinema.Interface`, which loads the C++ core library at import
   time — source the environment script first (see [Installation](install)).
2. None of the three is exercised by the default test run end-to-end; the exact state is
   listed per module below.

## 2. Tak — MD trajectories to scattering kernels

`Cinema.Tak` (a historical project name) computes the coherent static structure factor
S(Q), the velocity density of states (VDOS), the mean-square displacement (MSD) and
coherent/incoherent dynamic structure factors S(Q,omega) from a molecular-dynamics
trajectory. The kernels are numba-accelerated Python with C++ helpers
(`autocorrelation`, `parFFT`) from `libprompt_core`.

The chain is: load an H5MD-style trajectory, compute S(Q) and the VDOS, unwrap and
re-save the trajectory, then compute S(Q,omega) from the unwrapped file:

```python
from Cinema.Interface.Utils import findData
from Cinema.Tak.analysor import AnaSFactor, AnaSF2VD, DynamicFactor

s = AnaSFactor(findData('md/dump_h5md.h5'))   # H5MD trajectory
q, sq = s.getSq(10)                           # static S(Q), 10 Q points; Q_i = (i+1)*2*pi/<box>

vd = AnaSF2VD(s)                              # reuse the loaded trajectory
fre, vdos = vd.vdos(atomoffset=0, numcpu=-1)  # VDOS (C++ autocorrelation)
vd.vdos_python(0)                             # pure-numpy reference implementation
t, msd = vd.msd()                             # mean-square displacement
vd.saveTrj('unwrapped.h5')                    # reduced trajectory for step 2

df = DynamicFactor('unwrapped.h5')            # reads saveTrj output
fre, s_inc = df.calIncoherent(Q=1.0)          # incoherent S(Q,omega) at one Q
fre, s_co  = df.calCoherent(Q=1.0)            # coherent S(Q,omega)
```

The trajectory input must be an H5MD-layout HDF5 file with these datasets:

| Dataset | Content |
|:---|:---|
| `particles/all/species/value` | species per atom (also used to infer molecules) |
| `particles/all/position/value` | wrapped positions, frame-major |
| `particles/all/box/edges/value` | box per frame |
| `particles/all/species/time` | frame times |

`saveTrj()` writes `reduced_trj` (positions in units of `2*pi/box`), `Q_unit`
(`2*pi/mean(box)`), `dt`, `atomid` and `atominfo` (`[nAtom, nFrame, nMolecule,
nAtomPerMole]`) — exactly the layout `DynamicFactor` reads back, so the two-stage
Trj -> saveTrj -> DynamicFactor round trip is the intended workflow. The frequency axes
returned by `vdos()`, `calIncoherent()` and `calCoherent()` are angular frequencies;
multiply by `units.hbar` for energies, as the driver scripts do.

Two ready-made drivers wrap the chain (`scripts/tak_trj2_sq_vdos.py` for S(Q) + VDOS
and `scripts/tak_uwrptr_sqw.py` for S(Q,omega) plots), and the produced grids feed
straight into the NCMAT writers of section 5.

Caveats (all verified against the current code and environment):

1. **`numba` is required and missing from the default environment.** `analysor.py`
   imports numba at module level, but numba is commented out in the `requirement` file,
   so a fresh environment cannot import `Cinema.Tak.analysor` at all (`ModuleNotFoundError:
   No module named 'numba'`). `pip install numba` restores it. This is also why the
   trajectory tests (`test_tak_trj.py`, `test_tak_parfft.py`) are skipped by the pytest
   configuration. The numba-free parts still work: `Cinema.Tak`'s Filon quadrature
   bindings and the `FunctionXY` curve-algebra module import and pass their unit test
   (measured in the default environment: `test_tak_functionXY.py`, 1 test, OK in under
   a second).
2. **`Cinema.Tak.cdft` is broken.** Its `from Tak import takconv` is an absolute import
   that no longer resolves, so the module fails to import — the classical-to-quantum
   detailed-balance machinery (`DensityOfState`, `Gamma`, `HDRFT`) is unusable until that
   line is fixed. The working path to detailed-balance-correct kernels is the NCMAT
   export (section 5).
3. **The Filon quadrature needs odd-length arrays.** `tak_cal_filon` raises
   `RuntimeError: x should be odd` for even-length frequency grids; pad or crop your grid
   to an odd sample count.
4. **S(Q) wants wrapped positions, S(Q,omega) wants unwrapped ones.** That is what the
   `saveTrj` round trip is for; `AnaSF2VD` performs the unwrap internally when you reuse
   an `AnaSFactor` object.
5. Debugging `print` output is chatty and there is no API documentation beyond this
   page and the source. Treat it as a research tool: check the VDOS against the
   `vdos_python` reference and check S(Q,omega) normalisation against physical
   expectations before trusting a kernel.

## 3. BzScope (formerly PiXiu) — DFT phonons to S(Q,omega)

BzScope goes from a crystal structure to a coherent one-phonon scattering law
S(Q,omega): structure databases or local cells feed Quantum ESPRESSO (QE) and phonopy
calculations, and the phonon mesh is converted into a one-phonon S(Q,omega) with
Debye-Waller factors and detailed balance, stored as HDF5 and convertible to NCMAT
kernels (section 5). The method paper is [arXiv:2511.01178](https://arxiv.org/abs/2511.01178).

> **Naming.** The pipeline was published as BzScope; the paper is
> [arXiv:2511.01178](https://arxiv.org/abs/2511.01178) and the NCrystal plugin that
> packages the resulting kernels is
> [github.com/mctools/ncrystal-plugin-BzScope](https://github.com/mctools/ncrystal-plugin-BzScope).
> The in-repo package directory is still `Cinema/PiXiu`, so imports keep the old name.

Main components (all under `src/python/Cinema/PiXiu/`):

| Component | What it does |
|:---|:---|
| `AtomInfo` | element table (mass, coherent scattering length, incoherent/absorption cross sections) sourced from NCrystal 0.9.18; `getAtomMassBC(element)` |
| `SSSP` | QE input generation (`qems(...)`, `QEType.Scf`/`Relax`) from SSSP pseudo-potential data; shells out to the `phonopy` CLI for supercells |
| `io/` | cell readers: QE XML output (`QeXmlCell`), Materials Project JSON (`MPCell`), plus REST/OPTIMADE/AFLOW download helpers (an API key is needed for Materials Project) |
| `PhononCalc/` | the S(Q,omega) calculators: `CalcBase` (Bose factors, MSD, Debye-Waller, one-phonon form factor), `CalcPowder` (powder-averaged S(Q,omega), `savePowerSqw` HDF5 output), phonopy mesh loaders |
| `phon.py` | direct S(Q) at arbitrary Q via phonopy/euphonic (`CohPhon`) and a vegas Monte-Carlo Q integrator |

Driver scripts live in `scripts/`: `px_pre.py` (DFT preparation), `px_inelastic_direct.py`
(mesh -> S(Q,omega)), `px_inelastic_indirect.py` (inspect an HDF5 result through
`Interface.sctfunc.QeSqw`) and `px_sqw2ncmat.py` (HDF5 -> NCMAT `@DYNINFO` text, section 5).

Caveats:

1. **It does not import without the DFT stack.** `import Cinema.PiXiu` fails in the
   standard Cinema environment with `ModuleNotFoundError: No module named 'spglib'`,
   because the package `__init__` pulls in spglib and phonopy at module level. Even the
   dependency-free element table is unreachable without installing that stack.
2. **External toolchain required end to end**: spglib, phonopy, euphonic, vegas, a QE
   (`pw.x`) installation, and the pseudo-potential data set exposed through the
   `PIXIUSSSP` environment variable (pointed at a repository-external SSSP directory by
   the install script).
3. **`CalcPowder` must be configured before use**: call `configHistgrame(maxQ, enSize,
   QSize, ...)` (the misspelling is the API) before `getSqw()`. Stored energy axes use
   negative energies for down-scattering.
4. **The element table has gaps**: samarium (Z=62) is absent and raises `KeyError`.
5. **Known code drift**: `scripts/px_inelastic_direct.py` carries its own diverging copy
   of `CohPhon`; treat the script and the module as independent experiments.

> **Supported entry point.** This in-repo pipeline is maintainer-only research code; the
> supported way to consume BzScope phonon kernels in a simulation is the
> [ncrystal-plugin-BzScope](https://github.com/mctools/ncrystal-plugin-BzScope)
> repository. Plugin installation into the NCrystal environment follows the same
> mechanism as other NCrystal plugins (see the plugin material section of
> [Materials and physics](materials-physics) and the SANS walkthrough in
> [tutorial-sans](tutorial-sans) for the pattern).

## 4. Experiment.Analyser — comparing with beamline data

`Cinema.Experiment.Analyser` reads real detector data in a CSNS-flavoured HDF5 layout
and normalises/subtracts it the way a beamline campaign does, so simulation histograms
(see [Scoring](scorers) and [Results analysis](results-analysis)) can be compared with
measurement on equal footing.

```python
from Cinema.Experiment.Analyser import DataLoader, RunData, SampleData, PixelLocator

dl  = DataLoader('run.h5', 'Mod1')          # detector module 'Mod1'; zero the first 30 TOF bins (index cut, not a time cut)
rd  = RunData('run.h5', 'Mod1')             # monitor-normalised run
sd  = SampleData('sample.h5', 'Mod1')
sd -= rd                                    # error-propagating background subtraction
loc = PixelLocator(pixelID, positions)      # pixel ids + (x,y,z) positions; KD-tree lookup
```

| Class | Purpose |
|:---|:---|
| `DataLoader(fname, moduleName, tofcut=30)` | reads `/csns/instrument/<module>/time_of_flight` (converted to seconds), `pixel_id`, `histogram_data`, and the beam monitor at `/csns/histogram_data/monitor01`. `tofcut` is a channel count, not a time: the first `tofcut` TOF bins are zeroed in both the detector matrix and the monitor histogram, whatever the file's bin width |
| `ErrorPropagator` | weight + error arrays with sigma-propagating `+=`, `-=`, `/=` operators plus `scale(factor)` — the arithmetic behind run subtraction |
| `RunData` / `SampleData` | monitor normalisation (`Normalise.byMonitor` default), background/holder subtraction via operator overloading, TOF x pixel views |
| `PixelLocator` | scipy KD-tree over pixel positions: nearest-pixel `locate(locations)`, hit-list to (pixel, TOF) binning helpers |

Caveats:

1. **Shaped by one campaign.** The module was written around a single 2022 powder
   experiment ("MPI2022"): the HDF5 layout is the CSNS flavour of that campaign and
   `MPI2022ExpInfo.py` hardcodes its run list, sample geometries and intranet
   data-server addresses. Configure your own storage and run metadata instead of
   relying on that file — importing it also opens a campaign-specific data file from
   the repository data directory. Expect to adapt the loaders to your own file format.
2. **The top-level package initializer is misspelled** (`_init_.py`, never executes), so
   `Cinema.Experiment` behaves as a namespace package. Import from the sub-package,
   `from Cinema.Experiment.Analyser import ...` as above — that path works.
3. **Working examples are in `tools/`** (`yn_multiscat.py`, `example_pixellocator.py`),
   not in the test suite; the module itself has no unit tests.

## 5. How the three feed the NCMAT workflow

The common denominator is the S(Q,omega) grid and the kernel writers in
`Cinema.Interface.helper`. Everything Tak and BzScope produce eventually becomes an
NCMAT file that a plain config string can load:

| Writer | Signature | Emits |
|:---|:---|:---|
| `incoherentSqw2ncmat` | `(fname, Q, fre, sqw, kt=0.0253)` | NCMAT v2 file with an `@DYNINFO type scatknl` block (`alphagrid`/`betagrid`/`sab`) from one incoherent S(Q,omega) |
| `gaussSqw2ncmat` | `(fname, density, elements, Qs, fres, sqws, fractions, temperature=293.)` | multi-element variant, one `@DYNINFO` per element |
| `writeDynInfo` | `(fo, element, alpha, beta, fraction, temperature, knl)` | a single `@DYNINFO` block, for assembling files by hand |

```python
from Cinema.Interface.helper import incoherentSqw2ncmat

# Q (1/A), fre (angular frequency) and sqw from Tak or BzScope:
incoherentSqw2ncmat('mysample.ncmat', Q, fre, sqw)   # kt in eV, default 300 K
# then, in the simulation (materials-physics):
mat = Material('mysample.ncmat')
```

Two things to check in the generated file before using it:

1. `incoherentSqw2ncmat` writes a fixed water-like skeleton around the kernel (an
   O-1/3 `freegas` element plus an H-2/3 `scatknl` element). Edit the element, fraction
   and density lines to match your material.
2. The default `kt=0.0253` (eV) encodes room temperature; pass the temperature you
   simulated the trajectory at, since the alpha/beta grids and detailed balance depend
   on it.

`scripts/px_sqw2ncmat.py` shows the same conversion for a BzScope histogram
(`qehist.h5` with datasets `q`, `omega`, `s` — the layout `Interface.sctfunc.QeSqw`
reads) into an NCMAT v5 `@DYNINFO` text. For analysis-side use without transport, the
`Sqw`/`H5Sqw`/`QeSqw` classes in `Interface.sctfunc` load such HDF5 grids directly,
reconstruct the full omega axis with detailed-balance factors and interpolate.

For materials where NCrystal's shipped data suffices, skip all of this and use a
config string; for everything these modules produce, the resulting NCMAT file is
consumed exactly like any shipped one — see [Materials and physics](materials-physics)
for the config-string rules and [Your first simulation](first-simulation) for the
surrounding script shape.

Questions about any of these modules, and offers to maintain one properly:
**cinema-users@outlook.com**.

---

*Source files (repo-relative paths in the Cinema repository):
`src/python/Cinema/Tak/analysor.py`,
`src/python/Cinema/PiXiu/AtomInfo.py`,
`src/python/Cinema/Experiment/Analyser/DataLoader.py`,
`src/python/Cinema/Interface/helper.py`,
`scripts/tak_trj2_sq_vdos.py`,
`scripts/px_sqw2ncmat.py`.
BzScope paper: [arXiv:2511.01178](https://arxiv.org/abs/2511.01178); plugin:
[github.com/mctools/ncrystal-plugin-BzScope](https://github.com/mctools/ncrystal-plugin-BzScope).
Questions: cinema-users@outlook.com.*
