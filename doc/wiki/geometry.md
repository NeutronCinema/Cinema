# Geometry: volumes, solids and transformations

This page is the reference for building geometry with the Cinema/Prompt Python API:
the `Volume` class (logical volumes and the world assembly), the shape catalogue
(`Cinema.Prompt.solid`), and `Transformation3D` (placements and rotations).
It documents Cinema 2.0.0a5. Sources of truth:
[`src/python/Cinema/Prompt/geo.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/geo.py)
and
[`src/python/Cinema/Prompt/solid.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/solid.py).

Under the hood everything geometric is C++ [VecGeom](https://github.com/root-project/vecgeom):
a shape object wraps a `vg::VUnplacedVolume`, a `Volume` wraps a `vg::LogicalVolume`, and a
`Transformation3D` wraps a `vg::Transformation3D`. GDML file input exists only as the legacy v1
path (`prompt -g file.gdml`) and is **not** covered here — new work should always use the Python
API shown on this page.

---

## 1. Units and conventions

| Quantity | Unit | Where it applies |
|:---|:---|:---|
| Length | mm | shape dimensions, `Transformation3D` translations, `Volume.getCapacity()` (mm³), gun positions, detector coordinates |
| Angle | degrees | every Python-side angle: shape phi/theta/stereo angles and `Transformation3D` rotations (each wrapper converts to radians before calling C++; `degrees=True` is the default) |
| Energy | eV | gun energies (wavelength setters convert to eV) |

Conventions:

- **The beam axis is +z.** Guns fire along z by default, and downstream components are placed at
  positive z — `Transformation3D(0, 0, 1000)` is the idiom for "a detector 1 m downstream"
  (used in `doc/example_sas.py`).
- The interactive viewer's default camera is `view_zy()` (looking down x, z drawn vertical), and
  there is no automatic scaling — a long beamline needs the `xscale/yscale/zscale` options of
  `PromptMPI.show` to be readable (see [Visualisation](visualization)).

## 2. `Volume`: logical volumes and the world assembly

A `Volume` is a **logical** volume: a named combination of

- a **shape** (a solid from the catalogue below),
- an optional **material** config (`matCfg`) for the bulk physics,
- an optional **surface** config (`surfaceCfg`) for neutron-optics physics,
- any **scorers** attached to it.

```python
Volume(volname, solid, matCfg=None, surfaceCfg=None)
```

Placing a volume somewhere is a separate step. `placeChild` creates the physical-volume
relationship between a parent and an already-built logical volume:

```python
parent.placeChild(name, logVolume, transf=Transformation3D(0, 0, 0), scorerGroup=0)  # returns parent
```

- `name` is the physical-volume name (shows up in the viewer's pick output).
- `transf` maps **child-local coordinates into the parent frame**: the child's origin sits at
  `transf`'s translation and its axes are rotated by `transf`'s rotation (details in
  [section 3](#3-transformation3d-cookbook)).
- `scorerGroup != 0` sets the placement's copy number, which scorers read back to group detector
  copies ([section 7](#7-scorers-on-volumes-a-teaser)).

The canonical assembly, from
[`doc/example_basic.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py):

```python
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper

class Simulation(PromptMPI):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        mat = Material('Ge_sg227.ncmat;mos=0.0267deg;...'
                       )                                   # see materials-physics page
        vol = Volume("sampleSolid", Box(10, 10, 1), matCfg=mat.cfg)

        tof = TOFHelper("TOF", ptstate='ABSORB')
        tof.make(vol)                                      # scorer on the volume

        trf = Transformation3D(0, 0, 100).applyRotX(45)    # 100 mm up, tilted 45 deg about x
        world = Volume("world", Box(50, 50, 210))
        world.placeChild("samplePhyVol", vol, transf=trf)
        self.setWorld(world)                               # closes the geometry
```

World assembly rules:

1. **Build bottom-up.** A `Volume` has no position until it is `placeChild`ed into a parent.
2. **Nesting is arbitrary.** Volumes may contain volumes that contain volumes; the test suite
   assembles world → outer shell → shell → sample by chained `placeChild` calls
   (`test_integrated_cases.py`).
3. **Daughters must not overlap** each other — this is a plain VecGeom/GEANT4-style containment
   hierarchy, and overlapping daughters have an undefined transport order. `placeChild` runs a
   best-effort overlap estimate on every new daughter (pairwise against the already-placed ones)
   and emits a `RuntimeWarning` naming the two volumes and the estimated intersection volume in
   mm³ when they intersect; pass `checkOverlap=False` to skip the scan. The estimate is a
   Monte-Carlo capacity probe (~45 ms per pair, budget-capped at 200 probes per parent volume —
   a truncation is warned once) and prints the usual `pt_Volume_new cinema_overlap_probe` lines
   while it runs.
4. **Any shape can be the world.** A `Box` somewhat larger than everything else is the convention;
   some tests (e.g. the boolean-operation test) use `Box(s, s, s)` with `'void.ncmat'`, while most
   shape tests simply wrap the sample in a default-material `Box` (e.g. `Box(50, 50, 200)`).
5. **The gun/source position must lie inside the world volume.** Before any tracking starts each
   primary is tested against the world, and a primary born outside it is dropped before taking a
   single step — every scorer then reads zero on a run that still exits 0. The only diagnostic is
   one stdout line per dropped particle, `particle at {...} is outside the world` (20000 events
   produce 20000 such lines — loud, but easy to lose in a redirected or MPI-interleaved log).
   Keep the gun `position`/`src_z` inside the world extent: the examples'
   `setSource([10, 10, -200])` works because the world `Box(50, 50, 210)` spans z −210..210
   (half-sizes!).
6. **`setWorld` is one-shot per process** and *closes* the geometry (`GeoManager::SetWorld`,
   `CloseGeometry`, navigators built per logical volume according to daughter count). A second
   call raises the catchable Python exception `RuntimeError: World exist already: only one world
   can be set per process ...` (the guard now runs before the seed is re-applied). Note the
   `Launcher` is a process-wide singleton shared by every `Prompt` instance, so constructing a
   second `Prompt()` in the same process hits the same error on its first `setWorld` — run each
   world in its own process (a separate script or an `mpirun` rank), or `clear()` first when one
   `Simulation` object is reused. All `Volume`
   construction and placement must happen **before** `setWorld`; afterwards it has no effect on
   the closed geometry.
7. **To rebuild a geometry in the same process** (parameter scans, tests), call `sim.clear()`
   first — it resets the C++ geometry, the world flag and the scorer registry. Some tests (e.g.
   `test_prompt_geoBooleanOperation.py`) call `self.clear()` at the top of `makeWorld`.

## 3. `Transformation3D` cookbook

```python
Transformation3D(x=0., y=0., z=0., rot_z=0., rot_new_x=0., rot_new_z=0., degrees=True)
```

The constructor takes a translation in mm plus **intrinsic ZXZ Euler angles** (degrees by
default): first a rotation about z, then about the *new* x, then about the *new* z again.

Chainable mutators — the `applyRot*` family each right-multiplies the current rotation, pushes
the new matrix to the C++ object, and returns `self` for chaining (the `set*` methods below
**replace** the current rotation instead of composing):

| Method | Rotation applied |
|:---|:---|
| `applyRotX(angle, degrees=True)` / `applyRotY` / `applyRotZ` | single axis (composes on the right, returns `self`) |
| `applyRotAxis(angle, axis, degrees=True)` | arbitrary axis vector (composes on the right, returns `self`) |
| `applyRotxyz(rotx, roty, rotz, degrees=True)` | extrinsic xyz triple (scipy `from_euler('xyz')`; composes on the right, returns `self`) |
| `set_euler_ZXZ(rot_z, rot_new_x, rot_new_z, degrees=True)` | **replaces** the rotation with intrinsic ZXZ; returns `None`, so it cannot be chained |
| `setSciRot(scipy_rotation)` | **replaces** the rotation with a `scipy.spatial.transform.Rotation` object (returns `self`) |

Because the `applyRot*` mutators compose on the right, a chain such as
`Transformation3D().applyRotX(45).applyRotZ(30)` means: 45° about x, then 30° about the **z axis
of the already-rotated frame** (body-frame/intrinsic composition). If you prefer to think in
fixed laboratory axes, build the whole rotation at once with the extrinsic classmethod:

```python
Transformation3D.from_euler_xyz(x=0., y=0., z=0., rx=0., ry=0., rz=0., degrees=True)
# rotation = rx about fixed x, then ry about fixed y, then rz about fixed z
```

Typical recipes:

```python
from Cinema.Prompt.geo import Transformation3D

trf = Transformation3D(0, 0, 1000)                # 1 m downstream, no rotation
trf = Transformation3D(0, 0, 100).applyRotX(45)   # example_basic.py: up 100 mm, tilt 45 deg
trf = Transformation3D().applyRotX(90)            # pure rotation
trf = Transformation3D().applyRotAxis(90, [0, 1, 0])
trf = Transformation3D.from_euler_xyz(0, 0, 500, rx=90, rz=30)
trf = Transformation3D(rot_z=30, rot_new_x=45)     # intrinsic ZXZ, like the constructor
```

Inspection and scipy interop:

- `getRotMatrix()` → 3×3 numpy array; `getTranslation()` → `[x, y, z]`;
  property `euler_xyz` → extrinsic xyz angles in degrees.
- `setRotByAlignment(rotated, original)` **replaces** the rotation, setting it from **exactly
  two** vector pairs per argument (scipy `Rotation.align_vectors`); it returns `self`. The
  classmethod `from_alignment(rotated=..., original=..., rot=...)` builds a frame with it
  directly. The old spellings `setRotByAlignement`/`from_alignement` still work but emit a
  `DeprecationWarning`.
- `applyRotbyMatrix(refMatrix)` multiplies in a 3×3 matrix and returns `self`, so it can be
  chained like the `applyRot*` family.
- `deepcopy` is supported (the C++ twin is re-created).

Transformation algebra:

- `a * b` composes two transformations: `b` is applied first, then `a` —
  `Transformation3D(0, 0, 0).applyRotZ(90) * Transformation3D(10, 0, 0)` is the point
  (10, 0, 0) rotated to (0, 10, 0). This is what the `component.py` array helpers use to
  compose parent and member frames.
- `inv()` still does **not** exist (commented out in `geo.py` as TODO) — invert a rotation with
  scipy (`Rotation.inv()`) and pass it to `setSciRot` if you need one.

Point transforms: `trf.transform(points)` maps an `(N, 3)` array of points **global → local**
(VecGeom's `Transform`: subtract the translation, apply the inverse rotation). A pure-Python
variant `transform_py` exists and agrees with `transform()` (the two diverged for non-zero
translations in older versions; that sign bug is fixed).

## 4. Shape catalogue

All classes live in `Cinema.Prompt.solid`, inherit from `Solid`, and validate their arguments
(positivity checks, `min <= max` relations, angular-extent limits). All length parameters are mm,
all angles degrees.

| Class | Signature | Size semantics and notes |
|:---|:---|:---|
| `Box` | `(hx, hy, hz)` | **half**-lengths in x, y, z |
| `Tube` | `(rmin, rmax, z, phiStart_deg=0, phiDelta_deg=360)` | `z` = **half**-height; `rmin=0` gives a cylinder; `phiDelta_deg` must be ≤ 360 |
| `Sphere` | `(rmin, rmax, phiStart_deg=0, phiDelta_deg=360, thetaStart_deg=0, thetaDelta_deg=180)` | spherical shell; angles deg; `phiDelta_deg` ≤ 360, `thetaDelta_deg` ≤ 180 |
| `Orb` | `(r)` | full sphere of radius `r` |
| `Trapezoid` | `(x1, x2, y1, y2, z)` | `z` = **half**-height |
| `GenTrapezoid` | `(dz, theta, phi, dy1, dx1, dx2, alpha1, dy2, dx3, dx4, alpha2)` | GEANT4-like `GenTrap`; `dz` = half-height; the angles are deg and must lie in 0…90 (the positivity check is applied to the angles too, so negative angles are rejected) |
| `Polyhedron` | `(zPlanes, rMin, rMax, sideCount=6, phiStart_deg=0, phiDelta_deg=360)` | equal-length arrays; per-plane `rMin <= rMax` checked |
| `PolyCone` | `(vec_z, vec_rmin, vec_rmax, phiStart_deg=0, phiDelta_deg=360)` | equal-length arrays; the z-planes must be monotonic |
| `Cone` | `(rmaxBot, rmaxTop, z, rminBot=0, rminTop=0, phiStart_deg=0, phiDelta_deg=360)` | conical frustum; **the docstring says "Height" for `z`, but the value is passed straight to VecGeom's `UnplacedCone(..., dz, ...)` — it is a *half*-height.** |
| `Paraboloid` | `(rbot, rtop, halfHeight)` | |
| `HyperbolicTube` | `(rmax, inst, outst, halfHeight, rmin=0)` | hyperbolic tube; `inst`/`outst` stereo angles in deg, must not exceed 90° (the check rejects a value above 90°; "less than 90° suggested"). The old misspelling `HypebolicTube` still constructs but emits a `DeprecationWarning` |
| `Ellipsoid` | `(dx, dy, dz, zBottomCut=0, zTopCut=0)` | semi-axes; optional z cut planes (both 0 = uncut) |
| `Tetrahedron` | `(p1, p2, p3, p4)` | the 4 corner vectors |
| `ArbTrapezoid` | `(xy1, xy2, ..., xy8, halfz)` | 8 corner `(x, y)` points (VecGeom Arb8) |
| `Tessellated` | `(polydata, tranMat=None)` | **pyvista `PolyData` only** (checked); optional pre-transform of the points via a `Transformation3D`; prints a warning above 100 faces — triangulate the mesh first for safety |
| `CutTube` | `(rmax, halfHeight, botNormal, topNormal, rmin=0, sphi=0, dphi=360)` | **unimplemented — raises `NotImplementedError`** ("got problems, see issue") |

Two traps to know about:

- **Half-height caveat.** `Box` takes half-lengths, and the axial size of `Tube`, `Trapezoid`,
  `GenTrapezoid`, `Cone`, `HyperbolicTube`, `ArbTrapezoid` and `Paraboloid` is a **half**-height —
  except that the `Cone` docstring calls its `z` parameter "Height" while the code passes it
  through as VecGeom's `dz` (half-height). When in doubt, build the solid and check
  `Volume.getCapacity()` (returns the capacity in mm³) against the analytic value.
- **Angles are degrees — pass plain numbers.** The Python API takes plain degrees and converts
  internally. In-tree tests that pass `np.deg2rad(...)` values get them converted a *second*
  time (`Tube(1.0, 2.0, 5.0, 0, np.deg2rad(90))` is really a ~1.57° arc, not a quarter tube).
  Trust the parameter docs ("in deg") and **pass plain numbers**, never `np.deg2rad(...)` —
  the class docstring examples now do the same.

Note on keyword spellings: the canonical angular keywords are the `phiStart_deg`/`phiDelta_deg`
(and `thetaStart_deg`/`thetaDelta_deg` on `Sphere`) and `alpha1`/`alpha2` (`GenTrapezoid`) names
shown in the table. Older spellings (`startphi`/`deltaphi`, `starttheta`/`deltatheta`,
`startPhi`/`deltaPhi`, `sphi`/`dphi`, `Alpha1`/`Alpha2`) are still accepted but emit a
`DeprecationWarning`, and passing both a canonical and a deprecated spelling of the same angle
raises `ValueError`. Positional call order is unchanged.

## 5. Boolean solids

Three CSG classes combine two solids into a new, ordinary unplaced volume that can be used
anywhere a shape can — including as the `left` operand of further booleans:

```python
SolidUnion(left, right, right_transf3d=Transformation3D())
SolidIntersection(left, right, right_transf3d=Transformation3D())
SolidSubtraction(left, right, right_transf3d=Transformation3D())
```

The `right` solid is transformed by `right_transf3d` into the `left` frame before the operation.
The typical real-world pattern — a closed vessel built as the union of a side wall with two
end caps in one solid — comes from
[`src/pythontests/prompt_solids/test_prompt_geoBooleanOperation.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_solids/test_prompt_geoBooleanOperation.py)
(simplified here):

```python
from Cinema.Prompt.solid import Tube, SolidUnion
from Cinema.Prompt.geo import Transformation3D, Volume

# pre-moderator vessel as ONE solid: annular side wall closed by two caps
side  = Tube(83, 89, 73)                 # annular wall, half-height 73 mm
cap_b = Tube(0, 89, 9)                   # cap at the +z end, half-height 9 mm (the upstream test's "bot")
cap_t = Tube(0, 89, 14)                  # cap at the -z end, half-height 14 mm (the upstream test's "top")
sol   = SolidUnion(side, cap_b, Transformation3D(z=64))    # cap spans z = 55..73
sol   = SolidUnion(sol, cap_t, Transformation3D(z=-59))    # cap spans z = -73..-45
vol   = Volume("premod", sol, matCfg='Al_sg225.ncmat')
```

Visualisation caveat: boolean solids cannot be tessellated by VecGeom directly. The viewer and
the `Mesh` iterator detect them, mesh the two children separately and combine the meshes with
**vtkbool** operations — an explicitly experimental path that falls back to a slow point-cloud
surface reconstruction on failure. If a boolean volume renders oddly, rerun before debugging the
geometry.

## 6. Materials on volumes

`matCfg` accepts either a config string or a `Material` object (its `.cfg` is used), and
`surfaceCfg` takes a surface-physics string (e.g. `'physics=Mirror;m=2'` or
`'mirror=Al;substrate=Al'`); both can also be set later with `vol.setMaterial(cfg)` /
`vol.setSurface(cfg)`.

Two things every user must know:

- **`matCfg=None` is NOT vacuum.** It configures the default material
  `'freegas::H1/1e-26kgm3/H_is_1_H1'` — a very dilute hydrogen gas used as a stand-in for
  "nothing". It is a real material that neutrons can scatter on (extremely rarely). If you care
  about what fills your world, be explicit: `Volume` now prints a one-time `RuntimeWarning`
  naming the applied default, and `vol.matCfg` reports the applied string instead of staying
  `None`.
- **True void is `'void.ncmat'`** — a standard zero-density NCrystal data file (resolved from
  NCrystal's embedded standard data, not the repository's `ncmat/` directory), which is what the
  boolean-operation test uses for its world/simbox volumes:
  `worldsize = 500` and `Volume("world", Box(worldsize, worldsize, worldsize), "void.ncmat")`
  (in `test_prompt_geoBooleanOperation.py`). The repository's `ncmat/` data directory also ships
  a `vacuum.ncmat` (air at a vanishing density).

Because the material config is resolved by the NCrystal backend at `Volume` construction time, a
`Volume` **always** needs a resolvable material — even the freegas default. A missing or
misspelled data file, an unknown NCrystal key or a bad parameter value raises a normal Python
`ValueError` (the NCrystal error text is included); only a broken environment, such as the
missing-plugin setup described on the [Installation](install) page, can still abort inside C++.
Prefer an explicit `matCfg` on every volume. Config-string syntax, NCMAT files,
virtual materials and biasing are covered in [Materials and physics](materials-physics).

## 7. Scorers on volumes: a teaser

Scorers are attached to **logical volumes**, and fire for every placement of that volume. The
short version:

```python
tof = TOFHelper("TOF", ptstate='ABSORB')
tof.make(vol)                       # attach (mandatory); internally calls vol.addScorer(self, cobj)
                                    # with the freshly created C++ scorer

# one scorer, several placements: group copies with scorerGroup (= the copy number)
world.placeChild("detPhyVol_A", det, Transformation3D(0, 0, 1000), scorerGroup=1)
world.placeChild("detPhyVol_B", det, Transformation3D(0, 0, 2000), scorerGroup=2)
```

`make()` and a bare `vol.addScorer(tof)` are **not** interchangeable: `make()` is the
call that creates the C++ scorer and hands its pointer to `addScorer`; called without
that pointer, `addScorer` runs its config-string branch (the legacy
`vol.addScorer('Scorer=TOF; ...')` route) and raises `AttributeError` on a helper
object, which has no `.cfg`.

Registered scorers land in the class-level `Volume.scorer_dict`, which is what
`sim.scorer` and `sim.gatherHistData(name)` read. `placeChild` prints
`"<name> Group ID <n>"` for every placement (from the C++ side, unconditionally) — that line is
the copy number being registered, not an error. The full catalogue, the `ptstate` semantics and
reading results are on the [Scoring](scorers) page.

## 8. `component.py` helpers (experimental)

`Cinema.Prompt.component` offers higher-level builders on top of `Volume`:

- `makeTrapezoidGuide(length, front_x, front_y, rear_x, rear_y, m, thickness=20., outer_mateiral='solid::Cd/8.65gcm3', inner_mat='freegas::H1/1e-26kgm3')`
  — a tapered mirror guide (inner trapezoid inside a larger mirrored one).
- `makeDiskChopper(r_outer, r_inner, phase, num_slit, freq, theta)` — a disk-chopper volume with
  the chopper surface model attached.
- `EntityArray` / `FlatAnalyser` — repeat/reflect/rotate helpers for detector and analyser arrays.

**Treat these as experimental.** The internal plumbing has been repaired: `Transformation3D`
multiplication (`refFrame * member.refFrame`) works, and `Anchor.getRelTransf`,
`EntityArray.reflect` (mirrors member positions across the XY/XZ/YZ plane, carrying orientations
over unchanged — with a warning when a member is rotated, since a mirrored orientation is not
representable), `make_rotate_z` (adds rotated copies of all existing members) and `selectByZ`
operate on real frame accessors again. They are still not exercised by the examples or the test
suite, so for production geometry the supported route remains explicit per-element `placeChild`
calls with explicit `Transformation3D` objects — as all examples and tests do. Note that
`makeDiskChopper` builds on the canonical `physics.DiskChopper`; constructing the old
`component.DiskChopper` alias directly emits a `DeprecationWarning`.

## 9. Gotchas

1. **Half vs full sizes.** `Box` takes half-lengths; the axial parameter of most shapes is a
   half-height; `Cone`'s docstring says "Height" but means half-height (section 4). Sanity-check
   with `Volume.getCapacity()` (mm³).
2. **All angles are degrees — pass plain numbers.** Some in-tree docstrings/tests pass
   `np.deg2rad(...)` values, which get double-converted (`Tube(1.0, 2.0, 5.0, 0, np.deg2rad(90))`
   is really a ~1.57° arc).
3. **`setWorld` closes the geometry and is one-shot.** All volumes and placements must precede
   it; a second call raises the catchable `RuntimeError: World exist already: only one world can
   be set per process`. The `Launcher` is a process-wide singleton, so a second `Prompt()` in the
   same process hits the same error — run each world in its own process. Rebuild with
   `sim.clear()`.
4. **Overlaps are checked, best-effort.** `placeChild` estimates the intersection of every new
   daughter against its sisters and emits a `RuntimeWarning` on overlap; pass
   `checkOverlap=False` to skip the scan (rule 3 above).
5. **Transformation algebra is partial.** `Transformation3D.__mul__` now exists (`a * b`
   applies `b` first), but `inv()` and `Volume.placeArray` are still commented out; invert
   rotations via scipy and place arrays with explicit loops.
6. **`from_alignment`/`setRotByAlignment` are the canonical names.** The misspelled
   `from_alignement`/`setRotByAlignement` still work but emit a `DeprecationWarning`.
7. **`transform()` is global → local**; `transform_py` agrees with it again (the old
   non-zero-translation divergence is fixed) — either works.
8. **Default material is dilute H1 gas, not vacuum** (`freegas::H1/1e-26kgm3/H_is_1_H1`) —
   announced with a one-time `RuntimeWarning`. Use `'void.ncmat'` for true void, and give every
   volume an explicit, resolvable `matCfg` (bad configs raise `ValueError`).
9. **`placeChild` always prints** `"<name> Group ID <copyNo>"` — a C++-side notice, not an error.
10. **Registries are class-global.** `Volume.scorer_dict` is keyed by scorer name (duplicates
    collide); `Volume.volume_list` grows for the lifetime of the process (by design, for C++
    memory ownership).
11. **Shape limits.** `CutTube` raises `NotImplementedError`; `Tessellated` accepts only pyvista
    `PolyData` and warns above 100 faces; boolean solids mesh only via the experimental vtkbool
    path.
12. **`component.py` helpers are experimental** (section 8) — the repair made them functional,
    but they remain untested by the suite; write explicit `placeChild` loops for production.
13. **Viewer colours are random per volume** — regenerated every run, so saved screenshots are
    not reproducible figure-for-figure.

---

## Planned pages

The page below is planned for this wiki but does not exist yet; it is named here as plain
text only: legacy-gdml (the v1 GDML input path). The visualization, guns, units and faq
material now has its own pages — see the wiki map on [home](home).

## Where to go next

- [Your first simulation](first-simulation) — a line-by-line walkthrough of the example above
- [The Simulation class](simulation-lifecycle) — life-cycle, seeds, MPI
- [Materials and physics](materials-physics) — NCrystal config strings, surfaces, biasing
- [Scoring](scorers) — the scorer catalogue and `ptstate` semantics
- [Installation](install) — environments and the NCrystal setup this page depends on

---

*Source files: [`geo.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/geo.py),
[`solid.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/solid.py),
[`component.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/component.py),
[`doc/example_basic.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py),
shape tests in [`src/pythontests/prompt_solids/`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/pythontests/prompt_solids/).
Questions: cinema-users@outlook.com.*
