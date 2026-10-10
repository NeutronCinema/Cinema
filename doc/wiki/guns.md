# Particle guns

The gun is the primary generator: for every simulated event it produces one neutron with a
position, direction, energy, emission time and weight. `show(gun, n)` and `simulate(gun, n)`
accept three gun forms:

1. a **gun object** with a `.cfg` string (all built-in guns, section 1 and 2);
2. a **raw config string**, e.g. `"gun=SimpleThermalGun;position=0,0,-100;direction=0,0,1;energy=1e-3"`
   (keep the position **inside the world volume** — primaries born outside it are dropped
   before tracking with one `particle at {...} is outside the world` stdout line each; see
   [geometry](geometry), world-assembly rule 5);
3. a **`PythonGun`** — a user subclass that samples particles in numpy (section 4).

This page documents **Cinema 2.0.0a5**. Every default below was checked by introspection, and
every measured number was produced for this wiki (October 2026, seed 4096, single process,
200000 events unless stated otherwise, neutrons scored at `ptstate='ENTRY'` on a small
detector volume in a near-void world). Source of truth:
[`src/python/Cinema/Prompt/gun.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/gun.py)
on the Python side and the gun factory in `src/cxx/Gun/` on the C++ side.

---

## 1. Built-in guns

| Python class | `gun=` id | Parameters (defaults) | What it emits |
|---|---|---|---|
| `SimpleThermalGun` | `SimpleThermalGun` | `position` (default `0,0,0.`), `energy` (default `0`, **eV**), `direction` (default `0,0,1.`) | Point source, fixed direction. `energy > 0`: monoenergetic. `energy = 0`: **not zero energy** — a built-in thermal spectrum (see below) |
| `IsotropicGun` | `IsotropicGun` | `position` (default `0,0,0.`), `energy` (default `0`, **eV**) | Point source, directions uniform on the full sphere; same `energy = 0` thermal-spectrum behaviour |
| `UniModeratorGun` | `UniModeratorGun` | `src_w, src_h, src_z`, `slit_w, slit_h, slit_z` (all mandatory, **mm**), `mean_wl`/`range_wl` (defaults `1.0`/`0.0001` **Å**; these are the config-string keys — the constructor arguments and `setWlMean`/`setWlRange` spell them `wl_mean`/`wl_range`, which is also what `prompt -g` introspection generates, e.g. `--wl_mean`) | Rectangle source collimated onto a slit, wavelengths uniform in `[mean − range/2, mean + range/2]` (see gotcha 2) |
| `MaxwellianGun` | `MaxwellianGun` | same six source/slit parameters (mandatory), `temperature` (default `293.15` **K**) | Rectangle source + slit, Maxwell flux spectrum `φ(E) ∝ E·exp(−E/k_BT)` — mean energy `2k_BT` |
| `MPIGun` | `MPIGun` | the six source/slit parameters (mandatory), nothing else | Rectangle source + slit with a **hardcoded** moderator energy spectrum (inverse-CDF table spanning ~0.003–4.5·10³ eV baked into the library). Despite the name it has no connection to MPI parallelism |
| `SANSGun` | `SANSGun` | the six source/slit parameters (mandatory), nothing else | Rectangle source + slit with a **hardcoded** wavelength spectrum (0.18–4.37 Å inverse-CDF table; the source file records no provenance for the data). Despite the name, the SasCSNS SANS tutorial does **not** use this gun — its beam is currently monoenergetic (see [tutorial-sans](tutorial-sans)) |
| `MCPLGun` | `MCPLGun` | `mcplfile` (mandatory) | Replays particles from an MCPL file, or samples a KDSource phase-space model from a `.xml` file (section 5) |
| `PythonGun` | — (not a config-string gun) | `pdg` (default `2112`), `vectorized` (default `1`) | Whatever you sample, in numpy (section 4) |

All guns emit **neutrons** (`pdg` 2112), one particle per event, weight 1 and emission time 0
unless stated otherwise.

### Source-and-slit geometry

`UniModeratorGun`, `MaxwellianGun`, `MPIGun` and `SANSGun` share the same emission geometry
(`SurfaceSource` on the Python side):

- the particle is born at a point uniform over a `src_w × src_h` rectangle centred on the z axis
  at `z = src_z` — the `w`/`h` values are **full widths** (the rectangle spans `±w/2`, `±h/2`),
  unlike solid shapes where dimensions are half-sizes;
- the direction points from the source point to a point uniform over the `slit_w × slit_h`
  rectangle at `z = slit_z`: the slit is the collimator that defines the beam divergence;
- all lengths are mm; both rectangles are centred on the z axis, so the beam axis is **+z**.

Measured divergence (50000 events, seed 4096; source plane at `src_z = -10`, 5 mm slit at
`z = 10`, x-RMS scored on a screen at `z = 100 mm`): a 10 mm wide source gives an x-RMS of
15.2 mm; the same source with `slit_z = 1e99` gives 2.89 mm — the source-size-limited
parallel beam of gotcha 6 (`10 mm/√12 = 2.89 mm`). State `src_z` when quoting divergence:
with the source at the origin the same slit gives ~30 mm, because the divergence scales with
the source–slit distance.

### Energy spectra

- **`SimpleThermalGun` / `IsotropicGun`, `energy = 0`** (the default): the C++ gun samples
  `E = 0.0253 eV · (−ln r₁ − ln r₂·cos²(π r₃/2))` — a fixed built-in thermal spectrum,
  independent of any temperature parameter. Measured mean energy 0.0380 eV (= 1.5 × 0.0253).
  With `energy > 0` every neutron has exactly that energy (eV); measured: `energy=0.0253`
  puts all 200000 events in a single 0.1 meV bin.
- **`UniModeratorGun`**: wavelengths uniform in Å over a band of **full width `range_wl`**
  centred on `mean_wl`, converted to energy afterwards (so the energy distribution is *not*
  uniform). Measured with `mean_wl=2.0; range_wl=0.5`: observed wavelengths span exactly
  [1.7500, 2.2500] Å, mean 1.9999 Å, no under/overflow.
- **`MaxwellianGun`**: energy distributed as the Maxwell flux spectrum
  `φ(E) ∝ E·exp(−E/k_BT)` (mean `2k_BT`, most probable `k_BT`); the temperature default
  293.15 K corresponds to `k_BT = 25.3 meV`, i.e. mean 50.5 meV. Measured mean 0.0512 eV over
  a 5 meV–0.5 eV scoring window (the spectrum's low-energy tail below the window falls to
  underflow). The sampler is `λ = λ_T/√(−ln r₁r₂)` with `λ_T = 1.7995 Å` at 293.15 K —
  listed here because the wavelength detour makes the distribution look exotic in source
  readers; in energy it is the plain Maxwell spectrum.
- **`MPIGun` / `SANSGun`**: fixed tabulated spectra sampled by inverse CDF
  (`PointwiseDist` percentile). They take no spectrum parameters — to change the spectrum,
  use another gun or a `PythonGun`.

> **Legacy notice.** Guns can also be defined inside GDML geometry files
> (`prompt -g file.gdml`, `<auxiliary auxtype="PrimaryGun" auxvalue="gun=..."/>`). That is
> legacy v1 functionality; define guns in Python as on this page.

---

## 2. Object API vs config strings

Every built-in gun is a `ConfigString` (a dict whose `cfg_`-prefixed attributes become
`key=value;` pairs). `simulate` and `show` simply pass `gun.cfg` to the C++ gun factory, so
these two are equivalent:

```python
from Cinema.Prompt.gun import MaxwellianGun

# object form
gun = MaxwellianGun()
gun.setSource([2, 2, -100])    # [w, h, z] in mm
gun.setSlit([2, 2, 1e99])
gun.setTemperature(293.15)
sim.simulate(gun, 1e5)

# string form — the same factory call
gunCfg = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;" \
         "slit_w=2;slit_h=2;slit_z=1e99;temperature=293.15;"
sim.simulate(gunCfg, 1e5)
```

The setters are thin wrappers over dict entries (`setWlMean`, `setWlRange`, `setTemperature`,
`setPosition`, `setEnergy`, `setWavelength`, `setDirection`, `setMCPLFile`, `setSource`,
`setSlit`). Printing `gun.cfg` shows exactly what the factory will receive, and the factory
echoes the parsed string to the console on every run.

When each form is useful:

- **Object form** for scripts you edit and reuse: attribute access is discoverable
  (`gun.cfg_temperature`), and `show()`/`simulate()` both accept the same object.
- **String form** for one-off runs, tests and parameter scans: the whole source definition is
  one line you can format — `"gun=UniModeratorGun;mean_wl=%f;..." % wl` — without keeping a
  gun object around. `doc/example_sas.py` uses this idiom.

**The `slit_z=1e99` trick.** The flight path is `slit_z − src_z`; setting the slit plane at
`z = 1e99` makes the transverse direction components ~1e−97, i.e. the beam is exactly parallel
to +z regardless of the slit size, while the source rectangle still sets the beam size. This
is the standard way to build a divergence-free beam (verified: the 2.89 mm vs 15.2 mm x-RMS
comparison above).

Two sharp edges of the config-string route:

- **Factory keys are exact.** Each gun accepts a fixed set of keys with exact parameter-count
  checks: a missing mandatory key *or* an unknown extra key aborts the process with
  `Prompt::Error::BadInput` — an uncatchable hard abort, not a Python exception (verified with
  `"gun=UniModeratorGun;mean_wl=2.0;range_wl=0.5;"`: process terminated). A bare
  `UniModeratorGun()` object has no source/slit keys yet, so `simulate(UniModeratorGun(), ...)`
  aborts the same way — always call `setSource`/`setSlit` (or pass `src_whz`/`slit_whz`).
- **Energy and wavelength setters write the same key.** `IsotropicGun.setEnergy(e)` and
  `IsotropicGun.setWavelength(wl)` both set `cfg_energy` — `setWavelength` just converts with
  `wl2ekin` (1 Å = 0.0818 eV). The **last setter called wins**; there is no separate
  wavelength field.

---

## 3. Runtime selection with the `prompt` CLI

The [CLI](cli) can select and parameterise a gun at runtime from a script:

```bash
prompt -g my_sim.py --gun BeamGun -n 1000000 -s 42
prompt -g my_sim.py -h                        # lists the generated options per class
prompt -g my_sim.py --gun BeamGun --wl_mean 2.0 -n 1000000
mpirun -n 4 prompt -g my_sim.py --gun BeamGun -n 1000000
```

How it works:

- The CLI introspects the classes defined **in the script** and requires at least one `Gun`
  subclass; `--gun <ClassName>` picks which one to instantiate (mandatory to run). Imported
  gun classes do not count — subclass the built-in you want (`class BeamGun(UniModeratorGun)`)
  even if you change nothing.
- One `--<param>` option is generated per constructor parameter from its type hint, with the
  constructor default shown in `--help`; `list`/`dict` parameters are parsed as Python
  literals. **Never annotate a constructor parameter `bool`.** The code intends
  `--param`/`--no-param` switches, but passes `type=bool` to `action='store_true'` as well, so
  argparse raises `_StoreTrueAction.__init__() got an unexpected keyword argument 'type'`
  while the parser is still being built — the CLI dies before any parsing. Use an `int`
  (0/1) or a `str` flag instead; see [cli](cli), section 6 gotcha 2.
- The world must already exist when the CLI instantiates the simulation class — build it in
  the constructor, not under `if __name__ == "__main__":` (the CLI never runs `__main__`).

A complete verified CLI-ready script is in
[first-simulation, section 3.2](first-simulation); the full option reference lives on the
[CLI page](cli).

---

## 4. `PythonGun`: custom numpy-vectorised guns

`PythonGun` replaces the C++ samplers with numpy code you write. Subclass it, override any of
the `sample*` methods, and write into `self.pdata` — a structured array of `vectorized`
particles:

| `pdata` key | Meaning | Default |
|---|---|---|
| `ekin` | kinetic energy, **eV** | `0.0253` |
| `w` | weight | `1.0` |
| `t` | emission time, **s** | `0.0` |
| `pos` | position (x, y, z), **mm** | origin |
| `dir` | direction vector — normalised automatically by `generate()` | `+z` |

The five named fields are a view onto a packed buffer of **9 float64 values per particle**
(`ekin, w, t, pos[3], dir[3]`), which the C++ backend reads at fixed offsets. The dtype is
validated before every push: replacing `pdata` with a different layout raises `ValueError`
("pdata must have the packed float64 layout ...") — keep the field order and types, and do
not override `particle_dtype`.

`PythonGun(pdg=2112, vectorized=1)`: `vectorized` is the batch size. `simulate(gun, num)`
loops `gun.generate()` + one C++ event, `num // vectorized` times, with a tqdm progress bar on
rank 0. The `num % vectorized` tail does **not** reliably reach exactly `num` events — for
array-writing sample methods it crashes the run (gotcha 10); exact totals are guaranteed only
when `num` is a multiple of `vectorized`, or the remainder is 0 or 1.
`generate()` normalises `dir` and raises `RuntimeError('Sampled direction is zero')` for a
zero-length direction; `vectorized < 1` raises `RuntimeError('vectorized must be a positive
integer, got ...')`.

A complete worked example (the exact code measured for this page; all 200000 events reached
the detector, total hits 200000 — 200000 is a multiple of the 1000-event batch, see gotcha 10):

```python
import numpy as np
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box
from Cinema.Prompt.scorer import ESpectrumHelper

class BandGun(PythonGun):
    """Quasi-parallel 10x10 mm source at z=-10, Gaussian 0.0253 eV +- 5%."""
    def __init__(self, base=300, vec=1000):
        super().__init__(vectorized=vec)               # batch of 1000 per generate()
        self.rds = [np.random.RandomState(base + i) for i in range(4)]

    def sampleEnergy(self, n):
        self.pdata['ekin'] = self.rds[0].normal(0.0253, 0.0253 * 0.05, n)

    def sampleDirection(self, n):                      # ~+z with 1 mrad jitter
        d = self.rds[2].normal(0., 1e-3, (n, 3))
        d[:, 2] = 1.0
        self.pdata['dir'] = d                          # generate() normalises

    def samplePosition(self, n):
        p = self.rds[3].rand(n, 3)
        self.pdata['pos'] = np.column_stack(
            [(p[:, 0] - 0.5) * 10., (p[:, 1] - 0.5) * 10., np.full(n, -10.)])
        # weight (w=1) and time (t=0) left at their defaults

class Simulation(Prompt):
    def __init__(self, seed=4096):
        super().__init__(seed)
    def makeWorld(self):
        world = Volume("world", Box(200, 200, 400))
        det = Volume("det", Box(40, 40, 0.1))
        ESpectrumHelper('en', 0.01, 0.05, 100, ptstate='ENTRY', log=False).make(det)
        world.placeChild("detPhy", det, Transformation3D(0, 0, 100))
        self.setWorld(world)

sim = Simulation()
sim.makeWorld()
sim.simulate(BandGun(), 200000)
hist = sim.gatherHistData('en')
```

**Reproducibility guarantees** (all verified for this page):

- `PythonGun` sampling is **not** governed by the C++ simulation seed — the numpy `RandomState`
  objects are yours. Seed one per component (energy, time, direction, position) as above.
- Same `RandomState` seeds + same C++ seed + same `vectorized` + same event count ⇒
  **bit-identical** histograms (checked: two runs with `RandomState(300+i)` produced identical
  hit arrays; `RandomState(900+i)` produced different ones). The C++ seed still controls all
  transport and NCrystal sampling, exactly as on
  [simulation-lifecycle](simulation-lifecycle).
- Under MPI, fixed seeds emit the **same batches on every rank** (verified with
  `mpirun -n 2`: both ranks drew identical first batches). Offset your seeds by rank, e.g.
  `base + 1000 * MPI.COMM_WORLD.Get_rank() + i`, or the ranks only resample each other's
  primaries. See [mpi-scale](mpi-scale).
- `save2Disk=True` is **silently ignored** for a `PythonGun` (the C++ end-of-run dump is not
  reached) — save with `save_all_scorers()` or `hist.save(...)` instead
  ([results-analysis](results-analysis)).

---

## 5. `MCPLGun`: starting from an MCPL file

```python
sim.simulate("gun=MCPLGun;mcplfile=source.mcpl.gz;", 1000000)
```

- Particles are read from the file **in file order**, converted from MCPL units to Prompt
  internal units — the file stores position **cm**, kinetic energy **MeV**, time **ms** — and
  the particle's weight and direction come from the file. The path is checked when it is set:
  a missing file raises a normal Python `FileNotFoundError('MCPL input file not found: ...')`
  (from the object API's `setMCPLFile`) instead of a bare C-side MCPL error.
- When the file is exhausted it is **rewound and cycled**, so the event count is not limited
  by the file size. Verified for this page: a 7-particle file with weight 2.0 simulated for
  17 events scored total weight 34.0 and mean energy 0.0254 eV, matching the 0.0253 eV
  particles written into the file.
- The file must contain **neutrons**: a particle whose PDG code differs from the gun's
  (2112) aborts the run.
- Files ending in **`.xml`** are not read as particle lists but opened as KDSource
  phase-space models, sampled with weight-critical resampling. Note that this mode seeds its
  RNG from the wall clock (`srand(time)`) — runs are **not reproducible** via the simulation
  seed in this mode (known defect; the `.mcpl` mode is fully reproducible).

MCPL output — writing particle records at the other end of a simulation — is covered on
[scorers](scorers) (`MCPLOutHelper`) and [results-analysis](results-analysis) (`PTMCPL`,
`PromptFileReader`): the standard pattern is to dump particles at a surface with one run and
feed the file back as a gun source for the next stage of the instrument. Mind the unit
convention when crossing tools: Cinema's own files store internal units (eV/s/mm) while
`MCPLGun` (and every standard MCPL reader) expects cm/MeV/ms — the round trip works because
each side converts, but a file handed to other codes first needs the conversion recipe on the
[Units](units) page.

---

## 6. Gotchas

1. **`energy=0` does not mean zero energy.** For `SimpleThermalGun` and `IsotropicGun`,
   `energy=0` (the Python default) selects a fixed built-in thermal spectrum with mean
   0.0380 eV (measured); `energy>0` selects monoenergetic emission. There is no way to emit
   E = 0 particles — and you would not want to.
2. **`UniModeratorGun` docstring is wrong about the band.** The docstring (Python and C++)
   says `U[mean−range, mean+range]`; the code draws `mean + range·(r − 0.5)`, i.e. the band is
   `[mean − range/2, mean + range/2]` with `range_wl` the **full width** (measured: exact
   span [1.75, 2.25] Å for `mean_wl=2.0; range_wl=0.5`). This page documents the actual
   behaviour; the docstring defect is known.
3. **A source/slit gun without source/slit aborts the process.** The factory requires all six
   `src_*`/`slit_*` keys; `simulate(MaxwellianGun(), n)` with a bare constructor kills the
   process with an uncatchable `Prompt::Error::BadInput`. Unknown extra keys abort the same
   way (exact parameter-count checks).
4. **Gun `w`/`h` are full widths, not half-sizes.** `setSource([10, 10, -200])` is a 10 × 10 mm
   rectangle; `Box(10, 10, 1)` is 20 × 20 × 2 mm. Mixing the two conventions doubles your
   beam size.
5. **Energy/wavelength setters collide.** `setEnergy` and `setWavelength` write the same
   `energy` config key (the latter converts Å → eV); the last call wins. `UniModeratorGun` is
   the exception — it is parameterised in Å (`mean_wl`/`range_wl`) from the start.
6. **`slit_z=1e99` = parallel beam**, not "slit removed": the slit size becomes irrelevant and
   the beam keeps the source size with zero divergence (measured x-RMS 2.89 mm vs 15.2 mm at
   `z = 100 mm`; 10 mm source at `src_z = -10`, 5 mm slit at `z = 10`, with and without the
   trick).
7. **Seed interaction.** Config-string guns sample everything (position, direction, energy)
   from the C++ stream seeded in `setWorld` — same seed ⇒ identical primaries ⇒ identical
   histograms. Consequence: changing any gun parameter shifts the whole random sequence
   downstream, so gun variants are statistically independent comparisons, not paired samples.
   `PythonGun` needs its own `RandomState` seeds (section 4), and its `save2Disk` is ignored.
8. **`MCPLGun` `.xml` (KDSource) mode is not seed-reproducible** — it seeds the C library RNG
   from the wall clock. Use `.mcpl` files if you need reproducible runs; both modes abort on
   non-neutron records.
9. **No gun set.** If the C++ `go()` loop runs without a gun (only reachable via the raw
   launcher, e.g. `sim.l.go(...)`, or the legacy GDML path) it falls back to a 0.0253 eV
   `IsotropicGun` at the origin and prints `PrimaryGun is not set, fallback to the neutron
   IsotropicGun`. The Python API always sets the gun you pass to `simulate`.
10. **The `PythonGun` remainder batch crashes array-writing guns.** After the full batches,
    `simulate` shrinks `gun.vectorized` to `num % vectorized` but still calls `generate()`
    with no argument (`promptCore.simulate`), so the `sample*` methods receive
    `n = num % vectorized` while `self.pdata` keeps the original batch size. Any sample
    method that writes shape-`(n,)` arrays — the section 4 example pattern — then dies on a
    numpy broadcast error: measured `vectorized=7` with 3000 events →
    `ValueError: could not broadcast input array from shape (4,) into shape (7,)`, and the
    same for `vectorized=1000` with 2002, 2003 or 2999 events. Remainders 0 and 1 are fine
    (`vectorized=1000`, 2001 events → exactly 2001 scored hits); a remainder > 1 survives
    only if every overridden `sample*` method writes scalars — the built-in defaults do
    (3000 = 428 × 7 + 2 default-written events score exactly 3000). Workaround until the
    tail passes the remainder to `generate()`: pick event counts divisible by `vectorized`,
    or set `vectorized=1`.

---

## Where to go next

- [Your first simulation](first-simulation) — a `UniModeratorGun` beam line by line
- [Geometry](geometry) — placing the volumes the beam flies through
- [Materials and physics](materials-physics) — what happens to the particles after emission
- [Scoring](scorers) — measuring the beam: scorers, `ptstate`, weights
- [Simulation lifecycle](simulation-lifecycle) — seeds, MPI event split, `clear()`-and-rebuild
- [Units](units) — the mm / eV / Å / s convention used throughout this page

---

*Source files: [`gun.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/gun.py)
(Python), `src/cxx/Gun/` (C++ samplers and factory).
Questions: cinema-users@outlook.com.*
