# Units and conversions

Cinema/Prompt transports particles in one fixed internal unit system, while the Python
analysis layer and the file formats around it use different conventions. This page collects
the three layers in one place: the internal (transport) units that every scorer result comes
back in, the unit conventions at the boundaries (MCPL files, the `Cinema.analysis`
post-processing classes), and the conversion helpers shipped in `Cinema.convertor` and
`Cinema.Interface.units`.
It documents Cinema 2.1.0. Sources of truth:
[`src/python/Cinema/convertor.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/convertor.py),
[`src/python/Cinema/Interface/units.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Interface/units.py),
[`src/python/Cinema/Interface/helper.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Interface/helper.py),
[`src/cxx/Utils/libinc/PTUnitSystem.hh`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Utils/libinc/PTUnitSystem.hh)
and
[`src/python/Cinema/analysis.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/analysis.py).

Most API numbers are bare floats whose unit is fixed by the producer — the exceptions are
config-string values that embed their unit (`mos=0.0267deg`, `temp=25C`,
`density=1.0gcm3`), which NCrystal parses. When in doubt, convert with the functions of
section 3 and check against a worked example of section 6.

---

## 1. The internal unit system

The transport engine (`libprompt_core`, `PTUnitSystem.hh`) works in exactly one unit system:

| Quantity | Internal unit | Note |
|:---|:---|:---|
| energy | eV | the NCrystal models assert `Unit::eV == 1` at construction |
| length | mm | shape dimensions, `Transformation3D` translations, gun positions, volume capacity |
| time | s | time-of-flight, particle clocks |
| angle | deg | every Python-side angle: shape angles, rotations (`degrees=True` is the default), config-string angles (`mos=`, `theta0=`, `phase=`) |
| microscopic cross section | barn | `1 barn = 1e-22 mm²`; macroscopic Σ = N·σ comes out in 1/mm |
| number density | atoms/mm³ | NCrystal reports atoms/Å³; converted once at model creation (section 6.3) |
| temperature | K | NCrystal data temperatures, `kT` |

Geometry conventions: the beam axis is **+z** — sources sit at negative z and detectors
downstream at positive z. See [Geometry](geometry), section 1, for the full statement.

Scorer results are returned in these internal units. The defaults of the scorer helpers,
for reference (full catalogue and semantics on [Scoring](scorers)):

| Helper | Scores (unit) | Default range |
|---|---|---|
| `TOFHelper` | time-of-flight, **s** | 0..40e-3 s, linear |
| `ESpectrumHelper` | kinetic energy, **eV** (energy transfer if `energyTransfer=True`) | 1e-5..1 eV, log bins |
| `WlSpectrumHelper` | wavelength, **Å** | 0.1..10 Å, log bins |
| `PSDHelper` | 2D position, **mm** | ±10 mm, linear |
| `VolFluenceHelper` | raw track length, **mm**; divide by the volume in mm³ after the run for the fluence in 1/mm² | 1e-6..10 eV, log bins |
| `DirectSqHelper` | momentum transfer Q, **Å⁻¹** | none — `qmin`/`qmax` required, log bins |
| `DirectSqwHelper` | Q (**Å⁻¹**) x energy transfer ω (**eV**) | Q 0.1..10 Å⁻¹, ω −0.1..0.1 eV |

Two length bases coexist on the Python side: the *transport* units above (mm), and the
*analysis* units of `Cinema.Interface.units`, where the base length is the Ångström
(`aa = 1.`) — which is why the conversion helpers of section 3 speak Å while your
histograms speak mm.

## 2. Unit boundaries: MCPL files and `Cinema.analysis`

### 2.1 MCPL particle files

The MCPL standard fixes the particle fields to **cm / MeV / ms**, and Cinema honours that on
both sides: the *reading* side (`MCPLGun`) multiplies `ekin` by `Unit::MeV`, positions by
`Unit::cm` and times by `Unit::ms` when sampling, and the *writing* side (`MCPLOutHelper`,
C++ `KillerMCPL`) applies the inverse conversions on write — position x0.1, `ekin` x1e-6,
time x1e3, and the same x1e-6 for the ΔE stored in `polarisation[2]`. Verified by round
trip (pinned by `src/pythontests/test_mcpl_units.py` and the `mcpl_roundtrip_*` C++ cases):
a 1e-3 eV beam killed on a detector entered 95 mm from the gun produces a file that the
`mcpl` package reads back as `ekin=1e-9 MeV, z=9.5 cm, t=0.217 ms`. The file header itself
says nothing about units (`MCPLFile.comments` is an empty list on a fresh output), but
Cinema-written files need no manual conversion:

