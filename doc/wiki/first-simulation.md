# Your first simulation

This page walks through a complete, minimal Cinema/Prompt simulation: a Germanium
single-crystal slab hit by a 1 Å neutron beam, with a time-of-flight scorer on the
neutrons that are absorbed in the crystal. It is the spine tutorial of this wiki —
every other tutorial and reference page builds on the pattern shown here.

This page documents **Cinema 2.0.0a5** and was checked against the
repository [doc/example_basic.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py).
Measured runtimes were taken on the machine used to prepare this wiki (October 2026);
conditions (event count, seed) are stated with every number.

> **The one rule:** the Python API shown here (`Cinema.Prompt`, a `Simulation`
> subclass, `Material`/`Volume`/scorers/guns) is the supported path. The old
> GDML file input is legacy and is not covered in this tutorial.

Before starting, [install](install) Cinema and source the environment once per shell
from the root of your checkout:

```bash
. <cinema-checkout>/env.sh
```

On the recommended conda-package route (`conda install csns::cinema-prompt`) there is
no checkout and no `env.sh`: activate the env, save the section-2 listing below as
e.g. `my_first_sim.py`, and run it with `python3 my_first_sim.py` — the rest of this
page applies unchanged.

---

## 1. The five-step pattern

Every Cinema/Prompt script, from a 30-line test to a full beamline model, follows the
same five steps:

| Step | What you write | Why |
|---|---|---|
| 1. Subclass the engine | `class Simulation(PromptMPI):` (or `Prompt` for serial-only work), with `super().__init__(seed)` | `PromptMPI` adds MPI rank/size handling and rank-0-gathered results; the constructor seed makes runs reproducible |
| 2. Build the world in `makeWorld()` | `Material`, `Volume`, shape solids, scorer helpers, then `self.setWorld(world)` | `makeWorld` is abstract on the base class; `setWorld` closes the geometry and applies the random seed |
| 3. Make a gun | `UniModeratorGun()` (or another built-in gun, a gun config string, or a custom `PythonGun`) | the primary generator: position, direction and energy spectrum of every neutron |
| 4. Look before you leap | `sim.show(gun, 100)` | interactive 3D check of geometry plus 100 trajectories before burning production time |
| 5. Run and read out | `sim.simulate(gun, n)`, then `sim.gatherHistData('name')` and/or `sim.save_all_scorers()` | transport `n` primaries and retrieve the scorer histograms by name |

Two things to internalise early:

- **`setWorld` may be called once per process.** A second call without `sim.clear()`
  in between raises the catchable `RuntimeError: World exist already: only one world can
  be set per process` — and since the `Launcher` is a process singleton shared by every
  `Prompt` instance, constructing a second `Simulation()` in the same process trips the
  same error. To rebuild (parameter scans, tests),
  call `sim.clear()` first.
- **The seed is applied in `setWorld`**, not in `simulate()`. Under MPI every rank
  automatically uses `seed + rank`, so streams never overlap.

---

## 2. Line by line: `doc/example_basic.py`

The full example (also in the repository:
[doc/example_basic.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py)):

```python
#!/usr/bin/env python3

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class Simulation(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)

    def makeWorld(self):

        # material defined in NCrystal configstring
        nccfg = 'Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'
        mat = Material(nccfg)

        # volume defined with shape, size and material
        vol = Volume("sampleSolid",Box(10,10,1),matCfg=mat.cfg)

        # TOF scorer/counter,
        tof = TOFHelper("TOF",ptstate='ABSORB')
        # make vol capable to score neutron absorbed by real physcis channel
        tof.make(vol)

        # coordinate transformation in simulation world
        trf = Transformation3D(0,0, 100).applyRotX(45)

        # volume representing the simulation world,
        world = Volume("world", Box(50, 50, 210))
        # volume location and transformation in simulation world
        world.placeChild("samplePhyVol",vol, transf=trf)
        # assign the simulation world
        self.setWorld(world)

if __name__ == "__main__":
    # gun, beamline
    gun = UniModeratorGun()
    gun.setSource([10,10,-200])
    gun.setSlit([5,5,-20])

    # initialize
    sim = Simulation()
    sim.makeWorld()

    # to visualize
    sim.show(gun,100)
    # or to run in production
    # sim.simulate(gun,1e7)
```

