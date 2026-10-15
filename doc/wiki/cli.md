# The command line: `prompt` and `ptplot`

Cinema/Prompt ships two commands: `prompt` runs a simulation from the terminal, `ptplot`
plots the `.h5` result files. This page is the reference for both. It documents
**Cinema 2.0.0a5**; every option, default and error message below was checked against the
current sources
([promptcli.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/promptcli.py),
[ptplotcli.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/ptplotcli.py))
and exercised live on small runs (event counts and seeds stated with every number,
October 2026).

Before using either command, [install](install) Cinema and source the environment once per
shell:

```bash
. <cinema-checkout>/env.sh
```

> **Known issue on current installs:** sourcing the environment currently exports an
> `NCRYSTAL_PLUGIN_LIST` with a stray trailing `;` (a quirk of how `install.sh` assembles it
> from `ncrystal-pluginmanager` output), so NCrystal aborts *every* simulation run — the
> section-2 quickstart included — with `Could not find dynamic plugin shared library:
> .../libNCPlugin_SasCSNS.so;` (SIGABRT, exit code 134). Workaround — the canonical remedy
> from [Installation](install), section 6, re-applied after every `. env.sh`:
> `export NCRYSTAL_PLUGIN_LIST="$(printf '%s' "$NCRYSTAL_PLUGIN_LIST" | tr -d ';')"`.
> (`unset NCRYSTAL_PLUGIN_LIST` also stops the aborts, because NCrystal then locates plugins
> itself — but a non-empty list *replaces* automatic discovery, so unsetting only works while
> the conda env owning the plugins is reachable.) All numbers on this page were verified with
> a corrected list in place.

---

## 1. Your script is the interface

The `prompt` command does not have a simulation definition language of its own. In its
recommended mode it **reads a Python script, introspects the classes defined in it and
generates a command-line interface from their constructor type hints**. The script you
already wrote for [your first simulation](first-simulation) becomes a configurable tool:
every constructor parameter turns into a `--option`, without writing a single line of
argparse code.

| Use | Route | Why |
|---|---|---|
| Developing, debugging, quick looks | `python3 mysim.py` | real tracebacks, interactive `show()`, results analysis in the same script |
| A reusable, parameterised run tool | `prompt -g mysim.py --gun ... --param ...` | auto-generated options, uniform `-n`/`-s` across all scripts, one-line shell sweeps |
| MPI production | `mpirun -n 4 prompt -g mysim.py ...` | identical to the in-Python route, no `__main__` bookkeeping needed |
| Legacy v1 GDML files | `prompt -g model.gdml` | old workflows only — see the legacy notice in section 4 |

Nothing is CLI-only: the CLI just instantiates your classes and calls
`simulate()` + `save_all_scorers()` — five lines of Python. If you find yourself fighting
the CLI, run the script directly.

---

## 2. `prompt -g yourscript.py`

### 2.1 What the script must look like

The CLI imports the module (it **never executes** the `if __name__ == "__main__":` block)
and requires:

- **exactly one** subclass of `Prompt` or `PromptMPI` defined in the file — more than one
  aborts with `Class 'Prompt' is duplicated in N classes`;
- **one or more** subclasses of `Gun` defined in the file. Imported gun classes are
  invisible to the introspection — a script that only imports `UniModeratorGun` fails with
  `No class 'Gun' is defined.` Wrap the gun in a trivial subclass, as below.

`makeWorld()` must already have run when the CLI instantiates the simulation class (it
checks `sim.l.worldExist` and exits with `World not made.` otherwise). The clean way is to
call it from the constructor — that also lets the CLI-supplied seed flow into `setWorld`
(section 2.4). A CLI-ready script:

