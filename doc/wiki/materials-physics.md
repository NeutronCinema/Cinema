# Materials and physics models

This page is the reference for materials and physics in Cinema/Prompt: how a material
config string becomes the physics of a volume, the `Material` class, the NCrystal config
string syntax (NCMAT files, virtual materials, single crystals), the physics model
inventory, surface physics, probability-conserving biasing, GIDI+ ENDF transport, and
offline ways to verify a material before running a simulation.
It documents Cinema 2.0.0a5. Sources of truth:
[`src/python/Cinema/Prompt/physics.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/physics.py),
[`compoundModel.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/compoundModel.py),
[`GidiSetting.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/GidiSetting.py)
and the C++ factories under
[`src/cxx/`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/).

GDML file input is the legacy v1 path and never carries materials into new work — every
snippet on this page uses the Python API. See [Geometry](geometry) for how `matCfg` and
`surfaceCfg` attach to volumes.

---

## 1. How a config string becomes physics

A material in Prompt is a *configuration string*, not an object graph. The chain from a
line of Python to transported physics is:

```text
Material(nccfg).cfg                      (python, physics.py)
  -> Volume(name, solid, matCfg=...)     geo.py -> pt_ResourceManager_cfgVolPhysics
  -> Prompt::ParticleProcess(cfgstr)     PTParticleProcess.cc
       PhysicsFactory::checkPhysicsType  PTPhysicsFactory.cc
         NC_RAW       string failed key=value parsing -> raw NCrystal cfg
         NC_SCATTER   physics=ncrystal;nccfg='...';scatter_bias=..;abs_bias=..
         NC_IDEALSCAT physics=idealElaScat;xs_barn=..;density_per_aa3=..
  -> ModelCollection (one per particle type, cached per config string)
       built from DiscreteModel(s):
         NCrystalScat   thermal + elastic scattering kernel
         NCrystalAbs    absorption (kills the particle, analog mode)
         GIDIModel      ENDF-based reactions, if GIDI is enabled
         IdealElaScat   analytic test scatterer
  -> macroscopic cross section = number_density * sum(biased microscopic xs)
```

`PhysicsFactory::nccalNumDensity` resolves the NCrystal material once, converts its
number density from atoms/Å³ to atoms/mm³, and the transport then works purely in
internal units:

| Quantity | Internal unit | Note |
|:---|:---|:---|
| energy | eV | the NCrystal scattering model asserts `Unit::eV == 1` at construction |
| length | mm | geometry, step lengths, macroscopic xs in 1/mm |
| time | s | TOF |
| microscopic cross section | barn | `1 barn = 1e-22 mm²` |
| number density | atoms/mm³ | NCrystal reports atoms/Å³; divided by Å³-in-mm³ |

The transport is neutron-first (particle type 2112); photons enter only through the
optional GIDI gamma transport (section 8).

Physics is cached: volumes that share the same material config string share one
`ParticleProcess`. In the Python layer the same machinery is reachable offline through
`Cinema.Prompt.compoundModel.ModelCollection` (section 9).

## 2. The `Material` class

`Material` (`Cinema.Prompt.physics`) wraps an NCrystal config string and the bias
parameters into one renderable config string:

```python
from Cinema.Prompt.physics import Material

mat = Material('Al_sg225.ncmat')     # nccfg may also be set later
mat.cfgMaterial('Al_sg225.ncmat')    # set/replace the NCrystal config string
mat.setBiasScat(2.0)                 # scatter-channel bias factor
mat.setBiasAbsp(1.0)                 # absorption-channel bias factor
mat.setAbsorpInWeight(True)          # implicit capture instead of analog kill
vol = Volume("sample", Box(10, 10, 1), matCfg=mat)     # object with .cfg
# ... or equivalently: Volume("sample", Box(10, 10, 1), matCfg=mat.cfg)
```

| Member | Effect |
|:---|:---|
| `Material(nccfg=None)` | construct; the NCrystal config string may be `None` initially |
| `cfgMaterial(cfg)` | set/replace the NCrystal config string |
| `setBiasScat(factor)` | `scatter_bias`; `1.0` (default) means unbiased, `0` disables the scattering model |
| `setBiasAbsp(factor)` | `abs_bias`; `1.0` means unbiased, `0` disables the absorption model |
| `setAbsorpInWeight(flag)` | a **bool flag** (or numeric `0`/`1`) folds absorption into the particle weight (`;absorp_in_weight=true`) instead of the analog kill; any other value raises `TypeError` — it is not a magnitude |
| `.cfg` (property) | renders `physics=ncrystal;nccfg='<nccfg>'[;scatter_bias=..][;abs_bias=..][;absorp_in_weight=true]` |

Rendering rules worth knowing (verified in `physics.py`):

- Factors equal to `1.0` are omitted from the string, so an unbiased `Material(...).cfg`
  is exactly `physics=ncrystal;nccfg='...'`.
- `absorp_in_weight` is a **mode flag**, not a magnitude — `setAbsorpInWeight` accepts a
  bool (or numeric `0`/`1`) and raises `TypeError` for anything else (e.g. `0.5`), so a
  misused "factor" can no longer silently enable the mode.
- Reading `.cfg` before a config string was set raises
  `ValueError("Material config string is not set")`.
- Setting both biases to `0` does **not** throw: both models are skipped and the volume
  becomes transparent (total cross section 0). Keep at least one bias non-zero. (A
  `BadInput` guard for this case exists in `PhysicsFactory::createParticleProcess`, but
  that helper is not on the current `Volume`/`ModelCollection` code path.)

`Material` stores its cfg_-prefixed attributes like every
[`ConfigString`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/configstr.py)
subclass, but overrides the `.cfg` property with the custom renderer described above;
surfaces and scorers render via the generic `makeCfg()` (cfg_-prefixed keys as
`key=value;` in insertion order).

## 3. NCrystal config strings

The `nccfg` value is handed to [NCrystal](https://github.com/mctools/ncrystal), which
resolves the material and its scattering/absorption data. Two families exist: on-disk
NCMAT files and *virtual* direct materials. A string is generally
`<file-or-virtual>;key=value;key=value...`.

### 3.1 NCMAT files and `NCRYSTAL_DATA_PATH`

Files in the repository's `ncmat/` directory are found because `env.sh` exports
`NCRYSTAL_DATA_PATH=<cinema-checkout>/ncmat` (see [Installation](install)). Shipped files:

| File | Content |
|:---|:---|
| `Cd.ncmat`, `B4C.ncmat` | strong absorbers (beam stops, filters) |
| `Si_640f.ncmat` | single-crystal silicon (`@CELL`/`@SPACEGROUP`/`@ATOMPOSITIONS`) + VDOS phonons |
| `He3_Gas_1bar.ncmat`, `He3_Gas_10bar.ncmat`, `He3_Gas_20bar.ncmat` | He-3 gas at pressure (detectors) |
| `tsl-D2O_M*_nsk*_temp293.6K.ncmat` | heavy-water S(α,β) tables (TSL variants) |
| `LiquidHeavyWaterD2O_nsk0_T293.6K.ncmat` | liquid D2O |
| `ambient_air.ncmat` | air |
| `vacuum.ncmat` | air at ~1e-6 kg/m³ — effectively nothing |
| `nanodiamond.ncmat` | diamond nanoparticles (incl. a `@CUSTOM_HARDSPHERESANS` section) |
| `ndtest.ncmat` | nanodiamond test variant carrying an `@OTHERPHASES` section (90% heavy-water phase) |
| `sascsns_sio2_spheres.ncmat` | SiO2 spheres with the SasCSNS SANS plugin section (below) |

NCMAT sections in use include `@CELL`, `@SPACEGROUP`, `@ATOMPOSITIONS`, `@DENSITY`,
`@STATEOFMATTER`, `@ATOMDB`, `@OTHERPHASES` and `@DYNINFO` with
`type freegas | vdos` (@DYNINFO also supports the modern `type tsl`; the shipped
D2O files predate it and use the older `scatknl` spelling), plus the plugin
`@CUSTOM_*` sections. In addition to these
files, the NCrystal installation itself ships a large standard-material library
(`Al_sg225.ncmat`, `Ge_sg227.ncmat`, `Al2O3_sg167_Corundum.ncmat`, ...) which resolves
automatically — `doc/example_basic.py` gets its `Ge_sg227.ncmat` from there, not from the
repository.

### 3.2 Virtual (direct) materials

No file needed — the composition is written directly into the string (used widely in the
tests):

```python
'solid::Cd/8.65gcm3'                                # elemental solid with density
'solid::B4C/2.52gcm3/B_is_0.95_B10_0.05_B11'        # compound with explicit isotope mix
'freegas::H2O/1gcm3/H_is_H1/O_is_O16'               # free-gas model of a compound
```

Related: **`matCfg=None` is NOT vacuum** — a volume without `matCfg` gets
`'freegas::H1/1e-26kgm3/H_is_1_H1'`, a near-vacuum dilute hydrogen gas (see
[Geometry](geometry)). For a deliberately empty world volume use `'void.ncmat'`.

### 3.3 Single crystals: `mos=`, `dir1`/`dir2`, `dcutoff`

```python
nccfg = 'Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'
```

- `mos=<fwhm>` — mosaic spread; repo usages include `0.0267deg`, `40arcsec`, `2deg`.
- `dir1`/`dir2` — pin two crystallographic planes (`@crys_hkl:h,k,l`) to laboratory
  directions (`@lab:x,y,z`). Two planes fully define the crystal orientation.
- `dcutoff=<length>` — Bragg-cutoff tuning: crystal planes with a d-spacing below this
  value are ignored; the unit is Angstrom by default (e.g. `dcutoff=0.5`).
- `mos=`, `dir1` and `dir2` are all-or-nothing: either omit all three (the file behaves as
  an unoriented crystal/powder) or set all three together to pin the crystal orientation.
  Partial combinations (e.g. `mos=` alone, or `dir1`/`dir2` without `mos=`) are rejected by
  NCrystal (>=4.x) with "Must set all or none of mos, dir1 and dir2 parameters" — Cinema's
  Python pre-check surfaces that as a catchable `ValueError` at `Volume`/`Material`
  construction (section 4).
  Oriented strings double as physics devices — the wavelength
  cutoff filter of [`test_prompt_filter.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/test_prompt_filter.py)
  is just an Al2O3 crystal with `mos=2deg` and two pinned planes in front of the
  detector.