| Quantity | Inside Cinema | On disk (MCPL standard) | Standard reader sees |
|:---|:---|:---|:---|
| position | mm | cm | mm |
| kinetic energy | eV | MeV | eV |
| time | s | ms | s |
| direction, weight, pdgcode | — | unchanged | unchanged |
| `userflags` | — | event ID | event ID |
| polarisation triple | — | survival probability, scattering number, ΔE (MeV) | same fields |

Two cases still need manual attention:

- **Files written by Cinema v2.0.1a1 through v2.1.0** stored the internal mm / eV / s numbers
  unconverted — energies x1e6, positions x10, times x1e-3 too large for any standard-unit
  reader (`MCPLGun`, `MCPL_Analyzer_1D/2D`, the `mcpl` tools). Re-simulate, or convert them
  with the passthrough recipe below.
- The passthrough write path is unit-blind: the `MCPLParticle` struct of
  `Cinema.Prompt.files.MCPLBinaryWrite` is memcpy-copied into the file with no conversion
  (the write call lands on the passthrough `write(const mcpl_particle_t&)` overload), so
  fill it in MeV / cm / ms yourself. The `mcpl` python package cannot do this for you — it
  is read-only (its particle objects reject attribute assignment), so post-processing has
  to go through `MCPLBinaryWrite`. The recipe below (verified end-to-end: `mcpl.MCPLFile`
  reads the result back as 200 particles with `ekin=1e-9 MeV, z=9.99 cm, t=0.457 ms`)
  converts a scorer file in a second process:

  ```python
  from Cinema.Prompt import PTMCPL
  from Cinema.Prompt.files import MCPLBinaryWrite, MCPLParticle

  src = PTMCPL('det_pro0.mcpl.gz')      # pre-2.1.0 output: internal units on disk
  out = MCPLBinaryWrite('det_std.mcpl', enable_double=True,
                        enable_extra3double=True, enable_extraUnsigned=True)
  for pb in src.particle_blocks:
      for i in range(len(pb.ekin)):
          p = MCPLParticle()
          p.ekin = pb.ekin[i] * 1e-6                                # eV  -> MeV
          p.polarisation_x = pb.survival_probability[i]
          p.polarisation_y = pb.scattering_number[i]
          p.polarisation_z = pb.differential_energy[i] * 1e-6       # eV  -> MeV
          p.position_x, p.position_y, p.position_z = (pb.position[i] * 0.1).tolist()  # mm -> cm
          p.direction_x, p.direction_y, p.direction_z = pb.direction[i].tolist()
          p.time = pb.time[i] * 1e3                                 # s   -> ms
          p.weight = pb.weight[i]
          p.pdgcode = 2112
          p.userflags = int(pb.event_id[i])
          out.write(p)
  out.close()
  ```

  Timing note: the scorer gzips only when it is destroyed, i.e. at process exit — while the
  producing run is still alive the file is `det_pro0.mcpl`, afterwards `det_pro0.mcpl.gz`.
- `PTMCPL` (`Cinema.Prompt.mcpl`) and the `mcpl` package hand you the raw stored fields —
  cm / MeV / ms for current files, internal mm / eV / s for the 2.1.0-and-earlier ones.

Histogram-in-MCPL output (`<name>_seed<seed>.mcpl.gz`) is a different container: its blobs
(`edge`, `content`, ...) are plain arrays in internal units (section 1).
Post-processing is covered on [Results analysis](results-analysis).

### 2.2 `Cinema.analysis` default units

The unit enums of `Cinema.analysis` (`TimeUnit`, `EnergyUnit`, `LengthUnit`, `AngleUnit`,
`MomentumTransferUnit`, `WavelengthUnit`, `VelocityUnit`) each define a `get_default()` —
the unit assumed when you pass `unit=None` to an analyzer:

