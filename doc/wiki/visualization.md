# Visualisation: geometry and trajectory viewing

Cinema/Prompt ships a 3-D viewer built on [pyvista](https://github.com/pyvista/pyvista).
`sim.show(gun, n)` meshes the closed geometry and overlays the trajectories of `n` gun
events; the `Mesh` iterator gives programmatic access to the same meshes without any
window. This page documents Cinema 2.1.0. Sources of truth:
[`Visualiser.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Visualiser.py),
[`Mesh.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Mesh.py),
[`launcher.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/launcher.py)
and
[`cli/promptcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/promptcli.py).

The viewer needs a world that was closed with `setWorld` — it walks the C++ geometry
tree, not the Python objects you built it from. How to build that world is on
[Geometry](geometry) and in [Your first simulation](first-simulation).

```python
sim.show(gun, 100)      # geometry + 100 trajectories, interactive window
sim.show(gun, 0)        # geometry only
sim.show(None, 0)       # geometry only, no gun needed
```

> **Legacy notice.** GDML file input (`prompt -g file.gdml`) is legacy v1 functionality; its
> visualise branch (`-v`) currently fails with a `TypeError` before any window opens (see
> section 9). It is not covered on this page — build and view geometry with the Python API.

## 1. Mental model and a runnable minute

Three layers, one geometry:

| Layer | Entry point | Window? | Files? |
|:---|:---|:---|:---|
| Simple call | `sim.show(gun, n)` | yes (off-screen if no display) | no |
| Scripted meshing | the `Mesh` iterator (section 7) | no | your own code |
| Direct `Visualiser` (section 8) | `Visualiser(...).show()` | yes | screenshots, HTML export |

`show` is a method of the simulation object after `makeWorld()`. It always renders the
*whole* closed world — there is no camera path, no partial render and no file output. To
save images, drive the `Visualiser` and its pyvista plotter (section 8).

Every example below is a complete, runnable script in
[`doc/wiki/examples/`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/wiki/examples);
each writes only into its working directory and runs in seconds:

| Example | Demonstrates | Runtime |
|:---|:---|:---|
| `ex_materials_units.py` | mm units, Box **half**-lengths, materials by name — no rendering | ~3 s |
| `ex_mesh_iterator.py` | meshes without any window; boolean-solid handling | ~5 s |
| `ex_minimal_show.py` | smallest world, off-screen render, save a PNG | ~5 s |
| `ex_nested_volumes.py` | world → box → smaller box (top-down nesting) | ~5 s |
| `ex_headless_show.py` | the no-display cluster/CI recipe | ~4 s |
| `ex_show_options.py` | `byMat`, `addLegend`, axis scaling | ~7 s |
| `ex_scorer_show.py` | trajectories in the viewer + a scored histogram | ~7 s |

The examples are smoke-tested by `src/pythontests/test_wiki_examples.py`, which runs each
one in a fresh temporary directory.

## 2. Installation and dependencies

The plotting stack is an **optional extra** of the package:

```bash
pip install "neutron-cinema[viz]"    # pyvista + matplotlib + tetgen
```

| Package | Needed for | If it is missing |
|:---|:---|:---|
| `pyvista` (+ VTK) | every kind of viewing and meshing | the plotting modules refuse to import: `ImportError: pyvista is required to visualize.` |
| `matplotlib` | the histogram/plot layer, and the headless backend switch (section 6) | `import Cinema.Prompt` and the `Mesh` iterator still work, but `show` fails when the `Visualiser` module is imported (`import matplotlib.colors` at its top) and histogram `plot()`/`savefig()` fail at call time |
| `tetgen` | `geoClip` only (builds the volumetric mesh the clip widget cuts) | **graceful degradation**: the render continues without clipping, printing the tetgen hint and `Fall back without geoClip` (section 4) |
| `vtkbool` | meshing **boolean solids** (`SolidUnion`/`SolidIntersection`/`SolidSubtraction`) — VecGeom cannot tessellate them directly | experimental fallback: surfaces are point-sampled and reconstructed (`reconstruct_surface`); slow, approximate, and the console says so |
| `trame` | embedded rendering in Jupyter (section 6) **and** the `exported.html` export (section 5) | the HTML export raises `ImportError: Please install trame dependencies: pip install "pyvista[jupyter]"` |
| `psutil` | the Jupyter-session detection heuristic | Jupyter auto-detection is skipped |
| `libgl1` (system) | VTK rendering on headless Linux servers | rendering/imports fail; the source-build recipe on [Installation](install) includes it |

`vtkbool`, `trame` and `psutil` are not part of the `[viz]` extra — install them separately
if you need boolean-solid meshing, notebook embedding or the HTML export.

## 3. `sim.show(gun, n)`

| Class | Signature | Notes |
|:---|:---|:---|
| `Prompt.show` | `(gun, num=0, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False)` | serial use |
| `PromptMPI.show` | identical signature | only rank 0 renders; all ranks then meet at a barrier |

`gun` accepts the same three forms as `simulate`: a gun object, a gun config string, or a
`PythonGun` instance. With `num=0` (or `gun=None`) no trajectories are drawn.

What happens under the hood (`Launcher.showWorld`):

1. a pyvista plotter is created (1920 x 1080 window), axis scales applied, axes drawn at the
   origin;
2. every node of the closed geometry is tessellated (VecGeom `CreateMesh3D`,
   `nSegments=30`) and added as a translucent surface actor;
3. if `num > 0`, the gun is **re-simulated event by event with trajectory recording** — for
   config-string guns via `go(1, recordTrj=True)`, for `PythonGun` objects via
   `gun.generate()` + `simOneEvent(recordTrj=True)`;
4. each recorded trajectory (an `(N, 3)` array of step positions in mm) becomes a blue
   polyline (opacity 0.2, line width 2) with red dots on its intermediate points (size 8,
   opacity 0.3); trajectories with fewer than two points are silently skipped;
5. the window opens with the default camera `view_zy` — see section 5 for what that means
   geometrically.

### 3.1 What is plotted

- **One actor per placement.** Every physical volume (i.e. every `placeChild`) gets its own
  mesh and actor — a logical volume placed N times is drawn N times.
- **Surfaces, translucent.** Volumes are drawn as surfaces at opacity 0.3 (0.5 under
  `geoClip`) with depth peeling, so nested structures stay visible. There is no
  wireframe/edge mode in `show`; publication-style styling means driving pyvista actors
  yourself via the `Mesh` iterator (section 7).
- **Random colour per volume.** Each volume gets a `random.choice` from a fixed 28-colour
  high-contrast palette at meshing time. `byMat=True` switches to one colour per material.
- **Coordinates are world coordinates in mm**, drawn 1:1 — a 20 m beamline is 20000 units
  long and needs the `zscale`-style axis scaling to be readable. Bounds, an axes widget at
  the origin and a grid are drawn around the scene.

**Under MPI only rank 0 renders**; all other ranks wait at a `comm.Barrier()` until the
window is closed. The window is interactive and blocks the calling process: **do not call
`show` in batch scripts or CI** — `doc/example_basic.py` ships with `sim.show(gun,100)`
active for interactive use; for a batch run, comment that line out and uncomment the
`sim.simulate(gun,1e7)` line instead (the swap is spelled out in
[Your first simulation](first-simulation)).

Trajectories are *not* cached from a previous `simulate`: `show` runs its own `num`-event
re-simulation, so its cost scales linearly with `num`. Measured on the machine used to
prepare this wiki (October 2026, single process, seed 4096, the `doc/example_basic.py`
world and `UniModeratorGun` defaults): the transport-only part of the overlay took 0.005 s
for `n=500` and 0.297 s for `n=20000` (~0.015 ms/event for this toy model; your per-event
cost is whatever your production simulation costs). A few hundred trajectories are
effectively free; a trajectory plot of 1e6 events is a 1e6-event simulation. Plotting
start-up itself (VTK initialisation) is about a second. See section 10 for where the rest
of the render time goes.

## 4. Keyword options (identical on `Prompt.show` and `PromptMPI.show`)

| Option | Default | Effect |
|:---|:---|:---|
| `mergeMesh` | `False` | combine all volumes into a single actor ("Combined geometry", one random colour). Mutually exclusive with `byMat` and `geoClip` — those silently un-merge it with a `WARNING`. Picking then reports "Material not defined for a combined geometry" |
| `xscale`, `yscale`, `zscale` | `1.0` | anisotropic axis scaling of the *drawing* (geometry stays in mm). A 20 m beamline with mm-sized detectors is unreadable at scale 1 — squash the beam axis (`zscale=0.02`) or stretch the transverse ones. There is no automatic fitting |
| `byMat` | `False` | one colour per **material** instead of per volume; volumes sharing a material get the same colour, labels become `name[material]` |
| `addLegend` | `False` | legend box (upper left), sized from the number of geometry-tree nodes. Note the `Visualiser` class default is `True`; it is `show` that turns it off |
| `geoClip` | `False` | interactive clipping-plane widget for looking inside volumes. Builds a **volumetric (tetrahedral) mesh per volume with tetgen**, then clips it — surface clipping would leave hollow shells. The plane normal is fixed along **x** and the interactive widget is attached to the world volume only. Clipped volumes are drawn at opacity 0.5 (not the 0.3 of the plain path). `geoClip` disables `mergeMesh` (with a `WARNING`) and clears the blacklist (the world must not be masked) |

`byMat` is the tool for "which physics is where" questions; the default per-volume colouring
is the tool for "which placement is where" (picking prints both names either way).

### 4.1 `geoClip` failure behaviour: degrade, do not die

`geoClip` is designed to fail soft. If the volumetric meshing or clipping of a volume
fails — including the case where **tetgen is not installed** — the viewer prints the
underlying error plus

```text
Warning: Failed to visualize <volume> with geoClip. Fall back without geoClip.
```

discards the clipping for the whole scene and re-renders everything as ordinary translucent
surface meshes. The process survives; the plot is simply unclipped (a missing tetgen prints
`ModuleNotFoundError: tetgen is required. Use 'pip install tetgen' to install.` first).
This behaviour is pinned by `src/pythontests/test_viz_geoclip_fallback.py`.

Two caveats:

- the fallback **re-meshes the entire scene** (a full re-tessellation of every volume), so
  a failed `geoClip` render costs roughly double;
- if the *retry itself* throws, the viewer gives up with `sys.exit(1)` — one of the very
  few places where library code can still kill your process (section 8).

### 4.2 `geoClip` + picking: a known limitation

Under `geoClip` the picked mesh (the volumetric one) does not match the stored actor (the
surface one), so pressing `m` on a clipped volume raises
`ValueError: Selected mesh has no actor.`. Avoid masking volumes in a clipped scene; render
without `geoClip` when you want to pick-and-mask.

## 5. The interactive window

The scene is rendered translucent with depth peeling, an axes widget at the origin, a grid
and the scene bounds. The default camera is pyvista's `view_zy`: the camera looks **along
−x** with the view-up vector (0, 1, 0) — **y is drawn vertical and the +z beam axis
horizontal**. Use the standard pyvista mouse controls to rotate/zoom.

Mesh picking is enabled: **right-click a surface (or press `p`)** and the console prints

```text
Picked volume info:
	- Volume name: samplePhyVol
	- Material: physics=ncrystal;nccfg='Ge_sg227.ncmat;...'
```

i.e. the physical-volume name from `placeChild` and the material physics config. This is the
fastest way to find out what you are looking at — and why volume names given to
`placeChild` should be meaningful. The viewer passes `show_message=False` to pyvista, so the
on-screen hint that pyvista would normally draw is suppressed — a plain left-click just
orbits the camera, and this page is the only reminder of the binding. Trajectories are
pickable actors too (labelled `Trajectory` and `Interections` — the typo is in the source —
with material "Not defined").

Key bindings:

| Key | Action |
|:---|:---|
| `s` | save `screenshot.svg` in the working directory (the console print says "screenshot.png"; the file written is the SVG) |
| `m` | mask the picked volume (removes its actor; masked names are listed). Raises `ValueError` under `geoClip` (section 4.2) |
| `u` | unmask — bring back all masked volumes |
| `r` | reload: clear and re-mesh/re-plot everything |

For raster images (`PNG`) use `plotter.screenshot(...)` on a direct `Visualiser` — the
examples do exactly that.

Artefacts the viewer can write:

- `screenshot.svg` — the `s` key above (vector graphic of the current view);
- `exported.html` — a standalone interactive 3-D web export (`plotter.export_html`),
  written when the `Visualiser` is built with `doDumpMesh=True`. Not reachable through
  `show()` — only through a direct `Visualiser` construction (section 8). The export needs
  the `trame` package (`pip install "pyvista[jupyter]"`) even outside Jupyter; without it,
  the run dies with `ImportError` the moment the dump executes — after the meshes were
  already built and plotted.

## 6. Headless, clusters and Jupyter

**The recipe for clusters and CI** (spelled out and tested in
`doc/wiki/examples/ex_headless_show.py`):

```python
import os
os.environ.pop("DISPLAY", None)             # no X server needed
os.environ.setdefault("MPLBACKEND", "Agg")  # before matplotlib is imported
import pyvista
pyvista.OFF_SCREEN = True                   # plotter.show() renders and returns
```

With that in place `sim.show(...)` renders off-screen through VTK's EGL fallback — no
display, no window, nothing to interact with — and `plotter.screenshot("file.png")` saves
the image. On some software-rendering stacks the off-screen path prints VTK
`vtkOpenGLQuadHelper ... Error binding ndCoords` warnings; they are noise, the render
completes. A small world renders in about a second wall-clock including VTK start-up.

Cinema also protects itself, in two ways worth knowing:

- **The display probe.** At package import (and again before every `showWorld`/`show`) the
  launcher checks whether a `DISPLAY` that is set is actually reachable — a dead SSH X
  forwarding would otherwise hang matplotlib and VTK, and stall an MPI job on the rank
  barrier. When the probe fails it warns on stderr and degrades to headless rendering:

  ```text
  WARNING: DISPLAY=... is set but not reachable within 2.0s, forcing headless rendering (matplotlib Agg backend, VTK off-screen); interactive show() is disabled.
  ```

  After the degradation the render still happens off-screen, but keys, picking and
  screenshots are unavailable (there is nothing to interact with). Because the probe runs
  at import time, this warning can appear before your script has done anything at all.
  A simply *unset* `DISPLAY` is the normal headless case: nothing is warned, but set
  `pyvista.OFF_SCREEN = True` explicitly to keep `show()` non-blocking.

- **Jupyter auto-detection.** In a JupyterLab session (detected via a psutil
  parent-process/env heuristic) pyvista is switched to the `trame` backend automatically,
  so the window is embedded in the notebook. The heuristic can mis-detect classic notebook
  front-ends started from JupyterLab.

Batch/CI guidance: guard or omit `show` calls — even off-screen they cost a render, and
with a display present they open a blocking window.

## 7. Scripted inspection: the `Mesh` iterator

The same meshes the window shows can be produced in a plain script — useful for off-screen
screenshots, sanity checks of sizes, or building custom figures:

```python
from Cinema.Prompt.Mesh import Mesh

for m in Mesh():                       # walks every node of the closed geometry
    name, mesh = m.getMesh(30)         # (physical-volume name, pyvista PolyData)
    print(name, m.getMaterialName(), mesh.n_points)
```

Verified transcript (October 2026) for the world of
`doc/wiki/examples/ex_mesh_iterator.py` — a void world with one boolean-solid volume (a
slab with a slot cut out, meshed via the point-cloud fallback here because vtkbool was not
installed) and one plain sample box, meshed with `getMesh(30)`:

```text
world        void.ncmat      8 points
boolPhy      Cd.ncmat     2334 points  (boolean: point-cloud fallback)
samplePhy    Al_sg225.ncmat   8 points
```

The boolean point count is **construction-dependent**: the fallback samples the two child
solids as a point cloud and reconstructs a surface from it, so the result varies with the
solids and the VTK version. Read the number above as an order of magnitude, not an anchor.

Per node the iterator exposes `getMeshName()`/`getPhysicalVolumeName()` (the names used in
viewer labels, picking and blacklists), `getMaterialName()` (the physics config string),
`getLogVolumeInfo()`, `meshInfo()` (raw tessellation statistics, including the left/right
child ids and operation code of boolean nodes) and `printMesh()` (dumps the whole node
tree). The iterator requires a closed world — it walks the C++ geometry manager singleton,
not your Python objects.

`getMesh(nSegments=30, byPointCloud=False)` — `nSegments` is the tessellation fineness per
curved solid; mesh size grows linearly with it (a tube yields 124 points at the default 30,
1204 at 300). Note `meshInfo()` has its own default (`nSegments=10`), finer than the rest
of the stack. Boolean-solid nodes are detected and handled by meshing the two children
separately and combining them with vtkbool set operations (`|` union, `&` intersection,
`-` difference); pass `byPointCloud=True` to force the point-cloud reconstruction instead
of even attempting vtkbool.

> **Experimental.** The code itself warns: *"Meshing boolean operation via `vtkbool` is
> highly experimental. May be a rerun can solve it."* When the vtkbool path fails (or
> vtkbool is not installed), the node falls back to a point-cloud surface reconstruction.
> Expect slow meshing and approximate surfaces for boolean volumes; if one renders oddly,
> rerun before debugging the geometry.

