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

from ..Interface import *

import random
import matplotlib.colors as mcolors
from .Mesh import Mesh

import pyvista as pv

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

class Visualiser():
    def __init__(self, blacklist, printWorld=False, nSegments=30, mergeMesh=False, dumpMesh=False, window_size=[1920, 1080], byMat=False, addLegend=False, geoClip=False):       
        if is_jupyterlab_session():
            pv.set_jupyter_backend('trame')  

        self.color =  list(mcolors.CSS4_COLORS.keys())
        self.worldMesh = Mesh()
        self.blacklist = blacklist
        if printWorld:
            self.worldMesh.printMesh()

        self.plotter = PtPlotter(window_size=window_size)
        
        # Enable depth peeling for better transparency handling
        self.plotter.enable_depth_peeling()

        self.loadMesh(nSegments, dumpMesh, mergeMesh, byMat, geoClip)
        if addLegend:
            self.plotter.add_legend()
        self.trj=pv.MultiBlock()
        self.redpoints=pv.MultiBlock()

        self.plotter.show_bounds()
        self.plotter.view_zy()
        self.plotter.show_axes()

        self.plotter.show_grid()
        self.plotter.enable_mesh_picking(callback=self.callback, left_clicking=False, show_message=False)
        self.plotter.add_key_event('s', self.save)

    def save(self):
        print('save screenshot.png')
        self.plotter.screenshot('screenshot.png')

    def addTrj(self, data):
        if data.size < 2:
            return
        line = pv.lines_from_points(data)
        line.add_field_data(['a neutron trajectory'], 'mesh_info')
        #draw the first and last position as red dots
        if data.size>2:
            point_cloud = pv.PolyData(data[1:-1])
            self.redpoints.append(point_cloud)
            point_cloud.add_field_data(['a neutron trajectory'], 'mesh_info')
        self.trj.append(line)

    def loadMesh(self, nSegments=30, dumpMesh=False, combineMesh=False, byMat=False, geoClip=False):
        if geoClip:
            try:
                from tetgen import TetGen
            except:
                raise ImportError("tetgen is required. Use 'pip install tetgen' to install. ")
            
        if combineMesh:
            self.loadCombinedMesh(nSegments, geoClip)
        elif byMat:
            self.loadMeshByMat(nSegments, geoClip)
        else:
            self.loadMeshDefault(nSegments,geoClip)
        if dumpMesh:
            self.dumpMesh()

    def dumpMesh(self):
        self.plotter.export_html('exported.html')
        # if dumpMesh:
        #     fn=f'{name}.ply'
        #     print(f'saving {fn}')
        #     mesh.save(fn, False)
        # count+=1

    def generateVolumetricMesh(self, mesh : pv.PolyData):
        try:
            from tetgen import TetGen
        except:
            raise ImportError("tetgen is required. Use 'pip install tetgen' to install. ")
        mesh.triangulate(True)
        tet = TetGen(mesh)
        tet.make_manifold()
        tet.tetrahedralize()
        mesh = tet.grid
        return mesh
    
    def loadMeshDefault(self, nSegments, geoClip=False):
        count = 0
        for am in self.worldMesh:
            name = am.getMeshName()
            name = f'{count}_{name}'
            mesh = self.getValidMesh(am, nSegments)
            rcolor = random.choice(self.color)
            if not mesh:
                continue
            if geoClip:
                mesh = self.generateVolumetricMesh(mesh)
                clippedMesh = self.plotter.addClipPlane([mesh], not am.n, normal='x', opacity=0.5) 
                self.plotter.addClippedMesh(clippedMesh, label=name , color=rcolor,opacity=0.5)

                mesh.add_field_data([' Volume name: '+name, ' Infomation: '+am.getLogVolumeInfo()], 'mesh_info')
            else:
                self.plotter.add_mesh(mesh, color=rcolor, opacity=0.3, label=name)
            count += 1

    def loadCombinedMesh(self, nSegments, geoClip=False):
        print('INFO: Visualizing combined geometry')
        allmesh = pv.MultiBlock()
        count = 0
        for am in self.worldMesh:
            mesh = self.getValidMesh(am, nSegments)
            if not mesh:
                continue
            allmesh.append(mesh)
            if geoClip:
                mesh = self.generateVolumetricMesh(mesh)
                clippedMesh = self.plotter.addClipPlane([mesh], not am.n, normal='x', opacity=0.5) # am.n = 0 if is world
                if count == 0:
                    label = 'Combined geometry'
                else:
                    label = None
                self.plotter.addClippedMesh(clippedMesh, label=label ,opacity=0.5)
                count = 1

        if not geoClip:
            g = allmesh.combine()
            g.add_field_data(['Combined geometry'], 'mesh_info')
            self.plotter.add_mesh(g, color=random.choice(self.color), opacity=0.3, label="Combined geometry")

    def loadMeshByMat(self, nSegments, geoClip=False):
        print('INFO: Visualizing geometry by materials')
        matColorMap = {}
        for am in self.worldMesh:
            matName = am.getMaterialName()

            if matName not in matColorMap.keys():
                rcolor = random.choice(self.color)
                matColorMap[matName] = rcolor
            else:
                rcolor = matColorMap[matName]
                matName = None

            mesh = self.getValidMesh(am, nSegments)
            if not mesh:
                continue

            if not geoClip:
                self.plotter.add_mesh(mesh, color=rcolor, opacity=0.3, label=matName)
            else:
                mesh = self.generateVolumetricMesh(mesh)
                clippedMesh = self.plotter.addClipPlane([mesh], not am.n, normal='x', opacity=0.5)
                self.plotter.addClippedMesh(clippedMesh , label=matName, color=rcolor, opacity=0.5)


    def getValidMesh(self, mesh : Mesh, nSegments):
        name = mesh.getMeshName()
        if self.blacklist is not None:
            if any(srchstr in name for srchstr in self.blacklist):
                return None
        name, mesh = mesh.getMesh(nSegments)
        return mesh

    def callback(self, mesh):
        print(f'\nPicked volume info:')
        for info in mesh['mesh_info']:
            print(info)
        # self.plotter.add_point_scalar_labels(mesh.cast_to_pointset(), 'mesh_name')

    def show(self):
        if self.trj.keys()!=[]:
            self.plotter.add_mesh(self.trj.combine(), color='blue', opacity=0.2, line_width=2 )

        if self.redpoints.keys()!=[]:
            crp = self.redpoints.combine()
            if crp.points.size>0:
                self.plotter.add_mesh(crp, color='red', opacity=0.3, point_size=8 )

        self.plotter.show(title='Cinema Visualiser')

class PtPlotter(pv.Plotter):
    def __init__(self, window_size=None):
        super().__init__(window_size=window_size)
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
        self.add_mesh(clippedMesh, **kwargs)