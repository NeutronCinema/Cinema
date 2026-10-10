# The Simulation class: lifecycle, seeds, MPI and outputs

This page is the reference for the `Simulation` class that every Cinema/Prompt script
builds: what the `Prompt` / `PromptMPI` base classes provide, the exact order in which
the life-cycle methods must run, how random numbers and MPI parallelism work, and what
a run writes to disk. It documents Cinema 2.0.0a5.

The supported workflow is the **Python API**: subclass `Prompt` (serial) or `PromptMPI`
(MPI parallel), build geometry in `makeWorld()`, then `show()` / `simulate()`.
A minimal walk-through lives in [Your first simulation](first-simulation); this page
formalises what happens under the hood. Source of truth:
[`src/python/Cinema/Prompt/promptCore.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/promptCore.py).

---

## 1. `Prompt` vs `PromptMPI`

`Cinema.Prompt` exports `Prompt`, `PromptMPI`, `PromptFileReader`, `Launcher` and `PTMCPL`.
Your script defines a subclass of one of the two bases; by convention it is called
`Simulation` (the [`prompt` CLI](#9-the-prompt-cli-python-mode-in-brief) requires exactly
one such subclass per script).

```python
Prompt(seed: int = 4096)     # serial
PromptMPI(seed: int = 4096)  # MPI parallel, subclass of Prompt
```

| Member | Class | Meaning |
|---|---|---|
| `seed` | both | Read-only property; the RNG seed stored on the object (default `4096`; under `PromptMPI` this is seed + rank, see below). |
| `.l` | both | Read-only property returning the process-wide `Launcher` singleton (the bridge to the C++ core). |
| `.scorer` | both | Read-only property returning `Volume.scorer_dict` — the registry of every scorer attached by any `Volume` so far (name → lookup key). Populated when a scorer helper's `.make(vol)` runs. |
| `makeWorld()` | both | Abstract — the base implementation raises `NotImplementedError`. You must override it. |
| `setWorld(world)`, `show(gun, num)`, `simulate(gun, num)`, `gatherHistData(cfg)`, `save_all_scorers()`, `clear()` | both | The life-cycle methods described below. |
| `.comm`, `.rank`, `.size` | `PromptMPI` | The `MPI.COMM_WORLD` communicator and this process's rank/size. |

Two properties of the base classes matter for everything else:

- **`Launcher` is a process singleton** (`@singleton` decorator; on the C++ side
  `Prompt::Launcher` is also a singleton, obtained via `pt_Launcher_getInstance()`).
  Every `Prompt` object you create shares the *same* launcher, and hence the same
  world and RNG. Constructing the launcher loads the C++ core and installs Cinema's
  RNG as NCrystal's default generator (see
  [section 5](#5-random-numbers-and-reproducibility)).
- **`PromptMPI` derives the per-rank seed in its constructor**: it calls
  `super().__init__(seed + rank)`, so each rank stores a different seed and therefore
  draws an independent random stream. Do not re-seed per rank yourself.

---

## 2. The `makeWorld` contract and `setWorld`

`makeWorld()` is your geometry-building hook. The contract:

1. Override it in your `Simulation` subclass.
2. Inside, create `Material`s, `Volume`s (with scorers attached via
   `scorer.make(vol)`), assemble the world volume with `placeChild` calls — see
   [Geometry](geometry) for the full API.
3. Finish by calling `self.setWorld(world)`.

`setWorld(world)` does exactly two things, in this order:

```python
def setWorld(self, world):
    self.l.setSeed(self.seed)   # <- the seed is applied HERE
    self.l.setWorld(world)
```

- **The seed is applied in `setWorld`, not in `simulate`.** Anything stochastic that
  happens before `setWorld` runs is not governed by the seed you passed to the
  constructor.
- `Launcher.setWorld` closes the VecGeom geometry (builds the navigators) and sets the
  internal `worldExist` flag. It is **one-shot per process**: a second `setWorld` without an
  intervening `clear()` raises the catchable Python exception
  `RuntimeError: World exist already: only one world can be set per process ...` (the guard
  now runs before the seed is re-applied). Note that the `Launcher` is a process singleton
  shared by every `Prompt` instance, so constructing a second `Simulation()` in the same
  process hits the same error on its first `setWorld` — run each world in its own process
  (a separate script or an `mpirun` rank), or `clear()` first when one object is reused.
  After it returns, creating or placing further `Volume`s is meaningless — all geometry
  must be built before it. Always call `sim.clear()` before rebuilding.

---

## 3. `show` vs `simulate`

Both methods accept the same **three gun forms**:

1. **A gun object** with a `.cfg` config string (all `ConfigString`-based built-in
   guns, e.g. `SimpleThermalGun`, `MaxwellianGun`, `UniModeratorGun`, `MCPLGun`).
   The object API (`gun.setSource(...)`, `gun.setSlit(...)`, ...) is a convenient way
   to populate the config; `simulate` passes `gun.cfg` to the C++ gun factory.
2. **A raw config string**, e.g.
   `"gun=SimpleThermalGun;position=0,0,-100;direction=0,0,1;energy=1e-3"` — keep the
   position inside the world volume ([Particle guns](guns));
3. **A `PythonGun`** — a user subclass with a numpy-vectorised `.generate()` method
   (see [Particle guns](guns)). `simulate`
   loops `gun.generate()` + one C++ event each, showing a progress bar on rank 0.

### `show(gun, num=0)` — look before you leap

`show` opens an interactive pyvista window with the geometry and, when `num > 0`,
re-simulates `num` events with trajectory recording and overlays the trajectories.
`num=0` shows geometry only. It requires the world to be set (`RuntimeError('World is
not set')` otherwise). It is interactive — do not use it in batch scripts or CI.

`show` accepts the visualisation keyword arguments `mergeMesh`, `xscale`, `yscale`,
`zscale` (for long, squashed beamlines), `byMat`, `addLegend`, `geoClip` — identical on
the serial `Prompt.show` and `PromptMPI.show`. Under MPI only rank 0 renders; all ranks
then meet at a barrier.

### `simulate(gun, num=0, timer=True, save2Disk=False)` — the production run

Serial and MPI signatures are now the same: `simulate(gun, num=0, timer=True,
save2Disk=False)`. The event split under MPI is automatic
([section 6](#6-mpi-semantics)); `timer` and `save2Disk` take effect on the root rank
only (non-root ranks run with both off, since their histograms are reduced to rank 0
afterwards).

Note that **`save2Disk` defaults to `False`** in the Python API (the underlying C++
`go()` default is `True`): a plain `simulate()` accumulates histograms in memory only.
See [section 7](#7-what-a-run-writes) for what `save2Disk=True` and
`save_all_scorers()` write.

---

## 4. The life-cycle end to end

A complete production run, in the order the API expects:

```python
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class Simulation(PromptMPI):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        mat = Material('Ge_sg227.ncmat;mos=0.0267deg;'
                       'dir1=@crys_hkl:5,1,1@lab:0,0,1;'
                       'dir2=@crys_hkl:0,1,-1@lab:1,0,0')
        vol = Volume("sampleSolid", Box(10, 10, 1), matCfg=mat.cfg)
        TOFHelper("TOF", ptstate='ABSORB').make(vol)
        trf = Transformation3D(0, 0, 100).applyRotX(45)
        world = Volume("world", Box(50, 50, 210))
        world.placeChild("samplePhyVol", vol, transf=trf)
        self.setWorld(world)                      # step 3 (seed + geometry close)

if __name__ == "__main__":
    gun = UniModeratorGun()
    gun.setSource([10, 10, -200])
    gun.setSlit([5, 5, -20])
    sim = Simulation(seed=4096)                   # step 1: construct
    sim.makeWorld()                               # step 2: build, ends in setWorld
    # sim.show(gun, 100)                          # step 4: optional visual check
    sim.simulate(gun, 1e7)                        # step 5: run
    hist = sim.gatherHistData('TOF')              # step 6: read results
    if sim.rank == 0:                             # rank-0 guard, as taught in section 6
        hist.savefig('tof.png')
    # sim.save_all_scorers()                      # ... or save every scorer
    # sim.clear()                                 # step 7: only for a rebuild
```

(Numbering below matches the comments.)

1. **Construct** `Simulation(seed=...)`. The `Launcher` singleton is created: the C++
   core library is loaded and the shared RNG is installed as NCrystal's default.
2. **`makeWorld()`** — your code creates materials, volumes and scorers (each
   `scorer.make(vol)` registers the scorer in `Volume.scorer_dict`, exposed as
   `sim.scorer`).
3. **`setWorld(world)`** (called at the end of `makeWorld`) — seed applied, geometry
   closed. From here the process is committed to this world.
4. **`show(gun, n)`** (optional) — interactive geometry + trajectory check.
5. **`simulate(gun, N)`** — the event loop. Config-string guns go through the C++
   `go()` main loop; a `PythonGun` is driven event-batch by event-batch from Python.
   Scorers accumulate weight/hit/Σw² in C++ histograms.
6. **Gather and save** — `sim.gatherHistData('name')` returns a live `Hist1D`/`Hist2D`
   view for plotting in the same script (`hist.savefig(...)`); `sim.save_all_scorers()`
   writes every scorer to disk. Details in
   [Scoring](scorers) and [section 7](#7-what-a-run-writes).
7. **`clear()`** (only if you want another simulation in the same process) — resets the
   C++ resource manager, `worldExist` and the scorer registry; see
   [section 8](#8-clear-and-rebuild-parameter-scans-in-one-process).

---

## 5. Random numbers and reproducibility

The seed flows through a single chain:

```text
Simulation(seed)            stored on the Python object (.seed)
   └─ setWorld(world)       self.l.setSeed(self.seed)
        └─ Launcher.setSeed C++ Singleton<SingletonPTRand>::setSeed(seed)
             └─ SingletonPTRand   std::mt19937_64, one instance per process
                  └─ NCrystal    Launcher's constructor installed a wrapper around
                                 SingletonPTRand as NCrystal's default RNG
```

Consequences:

- **One stream controls everything C++-side.** Because NCrystal samples from a wrapper around
  the same `SingletonPTRand` that drives the transport loop, the constructor seed
  reproduces the *whole* run for cfg-string guns and all transport/NCrystal sampling:
  identical seed + identical script ⇒ identical histograms
  (the test suite relies on this with exact-seed golden anchors).
  Exception: a `PythonGun` samples on the numpy side from your own
  `RandomState`/`Generator` seeds, which this C++ stream does not govern — seed those
  explicitly (see [Particle guns](guns)).
- **The seed is applied by `setWorld`.** Since `clear()` resets `worldExist` and the
  next `setWorld` calls `setSeed(self.seed)` again, a `clear()`-and-rebuild cycle
  re-starts the random stream from the same seed — a rebuilt simulation with
  unchanged parameters reproduces its predecessor exactly, and a scan point always
  starts from a known RNG state.
- **Under MPI each rank has its own stream**: `PromptMPI.__init__` stores
  `seed + rank`, and each rank's `setWorld` seeds its local `SingletonPTRand` with it.
- **Output file names embed the C++ RNG seed current when the scorer is created**
  (during `makeWorld`, i.e. before `setWorld` applies your constructor seed) — see
  [section 7](#7-what-a-run-writes). On the first build in a process this is the
  library default `5489`, so file names do not distinguish your chosen seed; from the
  second `clear()`/rebuild cycle onwards the constructor seed appears. Re-runs
  therefore overwrite regardless of seed — move or rename files you want to keep.

---

## 6. MPI semantics

Use `PromptMPI` and launch with `mpirun`; the class reads `MPI.COMM_WORLD` itself, no
extra code is needed:

```bash
mpirun -n 4 python3 doc/example_basic.py
```

The `prompt -g` CLI form can also be launched under `mpirun`, but only with a
conforming script — it must define a `Gun` subclass and run `makeWorld()` outside
`if __name__ == "__main__":` (see
[section 9](#9-the-prompt-cli-python-mode-in-brief)); `doc/example_basic.py` does not
satisfy this.

| Aspect | Behaviour |
|---|---|
| Seeds | Each rank simulates with `seed + rank` (independent streams; combined they are statistically independent — exactly what you want). |
| Event split | `PromptMPI.simulate(gun, num)` computes `batchSize = int(num / self.size)`. Ranks 1..n-1 run `batchSize` events each (progress timer and `save2Disk` off); **rank 0 runs the remainder** `num - batchSize*(size-1)`, with the timer on and, if requested, the `save2Disk` dump. The sum over ranks equals `num`. |
| `gatherHistData(cfg, raw=False, dst=0)` | **Collective.** After fetching the local histogram it prints `Scorer <name> rank <r>: weight ..., hit ...` per rank, then performs three `comm.Reduce` (sum) operations over the weight, hit and Σw² arrays to root `dst` (default 0). Every rank must call it, in the same order. The returned histogram holds the merged data **only on rank `dst`**; on other ranks ignore the returned arrays. |
| `show(...)` | Rank 0 renders the window and then all ranks barrier — no MPI-deadlocked windows, but do not call it in batch jobs. |
| `save_all_scorers()` | Writes files on **rank 0 only** under MPI (internally `rank = getattr(self, 'rank', 0)`, so plain serial `Prompt` runs write too). |
| Console | Rank 0 owns progress printing; `gatherHistData` prints one weight/hit line per rank. |

Plot and save only where the data is valid:

```python
sim.simulate(gun, 1e7)
hist = sim.gatherHistData('TOF')
if sim.rank == 0:
    hist.savefig('tof.png')
```

More on scaling out (multi-seed production, merging independent runs) is on
[Running at scale](mpi-scale).

---

## 7. What a run writes

All output files land in the **current working directory**; the examples use plain
relative names so results stay next to where you launched the job.

| Artefact | Produced by | Content |
|---|---|---|
| `<scorer>.h5` | `sim.save_all_scorers()` (rank 0) | HDF5 per scorer: datasets `center`, `edge` (1D) or `xcenter`, `ycenter`, `xedge`, `yedge` (2D) plus `weight`, `hit`, `sdev`, `note`, `type` (e.g. `ScorerTOF` for `TOFHelper("TOF")`); the numeric arrays are gzip-compressed. This is what the `ptplot` command-line plotter reads. |
| `<scorer>.pdf` | `sim.save_all_scorers(savepdf=True)` (rank 0) | Quick-look plot of each scorer, in addition to the `.h5`. |
| `<name>_seed<seed>.mcpl.gz` | `sim.simulate(..., save2Disk=True)` — written by rank 0 only under MPI (non-root ranks never dump) | Despite the extension, for ordinary histogram scorers this MCPL container carries the **histogram**: header blobs with numpy arrays (`content`, `hit`, `edge` — `xedge`/`yedge` for 2D) plus overflow/underflow and summary statistics in the header comments. A ready-made plotting template `<name>_view.py` is written next to it — the same base name as the `.mcpl.gz` file without the `_seed<seed>` suffix (e.g. `ScorerTOF_TOF_view.py` for `TOFHelper("TOF")`; `<name>` is the internal hist name `Scorer<Type>_<user name>`), showing the canonical reload with `PromptFileReader`. |
| `<name>.mcpl.gz` (particle records) | `MCPLOutHelper` scorers / `PTMCPL` usage | Actual particle records, reused MCPL fields (`userflags` = event ID, `polarisation` triple = survival probability / scattering number / ΔE). Under MPI the file name gets `_pro<rank>` appended. See [Scoring](scorers). |

Notes:

- The histogram MCPL name embeds the C++ RNG seed current when the scorer is created
  (`<name>_seed<seed>`) — which happens inside `makeWorld`, before `setWorld` applies
  your constructor seed. On the first build in a process this is the library default
  `5489`, so file names do not distinguish your chosen seed; from the second
  `clear()`/rebuild cycle onwards the constructor seed appears. A re-run therefore
  **overwrites** the previous output regardless of seed — rename or move files between
  runs if you want to keep both.
- `PromptFileReader('file.mcpl.gz')` (exported from `Cinema.Prompt`) reads the
  histogram blobs back: `f.getData('edge')`, `f.getData('content')`, `f.dataKeys()`.
- With the Python-API defaults (`save2Disk=False`, no `save_all_scorers()` call) a run
  writes **no files at all** — results live only in memory until you gather them.
- Console output: progress bars/timers during `simulate`, the per-rank scorer lines
  from `PromptMPI.gatherHistData`, and a logo when the launcher is destroyed at exit.

---

## 8. `clear()` and rebuild: parameter scans in one process

`clear()` tears a simulation down in-place:

```python
def clear(self):
    _pt_ResourceManager_clear()      # C++: volumes, physics, scorers, surfaces
    self.l.worldExist = False        # re-allows setWorld
    Volume.scorer_dict = {}          # scorer registry emptied
```

After `clear()` you can build a fresh world in the same process; the next
`setWorld` re-applies `self.seed`, so every scan point starts from the same known RNG
state. The canonical scan loop:

```python
sim = Simulation(seed=4096)
for thickness in (1.0, 2.0, 5.0):
    sim.clear()
    sim.makeWorld(thickness)          # your makeWorld can take parameters
    sim.simulate(gun, 100000)
    h = sim.gatherHistData('TOF')
    if sim.rank == 0:
        h.savefig(f'tof_t{thickness}.png')
```

Rules of thumb:

- `clear()` is **mandatory** before a second `setWorld` in one process — without it
  the second call raises `RuntimeError: World exist already: only one world can be set
  per process` — and between independent simulations in test scripts.
- One `Launcher` per process means you can never hold two worlds simultaneously —
  clear, rebuild, re-run.
- `Volume.volume_list` (python-side bookkeeping of every `Volume` ever constructed)
  is *not* cleared; that is by design (memory ownership), but it means long scan
  loops accumulate python-side objects.
- The built-in `Optimiser` (Optuna-based parameter tuning, on the planned
  parameter-optimization page) uses exactly this `clear()` → `makeWorld(params)` →
  `simulate` → score pattern.

---

## 9. The `prompt` CLI python mode in brief

Instead of running `python3 myscript.py` you can let the `prompt` command introspect
your script and expose its parameters on the command line:

```bash
prompt -g myscript.py --gun BeamGun -n 1000000 -s 42
mpirun -n 4 prompt -g myscript.py --gun BeamGun -n 1000000
```

What it does (python-script mode):

- Loads the `.py` file, requires exactly one `Prompt`/`PromptMPI` subclass and at least
  one `Gun` subclass **defined in that file** (imported gun classes are invisible to the
  introspection — e.g. `--gun UniModeratorGun` fails with `No class 'Gun' is defined.`
  unless `UniModeratorGun` is also a base of a class in the script, as with `BeamGun`
  in [first-simulation §3.2](first-simulation));
  `--gun <ClassName>` selects the gun (mandatory to run).
- Builds one `--<param>` option per constructor parameter from the type hints
  (`bool` → `--param`/`--no-param`, `list`/`dict` parsed as Python literals).
  Name your seed parameter `seed` — the general `-s/--seed` value is forwarded into
  the constructor. `-n/--neutronNum` (default 100) is the event count.
- Checks `sim.l.worldExist` and raises `"World not made."` if `makeWorld()` has not
  run — so put the `sim.makeWorld()` call in the module body or the constructor when
  you intend to use the CLI (code inside `if __name__ == "__main__":` is **not**
  executed by the CLI).
- Then either `sim.show(...)` (with `-v`) or `sim.simulate(gun, n)` followed by
  `sim.save_all_scorers()`.

A full option reference lives on [The command line](cli).

---

## 10. Gotchas

| Symptom | Cause and remedy |
|---|---|
| `RuntimeError: World exist already: only one world can be set per process` | `setWorld` is one-shot per process: a second `setWorld` without `clear()` raises this (catchable) error. The `Launcher` is a process singleton, so a second `Simulation()` in the same process trips it too — run each world in its own process or `clear()` first ([section 8](#8-clear-and-rebuild-parameter-scans-in-one-process)). |
| Where is the traceback? | Without `--debug` the CLI prints a one-line error and exits 1; pass `--debug` to get the full Python traceback. Uncatchable C++ aborts (SIGABRT/SIGSEGV) by nature print no traceback — reproduce them with `python3 myscript.py`. |
| Scorer results missing | Duplicate scorer names now raise `ValueError` at `.make(vol)` instead of silently aliasing — give each scorer a unique name. Also check the scorer helper was actually `.make(vol)`-ed. |
| Run finishes, no output files | Python-API default is `save2Disk=False`; files appear only via `save_all_scorers()` (`.h5`) or `simulate(..., save2Disk=True)` (`.mcpl.gz`). |
| Reproducibility: "same seed, different histogram" | Check that nothing stochastic happens before `setWorld` (the seed is applied there), and that under MPI you compare merged rank-0 results. Same seed ⇒ identical results only for an identical script and event split. |
| Old output silently replaced | Histogram MCPL file names embed the RNG seed current at scorer creation (`<name>_seed<seed>.mcpl.gz` — the library default 5489 on the first build, not your constructor seed); a rerun overwrites regardless of seed. |
| MPI run hangs or crashes in `gatherHistData` | It is a collective call: every rank must call it, in the same order. Use its result only on rank `dst` (default 0). |
| `show()` in a batch job | It opens an interactive window. Use it for visual checks only; gate any plotting with `if sim.rank == 0:`. |
| Second `Simulation()` object behaves strangely | `Launcher` is a process singleton — all `Prompt` instances share one world and one RNG. Never keep two simulations alive in one process; `clear()` and rebuild instead. |

---

## Planned pages

The pages below are planned for this wiki but do not exist yet; they are named here as
plain text only: parameter-optimization (the `Optimiser`), ncrystal-plugins, legacy-gdml,
dev-notes. The guns, results-analysis, cli, visualization, units, mpi-scale and faq
material now has its own pages — see *Where to go next* and the wiki map on [home](home).

## Where to go next

- [Your first simulation](first-simulation) — line-by-line walkthrough of the example above
- [Geometry](geometry) — `Volume`, shapes and `Transformation3D`
- [Materials and physics](materials-physics) — NCrystal config strings and biasing
- [Scoring](scorers) — scorer catalogue, `ptstate` semantics, reading results

---

*Source files: [`promptCore.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/promptCore.py).
Questions: cinema-users@outlook.com.*
