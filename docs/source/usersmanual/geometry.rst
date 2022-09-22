Geometry
==========

.. jupyter-execute::
   :hide-code:

   # Configure for pythreejs
   from pickletools import pybool
   import pyvista
   pyvista.set_jupyter_backend('ipyvtklink')
   pyvista.global_theme.background = 'white'
   pyvista.global_theme.window_size = [600, 400]
   pyvista.global_theme.axes.show = True
   pyvista.global_theme.smooth_shading = True
   

.. jupyter-execute::
   :hide-code:

   import pyvista as pv
   from pyvista import examples
   pv.set_jupyter_backend('ipyvtklink')

   mesh = pv.Cube()
   mesh.plot(show_edges=True)
