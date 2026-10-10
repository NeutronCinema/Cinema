# SANS with the SasCSNS plugin

This page is a worked tutorial for small-angle neutron scattering (SANS) in
Cinema/Prompt, using the SasCSNS NCrystal plugin. It builds directly on
[your first simulation](first-simulation): same five-step pattern, new ingredient — a
sample whose scattering kernel is a SANS form factor instead of a crystal or free-gas
model. Along the way it covers the plugin's two model modes, the unit and Q-coverage
rules that make or break a SANS simulation, and three useful variations.

This page documents **Cinema 2.0.0a5** and was checked against the repository
[doc/example_sas.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_sas.py)
and the plugin's documentation and sources at
[ncplugin-sascsns](https://code.ihep.ac.cn/cinema-developers/ncplugin-sascsns/-/wikis/home).
Every measured number on this page was produced with the stated event count and seed
(October 2026, single process unless noted).

---

## 1. What the plugin adds

NCrystal plugins extend the material config-string language with new physics. SasCSNS
adds one NCMAT section, `@CUSTOM_SASCSNS`, which turns the material into a small-angle
scatterer: neutrons elastically scatter through the momentum transfer
`Q = 2k·sin(θ/2)` with a form factor `I(Q)` you choose. Two model modes exist:

| Mode | Section syntax | What it models |
|:---|:---|:---|
| `HardSphere` | `radius <R>` (R in Å) | analytic I(Q) of a solid sphere of radius R; the contrast (scattering length density) is computed from the NCMAT's own atom data; the plugin builds a dense log-spaced Q grid (1000 points) itself |
| `DirectLoad` | `Q <list>` and `I <list>` | your measured or calculated I(Q), tabulated; Q in Å⁻¹ (ascending), I in barn/(atom·sr), equal-length lists |

(A third mode, `DirectLoad2D`, transports tabulated *anisotropic* I(Qx,Qy) patterns;
it is documented in the plugin's own manual, see section 6.)

The shipped demo material is
[`ncmat/sascsns_sio2_spheres.ncmat`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/ncmat/sascsns_sio2_spheres.ncmat)
— amorphous SiO2 spheres of 100 Å radius:

```text
NCMAT v6
@DENSITY
  2.2 g_per_cm3
@DYNINFO
  element Si
  fraction 0.3333333
  type freegas
@DYNINFO
  element O
  fraction 0.6666667
  type freegas
@CUSTOM_SASCSNS
  HardSphere
  #sphere radius in Angstrom:
  radius 100
```

From there everything downstream is ordinary Cinema machinery: the material is used
like any other NCrystal material, the plugin supplies the scattering cross section
σ(E) and the elastic Q sampling, and Cinema folds the per-atom cross section with the
number density into the macroscopic cross section that drives the transport. The SANS
kernel **replaces** the `@DYNINFO` elastic model outright — the plugin's factory serves
it with overriding priority instead of stacking it on the standard kernel — so the
`freegas` entries survive only as input to the contrast calculation, while the
material's 1/v absorption continues to act on top of the SANS channel.

## 2. Prerequisites

### 2.1 Install the plugin

The plugin is a pip package (distribution name `ncrystal-plugin-SasCSNS`) that must
live **in the conda environment that owns NCrystal** — the same
NCrystal-never-elsewhere policy as every other plugin. From a plugin checkout:

```bash
conda activate <ncrystal-env>
pip install ./ncplugin-sascsns
```

The environment policy (why the plugin goes into the conda env and not Cinema's own
python environment, and how `NCRYSTAL_PLUGIN_LIST` wires it into a Cinema shell) is on
the [Installation](install) page.

Verify the installation:

```bash
ncrystal-pluginmanager --test SasCSNS     # expect: "All ok"
```

Run this from a fresh shell with only the NCrystal conda environment activated — not
from a shell with Cinema's `env.sh` sourced, where the self-test fails however the
environment variables are arranged (gotcha 2 below). The self-test loads every
plugin-shipped material and exercises all model modes.

### 2.2 The physics rules to check before burning events

SANS results are only as good as the I(Q) table and its units. Four rules:

1. **Q coverage.** The plugin samples an allowed Q with rejection: a sampled Q is
   accepted only when `Q ≤ 2k` of the incident neutron. Consequences for a DirectLoad
   table:
   - the **largest** Q must reach `2k(E_max) = 4π/λ_min` of your beam band, otherwise
     the fast edge of the spectrum under-scatters (above the table's top energy the
     cross-section lookup falls only like `const/√E` instead of the physical `1/k²`, and
     the sampler can no longer produce `Q > Q_max`, so fast neutrons under-scatter);
   - the **smallest** Q must sit well below `2k(E_min)`, otherwise cold neutrons have
     no allowed Q at all and the sampler cannot terminate.
   For the 9 Å beam of the tutorial (`E = 1 meV`), `2k = 1.39 Å⁻¹`. The `HardSphere`
   mode builds its own 1000-point log grid from 1e-6 Å⁻¹ upward, so coverage is
   automatic there; it is a DirectLoad responsibility only.
2. **Units: barn/object → barn/atom.** SasView and most SAS calculators report I(Q)
   **per particle (object)**; NCrystal expects **per atom**. The plugin's conversion
   script (`script/sasview2ncmat.py` in the plugin checkout) always and automatically
   applies the scale `(φ/V_p)/n_d` — particle number density over atomic number
   density, with φ the particle volume fraction and V_p the particle volume. If you
   hand-build a DirectLoad table, you own this conversion.
3. **Compare macroscopic Σ, not microscopic σ.** Beamline transmission and detector
   rates are governed by `Σ = n·σ` with `n` the *atomic* number density. Count atoms,
   not formula units: SiO2 at 2.2 g/cm³ holds `n ≈ 6.6e19 atoms/mm³` (three atoms per
   formula unit), not a third of that.
4. **Verify offline first.** `ModelCollection.xs(E)` returns the total (biased)
   microscopic cross section of a config string without a simulation — see
   [Materials and physics](materials-physics). That is the cheapest SANS sanity check:

   ```python
   from Cinema.Prompt.compoundModel import ModelCollection
   mc = ModelCollection("physics=ncrystal;nccfg='sascsns_sio2_spheres.ncmat'")
   mc.xs(1e-3)     # 224.5 barn at 1 meV, measured (SANS channel plus 1/v absorption)
   ```

### 2.3 Known gotchas

1. **A fresh `. env.sh` can abort every plugin run.** On current builds the exported
   `NCRYSTAL_PLUGIN_LIST` carries a stray trailing semicolon; NCrystal then tries to
   open a library literally named `...so;` and the process hard-aborts (SIGABRT, no
   Python traceback) right after the `Configuring physics model` line. Remedy: the
   canonical [Installation](install) section-6 workaround,
   `export NCRYSTAL_PLUGIN_LIST="$(printf '%s' "$NCRYSTAL_PLUGIN_LIST" | tr -d ';')"`
   (on this installation the narrower `${NCRYSTAL_PLUGIN_LIST%;}` was equally
   sufficient). Verified here: with the tainted variable the tutorial core-dumps;
   stripped, it runs clean.
2. **`ncrystal-pluginmanager --test SasCSNS` under a sourced `env.sh` fails, and
   unsetting variables does not rescue it.** With the semicolon fixed (gotcha 1) the
   self-test cannot reach the plugin's *data* files (`NCFileNotFound: can not provide
   data: SasCSNS/sascsns_sio2_spheres.ncmat`); unset `NCRYSTAL_PLUGIN_LIST` and it
   fails differently (`NCLogicError: Required plugin was not loaded: "SasCSNS"`);
   unset `NCRYSTAL_LIB` too and it fails earlier still (`Could not locate the NCrystal
   shared library`). Remedy: run the self-test from a fresh shell with only the
   NCrystal conda environment activated — `conda activate <ncrystal-env>`, then the
   test prints `All ok`. (Under a sourced `env.sh` the command itself is also off `PATH` —
   env.sh prunes the conda bin; use `$NCRYSTAL_PLUGINMANAGER` or the conda env's absolute
   path.) The transport side of a Cinema shell is unaffected (it loads
   NCMAT files by name through `NCRYSTAL_DATA_PATH`).
3. **Mis-sized tables fail silently** (rule 1 above): too-narrow Q range shows up as a
   spectrum edge that "loses" scattering; a table whose first Q is too large can hang
   the sampler for the coldest neutrons.
4. **Wrong units fail loudly but confusingly**: a per-object table fed in as per-atom
   over-states the cross section by the atoms-per-object factor — from ~1e2 for 1 nm
   particles to ~3e5 for the demo's 10 nm spheres — the sample turns black instead of
   scattering weakly.

## 3. Walkthrough: `doc/example_sas.py`

The example puts a 2 mm slab of the SiO2 sphere material in a 9 Å beam and records the
scattering pattern on a 2D position-sensitive detector (PSD) one metre downstream. The
full script:

```python
#!/usr/bin/env python3

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import PSDHelper

class Simulation(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)

    def makeWorld(self):
        # material carrying the SasCSNS small angle scattering model
        mat = Material('sascsns_sio2_spheres.ncmat')

        # 1 mm thick sample slab
        sample = Volume("sample", Box(10, 10, 1), matCfg=mat.cfg)

        # PSD detector 1 m downstream, 200x200 bins over +-100 mm
        detector = Volume('detector', Box(200, 200, 0.1))
        psd = PSDHelper('sansPSD', xmin=-100, xmax=100, xnumbin=200,
                        ymin=-100, ymax=100, ynumbin=200)
        psd.make(detector)

        world = Volume("world", Box(300, 300, 2200))
        world.placeChild("samplePhyVol", sample)
        world.placeChild("detectorPhyVol", detector, Transformation3D(0, 0, 1000))

        self.setWorld(world)

if __name__ == "__main__":
    # 9 Angstrom neutron beam along +z
    gunCfg = "gun=SimpleThermalGun;position=0,0,-999;direction=0,0,1;energy=1e-3"

    sim = Simulation()
    sim.makeWorld()

    # to visualize geometry and trajectories:
    # sim.show(gunCfg, 100)

    # production run
    sim.simulate(gunCfg, 100000)

    # save the 2D PSD histogram: the SANS ring shows up around the direct beam
    hist = sim.gatherHistData('sansPSD')
    hist.savefig('sas_psd.png', title='SiO2 spheres, R=100 AA, 9 AA beam')
```

### 3.1 The class and the seed

Identical to the first tutorial: subclass `PromptMPI`, pass the seed to
`super().__init__()`. Under `mpirun` each rank automatically uses `seed + rank`.

### 3.2 The material

```python
mat = Material('sascsns_sio2_spheres.ncmat')
```

A plain file name resolves through `NCRYSTAL_DATA_PATH`, which `env.sh` points at the
repository's `ncmat/` directory. `Material(...)` wraps it into
`physics=ncrystal;nccfg='...'` — always use the wrapper when the string could grow
NCrystal parameters (the wrap-in-`Material` rule, see
[Materials and physics](materials-physics)). The `@CUSTOM_SASCSNS` section inside the
file activates the plugin; without the plugin installed the load fails outright.

### 3.3 The sample slab

```python
sample = Volume("sample", Box(10, 10, 1), matCfg=mat.cfg)
```

`Box` arguments are **half**-sizes in mm, so the slab is 20 x 20 x **2** mm (the
in-file comment says "1 mm thick"; the half-size convention gives 2 mm). Thickness
matters more in SANS than usual: with Σ ≈ 1.5/mm at 1 meV (section 4) a 2 mm slab
gives ~95% scattering probability — multiple scattering is significant. Halve it for a
single-scattering-dominated measurement, or study the multiple-scattering
contribution explicitly.

### 3.4 The PSD detector

```python
detector = Volume('detector', Box(200, 200, 0.1))
psd = PSDHelper('sansPSD', xmin=-100, xmax=100, xnumbin=200,
                ymin=-100, ymax=100, ynumbin=200)
psd.make(detector)
```

The detector volume has **no `matCfg`**: it gets the default dilute hydrogen gas, a
near-vacuum that is deliberately *not* true void (see
[Materials and physics](materials-physics)) — 400 x 400 x 0.2 mm of almost nothing
that neutrons cross unimpeded. The full signature is

```python
PSDHelper(name, xmin=-10.0, xmax=10.0, xnumbin=100, ymin=-10, ymax=10,
          ynumbin=100, pdg=2112, ptstate='ENTRY', psdtype='XY', groupID=0,
          isGlobal=False)
```

so the example scores a 200 x 200 grid of 1 mm² bins over ±100 mm, in the volume's
**local** frame (`isGlobal=False`), firing at `ENTRY` — every neutron crossing into
the detector, direct beam included, fills the map. `psd.make(detector)` is what
actually registers the scorer; a helper that is never `make()`-d scores nothing. The
scorer catalogue and the ptstate semantics are on [Scoring](scorers).

### 3.5 World and placement

```python
world = Volume("world", Box(300, 300, 2200))
world.placeChild("samplePhyVol", sample)
world.placeChild("detectorPhyVol", detector, Transformation3D(0, 0, 1000))
```

The world is a box big enough to contain the 2 m flight path. The sample sits
untransformed at the origin (the beam enters at `z = -999`), the detector is translated
to `z = +1000 mm` — one metre downstream, the SANS small-angle convention. Placement
semantics and the full `Transformation3D` toolkit are on [Geometry](geometry).

### 3.6 The gun

```python
gunCfg = "gun=SimpleThermalGun;position=0,0,-999;direction=0,0,1;energy=1e-3"
```

A gun given as a config string instead of an object: a monoenergetic beam at
`E = 1e-3 eV` = 1 meV, which is `λ = 9.045 Å` (the "9 Å beam"; conversion table on
[Units](units)), emitted from `z = -999` along `+z`. A point source with no slit is
fine here — the PSD itself separates the direct beam from the scattering. All gun
types, their object API and their config-string forms are on [Guns](guns).

### 3.7 Run and read out

```python
sim.simulate(gunCfg, 100000)
hist = sim.gatherHistData('sansPSD')
hist.savefig('sas_psd.png', title='SiO2 spheres, R=100 AA, 9 AA beam')
```

`gatherHistData('sansPSD')` returns the `Hist2D` registered under the scorer's exact
name; `savefig` renders a log-scale map and appends the total weight to the title.
(The commented `sim.show(gunCfg, 100)` opens the interactive geometry/trajectory
viewer — [Visualization](visualization); do not use it in batch runs.)

## 4. Expected output

`sas_psd.png` is a log-scale 2D map: the direct beam forms a compact spot at the
centre, surrounded by the SANS ring of the sphere form factor, fading toward the
window edge.

**Reference numbers** (measured for this page, 2026-10-09, single process, **seed
4096**, 1e5 events, serial). The annulus rows sum every 1 mm² bin whose *centre* lies
in the annulus (`lo ≤ r < hi`, centres from `getCentre()`); a different bin-selection
convention shifts those three values by a few per cent:

| Check | Value |
|:---|:---|
| total PSD weight | **91854.0** (exact — same seed and event count reproduce it bit for bit) |
| transport loop | 4.95e5 events/s → ≈0.2 s for 1e5 events |
| whole script | ≈5 s wall, model build and plotting included (hardware-dependent; slower/loaded nodes see tens of seconds) |
| central 0–5 mm annulus | 6316 (direct beam spot plus innermost ring) |
| ring maximum, 25–30 mm | 7502 |
| outer annulus, 95–100 mm | 1310 |

Why the numbers look the way they do:

- The unscattered direct beam is only ~5–6% of the events: Σ ≈ 224.5 barn x
  6.6e19 atoms/mm³ x 1e-22 ≈ 1.5/mm over the 2 mm slab (section 2.2, rule 3).
- The rest of the 91.85% is forward-scattered onto the detector — the ring.
- The missing ~8% scattered past the ±100 mm window (only ±5.7° at 1 m) or was
  absorbed.

Run it under MPI with `mpirun -n 4 python3 doc/example_sas.py` — the script's
`__main__` block qualifies. `gatherHistData` is collective (every rank, same order)
and complete on rank 0 only; gate the `savefig` call with `if sim.rank == 0:` for MPI
use. Scaling details are on [Running at scale](mpi-scale), output files and seed
semantics on [The simulation class](simulation-lifecycle).

## 5. Variations

### 5.1 DirectLoad: measured I(Q)

Replace the section in the NCMAT file (or point a new file at your converted data):

```text
@CUSTOM_SASCSNS
  DirectLoad
  Q 0.001 0.01 0.05 0.1 0.5 1.0 1.5
  I 12.0 11.8 9.1 5.2 0.9 0.15 0.03
```

Q in Å⁻¹ (ascending), I in barn/(atom·sr), lists of equal length. In practice generate the
file with the plugin's converter rather than by hand — it applies the mandatory
barn/object → barn/atom scale automatically (section 2.2). The example values above
are illustrative, not data.

The mode has a clean analytic anchor: in the low-energy limit every event samples the
Q → 0 region and σ → 4π·I(0). For a constant table the equality is exact at every
energy with `Q_min ≤ 2k(E) ≤ Q_max` — the grid's first node is built at `E(2k = Q_min)`
with value `4π·I(Q_min)` — and the plugin's own validation harness checks such a table
against the built-in HardSphere model to 0.14% (section 6). The same check in Cinema,
offline and cheap:

```python
from Cinema.Prompt.compoundModel import ModelCollection
cfg = "physics=ncrystal;nccfg='<mytable>.ncmat'"
mc = ModelCollection(cfg)
mc.xs(1e-3)   # measured 13.4 barn for a constant I=1 table; 4*pi*I0 = 12.57,
              # the difference being the sample's 1/v absorption alone (Si:
              # 0.171 barn at 1.798 A -> +0.86 barn at 9.045 A), not a free-gas
              # elastic baseline - the @CUSTOM_SASCSNS section replaces it
```

The residual above `4π·I0` is pure 1/v absorption and nothing else. Measured for the
constant I=1 table: 13.43 barn at 1 meV and 39.76 barn at 1e-6 eV (39.764974 unrounded) — the excesses
(0.860 and 27.20 barn) match `0.171 barn · λ/1.798 Å`, the natural-Si absorption, to about
0.01%, and their ratio is `√1000`, exactly the λ ratio of the two energies. (On
the SiO2 dyninfos of the shipped file the same table absorbs three times less —
0.057 barn at 1.798 Å — and measures 12.9 / 21.7.) Note that the 1e-6 eV point is not
an edge extrapolation: it still sits *inside* the table (with `Q_min = 0.001 Å⁻¹` the
first node lies at `E ≈ 5e-10 eV`, and below the table the lookup returns its first
value, flat). The rule to keep the first Q far below `2k(E_min)` (gotcha 3) is about
the sampler, not the lookup: at energies where every tabulated Q exceeds `2k`, no
scattering outcome is kinematically allowed and the rejection loop cannot terminate.

### 5.2 Detector placements and `groupID`

When one detector logical volume is placed several times, a scorer tagged
`groupID=g` counts only particles entering placements placed with
`scorerGroup=g`; `groupID=0` counts **all** placements:

```python
PSDHelper('mon1', ..., groupID=1).make(detector)
...
world.placeChild("detectorArm1", detector, trf1, scorerGroup=1)
world.placeChild("detectorArm2", detector, trf2, scorerGroup=2)
```

With the tutorial's default placement (`scorerGroup=0`) the two behaviours do **not**
coincide: measured on the tutorial geometry (20k events, seed 4096), the `groupID=1`
PSD records nothing (**0.0**) while the `groupID=0` PSD records **18393.0** — the
placement itself sits in group 0, and a `groupID=g` scorer counts only placements
tagged `scorerGroup=g`. The two coincide only when the single placement is itself
tagged `scorerGroup=1` (then both PSDs report 18393.0). Note that 19625.0 at 20k
events is the volume-entry count — what the wavelength scorer of section 5.3 sees —
not a PSD window total. See [Scoring](scorers) for the full semantics.

### 5.3 A wavelength spectrum alongside the PSD

Any number of scorers can share the detector volume; add e.g. a wavelength spectrum
to confirm the band that produced the ring:

```python
from Cinema.Prompt.scorer import WlSpectrumHelper
WlSpectrumHelper('wl', min=1, max=20, numbin=38, linear=True).make(detector)
...
sim.gatherHistData('wl').savefig('sas_wl.png')
```

Measured with the tutorial beam (20k events, seed 4096): total weight 19625.0 — the
same particles the PSD sees, binned by wavelength — with the spectrum peaking in the
bin containing 9.045 Å. Take the chance to double-check rule 1: the fast edge of this
band has `2k = 4π/λ_min`, and that is the number your DirectLoad table must cover.

## 6. Validation ladder and full plugin documentation

The plugin ships with its own validation programme — an eight-rung "validation ladder"
of scripts (closed-form limits, python-reference comparisons, transport-integrated
attenuation, regression anchors) documented in the plugin README:

- Plugin README and documentation (model table, conversion tool, the ladder commands
  `python script/validate_*.py` — with `ncrystal-pluginmanager --test SasCSNS` as the
  regression-anchor rung — and the 2D mode), hosted on the plugin project:
  <https://code.ihep.ac.cn/cinema-developers/ncplugin-sascsns/-/wikis/home>

The validation-first doctrine behind the ladder, and the offline tools
(`ModelCollection`, NCrystal's own python API) for checking a material before a run,
are described in [Materials and physics](materials-physics).

Where to go next:

- [Your first simulation](first-simulation) — the base pattern this tutorial reuses.
- [Scoring](scorers) — the scorer catalogue; multi-scattering counters for separating
  single and multiple SANS events.
- [Results analysis](results-analysis) — reading `.h5`/MCPL outputs, merging
  multi-seed runs for better ring statistics.
- [Guns](guns) — wavelength-band beams (`MaxwellianGun`, `UniModeratorGun`) instead of
  the monoenergetic tutorial beam.

Questions or problems: write to cinema-users@outlook.com.

---

*Source files:
[`doc/example_sas.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_sas.py),
[`ncmat/sascsns_sio2_spheres.ncmat`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/ncmat/sascsns_sio2_spheres.ncmat),
[plugin documentation](https://code.ihep.ac.cn/cinema-developers/ncplugin-sascsns/-/wikis/home),
[`compoundModel.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/compoundModel.py),
[`scorer.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/scorer.py).*

> **Note on the source links.** The four `blob/master` links above (`doc/example_sas.py`,
> `ncmat/sascsns_sio2_spheres.ncmat`, `compoundModel.py`, `scorer.py`) resolve only once the
> branch carrying the SasCSNS example is merged to master; none of the four files exists on
> master yet. They are deliberately written against master rather than a branch URL — if a
> link 404s, the merge has not landed yet (branch/commit URLs are not an option under the
> link policy).