Once a material is *oriented*, its microscopic cross section depends on the neutron
flight direction. The transport converts the global direction into the placed volume's
local frame before calling the model, so **the crystal orientation is relative to the
placement transformation** of the volume it sits in (rotate the placement to rotate the
crystal). A consequence for offline checks: `ModelCollection.xs()` passes a null
direction and aborts on oriented materials (section 9).

### 3.4 Temperature and density

Temperature and density come from the data by default — `@DENSITY`, the `@STATEOFMATTER`
section, or a TSL/filename tag such as `temp293.6K`. Standard NCrystal keys override them
in the string:

```python
'LiquidHeavyWaterD2O_nsk0_T293.6K.ncmat;density=1.0gcm3'
'Al_sg225.ncmat;temp=25C'
```

The material temperature is also what the GIDI layer matches against (section 8 snaps to
the nearest available ENDF temperature).

### 3.5 Plugin materials

An `@CUSTOM_SASCSNS` NCMAT section activates the SasCSNS small-angle-scattering plugin —
`HardSphere` with a sphere radius in Å (analytic I(Q)), `DirectLoad` with
measured `Q`/`I` lists, or `DirectLoad2D` for tabulated 2D `I(Qx,Qy)` — provided the plugin is installed in the NCrystal conda
environment and listed in `NCRYSTAL_PLUGIN_LIST` (environment policy in
[Installation](install)). The worked example is `doc/example_sas.py`. SANS-specific
doctrine: the plugin's Q table must cover the beam (up to `2·k(E_max)`), plugin xs are
per-object and get folded through the number density, and comparisons should be made on
macroscopic Σ, not microscopic σ.

