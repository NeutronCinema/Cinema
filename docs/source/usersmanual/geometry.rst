Geometry
==========

.. jupyter-execute::
   :raises:

   import pyvista as pv
   pv.set_jupyter_backend('pythreejs')

   mesh = pv.Cube()
   mesh.plot(show_edges=True)
