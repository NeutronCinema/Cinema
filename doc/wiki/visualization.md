# Visualisation: geometry and trajectory viewing

Cinema/Prompt ships an interactive 3-D viewer built on [pyvista](https://github.com/pyvista/pyvista).
`sim.show(gun, n)` meshes the closed geometry into a window and overlays the trajectories of `n`
gun events; the `Mesh` iterator gives programmatic access to the same meshes without any window.
This page documents Cinema 2.0.0a5. Sources of truth:
[`Visualiser.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Visualiser.py),
[`Mesh.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Mesh.py),
[`launcher.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/launcher.py)
and
[`cli/promptcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/promptcli.py).

The viewer needs a world that was closed with `setWorld` — it walks the geometry tree, not the
Python objects you built it from. How to build that world is on
[Geometry](geometry) and in [Your first simulation](first-simulation).

```python
sim.show(gun, 100)      # geometry + 100 trajectories, interactive window
sim.show(gun, 0)        # geometry only
```

> **Legacy notice.** GDML file input (`prompt -g file.gdml`) is legacy v1 functionality; its
> visualise branch (`-v`) currently fails with a `TypeError` before any window opens (see
> section 2). It is not covered on this page — build and view geometry with the Python API.

---

## 1. `sim.show(gun, n)`

`show` is a method of the simulation object, after `makeWorld()`:

| Class | Signature | Notes |
|:---|:---|:---|
| `Prompt.show` | `(gun, num=0, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False)` | serial use |
| `PromptMPI.show` | identical signature | only rank 0 renders; all ranks then meet at a barrier |

What happens under the hood (`Launcher.showWorld`):

1. a pyvista plotter is created (1920 x 1080 window), axis scales applied, axes drawn at the origin;
2. every node of the closed geometry is tessellated and added as a translucent actor;
3. if `num > 0`, the gun is **re-simulated event by event with trajectory recording** — for
   config-string guns via `go(1, recordTrj=True)`, for `PythonGun` objects via
   `gun.generate()` + `simOneEvent(recordTrj=True)`;
4. each recorded trajectory (an `(N, 3)` array of step positions) becomes a blue polyline
   (opacity 0.2), with red dots on its intermediate points;
5. the window opens with the default camera `view_zy` — looking along the x axis with the y
   axis drawn vertical (pyvista's viewup is (0,1,0)), so the +z beam axis appears horizontal.

**Under MPI only rank 0 renders**; all other ranks wait at a `comm.Barrier()` until the window is
closed. The window is interactive and blocks the calling process: **do not call `show` in batch
scripts or CI** — `doc/example_basic.py` ships with `sim.show(gun,100)` active for interactive
use; for a batch run, comment that line out and uncomment the `sim.simulate(gun,1e7)` line
instead (the swap is spelled out in [Your first simulation](first-simulation)).

Trajectories are *not* cached from a previous `simulate`: `show` runs its own `num`-event
re-simulation, so its cost scales linearly with `num`. Measured on the machine used to prepare
this wiki (October 2026, single process, seed 4096, the `doc/example_basic.py` world and
`UniModeratorGun` defaults): the transport-only part of the overlay took 0.005 s for
`n=500` and 0.297 s for `n=20000` (~0.015 ms/event for this toy model; your per-event cost is
whatever your production simulation costs). A few hundred trajectories are effectively free; a
trajectory plot of 1e6 events is a 1e6-event simulation. Plotting start-up itself (VTK
initialisation) is about a second.

`gun` accepts the same three forms as `simulate`: a gun object, a gun config string, or a
`PythonGun` instance.

## 2. Options

### 2.1 Keyword options (identical on `Prompt.show` and `PromptMPI.show`)

| Option | Default | Effect |
|:---|:---|:---|
| `mergeMesh` | `False` | combine all volumes into a single actor ("Combined geometry", one random colour). Mutually exclusive with `byMat` and `geoClip` — those silently un-merge it with a `WARNING`. Picking then reports "Material not defined for a combined geometry" |
| `xscale`, `yscale`, `zscale` | `1.0` | anisotropic axis scaling of the scene. A 20 m beamline with mm-sized detectors is unreadable at scale 1 — squash the beam axis (`zscale=0.02`) or stretch the transverse ones. There is no automatic fitting |
| `byMat` | `False` | one colour per **material** instead of per volume; volumes sharing a material get the same colour, labels become `name[material]` |
| `addLegend` | `False` | legend box (upper left), sized from the number of geometry-tree nodes. Note the `Visualiser` class default is `True`; it is `show` that turns it off |
| `geoClip` | `False` | interactive clipping-plane widget (plane normal along x) for looking inside volumes. Needs `tetgen` (section 4); disables `mergeMesh` and clears the blacklist; the plane widget is attached to the world volume. On failure it retries once without clipping |

`byMat` is the tool for "which physics is where" questions; the default per-volume colouring is
the tool for "which placement is where" (picking prints both names either way).

### 2.2 The `prompt` CLI equivalents

`prompt -g script.py -v` visualises a script instead of simulating it
(the CLI is documented on [CLI](cli)). The viewer-related flags:

| Flag | Python-script mode (`-g sim.py`) | Legacy GDML mode (`-g file.gdml`) |
|:---|:---|:---|
| `-v/--visualize` | forwarded: `sim.show(gun, n)` | broken — dies with `TypeError` before rendering (name shadowing, below) |
| `-Z/--zscale` | forwarded as `zscale` (default 1.0) | parsed, unused |
| `-b/--blacklist NAMES...` | parsed, **silently ignored** | passed to the viewer |
| `-m/--mergemesh` | parsed, **silently ignored** | passed to the viewer |
| `--nSeg N` | parsed, **silently ignored** (default 30) | passed to the viewer |
| `-d/--dumpmesh` | parsed, **silently ignored** | would pass `dumpMesh=...`, which the `Visualiser` class does not accept (it expects `doDumpMesh`) — but the branch dies before that kwarg is ever checked (see below) |

In Python-script mode only `-v` and `-Z` reach your simulation. If you need blacklisting,
tessellation control or the HTML export from Python, construct the `Visualiser` directly
(section 5).

The legacy GDML `-v` branch fails before any of these options matter. `promptcli.py` opens
with `from Cinema.Prompt import Prompt, PromptMPI, Visualiser`, but the package `__init__.py`
never imports the class, so the name `Visualiser` binds the *submodule*
`Cinema.Prompt.Visualiser`. The branch's `Visualiser(blacklist, ..., dumpMesh=...)` call then
raises `TypeError: 'module' object is not callable` before any window or kwarg validation.
The `dumpMesh`-vs-`doDumpMesh` spelling in that call is a real second bug, but a masked one:
it is never reached, so correcting the kwarg alone does not un-break the branch. Until this
is repaired, view GDML-defined geometry by rebuilding it with the Python API
([Geometry](geometry)) and using `sim.show`.

The blacklist semantics (wherever they are honoured): each entry is a **substring**; a volume is
skipped when its physical-volume name contains any entry (material names are matched too).

## 3. The interactive window

The scene is rendered translucent — every volume is added with opacity 0.3 by design — with depth
peeling, an axes widget at the origin, a grid and the scene bounds. The default camera is
`view_zy` (looking along x with y drawn vertical, so the +z beam axis appears horizontal); use
the standard pyvista mouse controls to rotate/zoom.

Mesh picking is enabled: **right-click a surface (or press `p`)** and the console prints

```text
Picked volume info:
	- Volume name: samplePhyVol
	- Material: physics=ncrystal;nccfg='Ge_sg227.ncmat;...'
```

i.e. the physical-volume name from `placeChild` and the material physics config. This is the
fastest way to find out what you are looking at — and why volume names given to `placeChild`
should be meaningful. The viewer passes `show_message=False` to pyvista, so the on-screen hint
("Right-click or press P to pick...") that pyvista would normally draw is suppressed — a plain
left-click just orbits the camera, and this page is the only reminder of the binding.

Key bindings:

| Key | Action |
|:---|:---|
| `s` | save `screenshot.svg` in the working directory (the console print says "screenshot.png"; the file written is the SVG) |
| `m` | mask the picked volume (removes its actor; masked names are listed) |
| `u` | unmask — bring back all masked volumes |
| `r` | reload: clear and re-mesh/re-plot everything |

Artefacts the viewer can write:

- `screenshot.svg` — the `s` key above (vector graphic of the current view);
- `exported.html` — a standalone interactive 3-D web export (`plotter.export_html`), written when
  the `Visualiser` is built with `doDumpMesh=True`. Not reachable through `show()` — only through
  a direct `Visualiser` construction (section 5). The export needs the `trame` package
  (`pip install "pyvista[jupyter]"`) even outside Jupyter; without it, `show()` dies with
  `ImportError: Please install trame dependencies: pip install "pyvista[jupyter]"` the moment the
  dump runs — after the meshes were already built and plotted.

## 4. Dependencies and environments

| Package | Needed for | If it is missing |
|:---|:---|:---|
| `pyvista` (+ VTK) | **hard dependency** of any viewing or meshing (`Mesh.py`/`Visualiser.py` refuse to import without it) | importing `Cinema.Prompt` fails at **import time** — and with it any simulation script, since `geo.py` imports `Mesh.py`: `ImportError: pyvista is required to visualize.` There is no `show()`-time degradation; pyvista must simply be installed |
| `vtkbool` | meshing **boolean solids** (`SolidUnion`/`SolidIntersection`/`SolidSubtraction`) — VecGeom cannot tessellate them directly | experimental fallback: surfaces are point-sampled and reconstructed (`reconstruct_surface`); slow, approximate, and the console says so |
| `tetgen` | `geoClip` only (builds the volumetric mesh the clip widget cuts) | the process **exits** (`sys.exit(1)`, "tetgen is required. Use 'pip install tetgen' to install.") — not caught by the clip-path fallback |
| `trame` | embedded rendering in Jupyter (auto-selected backend, below) **and** the `exported.html` export (section 3) — both outside as well as inside notebooks | install it to view inside notebooks or to run `Visualiser(..., doDumpMesh=True)`; without it the export raises `ImportError` |
| `psutil` | the Jupyter-session detection heuristic | — |
| `libgl1` (system) | VTK rendering on headless Linux servers | rendering/imports fail; the source-build recipe on [Installation](install) includes it |

Environment behaviour worth knowing:

- **Jupyter** sessions (detected via a psutil parent-process/env heuristic on the `jupyter-lab`
  process) automatically switch pyvista to the `trame` backend, so the window is embedded in the
  notebook. The heuristic can mis-detect classic notebook front-ends started from JupyterLab.
- **Headless servers**: `showWorld` runs a display sanity probe (`ensureDisplayUsable`). A
  `DISPLAY` that is set but unreachable (stale SSH forwarding) would otherwise hang VTK — and an
  MPI job on the rank barrier. When the probe fails it warns and degrades to headless rendering:

  ```text
  WARNING: DISPLAY=... is set but not reachable within 2.0s, forcing headless rendering (matplotlib Agg backend, VTK off-screen); interactive show() is disabled.
  ```

  The render still happens off-screen (verified on a headless node: `sim.show(gun, 5)` completes
  in about 1 s wall including VTK start-up) — but there is nothing to interact with, so keys,
  picking and screenshots are unavailable. For scripted use see section 5.

## 5. Scripted inspection: the `Mesh` iterator

The same meshes the window shows can be produced in a plain script — useful for off-screen
screenshots, sanity checks of sizes, or building custom figures:

```python
from Cinema.Prompt.Mesh import Mesh

for m in Mesh():                       # walks every node of the closed geometry
    name, mesh = m.getMesh(30)         # (physical-volume name, pyvista PolyData)
    print(name, m.getMaterialName(), mesh.n_points)
```

Verified transcript (October 2026) for the `doc/example_basic.py` world plus one boolean-solid
volume — construct it with
`boolvol = Volume("boolSolid", SolidSubtraction(Box(5,5,5), Box(2,2,8)), matCfg="Al_sg225.ncmat")`
and place it with `world.placeChild("boolPhyVol", boolvol)` before `setWorld` —
meshed with `getMesh(20)`; only the sample's ncrystal config string is elided (`'...'`),
while `Al_sg225.ncmat` is the complete string `getMaterialName()` returns:

```text
world        freegas::H1/1e-26kgm3/H_is_1_H1   8 points
boolPhyVol   Al_sg225.ncmat                    1347 points  (boolean: point-cloud fallback)
samplePhyVol physics=ncrystal;nccfg='Ge_sg227.ncmat;...'     8 points
```

The boolean point count is **construction-dependent**: the fallback samples the two child solids
as a point cloud and reconstructs a surface from it, so the result varies with the solids and the
VTK version. Read the number above as an order of magnitude for this toy subtraction, not as an
anchor.

Per node the iterator exposes `getMeshName()`/`getPhysicalVolumeName()` (the names used in viewer
labels, picking and blacklists), `getMaterialName()` (the physics config string),
`getLogVolumeInfo()`, `meshInfo()` (raw tessellation statistics, including the left/right child
ids and operation code of boolean nodes) and `printMesh()` (dumps the whole node tree). The
iterator requires a closed world — it walks the C++ geometry manager singleton, not your Python
objects.

`nSegments` is the tessellation fineness per curved solid; mesh size grows linearly with it
(a tube yields 124 points at the default 30, 1204 at 300). Boolean-solid nodes are detected and
handled by meshing the two children separately and combining them with vtkbool set operations
(`|` union, `&` intersection, `-` difference).

> **Experimental.** The code itself warns: *"Meshing boolean operation via `vtkbool` is highly
> experimental. May be a rerun can solve it."* When the vtkbool path fails (or vtkbool is not
> installed), the node falls back to a point-cloud surface reconstruction — the 1347-point mesh
> above is such a fallback. Expect slow meshing and approximate surfaces for boolean volumes; if
> one renders oddly, rerun before debugging the geometry.

For full control without the fixed `show` pipeline, drive the `Visualiser` yourself — this is
also the only Python-level route to the blacklist, `nSegments` and the HTML export:

```python
from Cinema.Prompt.Visualiser import Visualiser

v = Visualiser(blacklist=['world'], nSegments=60)
v.plotter.set_scale(1.0, 1.0, 0.05)     # squash z for a long beamline
v.set_plotter_style()
v.show()                                # off-screen if no display (section 4)
```

Pass `doDumpMesh=True` to additionally write `exported.html` — but only if `trame` is installed
(section 3); with a plain pyvista install the run ends in `ImportError` when the dump executes.

`Visualiser(blacklist, printWorld=False, nSegments=30, mergeMesh=False, doDumpMesh=False,
window_size=[1920,1080], byMat=False, addLegend=True, geoClip=False)` — the full signature; the
`show` keyword options of section 2 are a subset. Note that `addLegend` defaults to `True` here
but `show()` passes `False`.

## 6. Gotchas

1. **Colours are random.** Each volume (or material, under `byMat`) gets a `random.choice` from a
   fixed 28-colour high-contrast palette at meshing time. Two runs of the same simulation look
   different, and saved screenshots are **not reproducible pixel-for-pixel**. There is currently
   no seed or option to pin the colours.
2. **`show` re-simulates.** The `n` trajectories are produced by re-running the gun for `n` events
   with trajectory recording — the cost of `sim.show(gun, n)` scales linearly with `n` and is
   roughly the cost of simulating `n` events (section 1). Do not "preview" with `n=1e6`.
3. **`geoClip` needs `tetgen`, or the process exits.** The tetgen import failure path calls
   `sys.exit(1)`, which the clip-path exception handler does not catch. Install tetgen before
   using `geoClip=True`.
4. **Boolean solids mesh only experimentally** (vtkbool path, point-cloud fallback) — section 5.
   This affects both the window and the `Mesh` iterator.
5. **`mergeMesh` excludes `byMat` and `geoClip`.** Combos are auto-disabled with a `WARNING`,
   not an error.
6. **CLI flags beyond `-v`/`-Z` are silently ignored** in `prompt -g script.py` mode
   (`-b`, `-m`, `-d`, `--nSeg`), and the legacy GDML `-v` branch is broken outright
   (section 2). Use a direct `Visualiser` for those features.
7. **`show()` has no blacklist.** `Launcher.showWorld` constructs its `Visualiser` with an empty
   blacklist, so every volume is always meshed; to skip volumes use a direct `Visualiser` with
   `blacklist=['substring', ...]` (matched against physical-volume and material names).
8. **A dead `DISPLAY` degrades to headless** with a warning (section 4) — after that, `show`
   returns after an off-screen render instead of showing a window. Check stderr before wondering
   where your window went; this probe is also what keeps an unreachable X forward from hanging an
   MPI job at the rank barrier.
9. **Translucency is the default, not a bug** — every volume is drawn at opacity 0.3 so nested
   structures stay visible. Publication-style styling (opaque surfaces, fixed colours) means
   driving the pyvista actors yourself via the `Mesh` iterator (section 5).
10. **Large scenes**: meshing cost is dominated by the number of volumes, and the per-volume mesh
    by `nSegments` (default 30). For a big instrument, blacklist what you do not need (section 5),
    or use `geoClip` to explore the inside of dense regions interactively.

---

## Where to go next

- [Geometry](geometry) — the volumes, names and boolean solids the viewer renders
- [Your first simulation](first-simulation) — where `sim.show(gun, 100)` fits in the workflow
- [CLI](cli) — the `prompt -g ... -v` flags and their caveats
- [Installation](install) — the pyvista/vtkbool environment; note `tetgen` (needed for `geoClip`) and `trame` (needed for HTML export, section 3) are extra installs beyond that recipe
- [MPI at scale](mpi-scale) — the rank-0-only rendering and barrier semantics
- [Results analysis](results-analysis) — what to do after the window closes

---

*Source files: [`Visualiser.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Visualiser.py),
[`Mesh.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Mesh.py),
[`launcher.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/launcher.py),
[`cli/promptcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/promptcli.py),
[`doc/example_basic.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py).
Questions: cinema-users@outlook.com.*