## 4. The wrap-in-Material rule

Prompt's C++ config parser (`PTCfgParser.cc`) splits a config string on `;` and expects
each section to be exactly one `key=value`. Before any string reaches that parser,
`Volume.setMaterial`/`Material` pre-checks it in Python — data files are looked up, and
the NCrystal part is round-tripped through the real NCrystal parser — so most mistakes now
raise a normal, catchable `ValueError` ("NCrystal rejected the material config '...': ...")
instead of a `BadInput` abort inside the ctypes boundary. Three structural consequences of
the split rule remain (all verified against the current code):

1. **Strings that cannot be parsed as key=value pairs are treated as raw NCrystal cfg
   strings (`NC_RAW`).** Any string that starts with a plain file/virtual-material name —
   `'Al_sg225.ncmat'`, `'solid::Cd/8.65gcm3'`, or
   `'Ge_sg227.ncmat;mos=...;dir1=...'` (the first section has no `=`) — falls into this
   class and can be passed **directly** as `matCfg`. The whole string is then interpreted
   by NCrystal.
2. **A parameterised raw string is accepted but warned about and auto-wrapped.** A string
   that contains `;` but no `physics=` key emits a `RuntimeWarning` ("... looks like a raw
   NCrystal cfg. It is accepted, but the canonical matCfg is a Material-style string like
   `physics=ncrystal;nccfg='...'`...") and is wrapped into that explicit form before use —
   because only the `physics=ncrystal;nccfg='...'` form can carry the bias keys; a raw
   string would silently drop them. Bare raw strings (a single `.ncmat` file or a compound
   material like `solid::Cd/8.65gcm3`) pass through unchanged.
3. **Therefore: wrap parameterised NCrystal cfg strings in `Material(...)`.** Raw strings
   cannot carry `scatter_bias`/`abs_bias`/`absorp_in_weight`; the wrapper produces the
   explicit `physics=ncrystal;nccfg='...'` form that can:

   ```python
   # WRONG - ValueError at construction (NCrystal rejects the unknown keys):
   #   vol = Volume("s", Box(2,2,0.5), "scatter_bias=2.0;something_else=1")
   # right:
   mat = Material('Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;'
                  'dir2=@crys_hkl:0,1,-1@lab:1,0,0')
   mat.setBiasScat(2.0)
   vol = Volume("s", Box(2, 2, 0.5), mat.cfg)
   ```

**Quote nesting.** In the rendered string the `nccfg` value is protected by single
quotes: `physics=ncrystal;nccfg='<nccfg>'`. The parser replaces quoted spans with
placeholders before splitting, and an **odd number of `'` characters is a `BadInput`** —
so the `nccfg` itself must not contain a single quote. (If you build the explicit form by
hand instead of using `Material`, the same quoting applies:
`"physics=ncrystal;nccfg='Al_sg225.ncmat';scatter_bias=2.0;abs_bias=1.0"` — the pattern
used throughout the test suite.)

## 5. Physics inventory

Per volume, Prompt builds one `ModelCollection` of discrete models; per model the
transport uses the model's (biased) cross section, and the channel sampling picks among
them proportionally (section 7).

| Model | Kind | What it does |
|:---|:---|:---|
| `NCrystalScat` | bulk, scattering | Bragg diffraction + S(α,β) thermal scattering + free-gas elastic from NCrystal data; oriented-aware (`crossSection(E)` or `crossSection(E, dir)`); `sampleReaction` returns the final energy and direction; xs in barn, energies in eV; carries an energy-validity range and asserts `ekin < maxEkin` when its cross section is evaluated |
| `NCrystalAbs` | bulk, absorption | NCrystal capture; not direction-dependent; sampling marks the result "disappeared" with `deposition = ekin`; in analog mode the particle is killed |
| `GIDIModel` | bulk, reactions | continuous-energy ENDF reactions via GIDI+ (one MCGIDI protare per isotope per reaction group: elastic MT=2 and non-elastic); URR probability tables enabled for neutrons; delayed-neutron data handled (warning printed where incomplete); optional photon production; compile-time optional |
| `IdealElaScat` | bulk, scattering | analytic isotropic elastic scatterer: `xs_barn` (default 1, non-zero), `density_per_aa3` (default 0.05), optional fixed `energy_transfer_eV`, optional `scatter_bias`; intended for verification and tests |
| `Mirror`, `DiskChopper`, `EnergyReflector` | surface | neutron-optics models, attached via `surfaceCfg` (section 6) |

The dispatch between them is purely the config string: a raw NCrystal string creates
`NCrystalAbs` + `NCrystalScat` (unbiased); `physics=ncrystal;...` creates the two models
honouring the bias values; `physics=idealElaScat;...` creates the analytic model. GIDI
rearranges the combination (section 8). Only **one** disappearing (absorption-type) model
per `ModelCollection` is allowed — adding a second throws.

## 6. Surface physics

`Volume(..., surfaceCfg=...)` (or `vol.setSurface(cfg)`) attaches a surface/neutron-optics
model; like everything else it is a config string, and it must use the explicit
`physics=` form (the surface factory rejects strings without a `physics` key).

| Surface | Config string | Behaviour |
|:---|:---|:---|
| `Mirror` | `physics=Mirror;m=<m>[;threshold=<w>]` | specular reflection with a McStas-style reflectivity model (fixed `R0=0.99`, `Qc=0.0219`, `alpha=6.07`, `W=0.003`); `m` scales the critical Q and defaults to `1` (matching the Python wrapper `Mirror(m=1.0)` and McStas); `m=-1` always reflects with no weight change. The reflectivity is clamped at zero (the McStas linear factor would go negative beyond `Qc+1/alpha`, where the tanh factor is already zero). When the reflectivity is at or above the cut, the reflected particle's weight is scaled by the reflectivity; `threshold` (default `1e-3`) is a weight cut below which Russian roulette activates — reflect with probability reflectivity/cut at weight `threshold`, otherwise the particle is **absorbed** (kill type `ABSORB`, so it is scored like any other absorption and never transmitted through the wall); `threshold=0` disables the roulette entirely (pure weighting: every hit reflects with its weight scaled by the reflectivity) |
| `DiskChopper` | `physics=DiskChopper;theta0=<deg>;r=<mm>;phase=<deg>;rotFreq=<Hz>;n=<slits>` | rotating disk chopper with `n` slits of opening angle `theta0`; particles hitting the central disk of radius `r` are absorbed, particles in an open slit at their arrival time survive; throws if `theta0` exceeds the slit period `360°/n` |
| `EnergyReflector` | `physics=EnergyReflector;ekin=<eV>;islessthan=<0\|1>` | specularly reflects particles with `ekin <= threshold` (`islessthan=1`) or `ekin > threshold` (`islessthan=0`); `ekin=-1` reflects everything; no weight change |

Python wrapper classes for the first two exist in `Cinema.Prompt.physics`
(`Mirror(m=1.)`, `DiskChopper(rotFreq, r, theta0, n, phase)`) and render the `physics=`
strings via the `ConfigString` pattern; the `threshold` key of `Mirror` is not exposed by
the wrapper — hand-craft the string (`'physics=Mirror;m=2;threshold=1e-5'`) if you need
it. `physics.DiskChopper` is the canonical chopper class: the old
`component.DiskChopper` spelling still works but emits a `DeprecationWarning` (it is now
a thin alias producing byte-identical configuration strings), and the
`component.makeDiskChopper` builder uses the canonical class internally. A working example of the `EnergyReflector` form is
[`src/pythontests/prompt_physics/surfaceprocess/test_surf_energy_reflector.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_physics/surfaceprocess/test_surf_energy_reflector.py):
`surfaceCfg="physics=EnergyReflector;ekin=0.22;islessthan=0"`.

> **Legacy form.** The string `mirror=Al;substrate=Al` appears in one old test
> (`test_prompt_mirror.py`, which is excluded from the test run). No current code path
> handles it — the surface factory requires the `physics=`-style strings above. Use those.

## 7. Probability-conserving biasing

The point of `scatter_bias` / `abs_bias` is variance reduction: scale a channel's cross
section up or down to make (or stop) interactions happening, and compensate with particle
weights so the *expectation* of any unbiased estimator is unchanged. The mechanics
(`PTModelCollection.cc`, `PTParticleProcess.cc`), for a step of length `l` in a material
of number density `N`:

1. **Biased cross sections.** Each model reports `sigma_biased = bias * sigma` (the bias
   multiplies inside `getCrossSection`).
2. **Step sampling from the biased total.**
   `l = -ln(r) / (N * sum(sigma_biased))` — more (less) frequent reactions when the bias
   is above (below) 1.
3. **Channel selection** proportional to the biased channel cross sections.
4. **Weight correction per step.** For every model whose bias is not 1:
   `factor *= exp((bias - 1) * N * l * sigma_unbiased)`.
   When a reaction is actually sampled, the selected channel contributes an extra
   division `factor /= bias_selected`. When the particle leaves the volume at the end of
   the step (`hitWall`) only the survival factor is applied — no channel division.
5. **Implicit capture (`absorp_in_weight=true`).** Instead of the analog kill, every step
   multiplies the weight by `exp(-sigma_abs_unbiased * N * l)` and the particle survives.
   In this mode the absorption cross section used is the *unbiased* one. The two
   absorption treatments — analog kill and implicit capture — are mutually exclusive
   modes.

Constraints and side conditions:

- Biases of `1.0` are omitted from the string and are free (the factor is skipped).
- A bias of `0` **removes the model entirely** (`abs_bias=0.` is the idiom for "no
  absorption reactions", e.g. in the multi-scattering decomposition tests); setting both
  biases to zero does **not** throw — both models are skipped and the material becomes
  transparent, so keep at least one bias non-zero.
- Only one absorption-type model may exist per material (throws).
- With GIDI enabled, `scatter_bias` applies to the below-threshold NCrystal scattering
  model while `abs_bias` is handed to the GIDI models (section 8).

**The `bias=2` validation fact.** The shipped regression test
[`prompt_physics/ncrystal/test_prompt_ncrystal.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_physics/ncrystal/test_prompt_ncrystal.py)
builds the identical world twice — once with the pure kernel `'Al_sg225.ncmat'` and once
with `"physics=ncrystal;nccfg='Al_sg225.ncmat';scatter_bias=2.0;abs_bias=1.0"` — under
the comment that the two must agree "when NC changes", with an exact-seed histogram check
for the unbiased run and a weight check carrying a statistical tolerance
(`sqrt(10/WEIGHT_CHECK)`). That is the signature of probability-conserving biasing:
individual histories change, histograms do not (beyond statistics).

What biasing is **not**: it does not change physics you look at through weight-sensitive
tools — in particular `VolFluence` scoring is invalid in volumes where weights change
(see [Scoring](scorers)).

## 8. GIDI+ ENDF transport

The GIDI+ module (gidiplus) adds continuous-energy ENDF data on top of NCrystal. It is a
compile-time option: `option(ENABLE_GIDI ...)` in `src/cxx/CMakeLists.txt` (ON for a
plain cmake configure; `cimbuild` needs `--enablegidi` to keep it on — see
[Installation](install) for the feature-flag gotcha).

```python
from Cinema.Prompt.GidiSetting import GidiSetting

cd = GidiSetting()                  # singleton over the C++ settings object
cd.isCompiled                       # False when built without GIDI -> skip GIDI code paths
cd.setEnableGidi(True)              # default False
cd.setGidiThreshold(5.)             # eV; default 5.0; <= 0 means GIDI handles everything
cd.setGammaTransport(False)         # default False; adds photon transport + atomic models
cd.setEnableGidiPowerIteration(False)  # for k-eigenvalue style calculations
cd.setGidiPops('/path/to/pops.xml') # PoPI database
cd.setGidiMap('/path/to/all.map')   # GIDI map file
```

| Setting | Default | Meaning |
|:---|:---|:---|
| `setEnableGidi` | `False` | master switch |
| `setGidiThreshold` | `5.0` eV | hybrid switching energy; `> 0`: NCrystal below, GIDI above; `<= 0`: GIDI does *all* reactions including elastic (no NCrystal scattering model is created) |
| `setGammaTransport` | `False` | creates photon transport models and atomic (element-level) photon data |
| `setEnableGidiPowerIteration` | `False` | power-iteration (criticality-style) mode |
| `setGidiPops` / `setGidiMap` | `$CINEMAPATH/external/ptdata/pops.xml` / `all.map` | ENDF data description files; point at a local ENDF data directory containing your data (the test suite uses a `testdata/` tree with `pops.xml`, `all.map` and `neutron/`) |
| `.isCompiled` | — | attribute, `True` only when the library was built with GIDI; all GIDI tests guard with it |

**Configure before creating volumes.** The settings are read once when a volume's physics
is configured, and the GIDI factory (a singleton) bakes the pops/map paths at first use —
a `GidiSetting` call after `Volume(...)` construction has no effect. Configure it at the
top of `makeWorld()`, before any `Material`/`Volume` is created. (Known fixme: paths with
backslashes do not decode.)

What happens per material when GIDI is enabled (`PTParticleProcess.cc` +
`PTGIDIFactory.cc`):

1. The NCrystal material is decomposed into isotopes
   (`MaterialDecomposer::decompose(nccfg, T)`), which expands composite atoms and natural
   elements into isotope lists; the NCMAT temperature `T` is carried along.
2. For each isotope the ENDF protare is loaded, selecting the **nearest available ENDF
   temperature** (the selection is printed to stdout: "The specified temperature is X,
   the selected data is at Y Kelvin"). With a positive threshold two protares are built
   per isotope — elastic (MT=2) and non-elastic — otherwise a single combined protare.
3. Hybrid: with `gidiThreshold > 0` the `NCrystalScat` model is created with its energy
   range capped at the threshold (thermal scattering below), GIDI models covering above;
   with `gidiThreshold <= 0` GIDI covers the full range and no NCrystal scattering model
   is created.
4. Bias split: `abs_bias` is handed to the GIDI models; `scatter_bias` applies to the
   below-threshold NCrystal model. Note `abs_bias=0.` cannot remove GIDI's absorption
   handling (there is an explicit todo about this in the source).
5. `setGammaTransport(True)` additionally creates photon models from the isotope list
   *and* from the element-collapsed list (`shrink2element`) for atomic (photoelectric-
   style) data; isotopes with missing photon data are skipped with a warning.
6. URR probability tables are enabled for the neutron protares; incomplete delayed-neutron
   data prints a warning and is not included.

## 9. Verifying materials offline

The validation-first doctrine applies to materials too: before burning events, check the
material against an analytic limit, an independent implementation and previous results.
Prompt gives you three tools.

**`ModelCollection` — batch cross sections without a simulation**
([`compoundModel.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/compoundModel.py)):

```python
from Cinema.Prompt.compoundModel import ModelCollection

mc = ModelCollection(mat.cfg)     # accepts any material config string
mc.xs(0.0253)                     # total *biased* microscopic xs at 25.3 meV, in barn
mc.generate(0.0253)               # sample one reaction (smoke test; returns sampled final ekin in eV)
```

Example values (measured with Cinema 2.0.0a5 / NCrystal 4.2.12 on the development
machine, all at 25.3 meV):

| Config string | `xs(0.0253)` |
|:---|---:|
| `physics=ncrystal;nccfg='Al_sg225.ncmat'` | 1.678 barn (scatter + absorption) |
| same + `scatter_bias=2.0;abs_bias=1.0` | 3.124 barn (2 x scatter + abs) |
| same + `abs_bias=0.` | 1.447 barn (scatter only — the absorption model is gone) |
| `solid::Cd/8.65gcm3` | 2526 barn |
| `physics=idealElaScat;xs_barn=5;density_per_aa3=0.05` | 5.0 barn |

Caveats:

- `xs()` returns the **biased** total — that is exactly what makes it useful for checking
  bias settings, SANS Q coverage, etc.
- It passes a **null direction**: an oriented single crystal (section 3.3) aborts the
  process with a NCrystal "Can't scale null-vector" error. For oriented checks use
  NCrystal's own Python API (below) or an actual short simulation through a placed
  volume.
- `ModelCollection` bypasses the Python pre-check that makes `Volume.setMaterial` raise a
  catchable `ValueError` (section 4): a mis-formed string here still aborts the process —
  run such checks as small scripts, not inside a long-lived session you care about.

**`PointwiseDist`**
([`dist.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/dist.py))
— a piecewise-linear 1D distribution over `(x, y)` float64 arrays with an inverse-CDF
helper, handy for constructing or sanity-checking spectra (e.g. a source wavelength
distribution and its quantiles):

```python
from Cinema.Prompt.dist import PointwiseDist

d = PointwiseDist(x, y)      # 1D arrays of equal length
d.percentile(0.5)            # scalar (validated 0..1) or a 1D numpy array of quantiles
```

**NCrystal's own Python API** — the NCrystal package (in the conda environment that owns
it, see [Installation](install)) can independently inspect any NCMAT file or config
string: composition, number density, crystal orientation, S(α,β) tables and
`ncrystal-config` / `ncrystal-pluginmanager` for the environment. Because Cinema's
physics *is* NCrystal here, agreement between an NCrystal-direct calculation and a
Prompt volume result is the strongest cheap consistency check available; the
`ModelCollection` route above is the Prompt-side half of that comparison.

## 10. Plugin physics and the SANS tutorial

Plugin materials (`@CUSTOM_*` NCMAT sections, plugin discovery via
`NCRYSTAL_PLUGIN_LIST`, installing plugins into the conda NCrystal environment) are
covered in [Installation](install). The runnable walkthrough is
[SANS with the SasCSNS plugin](tutorial-sans) — `doc/example_sas.py` (SiO2 sphere slab,
9 Å beam, 2D PSD one metre downstream) — and unit conversions are on [Units](units).

> **Planned pages.** The following page is planned but does not exist yet; it is named
> here as plain text only: ncrystal-plugins (plugin installation and authoring).

## Where to go next

- [Your first simulation](first-simulation) — the canonical script using `Material`
- [Geometry](geometry) — where `matCfg` and `surfaceCfg` attach, volume placement
- [Scoring](scorers) — scorer catalogue; the weight-change caveat for `VolFluence`
- [The Simulation class](simulation-lifecycle) — `clear()`/rebuild, seeds, MPI
- [Installation](install) — the NCrystal-on-conda environment policy and
  `NCRYSTAL_DATA_PATH`/`NCRYSTAL_PLUGIN_LIST` wiring

---

*Source files:
[`physics.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/physics.py),
[`configstr.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/configstr.py),
[`compoundModel.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/compoundModel.py),
[`dist.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/dist.py),
[`GidiSetting.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/GidiSetting.py),
[`PTParticleProcess.cc`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Process/libsrc/PTParticleProcess.cc),
[`PTPhysicsFactory.cc`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Process/libsrc/PTPhysicsFactory.cc),
[`PTModelCollection.cc`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/ModelBulk/libsrc/PTModelCollection.cc),
[`ncmat/`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/ncmat/),
[`doc/example_basic.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py),
[`doc/example_sas.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_sas.py).
Questions: cinema-users@outlook.com.*