| Enum | Default | Members |
|:---|:---|:---|
| `TimeUnit` | **ms** | s, ms, us, ns |
| `EnergyUnit` | **MeV** | MeV, keV, eV, meV, neV |
| `LengthUnit` | **cm** | m, cm, mm, um |
| `AngleUnit` | **cosine** | cosine, deg, rad |
| `MomentumTransferUnit` | **Å⁻¹** | Å⁻¹, nm⁻¹ |
| `WavelengthUnit` | **Å** | Å, nm, um |
| `VelocityUnit` | **mm/s** | m/s, cm/s, mm/s |

Every enum member supports `.convert_to(value, target_unit)` and a matplotlib-ready
`.symbol`. The defaults match the MCPL *standard* (MeV, ms, cm) — not the internal units,
which is exactly what makes moving numbers between an analyzer, a histogram and the engine
a source of factor-1e6/1e3 mistakes. Check against the tables above whenever data crosses a
boundary.

## 3. `Cinema.convertor`: conversion functions

`Cinema.convertor` is the user-facing conversion module. The physics conversions are thin
wrappers over C functions of `libprompt_core`, vectorized with `np.vectorize`, so every
function accepts scalars or arrays. Conventions: energy in eV, wavelength in Å, Q in Å⁻¹.

| Function | Input | Output | Note |
|---|---|---|---|
| `eKin2k(ekin_eV)` | eV | Å⁻¹ | k = 2π/λ; also `sqrt(E * eV2kk)` |
| `wl2ekin(wl_angstrom)` | Å | eV | used by the wavelength setters of the guns ([Guns](guns)) |
| `ekin2wl(ekin_eV)` | eV | Å | E = 81.804 meV·Å²/λ²; input 0 maps to the largest finite float |
| `ekin2v(ekin_eV)` | eV | **mm/s** | 0.0253 eV → 2.200e6 mm/s (= 2200 m/s) |
| `v2ekin(v_mm_per_s)` | **mm/s** | eV | exact inverse of `ekin2v` |
| `angleCosine2Q(angle_cos, enin_eV, enout_eV=None)` | cosine, eV | Å⁻¹ | `enout=None` means elastic |
| `MeV2eV`, `eV2MeV`, `keV2eV`, `eV2keV` | energy | energy | plain powers of ten, array-native |
| `meV2eV`, `eV2meV` | energy | energy | plain powers of ten, array-native (the factors were inverted before 2.1.0 — gotcha 14) |

The `*_units` variants take or return other energy units (`'eV'`, `'meV'`, `'keV'`,
`'MeV'`):

| Function | Signature |
|---|---|
| `angleCosine2Q_units` | `(angle_cos, enin, enin_unit='eV', enout=None, enout_unit='eV')` |
| `wl2ekin_units` | `(wl_angstrom, ekin_unit='eV')` |
| `ekin2wl_units` | `(ekin, ekin_unit='eV')` |

All four unit spellings convert correctly as of 2.1.0 (the `'meV'` branch used to run
through inverted factors — gotcha 14), and an unrecognised unit string raises
`ValueError` listing the supported units instead of being silently treated as eV.
Matching is exact and case-sensitive: `meV` (milli) and `MeV` (mega) differ only by
case, so no case-insensitive folding is attempted.

The velocity pair is the odd one out: `ekin2v`/`v2ekin` speak **mm/s** (they come from the
C++ engine, whose length unit is mm; the `ekin2v` docstring in `convertor.py` says mm/s and
that is — unusually for this corner of the code — the correct one), while the
`Interface.units` *constant* of the same name `ekin2v` = 1.3831592645254673e14 converts eV
to velocity in **Å/s** via `v = ekin2v * sqrt(E)`. Same name, factor 1e7 apart — see
gotcha 2 for where the misleading comments live.

Performance note: the C-backed functions are `np.vectorize`-wrapped single-value ctypes
calls. That is fine for gun setup and config-time conversions; for million-element arrays
(pulling energies out of MCPL blocks, rebinning spectra) prefer the plain numpy formulas —
`E = 0.081804209605330899 / wl**2` and friends, or the constants of section 4.

## 4. `Cinema.Interface.units`: constants

The module is a flat list of physical constants and unit factors (values below measured in
Cinema 2.0.0a5; CODATA 2018 where annotated in the source):