### 2.1 The simulation class and the seed

```python
class Simulation(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)
```

Subclassing is how you tell the engine which world to build. `PromptMPI.__init__(seed)`
stores the RNG seed (default `4096`) and grabs `MPI.COMM_WORLD`; on an `mpirun` launch
each rank silently uses `seed + rank`. The seed drives the C++ random stream *and*
NCrystal's sampling, so the same seed reproduces the same histogram bit for bit.

### 2.2 The material: an oriented Ge single crystal

```python
nccfg = 'Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'
mat = Material(nccfg)
```

One NCrystal config string defines the whole material physics:

- `Ge_sg227.ncmat` — comes with NCrystal's built-in data, so it resolves out of the
  box; files placed in the repo's `ncmat/` directory (exposed via `NCRYSTAL_DATA_PATH`,
  e.g. `B4C.ncmat`, `sascsns_sio2_spheres.ncmat`) resolve alongside it;
- `mos=0.0267deg` — mosaic spread FWHM, i.e. this is a single crystal with slightly
  misoriented domains (Bragg diffraction physics);
- `dir1`/`dir2` — pin two crystallographic planes to lab directions
  (`@crys_hkl:5,1,1` along lab `0,0,1`, `@crys_hkl:0,1,-1` along lab `1,0,0`), which
  fully fixes the crystal orientation. From here on the cross section depends on the
  neutron's flight direction.

`Material(...)` wraps the string so the engine sees
`physics=ncrystal;nccfg='...'`. **Always wrap**: passing a raw NCrystal string that
contains `key=value` parts directly as a volume's `matCfg` fails with
`BadInput: physics keyword is not defined`. `mat.cfg` gives the wrapped string —
that is all `Volume` needs. See [Materials and physics](materials-physics) for the
full config-string anatomy.

### 2.3 The sample volume

```python
vol = Volume("sampleSolid", Box(10,10,1), matCfg=mat.cfg)
```

A `Volume` is a *logical* volume: a shape + material, with **no position yet**.
`Box(10,10,1)` takes **half**-lengths in mm, so the slab is 20 x 20 x 2 mm.
The name `"sampleSolid"` shows up in visualisation and output files.

### 2.4 The TOF scorer

```python
tof = TOFHelper("TOF", ptstate='ABSORB')
tof.make(vol)
```

Scorers are created as *helpers* and attached to a volume with `.make(vol)`.
The constructor signature is
`TOFHelper(name, min=0.0, max=0.04, numbin=100, pdg=2112, ptstate='ENTRY', groupID=0)`:

- the scorer is named `"TOF"` — you will retrieve the histogram by exactly this name;
- default binning is 100 linear bins over 0–0.04 s of time-of-flight;
- `ptstate='ABSORB'` scores at absorption events: every neutron really killed by the
  material's absorption physics (here NCrystal capture in Ge) fills the histogram with
  its time of flight.

The full catalogue of scorers and their trigger states lives in [Scoring](scorers).
Scorer names must be unique — duplicates silently alias in the scorer registry.

### 2.5 Placing the sample: `Transformation3D`

```python
trf = Transformation3D(0,0, 100).applyRotX(45)
```

`Transformation3D(x, y, z)` starts as a translation in mm; `applyRotX(45)` rotates
45 degrees (the API is degree-based) about x and returns the object, so calls chain.
`placeChild` then interprets the transformation as **child-local coordinates mapped
into the parent frame** — the slab centre sits at `z = +100 mm` in the world and is
tilted 45° about x. More rotation tools (`applyRotY/Z`, `from_euler_xyz`,
`setRotByAlignement`, ...) are covered in [Geometry](geometry).