## 8. The `Visualiser` class (advanced escape hatch)

`sim.show` is a thin, opinionated wrapper. For everything it does not expose — blacklists,
tessellation control, HTML export, screenshots — construct the viewer yourself:

```python
from Cinema.Prompt.Visualiser import Visualiser

v = Visualiser(blacklist=['world'], nSegments=60)
v.plotter.set_scale(1.0, 1.0, 0.05)     # squash z for a long beamline
v.set_plotter_style()
v.show()                                # off-screen if no display (section 6)
v.plotter.screenshot('myview.png')      # raster export
```

`Visualiser(blacklist, printWorld=False, nSegments=30, mergeMesh=False, doDumpMesh=False,
window_size=[1920,1080], byMat=False, addLegend=True, geoClip=False)` — the full signature;
the `show` keyword options of section 4 are a subset. `addLegend` defaults to `True` here
but `show()` passes `False`. `doDumpMesh=True` additionally writes `exported.html` — but
only if `trame` is installed (section 5); with a plain pyvista install the run ends in
`ImportError` when the dump executes.

- **Blacklist semantics**: each entry is a **substring**, matched against the
  physical-volume name *and* the material name — `blacklist=['air']` hides every volume
  whose name or material contains "air", including e.g. `NaI_air`. Note the filter runs
  *after* tessellation, so blacklisted volumes are meshed and then discarded (section 10).
