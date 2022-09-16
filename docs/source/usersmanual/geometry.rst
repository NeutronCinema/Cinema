Geometry
==========

.. jupyter-execute::
   :hide-code:

   # Configure for pythreejs
   import pyvista
   pyvista.set_jupyter_backend('pythreejs')
   pyvista.global_theme.background = 'white'
   pyvista.global_theme.window_size = [600, 400]
   pyvista.global_theme.axes.show = False
   pyvista.global_theme.smooth_shading = True
   

.. jupyter-execute::
   
   
   import pyvista
   import os
   filepath = os.path.abspath("./docs/source/_static/20_LV_Cube1.ply")
   mesh = pyvista.read(filepath)
   #print(reader.path)
   #mesh = reader.read()
   #mesh.plot()
   plotter = pyvista.Plotter()    # instantiate the plotter
   plotter.add_mesh(mesh)    # add a mesh to the scene
   plotter.view_zy()
   plotter.show_axes()
   plotter.show_grid()
   plotter.show()            # show the rendering window