| Name | Value | Meaning |
|:---|:---|:---|
| `aa` | 1.0 | Ångström — the Python-side base length unit |
| `mm`, `cm`, `m` | 1e7, 1e8, 1e10 | in Å |
| `fm`, `au` | 1e-5, 0.529177249 | fermi and Bohr radius, in Å |
| `barn` | 1e-8 | 1 barn = 1e-8 Å² = 1e-22 mm² |
| `K` | 1.0 | kelvin |
| `eV`, `meV`, `MeV` | 1.0, 1e-3, 1e6 | energies |
| `s`, `ps`, `fs`, `THz` | 1.0, 1e-12, 1e-15, 1e12 | time units in s; `THz` in 1/s |
| `c` | 2.99792458e18 | speed of light, Å/s |
| `hbar` | 6.582119569509068e-16 | reduced Planck constant, eV·s |
| `planck` | 4.13566769692386e-15 | Planck constant, eV·s |
| `radpsec2eV` / `eV2radpsec` | = `hbar` / 1/`hbar` | angular frequency (rad/s) ↔ energy |
| `radpsec2meV`, `radpfs2meV` | 6.582e-13, 658.212 | angular frequency in rad/s, rad/fs → meV |
| `eV2kk` | 482.59644941816356 | eV → Å⁻² for k² (`k = sqrt(E*eV2kk)`); 1/eV2kk = ħ²/2m_n = 2.0721e-3 eV·Å² |
| `kb`, `boltzmann` | 8.6173324e-5, 8.6173303e-5 | Boltzmann constant, eV/K (two CODATA editions — gotcha 4) |
| `umass`, `atomic_mass` | 1.0364269570e-28, 1.0364269575e-28 (agreeing to 10 significant digits) | one dalton in eV/(Å/s)² |
| `dalton2kg`, `dalton2eVc2` | 1.66053904e-27, 9.3149409517e8 | dalton → kg, → eV/c² |
| `avogadro` | 6.022140857e23 | mol⁻¹ |
| `neutron_mass` | 1.674927471e-24 | neutron mass in **gram** (cgs, not internal units) |
| `neutron_mass_evc2` | 1.0454075098625835e-28 | neutron mass in eV/(Å/s)²: E = 0.5·m·v² |
| `neutron_atomic_mass` | 1.00866491588 | neutron mass, u |
| `ekin2v` | 1.3831592645254673e14 | multiply by `sqrt(E[eV])` to get velocity in **Å/s** |
| `deg2rad` | 0.017453292519943295 | pi/180 |

Import them from the submodule — the constants are **not** re-exported by the
`Cinema.Interface` package itself (gotcha 1):

```python
from Cinema.Interface.units import avogadro, hbar, barn   # right
# from Cinema.Interface import hbar                       # ImportError
```

## 5. Kinematics helpers and the `Interface.helper` toolbox

`Cinema.Interface.helper` collects the numerical toolbox used by the analysis modules. The
kinematics half mirrors `convertor` but lives in numpy (no ctypes, no vectorize wrapper):

| Function | Signature | Meaning |
|---|---|---|
| `eKin2k(eV)`, `k2eKin(wn)` | | energy ↔ wave number (Å⁻¹), same convention as `convertor` |
| `angleCosine2Q(angleCosine, enin_eV, enout_eV)` | all three required | Q from the scattering-angle cosine; **no elastic default** here — pass `enout_eV=enin_eV` yourself |
| `angle2Q(angle_deg, enin_eV, enout_eV)` | degrees | Q from the scattering angle in degrees |
| `minMaxQ(enin_eV, enout_eV)` | arrays | `(qmin, qmax)` reachable for given in/out energies; **`enout_eV` must be an array** |
| `q2Alpha(Q, kt)`, `alpha2Q(alpha, kt)` | Q in Å⁻¹, `kt` in eV | dimensionless S(α,β) scaling variable: α = Q²/(kt·eV2kk), i.e. the free-neutron recoil energy ħ²Q²/2m_n in units of kT |
| `angle2Alpha(angle, enin_eV, enout_eV, kt)` | degrees | α directly from an angle (recoil-energy form) |
| `angularFre2eKin(fre)`, `eKin2AngularFre(en)` | rad/s ↔ eV | via `hbar` |

