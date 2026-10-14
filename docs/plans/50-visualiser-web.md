# Plan: Browser (trame) Web Mode for the Visualiser

Issue: #50

## Motivation

The 3D visualisation (`Cinema/Prompt/Visualiser.py`, pyvista-based) can only
open a desktop VTK window, which is unusable on headless remote login nodes
and clusters. pyvista ships a trame backend (`pyvista.trame`, aiohttp/wslink)
that can serve any `Plotter` to a browser; this change wires it into the two
choke points of `Visualiser` (plotter creation and `show()`).

## Approach

* **Module-level `launch_web_service(plotter, mode, port, host, open_browser, block)`**
  in `Visualiser.py` serves any pyvista `Plotter`. It builds the pyvista trame
  UI on an *unstarted* trame server and then starts it with
  `exec_mode='main'` — the canonical blocking serve-until-interrupt pattern
  (wslink catches SIGINT/SIGTERM). pyvista's own `launch_server()` is NOT
  used: it hardcodes `exec_mode='task'`, whose loop ownership is ambiguous in
  a plain script. `block=False` serves from a background thread
  (`thread=True`, trame-managed) and returns the server for
  `stop_web_service()`; trame imports are lazy so the module still imports
  without trame installed.
* **`Visualiser` ctor kwargs**: `web=False, web_mode=None (-> 'client'),
  web_port=0, web_host=None, web_open_browser=True`. In web mode the plotter
  is built `off_screen`, the desktop key events (mesh picking, s/m/u/r) are
  not registered, `enable_depth_peeling()` is skipped (its GL support probe
  renders once off-screen and aborts on a host without a display — in client
  mode the browser renders via vtk.js anyway), and `show()` dispatches to the
  new `show_web()` which
  blocks serving until Ctrl+C. `plotter.show()` is never called on the web
  path — it would auto-close the render window and trame would reject the
  plotter (`CLOSED_PLOTTER_ERROR`).
* **kwargs plumbing**: `Launcher.showWorld`, `Prompt.show`, `PromptMPI.show`
  take `**kwargs` forwarded to `Visualiser` (MPI: rank 0 serves, the other
  ranks wait at the existing `Barrier`).
* **CLI**: `prompt -v --web [--web-mode client|server|trame] [--web-port N]
  [--web-host H] [--web-no-browser]` via a `_web_kwargs()` helper wired into
  both the GDML and the python-script visualisation paths.
* **Rendering modes** (default `client`):

| mode    | GL on this host                | rendering                    | notes                                  |
|---------|--------------------------------|------------------------------|----------------------------------------|
| client  | none                           | vtk.js in the browser        | works on headless nodes; ssh -L to reach |
| server  | EGL/OSMesa or X (vtk 9.2 conda build: X only, use `xvfb-run`) | VTK here, streams images | full VTK parity (depth peeling, lighting) |
| trame   | as server                      | UI switch client/server      | interactive switch                     |

* **Dependencies**: new extra `viz-web = ["pyvista[jupyter]"]` (trame,
  trame-server/-client/-vtk/-vuetify, wslink, nest-asyncio). Known env
  gotcha: cinemavirenv is layered over the conda `stable` env, and conda
  site-packages wins on `sys.path` — the conda `wslink` must be >= 2.6.0
  (`trame_server` needs `NetworkMonitor.add_listener`, added in 2.6.0).
* **Incidental fix**: `promptcli.py` / `scripts/prompt.py` passed
  `dumpMesh=` to `Visualiser`, whose parameter is `doDumpMesh` — the GDML
  `-v -d` path raised `TypeError`. Fixed while touching those lines.

## Limitations (phase 1)

Desktop-only interactions are not available in the browser: mesh picking,
the s/m/u/r keys, and the geoClip plane widget (static clip in web mode,
warned). The trame UI provides camera presets, screenshot download, export
and a rendering-mode switch. vtk.js (client mode) may not fully reproduce
depth-peeled transparency/lighting — use `--web-mode server` under
`xvfb-run` for exact parity. Remote usage: `ssh -L <port>:localhost:<port>`.

## Verification

```bash
pip install '.[viz-web]'                     # plus wslink>=2.6.0 if a conda env shadows it

prompt -g <sim.py> --gun MyGun -n 10 -v      # desktop regression (unchanged)
prompt -g <sim.py> --gun MyGun -n 10 -v --web        # browser, Ctrl+C stops
DISPLAY= prompt -g <sim.py> --gun MyGun -n 5 -v --web --web-no-browser  # headless

cd cinemabin && python -m pytest ../src/pythontests/test_visualiser_web.py -v
```

Tests: `src/pythontests/test_visualiser_web.py` — HTTP smoke of
`launch_web_service(block=False)`, `Prompt.show(web=True)` dispatch, and a
subprocess integration test of `prompt -v --web` (parses the served URL,
asserts HTTP 200, SIGTERM for a clean exit).