### 2.6 The world volume

```python
world = Volume("world", Box(50, 50, 210))
world.placeChild("samplePhyVol", vol, transf=trf)
self.setWorld(world)
```

Any volume can be the world; a `Box` comfortably larger than everything else is the
convention. Note there is **no `matCfg`** here: the default material is a dilute
hydrogen gas (`freegas::H1/1e-26kgm3/H_is_1_H1`) that acts as near-vacuum — it is
*not* true void (that would be `'void.ncmat'`). See
[Materials and physics](materials-physics).

`placeChild` gives the placement its physical-volume name (`"samplePhyVol"`).
Finally `self.setWorld(world)` closes the geometry — after this call no further
volumes may be created in this process without `sim.clear()`.

### 2.7 The gun

```python
gun = UniModeratorGun()
gun.setSource([10,10,-200])
gun.setSlit([5,5,-20])
```

`UniModeratorGun` emits neutrons with wavelengths uniform in
`[wl_mean − wl_range/2, wl_mean + wl_range/2]` — `wl_range` is the **full width** of the
band — with defaults `wl_mean=1.0` Å and `wl_range=0.0001` Å, a quasi-monoenergetic
1 Å beam. `setSource([w, h, z])` defines a 10 x 10 mm emitting
rectangle at `z = -200 mm`; `setSlit([w, h, z])` a 5 x 5 mm collimator slit at
`z = -20 mm`. The beam then flies along **+z** into the tilted slab at `z = +100 mm`.
All gun variants and their parameters are catalogued on [Particle guns](guns).

### 2.8 What you should see on the console

A successful run prints, among progress output, lines like:

```text
pt_Volume_new sampleSolid, vol id 0
Configuring physics model: physics=ncrystal;nccfg='Ge_sg227.ncmat;...'
Added ABSORB type scorer: ScorerTOF_TOF
samplePhyVol Group ID 0
set random seed: 4096
```

If instead the run aborts with `NCrystal::Error::BadInput` right after a
`Configuring physics model` line, check the `NCRYSTAL_PLUGIN_LIST` environment
variable for a stray trailing semicolon — the remedy is described on
[Install](install).

---

## 3. Three ways to run

| Way | Command | Good for |
|---|---|---|
| Direct Python | `python3 doc/example_basic.py` | development, debugging, interactive `show()` |
| `prompt` CLI, Python mode | `prompt -g my_first_sim.py --gun BeamGun -n 1000000` | running a script as a configurable command-line tool |
| MPI | `mpirun -n 4 python3 doc/example_basic.py` | production statistics on one machine or a cluster (needs a script with a `__main__` block — the CLI-mode `my_first_sim.py` of §3.2 simulates nothing under `mpirun`, see §3.3) |

### 3.1 Directly with python3

```bash
. <cinema-checkout>/env.sh
python3 doc/example_basic.py
```

Conda users: skip the `env.sh` line — `doc/example_basic.py` only exists in a
checkout, so run the script saved in the intro step instead (`python3
my_first_sim.py`).

The script's `if __name__ == "__main__"` block runs, `show()` opens the interactive
viewer, and the `simulate` line is commented out. For a first production run, swap the
comment between the two lines. Debugging is the same as any Python program — run the
script and read the traceback.

### 3.2 The `prompt` CLI (Python mode)

The `prompt` command introspects a `.py` script and auto-generates command-line
options from the constructor type hints of the classes defined in it. Because the
CLI **imports the module and instantiates the classes itself** (it never runs
`__main__`), a CLI-ready script needs three adjustments to the example:

1. a `Gun` subclass must be **defined in the script** (an imported gun class does not
   count — the CLI reports `No class 'Gun' is defined.`);