The rest of the toolbox, in one breath: FFT pairs `takfft`/`takifft` (fftshift with 2π
scaling), `getOmegaFromTime`/`convOmT` time-frequency axis builders, conjugate-symmetric
spectral extension (`expand`, `fftEvenConjugate`, `autoCorrSpectrum`), smoothing (`smooth`,
`smoothVdos`), log-spaced Q seeding (`seed`, `brewSeed`, `calBrewNum`, `findSeed4Gamma`),
fit shapes (`Lorentz`, `Gaussian`, `PsdVoigt`), array I/O (`saveArrInH5`, `readArrInH5`,
`saveArrInDat`), and the NCMAT v2 writer helpers `incoherentSqw2ncmat` /
`gaussSqw2ncmat` + `writeDynInfo`, which emit `@DYNINFO` blocks so a measured or
simulated S(Q,ω) grid can be turned into an NCrystal scattering kernel.

> **Legacy path inside the toolbox.** `Interface.helper.findDataUnder` (renamed from
> `findData` in 2.1.0 to lift the name clash) is the old data-file lookup driven by the
> obsolete `TAKPATH` variable. The current one is `Interface.Utils.findData` (exported by
> `from Cinema.Interface import findData`), which resolves `'subdir/file.ext'` names
> under the data tree at `CINEMAPATH/data` — `CINEMAPATH` is the Cinema root configured
> on [Installation](install). Do not call the helper version.

## 6. Worked examples

All numbers below were produced with 2.0.0a5 and are unchanged in 2.1.0 — the examples
use only the eV-based functions and the `'keV'`/`'MeV'` unit branches, none of which the
gotcha-14 fix touched; the outputs are shown as comments.

### 6.1 Wavelength ↔ energy

```python
from Cinema import convertor

convertor.wl2ekin(1.8)                    # 0.025248212841151512   eV  (25.25 meV)
convertor.wl2ekin_units(1.8, ekin_unit="keV")   # 2.5248212841151512e-05
convertor.ekin2wl(0.0253)                 # 1.7981568253603895     Å
convertor.ekin2wl_units(3.4e-5, ekin_unit="keV")  # 1.5511306085764258 Å  (0.034 eV)
convertor.eKin2k(0.0253)                  # 3.4942367078203986     Å⁻¹  (= 2pi/1.7982)
```

The relation is the neutron E = ħ²(2π/λ)²/2m, i.e. E[meV] = 81.804/λ²[Å] and
k = 2π/λ — not k = 1/λ.

### 6.2 Q at a scattering angle

A 2.5 Å beam elastically scattered by 90°:

```python
import numpy as np
from Cinema import convertor
from Cinema.Interface.helper import angle2Q, minMaxQ

E = convertor.wl2ekin(2.5)                # 0.013088673536852944 eV, k = 2.5133 Å⁻¹
angle2Q(90., E, E)                        # 3.554306508020575  Å⁻¹ = 2 k sin(45 deg)
convertor.angleCosine2Q(0.0, E, E)        # 3.554306508020576  (cos 90 deg = 0)
angle2Q(30., E, E)                        # 1.3009664747718888 Å⁻¹
angle2Q(0., E, E)                         # 0.0 — forward, no momentum transfer
angle2Q(180., E, E)                       # 5.026548468473654  = 2 k, backscattering
```

For inelastic scattering the accessible Q band at fixed E_in, E_out is bounded:

```python
E0 = 0.0253
minMaxQ(E0, np.array([0.0053, 0.0253, 0.0453]))
# qmin = [1.89493649, 0.0, 1.18140433]
# qmax = [5.09353692, 6.98847342, 8.16987775]
# (down-scatter to 5.3 meV, elastic, up-scatter to 45.3 meV; remember the array argument)
```

These are the same formulas the `DirectSqHelper`/`DirectSqwHelper` scorers apply internally
([Scoring](scorers)) — handy for choosing `qmin`/`qmax` before a run.

### 6.3 Number density from density and molar mass

Number density is what turns microscopic cross sections (barn) into macroscopic ones
(1/mm) — see [Materials and physics](materials-physics). By hand, with the `avogadro`
constant:

