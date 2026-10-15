#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2024 Prompt developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################

import asyncio
import os
import sys
import threading
import time
from ..Interface import *

import random
import matplotlib.colors as mcolors
from .Mesh import Mesh, generateVolumetricMesh

try:
    import pyvista as pv
except Exception as e:
    print(e)
    sys.exit(1)

high_contrast_colors = ["#FF0000","#FF4500","#FF8C00","#FFD700","#FFFF00","#FF6347","#CD5C5C",
    "#0000FF","#1E90FF","#00BFFF","#00FFFF","#00FF00","#32CD32","#2E8B57","#20B2AA",
    "#800080","#9370DB","#8A2BE2","#DA70D6","#FF00FF","#00FF7F","#4B0082","#7FFF00","#FF1493",
    "#9400D3","#000000","#696969","#A9A9A9"]

# from https://stackoverflow.com/questions/57173235/how-to-detect-whether-in-jupyter-notebook-or-lab 
def is_jupyterlab_session() -> bool:
    """Check whether we are in a Jupyter-Lab session.
    Notes
    -----
    This is a heuristic based process inspection based on the current Jupyter lab
    (major 3) version. So it could fail in the future.
    It will also report false positive in case a classic notebook frontend is started
    via Jupyter lab.
    """
    import psutil

    # inspect parent process for any signs of being a jupyter lab server

    parent = psutil.Process().parent()
    if parent.name() == "jupyter-lab":
        return True
    keys = (
        "JUPYTERHUB_API_KEY",
        "JPY_API_TOKEN",
        "JUPYTERHUB_API_TOKEN",
    )
    env = parent.environ()
    if any(k in env for k in keys):
        return True

    return False


def launch_web_service(plotter, mode='client', port=0, host=None,
                       open_browser=True, block=True, ready_timeout=30.0,
                       timeout=0):
    """Serve any pyvista Plotter in a web browser via pyvista's trame backend.

    The browser gets the standard pyvista trame UI (camera presets, screenshot
    download, client/server rendering switch).  The desktop-only interactions
    of :class:`Visualiser` (mesh picking, the s/m/u/r keys and the geoClip
    plane widget) are not available in the browser.

    Args:
        mode: 'client' renders in the browser via vtk.js and needs no GL
            context on this host (useful on headless login nodes); 'server'
            renders on this host and streams images (needs GL); 'trame' adds
            a UI switch between the two.
        port: port to serve on, 0 picks a free port.
        host: interface to bind, default 127.0.0.1 (or $TRAME_DEFAULT_HOST).
        open_browser: try to open the URL in a browser once the server is up.
        block: True serve until Ctrl+C/SIGTERM and return None; False serve
            from a background thread and return the trame server (stop it
            with :func:`stop_web_service`).
        ready_timeout: seconds to wait for the port to be bound (block=False).
        timeout: idle auto-exit in seconds (wslink reaping): the server stops
            itself when no browser client has been connected for this long
            (this also fires if no client ever connects).  0 (default)
            serves until Ctrl+C/SIGTERM.  A grace period (e.g. 300) absorbs
            page refreshes and reconnect blips.
    """
    try:
        from pyvista.trame.jupyter import initialize, build_url
        from pyvista.trame.views import get_server
        from trame.widgets import html as html_widgets, vtk as vtk_widgets
        from trame.widgets import vuetify2, vuetify3
    except ImportError as exc:
        raise ImportError(
            "browser visualisation needs the trame stack, install it with "
            "pip install '.[viz-web]' (i.e. pyvista[jupyter])") from exc
    if mode not in ('client', 'server', 'trame'):
        raise ValueError(f"web mode must be one of client/server/trame, got {mode!r}")

    bind_host = host or os.environ.get('TRAME_DEFAULT_HOST', '127.0.0.1')
    server = get_server('prompt-visualiser')
    # widget-module init, mirroring pyvista.trame.jupyter.launch_server().
    # The UI is built on the unstarted server (supported by pyvista.trame);
    # unlike pyvista's launch_server we then use exec_mode='main' below,
    # which is the canonical blocking serve-until-interrupt pattern.
    html_widgets.initialize(server)
    vtk_widgets.initialize(server)
    (vuetify2 if server.client_type == 'vue2' else vuetify3).initialize(server)
    initialize(server, plotter, mode=mode)

    url_host = 'localhost' if bind_host in ('', '0.0.0.0', '::') else bind_host
    def _on_ready(**_):
        server._prompt_viz_loop = asyncio.get_event_loop()   # for stop_web_service
        url = build_url(server, ui=plotter._id_name, host=url_host)
        print(f'\nCinema Visualiser served at: {url}', flush=True)
        print('  press Ctrl+C to stop', flush=True)
        if open_browser:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass
    server.controller.on_server_ready.add(_on_ready)

    start = dict(host=bind_host, port=int(port), open_browser=False,
                 show_connection_info=False, disable_logging=True,
                 timeout=int(timeout), backend='aiohttp')
    if block:
        # blocks this thread; wslink catches SIGINT/SIGTERM and exits cleanly
        server.start(exec_mode='main', **start)
        return None

    # non-blocking (tests/embedders): exec_mode='main' always blocks its
    # calling thread (wslink runs the serve loop with run_until_complete),
    # so run it in a daemon thread that owns its own event loop.
    threading.Thread(target=_run_web_service_thread, args=(server, start),
                     daemon=True, name='prompt-viz-web').start()
    t0 = time.monotonic()
    while server.port == 0 and time.monotonic() - t0 < ready_timeout:
        time.sleep(0.05)
    if server.port == 0:
        raise TimeoutError(f'trame server not ready after {ready_timeout:.0f}s')
    return server