- **Public state** for custom tooling: `selected_mesh`, `selected_actor` and
  `mesh_actor_pair` (populated by picking); the plotter is a `PtPlotter` pyvista subclass
  whose `addClipPlane`/`addClippedMesh` helpers implement the `geoClip` path.
- **Failure edge**: if the first render fails, the viewer rebuilds the plotter and retries
  once; if the retry also fails it calls `sys.exit(1)` — keep that in mind before
  rendering untrusted geometries inside a long-lived process.

See the class docstrings in
[`Visualiser.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Visualiser.py)
for the remaining details.

## 9. CLI visualization flags

`prompt -g script.py -v` visualises a script instead of simulating it (the CLI is
documented on [CLI](cli)). The viewer-related flags:

| Flag | Python-script mode (`-g sim.py`) | Legacy GDML mode (`-g file.gdml`) |
|:---|:---|:---|
| `-v/--visualize` | forwarded: `sim.show(gun, n)` | broken — dies with `TypeError` before rendering (name shadowing, below) |
| `-Z/--zscale` | forwarded as `zscale` (default 1.0) | parsed, unused |
| `-n/--neutronNum` | supplies the trajectory count `n` (default 100) | event count |
| `-b/--blacklist NAMES...` | parsed, **silently ignored** | passed to the viewer |
| `-m/--mergemesh` | parsed, **silently ignored** | passed to the viewer |
| `--nSeg N` | parsed, **silently ignored** (default 30) | passed to the viewer |
| `-d/--dumpmesh` | parsed, **silently ignored** | would pass `dumpMesh=...`, which the `Visualiser` class does not accept (it expects `doDumpMesh`) — but the branch dies before that kwarg is ever checked (see below) |

In Python-script mode only `-v` and `-Z` reach your simulation, and `n` comes from
`-n/--neutronNum`. If you need blacklisting, tessellation control or the HTML export from
Python, construct the `Visualiser` directly (section 8).

The legacy GDML `-v` branch fails before any of these options matter. `promptcli.py` opens
with `from Cinema.Prompt import Prompt, PromptMPI, Visualiser`, but the package `__init__.py`
never imports the class, so the name `Visualiser` binds the *submodule*
`Cinema.Prompt.Visualiser`. The branch's `Visualiser(blacklist, ..., dumpMesh=...)` call
then raises `TypeError: 'module' object is not callable` before any window or kwarg
validation. The `dumpMesh`-vs-`doDumpMesh` spelling in that call is a real second bug, but
a masked one: it is never reached, so correcting the kwarg alone does not un-break the
branch. Until this is repaired, view GDML-defined geometry by rebuilding it with the Python
API ([Geometry](geometry)) and using `sim.show`.

## 10. Performance notes

- **`show` re-simulates**: the `n` trajectories cost `n` transport events (section 3).
  Do not "preview" with `n=1e6`.
- **Meshing scales with placements and `nSegments`.** Every placement is tessellated
  separately — no instancing, no caching between renders or `r` refreshes. A logical
  volume placed N times is meshed 2N times per render (each visible solid is tessellated
  twice: once to count, once to fill the buffers). Keep `nSegments` (default 30) modest on
  large assemblies; the raw numbers are tiny for toy worlds (~10 ms for 25 boxes) but grow
  linearly.
- **Blacklists are not free**: the filter runs after tessellation, so blacklisted volumes
  are fully meshed (twice) and then thrown away. `geoClip` clears the blacklist entirely —
  every volume is meshed *and* tetrahedralised.
- **Legend/labels**: a pyvista label is attached to every actor even when no legend is
  requested (it is what the legend would print); the legend box itself is only added with
  `addLegend=True`, sized from the node count. Dropping the legend saves its construction,
  not the labels.
- **Off-screen rendering** (EGL) initialises VTK in about a second; the display probe
  itself is negligible but runs once at import. For CI, prefer the `Mesh` iterator
  (section 7) when you only need data, and render images only where a figure is the
  deliverable.

## 11. Troubleshooting

| Symptom | Cause | What to do |
|:---|:---|:---|
| `ImportError: pyvista is required to visualize.` | plotting stack not installed | `pip install "neutron-cinema[viz]"` |
| `WARNING: DISPLAY=... is set but not reachable within 2.0s ...` | dead SSH X forwarding; the auto-degradation to headless fired | expected on stale forwards; unset `DISPLAY` or repair forwarding; interactive keys are gone for this process |
| No window appears on the cluster | you are headless — that is the designed behaviour | render to files with `Visualiser` + `plotter.screenshot` (section 8, examples) |
| `ModuleNotFoundError: tetgen is required...` then `Fall back without geoClip` | `geoClip=True` without tetgen | install tetgen to get clipping; the unclipped render is otherwise fine |
| Boolean volume looks wrong; "highly experimental" printed | vtkbool path failed, point-cloud fallback used | rerun; or force `byPointCloud=True` (section 7) |
| Pressing `m` raises `ValueError: Selected mesh has no actor.` | masking under `geoClip` (surface/volumetric mismatch, section 4.2) | pick-and-mask in a non-clipped render |
| Screenshots differ pixel-for-pixel between runs | random per-volume palette, no seed | use `byMat=True` for stable per-material colours within one render |
| Console says "save screenshot.png" but the file is `screenshot.svg` | stale print text | the SVG is the artefact; use `plotter.screenshot` for PNG |
| `ImportError: Please install trame dependencies: ...` on HTML export | `trame` missing | `pip install "pyvista[jupyter]"` |
| Batch script never returns after `show` | interactive window blocks the process | do not call `show` in batch/CI (section 6) |
| Long beamline is an unreadable sliver | 1:1 mm drawing, no auto-fit | `zscale=0.02`-style axis scaling (section 4) |
| `-b/-m/-d/--nSeg` seem dead in `prompt -g sim.py` | only `-v` and `-Z` are forwarded (section 9) | use a direct `Visualiser` |
| `Warning: Mesh ... is empty, not abled to visualize.` | a solid produced no tessellation | check the solid's parameters ([Geometry](geometry)) |
| MPI job appears stuck after `show` | rank 0 is showing an interactive window; the rest wait at the barrier | close the window; keep interactive `show` out of batch scripts |

## 12. Gotchas

1. **Colours are random.** Each volume (or material, under `byMat`) gets a `random.choice`
   from a fixed 28-colour high-contrast palette at meshing time. Two runs of the same
   simulation look different, and saved screenshots are **not reproducible
   pixel-for-pixel**. There is currently no seed or option to pin the colours.
2. **`show` re-simulates.** The `n` trajectories are produced by re-running the gun for
   `n` events with trajectory recording — the cost of `sim.show(gun, n)` scales linearly
   with `n` (section 3).
3. **`geoClip` without tetgen degrades, not exits.** The missing-dependency path raises a
   catchable error that the viewer turns into `Fall back without geoClip` (section 4.1).
   Only a *second*, post-retry failure ends the process (`sys.exit(1)`).
4. **Masking under `geoClip` is broken** (`Selected mesh has no actor.`) — section 4.2.
5. **Boolean solids mesh only experimentally** (vtkbool path, point-cloud fallback) —
   section 7. This affects both the window and the `Mesh` iterator.
6. **`mergeMesh` excludes `byMat` and `geoClip`.** Combos are auto-disabled with a
   `WARNING`, not an error.
7. **CLI flags beyond `-v`/`-Z` are silently ignored** in `prompt -g script.py` mode
   (`-b`, `-m`, `-d`, `--nSeg`), and the legacy GDML `-v` branch is broken outright
   (section 9). Use a direct `Visualiser` for those features.
8. **`show()` has no blacklist.** `Launcher.showWorld` constructs its `Visualiser` with an
   empty blacklist, so every volume is always meshed; to skip volumes use a direct
   `Visualiser` with `blacklist=['substring', ...]` (section 8).
9. **A dead `DISPLAY` degrades to headless** with a warning — and the probe already runs
   at import time, so the warning can precede your first statement (section 6). After the
   degradation, keys, picking and screenshots are unavailable.
10. **Translucency is the default, not a bug** — every volume is drawn at opacity 0.3
    (0.5 under `geoClip`) so nested structures stay visible. Publication-style styling
    means driving the pyvista actors yourself via the `Mesh` iterator (section 7).
11. **Large scenes**: meshing cost is dominated by the number of placements and
    `nSegments`, with no instancing or caching (section 10). For a big instrument,
    blacklist what you do not need — at the cost of still meshing the hidden volumes —
    or use `geoClip` to explore the inside of dense regions interactively.
12. **Trajectories are actors too**: polylines and the red dots are pickable, trajectories
    with fewer than two points are silently skipped (section 3).

## 13. Where to go next

- [Geometry](geometry) — the volumes, names and boolean solids the viewer renders
- [Runnable examples](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/wiki/examples) — seven small scripts, including the headless recipe
- [Your first simulation](first-simulation) — where `sim.show(gun, 100)` fits in the workflow
- [CLI](cli) — the `prompt -g ... -v` flags and their caveats
- [Installation](install) — environments; note `vtkbool`/`trame`/`psutil` are installs beyond the `[viz]` extra (section 2)
- [MPI at scale](mpi-scale) — the rank-0-only rendering and barrier semantics
- [Results analysis](results-analysis) — what to do after the window closes

---

*Source files: [`Visualiser.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Visualiser.py),
[`Mesh.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/Mesh.py),
[`launcher.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/launcher.py),
[`cli/promptcli.py`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/src/python/Cinema/Prompt/cli/promptcli.py),
[`doc/wiki/examples/`](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/wiki/examples).
Questions: cinema-users@outlook.com.*