```python
from Cinema.Interface.units import avogadro

rho = 2.699          # g/cm3, aluminium at room temperature
M = 26.9815385       # g/mol
N = rho / M * avogadro     # 6.024029420354589e+22 atoms/cm3
N_mm3 = N * 1e-3           # 6.024029420354589e+19 atoms/mm3 (1 mm3 = 1e-3 cm3)
```

Prompt computes the same quantity from a material config string; the result is atoms/mm³,
ready for Σ = N·σ with σ in barn:

```python
from Cinema.Prompt.utils import nccalNumDensity

nccalNumDensity("Al_sg225.ncmat")    # 6.023238256131623e+19 atoms/mm3
```

The 0.01% difference is expected: NCrystal derives the density of `Al_sg225.ncmat` from the
crystal structure, while 2.699 g/cm³ is the handbook value. `nccalNumDensity` accepts the
same strings as `Material` (raw NCrystal cfg or the full `physics=ncrystal;nccfg='...'`
form) and needs the NCrystal environment to be healthy — with the known
`NCRYSTAL_PLUGIN_LIST` trailing-semicolon defect a call like this aborts the process; apply
the workaround from [Installation](install) first.

---

## 7. Gotchas

1. **Import path.** `Cinema.Interface` does not re-export the constants or helpers:
   `from Cinema.Interface import hbar` raises `ImportError`. Use
   `from Cinema.Interface.units import hbar` and `from Cinema.Interface.helper import
   angle2Q`. The exceptions are `findData` and `plotStyle`, which the package `__init__`
   does export. Importing any of it loads `libprompt_core.so` at import time — the runtime
   must be configured first ([Installation](install)).
2. **Two `ekin2v`, factor 1e7 apart.** `convertor.ekin2v(E)` returns **mm/s**
   (0.0253 eV → 2.200e6 mm/s = 2200 m/s, measured); the constant
   `Interface.units.ekin2v` (1.3831592645254673e14) times `sqrt(E[eV])` gives **Å/s**.
   The misleading comment is upstream of both: the C++ constant behind the convertor
   (`const_neutron_mass_evc2` in `PTUnitSystem.hh`) is annotated `[eV/(Aa/s)^2]` but its
   numeric value (1.0454e-14) is eV/(mm/s)² because `const_c` is built from the *mm*-based
   `Unit::m` — the Python `units.py` twin (1.0454e-28) really is eV/(Å/s)².
   Star-importing both modules shadows one name with the other — whichever module is
   imported second wins: `Interface.units` last leaves the 1.383e14 Å/s constant,
   `convertor` last leaves the mm/s function. Convert with care: 2200 m/s is 2.2e6 mm/s
   and 2.2e13 Å/s.
3. **`fs` is a femtosecond factor now.** `Interface.units.fs` was briefly `1e15` (an
   inverted factor, inconsistent with `ps = 1e-12`); it is fixed to `1e-15` (`fs = s*1e-15`),
   matching the multiply-to-get-seconds convention. Older analyses that compensated for the
   old value must drop that compensation.
4. **`kb` and `boltzmann` disagree in the last digits** (8.6173324e-5 vs 8.6173303e-5
   eV/K — different CODATA editions). Pick one per calculation; do not mix.
5. **`neutron_mass` is in gram**, a plain cgs value; everything else in the module is in
   the internal/analysis units. For E = ½mv² arithmetic use `neutron_mass_evc2` (with v in
   Å/s) instead.
6. **`eV2kk` means k².** `k[Å⁻¹] = sqrt(E[eV] * eV2kk)`; it converts energy to
   wave-vector-squared (1/eV2kk = ħ²/2m_n = 2.0721e-3 eV·Å²). It is not a temperature
   conversion — for eV ↔ K divide by `kb`.
7. **`minMaxQ` needs arrays.** It calls `.min()` on the second argument; a scalar
   `enout_eV` fails with `AttributeError`. Wrap it: `minMaxQ(E0, np.array([Eout]))`.
8. **`helper.angleCosine2Q` has no elastic default** (unlike `convertor.angleCosine2Q`,
   where `enout_eV=None` means elastic). Three arguments or a `TypeError`.