def _run_web_service_thread(server, start):
    """Serve on a fresh event loop in this (daemon) thread until stopped."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server._prompt_viz_loop = loop   # captured for stop_web_service()
    try:
        # thread=True only disables the signal handlers (which must not be
        # installed off the main thread); main_exec still blocks this thread
        server.start(exec_mode='main', thread=True, **start)
    except SystemExit:
        pass    # raised by wslink when the server exits


def stop_web_service(server, timeout=5.0):
    """Best-effort graceful stop of a :func:`launch_web_service` server.

    Only meaningful for servers launched with ``block=False``; blocking
    servers are stopped with Ctrl+C/SIGTERM.
    """
    loop = getattr(server, '_prompt_viz_loop', None)
    if loop is not None:
        asyncio.run_coroutine_threadsafe(server.stop(), loop).result(timeout)


class Visualiser():
    def __init__(self, blacklist, printWorld=False, nSegments=30, mergeMesh=False, doDumpMesh=False, window_size=[1920, 1080], byMat=False, addLegend=True, geoClip=False, web=False, web_mode=None, web_port=0, web_host=None, web_open_browser=True, web_timeout=3):
        if is_jupyterlab_session():
            pv.set_jupyter_backend('trame')
        # self.color =  list(mcolors.CSS4_COLORS.keys())
        self.color = high_contrast_colors
        self.worldMesh = Mesh()
        self.blacklist = blacklist
        self._mesh_actor_pair = []
        if printWorld:
            self.worldMesh.printMesh()
        self._nSegments = nSegments
        self._mergeMesh = mergeMesh
        self._doDumpMesh = doDumpMesh
        self._byMat = byMat
        self._geoClip = geoClip
        self._addLegend = addLegend
        self._web = bool(web)
        self._web_mode = web_mode or 'client'
        self._web_port = web_port
        self._web_host = web_host
        self._web_open_browser = web_open_browser
        self._web_timeout = web_timeout
        if self._web and self._geoClip:
            print('WARNING: the geoClip plane widget is desktop-only; '
                  'in web mode the clip plane stays static.')
        self._selected_mesh = None
        self._selected_actor = None
        self._trj=pv.MultiBlock()
        self._redpoints=pv.MultiBlock()
        self._hidden_meshes = []
        self._window_size = window_size
        self._load_plotter()

    @property
    def selected_mesh(self):
        return self._selected_mesh

    @property
    def selected_actor(self):
        return self._selected_actor

    @property
    def mesh_actor_pair(self):
        return self._mesh_actor_pair

    def _config_key_events(self):
        self.plotter.enable_mesh_picking(callback=self._pick_callback, left_clicking=False, show_message=False)
        self.plotter.add_key_event('s', self.save)
        self.plotter.add_key_event('m', self._mask_selected)
        self.plotter.add_key_event('u', self._unmask_selected)
        self.plotter.add_key_event('r', self._refresh_plotter)

    def _load_plotter(self):
        self.plotter = PtPlotter(window_size=self._window_size, off_screen=self._web)
        if not self._web:
            # depth peeling probes GL with an off-screen render, which aborts on a
            # headless host; in web client mode the browser renders via vtk.js
            self.plotter.enable_depth_peeling()
            # mesh picking and the s/m/u/r keys act on the desktop interactor
            self._config_key_events()

    def _clear_plotter(self):
        self.plotter.clear_actors()
        self._mesh_actor_pair = []

    def _refresh_plotter(self):
        self._clear_plotter()
        self._plot_geo_and_trj()
        self.plotter.update()
        print(f"Plotter Reloaded!\n")

    def _plot_geo_and_trj(self):
        nosuccess = self.loadMesh(self._nSegments, self._doDumpMesh, self._mergeMesh, self._byMat, self._geoClip)
        if nosuccess:
            try:
                self._load_plotter() # perform a reload, try again 
                self.loadMesh(self._nSegments, self._doDumpMesh, self._mergeMesh, self._byMat, self._geoClip)
            except Exception as e:
                print(e)
                print("Error: Failed to load mesh.")
                sys.exit(1)
            
        if self._addLegend:
            mesh_num = self.worldMesh.countFullTreeNode() + 1
            s = min(mesh_num * 0.05, 1)
            ss = s * 0.5
            a = self.plotter.add_legend(loc='upper left', size=(s,ss))
        self._viz_trj()
        self.set_plotter_style()

    def _pick_callback(self, mesh):
        print(f'\nPicked volume info:')
        self._selected_mesh = mesh
        self._selected_actor = self._get_actor(self.selected_mesh)
        for info in mesh['mesh_info']:
            print(info)
        # self.plotter.add_point_scalar_labels(mesh.cast_to_pointset(), 'mesh_name')

    def _get_actor(self, mesh):
        if self.mesh_actor_pair:
            for m, a in self.mesh_actor_pair:
                if m == mesh:
                    return a
        else:
            return None
    
    def _mask_selected(self):
        if self.selected_mesh:
            if not self.selected_actor:
                raise ValueError("Selected mesh has no actor.")
            self.plotter.remove_actor(self.selected_actor)
            self._hidden_meshes.append(self.selected_mesh)
            self.plotter._clear_picking_representations()
            self._selected_mesh = None
            self.plotter.update()
            print(f'Masked Physical Volumes:')
            for hm in self._hidden_meshes:
                print(f'\t- {hm["mesh_name"]}')
    
    def _unmask_selected(self):
        if self._hidden_meshes:
            for m in self._hidden_meshes:
                self.plotter.add_actor(self._get_actor(m))
            self._hidden_meshes = []
            self.plotter.update()
            print("\nAll masked Physical Volumes recovered")

    def set_plotter_style(self):
        self.plotter.show_bounds()
        self.plotter.view_zy()
        self.plotter.show_axes()
        self.plotter.show_grid()

    def save(self):
        print('save screenshot.png')
        self.plotter.save_graphic('screenshot.svg')

    def addTrj(self, data):
        if data.size < 2:
            return
        line = pv.lines_from_points(data)
        line.add_field_data(['a neutron trajectory'], 'mesh_info')
        #draw the first and last position as red dots
        if data.size>2:
            point_cloud = pv.PolyData(data[1:-1])
            self._redpoints.append(point_cloud)
            point_cloud.add_field_data(['a neutron trajectory'], 'mesh_info')
        self._trj.append(line)

    def loadMesh(self, nSegments=30, doDumpMesh=False, combineMesh=False, byMat=False, geoClip=False):
        if geoClip:
            print('INFO: Visualizing geometry with a geoClipper')
            self.blacklist = [] # clip plane is on world, do not mask, especially for the world mesh
            if combineMesh:
                print('WARNING: meaningless to combine mesh with geoClip. Meshes not combined.')
                combineMesh = False

        if byMat:
            print('INFO: Visualizing geometry by material')
            matColorMap = {}
            if combineMesh:
                print('WARNING: meaningless to use combineMesh with byMat. Meshes not combined.')
                combineMesh = False

        if combineMesh:
            print('INFO: Visualizing combined geometry')
            combined_meshes_block = pv.MultiBlock()

        for amesh in self.worldMesh:
            mesh_name, mesh = self.loadOneMesh(amesh, nSegments)
            matName = amesh.getMaterialName()
            rcolor = random.choice(self.color)
            mesh_label = mesh_name

            if not mesh:
                continue

            if combineMesh:  # In this case, byMat and geoClip are both False
                combined_meshes_block.append(mesh)
            else: # byMat or geoClip may be True
                sur_mesh = mesh
                if byMat:
                    if matName not in matColorMap.keys():
                        matColorMap[matName] = rcolor
                    else:
                        rcolor = matColorMap[matName]
                    mesh_label = f"{mesh_label}[{matName}]"

                if geoClip:
                    try:
                        vol_mesh = generateVolumetricMesh(mesh)
                        vol_mesh = self.plotter.addClipPlane([vol_mesh], not amesh.n, normal='x', opacity=0.5)
                        actor = self.plotter.addClippedMesh(vol_mesh , label=mesh_label, color=rcolor, opacity=0.5)
                    except Exception as e:
                        print(e)
                        print(f"Warning: Failed to visualize {mesh_name} with geoClip. Fall back without geoClip.")
                        self._geoClip = False
                        return 1
                else:
                    actor = self.plotter.add_mesh(sur_mesh, color=rcolor, opacity=0.3, label=mesh_label)
                self._add_builtin_mesh_info(sur_mesh, mesh_name, matName)

                self._mesh_actor_pair.append((mesh, actor))
        if combineMesh:
            mesh = combined_meshes_block.combine()
            self._add_builtin_mesh_info(mesh, "Combined geometry", "Material not defined for a combined geometry")
            actor = self.plotter.add_mesh(mesh, color=random.choice(self.color), opacity=0.3, label="Combined geometry")
            self._mesh_actor_pair.append((mesh, actor))

        if doDumpMesh:
            self.dumpMesh()

        return 0

    def dumpMesh(self):
        self.plotter.export_html('exported.html')
        # if dumpMesh:
        #     fn=f'{name}.ply'
        #     print(f'saving {fn}')
        #     mesh.save(fn, False)
        # count+=1

    def add_mesh_metadata(self, mesh:pv.PolyData, field_data, field_name = 'mesh_info'):
        mesh.add_field_data(field_data, field_name)

    def _add_builtin_mesh_info(self, mesh:pv.PolyData, name, mat_label):
        self.add_mesh_metadata(mesh, [f"{name}"], 'mesh_name')
        self.add_mesh_metadata(mesh, [f"{mat_label}"], 'material')
        mesh_info = f"\t- Volume name: {name}\n\t- Material: {mat_label}\n"
        self.add_mesh_metadata(mesh, [f"{mesh_info}"], 'mesh_info')


    def loadOneMesh(self, amesh : Mesh, nSegments):
        name, mesh = self.getValidMesh(amesh, nSegments)
        if not mesh:
            print(f"Warning: Mesh {name} is empty, not abled to visualize.")
            return name, None
        return name, mesh

    def getValidMesh(self, ptmesh : Mesh, nSegments, byMat=True):
        # name = mesh.getMeshName()
        name, mesh = ptmesh.getMesh(nSegments)
        mat = ptmesh.getMaterialName()
        if self.blacklist is not None:
            if any(srchstr in name for srchstr in self.blacklist):
                return name, None
            if byMat:
                if any(srchstr in mat for srchstr in self.blacklist):
                    return name, None
        return name, mesh

    def _viz_trj(self):
        if self._trj.keys()!=[]:
            mesh = self._trj.combine()
            actor = self.plotter.add_mesh(mesh, color='blue', opacity=0.2, line_width=2 )
            self._mesh_actor_pair.append((mesh, actor))
            self._add_builtin_mesh_info(mesh, "Trajectory", "Not defined")

        if self._redpoints.keys()!=[]:
            crp = self._redpoints.combine()
            if crp.points.size>0:
                actor = self.plotter.add_mesh(crp, color='red', opacity=0.3, point_size=8 )
                self._mesh_actor_pair.append((crp, actor))
                self._add_builtin_mesh_info(crp, "Interections", "Not defined")

    def show(self):
        self._plot_geo_and_trj()
        if self._web:
            self.show_web(mode=self._web_mode, port=self._web_port,
                          host=self._web_host, open_browser=self._web_open_browser,
                          timeout=self._web_timeout)
        else:
            self.plotter.show(title='Cinema Visualiser')

    def show_web(self, mode='client', port=0, host=None, open_browser=True, timeout=0):
        """Plot the geometry and trajectories, then serve the window in a browser.

        Blocks until Ctrl+C/SIGTERM, or until the idle ``timeout`` (if > 0)
        fires after the last browser client disconnects.  ``mode`` is one of
        client/server/trame, see :func:`launch_web_service`.  On this path
        ``plotter.show()`` is never called: it would auto-close the render
        window and trame would reject the plotter afterwards.
        """
        launch_web_service(self.plotter, mode=mode, port=port, host=host,
                           open_browser=open_browser, block=True, timeout=timeout)

class PtPlotter(pv.Plotter):
    def __init__(self, window_size=None, off_screen=False):
        super().__init__(window_size=window_size, off_screen=off_screen)
        self.clippers = []
        self.clipFunction = None


    def addClipPlane(self, meshes, isWorld, normal='x', invert=False, widget_color=None, value=0, assign_to_axis=None, tubing=False, origin_translation=True, outline_translation=False, implicit=True, normal_rotation=True, crinkle=False, interaction_event='end', origin=None, outline_opacity=None, **kwargs):
        from pyvista.plotting.utilities.algorithms import algorithm_to_mesh_handler
        from pyvista.plotting.utilities.algorithms import add_ids_algorithm
        from pyvista.plotting.utilities.algorithms import outline_algorithm
        from pyvista.plotting.utilities.algorithms import set_algorithm_input
        from pyvista.plotting import _vtk

        from pyvista.core.utilities.helpers import generate_plane
        from pyvista.core.filters import _get_output  # avoids circular import
        for mesh in meshes:
            mesh, algo = algorithm_to_mesh_handler(
                add_ids_algorithm(mesh, point_ids=False, cell_ids=True),
            )

            name = kwargs.get('name', mesh.memory_address)
            rng = mesh.get_data_range(kwargs.get('scalars', None))
            kwargs.setdefault('clim', kwargs.pop('rng', rng))
            mesh.set_active_scalars(kwargs.get('scalars', mesh.active_scalars_name))
            if origin is None:
                origin = mesh.center

            self.add_mesh(outline_algorithm(algo), name=f"{name}-outline", opacity=0.0)

            if isinstance(mesh, _vtk.vtkPolyData):
                clipper = _vtk.vtkClipPolyData()
            else:
                clipper = _vtk.vtkTableBasedClipDataSet()
            set_algorithm_input(clipper, algo)
            clipper.SetValue(value)
            clipper.SetInsideOut(invert)  # invert the clip if needed

            plane_clipped_mesh = _get_output(clipper)
            self.plane_clipped_meshes.append(plane_clipped_mesh)
            self.clippers.append(clipper)

        def callback(normal, loc):  # numpydoc ignore=GL08
            for clipper in self.clippers:
                function = generate_plane(normal, loc)
                clipper.SetClipFunction(function)  # the implicit function
                clipper.Update()  # Perform the Cut
                clipped = pv.wrap(clipper.GetOutput())
                plane_clipped_mesh.shallow_copy(clipped)
                
        if isWorld:
            self.add_plane_widget(
                callback=callback,
                bounds=mesh.bounds,
                factor=1.25,
                normal=normal,
                color=widget_color,
                tubing=tubing,
                assign_to_axis=assign_to_axis,
                origin_translation=origin_translation,
                outline_translation=outline_translation,
                implicit=implicit,
                origin=origin,
                normal_rotation=normal_rotation,
                interaction_event=interaction_event,
                outline_opacity=outline_opacity,
            )
        return clipper

    def addClippedMesh(self, clippedMesh, **kwargs):
        from pyvista.plotting._vtk import vtkPlane
        function = vtkPlane()
        function.SetNormal(1,0,0)
        function.SetOrigin(0,0,0)
        clippedMesh.SetClipFunction(function)  # the implicit function
        actor = self.add_mesh(clippedMesh, **kwargs)
        return actor