```python
#!/usr/bin/env python3
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class GeSlabSim(PromptMPI):
    def __init__(self, seed: int = 4096):
        super().__init__(seed)
        self.makeWorld()   # the CLI requires the world to exist at instantiation

    def makeWorld(self):
        nccfg = 'Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'
        mat = Material(nccfg)
        vol = Volume("sampleSolid", Box(10, 10, 1), matCfg=mat.cfg)
        tof = TOFHelper("TOF", ptstate='ABSORB')
        tof.make(vol)
        trf = Transformation3D(0, 0, 100).applyRotX(45)
        world = Volume("world", Box(50, 50, 210))
        world.placeChild("samplePhyVol", vol, transf=trf)
        self.setWorld(world)

class BeamGun(UniModeratorGun):
    def __init__(self, src_whz: list = [10, 10, -200], slit_whz: list = [5, 5, -20],
                 wl_mean: float = 1., wl_range: float = 0.0001):
        super().__init__(src_whz, slit_whz, wl_mean, wl_range)
```

This is the tutorial example of [first-simulation](first-simulation) in CLI-ready form.

### 2.2 Auto-generated options

`prompt -g ge_slab.py -h` shows what the introspection built (excerpt). Note the help
cannot exist before the script loads — the per-class options are parsed from the loaded
classes — so `-h` executes the script's module level first. The CLI prints a `NOTE:`
line saying exactly that before loading; keep `makeWorld()` in the constructor (see
[2.4](#24-the-seed-and-the-makeworld-placement)) so that side effect stays cheap:

```text
Particle Gun Arguments:
  -s, --seed        random seed number
  -n, --neutronNum  neutron number
  --gun             gun class name. Available: ['BeamGun']

BeamGun:
  --src_whz         Default: [10, 10, -200] (eg.: '[1, 2, 3]')
  --slit_whz        Default: [5, 5, -20] (eg.: '[1, 2, 3]')
  --wl_mean         Default: 1.0
  --wl_range        Default: 0.0001
```

One `--<param>` option is generated per constructor parameter of the simulation class and
of every gun class; defaults from the signature appear in the help. Parameters without a
default become mandatory options. Run it:

```bash
prompt -g ge_slab.py --gun BeamGun -n 2000 -s 4096     # --gun is mandatory
prompt -g ge_slab.py --gun BeamGun --wl_mean 2.0 -n 1e6
```

After `simulate()` the CLI calls `sim.save_all_scorers()` for you, so the run leaves one
`<scorer>.h5` file per scorer (`TOF.h5` here) in the working directory. Nothing else is
written — the Python-API default `save2Disk=False` applies (see
[simulation-lifecycle](simulation-lifecycle) for the full output catalogue).

The built-in options:

| Option | Meaning |
|---|---|
| `-g, --geo` | the input file; `.py` (this section) or `.gdml` (legacy, section 4). Mandatory. |
| `--gun <ClassName>` | which gun class to instantiate. Mandatory to run; the class must be defined in the script. |
| `-n, --neutronNum` | number of primaries (default 100; a float, truncated to int, so `-n 1e6` works). With `-v`: number of trajectories instead. |
| `-s, --seed` | RNG seed (default 4096). Forwarded into a constructor parameter named `seed` — name yours `seed`. |
| `-v, --visualize` | show geometry + `-n` trajectories instead of simulating; writes no files. |
| `-Z, --zscale` | z-scale factor for `-v` (default 1), for squashed long beamlines. |
| `-b, --blacklist`, `-m, --mergemesh`, `-d, --dumpmesh`, `--nSeg` | mesh options of the **legacy GDML viewer only — they are parsed but ignored in `.py` mode**. `-d` here means "dump mesh", not downbinning. |
| `--debug` | print the full traceback of Python exceptions (see section 6). |

`-v` needs a display; without one the build falls back to off-screen rendering and no
interactive window appears.

### 2.3 Parameter type conventions

| Type hint | Command-line form | Verified behaviour |
|---|---|---|
| `int`, `float` | `--wl_mean 2.0`, `-n 1e6` | parsed as the annotated type |
| `str` | `--label det7` or `--label "'lab X'"` | bare strings pass through; wrap in double *and* single quotes for values with spaces (the quotes are stripped). Numeric-looking strings are converted to `float` — a string option `--tag 12.5` arrives as the number `12.5` |
| `list` | `--src_whz "[20, 20, -300]"` | parsed as a Python literal; `Optional[list]`, `list | None` and un-annotated `= None` list defaults all work (see section 6) |
| `dict` | `--tags "{'k': 2}"` | parsed as a Python literal; `= None` defaults work for `Optional[dict]` too (see section 6) |
| `bool` | `--verbose` | generated as a plain flag (present = true); usable on the supported Python (see section 6) |
| no default | — | option is required; missing it aborts with an argparse `the following arguments are required: --param` error |

Constructor parameters whose names collide with the built-ins (`seed`, `neutronNum`,
`visualize`, `zscale`, `blacklist`, `mergemesh`, `dumpmesh`, `nSegments`, and also `geo` and
`debug`) get **no** `--option` of their own; the general flag value is forwarded into the
constructor instead. That is exactly what you want for `seed`, and a trap for any other name:
a parameter named `debug` silently receives the `--debug` flag value, and one named `geo`
receives the script path. The general rule: *any argparse dest of the built-in options*
(including `geo` and `debug`) collides.

### 2.4 The seed and the `makeWorld` placement

The seed reaches the C++ RNG through `setWorld`, not through the constructor (see
[simulation-lifecycle](simulation-lifecycle)). Consequences, both verified with a probe
script printing the applied seed:

- `makeWorld()` called **in the constructor**: `prompt -g ... -s 7` prints
  `set random seed: 7`. This is the pattern to use.
- `makeWorld()` called at **module level** (`sim = Simulation(); sim.makeWorld()` in the
  module body): the world is built at import time with the module-level instance's default
  seed, and `-s 7` is **silently ignored** — the run printed `set random seed: 4096` while
  the CLI had been given 7. The world-exist check still passes (the launcher is a process
  singleton), so nothing warns you.
- Building at module level *and* in the constructor aborts the process: `setWorld` runs
  twice (it is one-shot per process).

---

## 3. MPI through the CLI

```bash
mpirun -n 4 prompt -g ge_slab.py --gun BeamGun -n 1000000
```

This is exactly equivalent to launching a `__main__`-style script under `mpirun` — the CLI
process becomes one MPI rank, `PromptMPI` picks up `MPI.COMM_WORLD` by itself, and all the
semantics of [simulation-lifecycle](simulation-lifecycle) apply unchanged: events split
across ranks with rank 0 carrying the remainder, per-rank seeds `seed + rank`, collective
`gatherHistData` (which `save_all_scorers()` calls per scorer on **every** rank, as it
must), files written by rank 0 only.

Measured check (October 2026): `mpirun -n 2 prompt -g ge_slab.py --gun BeamGun -n 1001
-s 4096` completes in ~6 s wall with exit code 0 and a single `TOF.h5`. The CLI-ready
script shape of section 2.1 (constructor-built world) is precisely what MPI needs — no
`__main__` block involved. More on scaling out in [mpi-scale](mpi-scale).

---

## 4. Legacy: `prompt -g file.gdml`

> **Legacy notice.** The GDML input mode is v1 functionality, kept so that old workflows
> keep running. It is documented in the method paper
> ([doi:10.1016/j.cpc.2023.109004](https://doi.org/10.1016/j.cpc.2023.109004)) and must
> **not** be used for new work — define geometry, guns and scorers in Python as in
> [geometry](geometry) and [scorers](scorers).

What the mode still does, verified on a bundled scorer example:

- `prompt -g model.gdml -n <events> -s <seed>` seeds the RNG, loads the geometry, and takes
  the gun from the GDML `PrimaryGun` userinfo block if present (otherwise a small default
  isotropic gun is substituted with a console notice). Bare file names are looked up in the
  installation's bundled `gdml/` directory.
- `-v` opens the raw trajectory viewer; the mesh options `-b/-m/-d/--nSeg` belong to this
  viewer only. Note this GDML `-v` branch is currently broken outright (a `TypeError`, not a
  display problem) — [visualization](visualization) documents the failure and the working
  Python-API viewing paths.
- There is **no Python-API result layer**: no auto-generated options, no scorer registry,
  no `.h5`. Disk output is on by default and each scorer writes
  `<name>_seed<seed>.mcpl.gz` (a histogram inside an MCPL container) plus a ready-made
  `<name>_view.py` reload template — e.g. `-n 10 -s 1` on the bundled TOF example produced
  `ScorerTOF_detector_seed1.mcpl.gz` and `ScorerTOF_detector_view.py`. Reading those files
  back is covered on [results-analysis](results-analysis).

---

## 5. `ptplot`: plotting result files

`ptplot` loads the `<scorer>.h5` files written by `save_all_scorers()` (or by
`hist.save(...)`) and renders them — 1D as errorbar curves, 2D as a colour map. The data
model inside the files is described on [results-analysis](results-analysis); here we stick
to the command line.

### 5.1 Worked example

Two runs of the section-2 script, differing only in wavelength, then a plot of each
(measured October 2026; 2000 events, seed 4096, single process). `ptplot` never creates
the output directory — create it first, or the save fails (section 5.2):

```bash
prompt -g ge_slab.py --gun BeamGun -n 2000 -s 4096               # writes TOF.h5
mkdir -p figures
ptplot TOF.h5 --no-show -o figures/                               # figures/TOF.png
```

```text
Loading HDF5 file: TOF.h5
Histogram type dataset: ScorerTOF
Successfully created CinemaXY object for TOF.h5
Data shape: (100,)
X coordinate range: [0.000, 0.040]
...
Statistics for TOF.h5:
  Data points: 100
  Curve integral: 33.000000
Successfully processed 1/1 file groups
```

The integral is the sum of the bin weights — here the 33 neutrons absorbed in the crystal
out of 2000 primaries (`TOFHelper("TOF", ptstate='ABSORB')`, so bin weights count absorbed
neutrons). The same run with `--wl_mean 2.0` gave an integral of 61: twice the wavelength,
roughly twice the absorption — a useful sanity anchor for `1/v` absorbers.

Combining curves uses `+` between file patterns; each group of files becomes one figure
(the first curve is drawn dimmed):

```bash
ptplot run1/TOF.h5+run2/TOF.h5 --no-show -o figures/   # one combined figure
ptplot run1/TOF.h5 run2/TOF.h5 --no-show               # two separate windows
```

```text
Integrals for combined plot TOF+TOF:
  TOF.h5: 33.00
  TOF.h5: 61.00
```

### 5.2 Options

| Option | Meaning |
|---|---|
| positional args | file names, shell globs, or `a.h5+b.h5` groups. One figure per argument; a multi-file argument (glob or `+`) produces one combined figure. `.h5`/`.mcpl`/`.mcpl.gz` are dispatched by extension. |
| `-o, --output` | a directory — which **must already exist** (one PNG per figure, named after the file) — or a file path (for a single/combined figure). A non-existent path is treated as a file path, so a missing directory fails the save with `[Errno 2] No such file or directory: 'figures/.png'`; `mkdir -p` it first. Without `-o`, figures are only shown on screen. |
| `--no-show` | headless mode — save only, never open windows. |
| `-d, --downbinning` | repeatable (`-dd` = twice): pair-sums the bins of the **rendered curve** to smooth it. The printed statistics and the curve label still refer to the original binning. |
| `--ylin` | linear y-axis (the default is logarithmic). |
| `-s, --show` | print the catalogue of accepted MCPL parameters and units (e.g. `para=time;unit=ms`), then exit. argparse still demands a positional argument, so pass a dummy: `ptplot x.h5 -s` — the file is not read. |
| `--debug` | re-raise the exception instead of the one-line error message. |

### 5.3 MCPL input mode

1D spectra can be histogrammed directly from MCPL particle files with a config-string
argument (`;`-separated); globs work inside it, so multi-process files merge into one
figure:

```bash
ptplot "det_scat_*_pro0.mcpl;para=scattering_angle;unit=deg;binmin=0;binmax=180;binnum=1800;incident_params=[incident_wavelength_A=4]"
```

`para` accepts direct MCPL quantities (`time`, `ekin`, `x` ... `uz`) and calculated ones
(`momentum_transfer_q`, `energy_transfer_omega`, `scattering_angle`, `wavelength`,
`velocity`); the calculated ones need `incident_params=[...]` with the incident energy or
wavelength. `ptplot x.h5 -s` lists every accepted `para`/`unit` pair. Bin bounds default
to `auto` (pre-scanned from the file). The `;` mechanism is for MCPL files only — an `.h5`
name containing `;` is rejected. On failure `ptplot` prints `Processing failed!` and exits
with code 1.

---

## 6. Known sharp edges

1. **List constructor parameters now parse as literals — previously a SIGABRT with no
   traceback.** Older releases attached a literal-parsing conversion only when the hint
   was exactly `list`, so `Optional[list] = None` (or a list parameter with **no
   annotation at all**) went unparsed: with an override, the raw *string* reached the gun
   and its first character was used (`ptstod failed to convert a double from the input
   string [`); left at the `None` default, the source/slit keys went missing
   (`Prompt::Error::BadInput: cfg is missing the key "src_w"`). Both were uncatchable C++
   aborts (exit code 134). Fixed: `Optional[list]`, `list | None` and un-annotated
   list/dict parameters (the kind is inferred from the default value) now parse
   `--opt "[1, 2, 3]"` as Python literals, and a malformed literal fails cleanly (argparse reports
   `argument --opt: invalid literal ...` with usage and exit 2; the `--opt expects a
   list, got ...` wording appears when the parser layer is bypassed) instead of aborting. The old advice to annotate
   exactly `list` with explicit non-`None` defaults is no longer needed — the
   section-2.1 script style still works unchanged.
2. **`bool`-annotated constructor parameters now work as `--param`/`--no-param` switches.**
   An older release passed a `type=` keyword into the `store_true`/`store_false` actions,
   which argparse rejects (`_StoreTrueAction.__init__() got an unexpected keyword
   argument 'type'`), so any script containing a `bool` hint failed before parsing —
   verified on the supported Python (3.10). Fixed: the flag actions are built without
   `type`, so `bool` parameters (including the `--no-param` variant for `= True` defaults)
   can be used directly instead of the former `int` (0/1) or `str` workaround.
3. **`--debug` prints tracebacks for Python exceptions only.** By default any exception
   prints one line (`PromptCLI Error: <message>`), the help text, and exits 1; with
   `--debug` the full traceback is printed — including errors raised while importing your
   script. It cannot help with hard C++ aborts (e.g. raised inside the transport kernel):
   those kill the process before Python can intervene. Debug by running the script
   directly with `python3`.
4. **`-v` and output saving work best with `PromptMPI`.** The CLI calls
   `sim.show(gun, n, zscale=...)` — the axis-scaling keywords exist on both `Prompt.show`
   and `PromptMPI.show` now — but it ends with `sim.save_all_scorers()`, and that method
   references `self.rank`, which plain `Prompt` does not define: derive from `PromptMPI`
   (verified: a `Prompt`-based class exits 1 with `AttributeError` once a scorer exists).
5. **The CLI never runs `__main__`, and module-level world building silently freezes the
   seed** (section 2.4). Call `makeWorld()` from the constructor, exactly once.
6. **Gun classes must be defined in the script** — imported built-ins are invisible
   (`No class 'Gun' is defined.`). Wrap them: `class BeamGun(UniModeratorGun)`.
7. **Avoid constructor parameter names that collide with built-in options** (`seed`,
   `neutronNum`, `visualize`, `zscale`, `blacklist`, `mergemesh`, `dumpmesh`, `nSegments`,
   `geo`, `debug`): no `--option` is generated for them and the general flag value is
   forwarded instead — a `debug` parameter silently receives the `--debug` value, a `geo`
   parameter the script path. `seed` is the one intended collision.
8. **ptplot labels curves by file base name.** Combining `run1/TOF.h5` with
   `run2/TOF.h5` prints two indistinguishable `TOF.h5` entries (verified above). Rename or
   move files before combining if the labels matter.

---

## Where to go next

- [Your first simulation](first-simulation) — the script that the CLI introspects.
- [Simulation lifecycle](simulation-lifecycle) — what `simulate`/`save_all_scorers` do
  under the hood; seeds and MPI semantics.
- [Results analysis](results-analysis) — the `.h5` and MCPL data models behind `ptplot`,
  and the in-Python analysis route.
- [Guns](guns) — the gun classes that `--gun` selects from.
- [Visualization](visualization) — the `show()` options the CLI does not expose.

---

*Source files:
[`promptcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/promptcli.py),
[`ptplotcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/ptplotcli.py).
Questions: cinema-users@outlook.com.*