9. **Negative energies are not rejected — they come back as NaN.** Only two of the C++
   helpers behind `convertor` carry input asserts — `neutronEKin2k` (`ekin >= 0`) and
   `neutronAngleCosine2Q` (`enin_eV > 0`), both in `PTMath.icc` — and `pt_assert` is a
   no-op when `NDEBUG` is set and the shipped `libprompt_core` is built optimised
   (`-O3 -DNDEBUG`). Nothing raises and nothing aborts: `eKin2k(-1.0)`, `ekin2wl(-1.0)`,
   `ekin2v(-1.0)` and `angleCosine2Q` with a negative `enin_eV` all return `nan`
   (measured) while the process exits 0. The wavelength/velocity pair carries no assert
   at all — `ekin2wl`/`ekin2v` yield NaN even in a debug build of the library; only
   `eKin2k` and `angleCosine2Q` terminate there. A quiet
   NaN then poisons whatever histogram the numbers feed, which is worse than a crash —
   filter inputs to `E > 0` first. Zero input is its own trap (gotcha 10).
10. **`ekin2wl(0)` returns the largest finite float**, not `inf` or 0 — zero-energy bins
    pass silently as a huge wavelength. Guard E > 0 before converting.
11. **Bulk conversions in pure numpy.** The `convertor` physics functions are
    `np.vectorize`-wrapped ctypes calls — convenient for setup, slow per element. For
    million-element MCPL dumps use `E = 0.081804209605330899/wl**2`,
    `v = ekin2v*sqrt(E)` (Å/s) and the power-of-ten factors (the correct ones — see
    gotcha 14), which are plain Python multiplication and array-native.
12. **Three unit conventions, one workflow.** Histograms come back in internal units
    (s, eV, Å, mm, Å⁻¹), `MCPLOutHelper` files on disk are in the MCPL standard cm/MeV/ms
    (section 2.1 — files written by v2.0.1a1 through v2.1.0 carry internal mm/eV/s instead), and
    `Cinema.analysis` defaults to MeV/ms/cm. `MCPL_Analyzer_1D/2D` convert from the MCPL
    standard for you and are correct for current files. `PTMCPL` never converts anything.
13. **`nccalNumDensity` returns atoms/mm³** — the internal-unit form used by Σ = N·σ.
    Multiply by 1e-21 to get atoms/Å³ (the unit NCrystal itself reports).
14. **`meV2eV`/`eV2meV` were inverted — fixed in 2.1.0.** The factors used to be each
    other's inverse (`meV2eV(1.0)` returned `1000.0`), so 25.3 meV converted to
    25300 eV and every `'meV'` branch of the `*_units` variants inherited the error
    (off by 1e6 in energy, 1e3 in the sqrt(E)-scaling wavelength/Q outputs). Any
    numeric output produced with 2.0.0a5 or earlier through a `'meV'` unit argument
    carries this error — redo the conversion with plain arithmetic (`x*1e-3`,
    `x*1e3`) rather than "correcting" old data with a blanket factor, since the
    output error depended on the variant. The current factors are pinned by
    `src/pythontests/test_fix_misc.py::test_convertor_mev_factors_physics` (thermal
    anchor: 1.798 Å ↔ 25.3 meV).

## Where to go next

- [Scoring](scorers) — the scorer catalogue whose default ranges section 1 tabulates
- [Geometry](geometry) — the +z convention, mm sizes and degree rotations
- [Materials and physics](materials-physics) — how number density and barns become Σ
- [Guns](guns) — wavelength setters that call `wl2ekin`
- [Results analysis](results-analysis) — `MCPL_Analyzer_*`, `PTMCPL` and histogram I/O
- [Installation](install) — the runtime environment all of this imports at load time

---

*Source files:
[`convertor.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/convertor.py),
[`Interface/units.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Interface/units.py),
[`Interface/helper.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Interface/helper.py),
[`analysis.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/analysis.py),
[`Prompt/utils.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/utils.py),
[`PTUnitSystem.hh`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Utils/libinc/PTUnitSystem.hh),
[`PTPythonConvertor.cc`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Python/libsrc/PTPythonConvertor.cc),
[`PTMath.icc`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Utils/libinc/PTMath.icc),
[`PTException.hh`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/Core/libinc/PTException.hh),
[`PTMCPLBinaryWrite.cc`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/cxx/MCPL/libsrc/PTMCPLBinaryWrite.cc).
Questions: cinema-users@outlook.com.*