2. `makeWorld()` must already have run when the CLI instantiates the simulation class
   — call it from the constructor (and *only* there; a second, module-level build
   makes `setWorld` run twice and raises `RuntimeError: World exist already`);
3. constructor parameters need explicit type hints — one `--<param>` option is
   generated per parameter. Annotate list parameters as plain `list` with a
   non-`None` default (an annotation like `src_whz: list = None` degrades to
   `Optional[list]`, the value then arrives unconverted and the gun aborts with
   `BadInput`).

A minimal CLI-ready version of the tutorial (`my_first_sim.py`), verified end to end:

```python
#!/usr/bin/env python3
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class GeSlabSim(PromptMPI):
    """Ge single-crystal slab with an absorption TOF scorer."""
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

Run it (1000 events were used to verify this page; use real statistics in practice):

```bash
prompt -g my_first_sim.py --gun BeamGun -n 1000 -s 4096
# or override any annotated parameter:
prompt -g my_first_sim.py --gun BeamGun --wl_mean 2.0 -n 1000000
```

Notes on the CLI:

- `--gun <ClassName>` is mandatory; `-n/--neutronNum` (default 100) is the number of
  primaries, `-s/--seed` (default 4096) the seed.
- `prompt -g my_first_sim.py -h` lists the generated options per class.
- After `simulate` the CLI calls `sim.save_all_scorers()` for you, so the run leaves
  one `<scorer>.h5` file per scorer (`TOF.h5` here) in the working directory.
- `-v` shows geometry plus `-n` trajectories instead of simulating.
- If something goes wrong, debug by running the script directly — the CLI's
  `--debug` flag currently does not print tracebacks.

### 3.3 MPI with mpirun

```bash
mpirun -n 4 python3 doc/example_basic.py
```

Any script works as long as it subclasses `PromptMPI` **and** actually instantiates the
simulation and calls `simulate` when executed. `doc/example_basic.py` qualifies — via
its `if __name__ == "__main__"` block, after swapping the commented `show()`/`simulate`
lines (a batch run must not call `show()`). The CLI-mode `my_first_sim.py` of §3.2 has
no `__main__` block: run directly or under `mpirun` it imports, instantiates nothing
and exits silently with code 0, simulating nothing. The MPI semantics are all automatic:

- events are split across ranks, with rank 0 carrying the remainder, so the total is
  exactly `n`;
- each rank runs with `seed + rank` — independent streams by construction;
- `sim.gatherHistData(...)` is a collective call: **every rank must call it** (same
  order); the histogram sums all ranks and is complete on rank 0 only;
- rank 0 is also the only rank that renders `show()` or writes files — gate any
  plotting/saving with `if sim.rank == 0:`.

For batch runs, remove the `show()` call. More on scaling and multi-seed production
in [Running at scale](mpi-scale).

---

## 4. Look before you leap: `sim.show(gun, 100)`

```python
sim.show(gun, 100)
```

`show` opens an interactive pyvista window with the geometry meshed and — for
`num > 0` — overlays the trajectories of `num` events, which it obtains by
re-simulating those events with trajectory recording. This is the cheap mistake
catcher: a misplaced slab, a slit that clips the whole beam, or a world that is too
small are all obvious in five seconds.

While the window is open:

- click a mesh to print the volume/material names;
- `s` saves `screenshot.svg`, `m` hides the picked volume, `u` unmasks all, `r`
  reloads;
- the default camera is `view_zy` (z vertical, looking along x) — matching the +z
  beam-axis convention.

Caveats: colours are chosen randomly per volume, so two runs look different; `show`
needs an interactive display and must not be used in batch scripts or CI; under MPI
only rank 0 renders (other ranks wait at a barrier).

---

## 5. The production run

Replace the `show` line with:

```python
sim.simulate(gun, 1e7)                 # transport 1e7 primaries
hist = sim.gatherHistData('TOF')       # fetch the histogram by scorer name
sim.save_all_scorers()                 # one <scorer>.h5 per scorer (rank 0)
hist.savefig('tof.png')                # quick matplotlib export (see caveat below)
```

- `simulate(gun, num)` runs the transport loop; a progress monitor is printed.
  Results stay in memory unless you ask for files (the Python API default is
  `save2Disk=False`).
- `gatherHistData('TOF')` returns the `Hist1D` for the scorer registered under that
  exact name. Under MPI it is collective and complete on rank 0 only (the console
  prints each rank's weight/hit sums).
- `hist.savefig('tof.png')` writes a matplotlib figure of the histogram
  (`savefig(fname, title='Histogram', log=False)`). Caveat: on current builds
  `savefig` raises `AttributeError ... 'close'` after the PNG is written and — unless
  caught — ends the script right there; that is why `save_all_scorers()` above runs
  before it (verified for this page).
- `save_all_scorers()` writes `<scorername>.h5` per scorer on rank 0 (add
  `savepdf=True` for PDFs as well). It is `PromptMPI`-only — it references `self.rank`,
  which plain `Prompt` does not define (AttributeError); on plain `Prompt`, save each
  histogram with `hist.save('name.h5')` instead. The `.h5` files are what the `ptplot` tool plots
  and what the analysis tooling reads back — see [Analysing results](results-analysis).

**Measured timing** (this example unchanged, single process, seed 4096, October 2026
on the machine used to prepare this wiki):

| Run | Transport time |
|---|---|
| 1e5 events | ~0.4 s (whole process ~3 s including start-up) |
| 1e7 events | ~40 s (transport; scales linearly from the 1e5 measurement) |

Start-up (loading the C++ core, building NCrystal models) dominates for small runs —
do not judge performance from a 1000-event run.

**Sanity anchor:** with 1e5 events, seed 4096, one process, the `"TOF"` histogram
reports weight = hit = **1583** absorbed neutrons. If you are in that ballpark (it
shifts with MPI event partitioning), your example is running correctly.

---

## 6. Conventions you must know

| Quantity | Unit | Where you meet it |
|---|---|---|
| Length | mm | shape half-sizes (`Box(10,10,1)`), positions (`setSource([10,10,-200])`), `Transformation3D` translation |
| Angle | degree | `applyRotX(45)`, mosaic spread `mos=0.0267deg` |
| Energy | eV | gun energy parameters |
| Wavelength | Å | `UniModeratorGun` `wl_mean`/`wl_range` |
| Time | s | TOF histograms |
| Temperature | K | material config strings (e.g. `T293.6K`) |

- **The beam axis is +z.** Sources sit at negative z, samples and detectors at
  positive z; the code's own examples place a detector "1 m downstream" as
  `Transformation3D(0, 0, 1000)`.
- Box (and most other solid) dimensions are **half**-sizes, not full sizes.
- Cross sections are handled internally in barn and number densities in atoms/mm³ —
  invisible at the API level, but good to know when reading the physics pages.

---

## 7. Where to go next

You have now touched every pillar of the API. Deepen each one:

- [Geometry](geometry) — all solids, nesting, the full `Transformation3D` cookbook.
- [Materials and physics](materials-physics) — NCrystal config strings, virtual
  materials, biasing, surface physics.
- [Scoring](scorers) — the scorer catalogue, trigger states, per-placement grouping.
- [Simulation lifecycle](simulation-lifecycle) — seeds, MPI semantics, output files,
  `clear()`-and-rebuild for parameter scans.

- [Particle guns](guns) — all primary generators in detail.
- [Analysing results](results-analysis) — histograms, MCPL files, `ptplot`, error propagation.
- [Visualisation](visualization) — the `show()` options and the `Mesh` iterator.
- [Running at scale](mpi-scale) — MPI, multi-seed production and merging.
- [SANS with the SasCSNS plugin](tutorial-sans) — the next tutorial, with the SasCSNS NCrystal plugin.

Questions or problems: write to cinema-users@outlook.com.
