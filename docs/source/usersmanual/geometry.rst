Geometry
==========

.. jupyter-execute::
   :hide-code:

   # Configure for pythreejs
   from pickletools import pybool
   import pyvista
   pyvista.set_jupyter_backend('pythreejs')
   pyvista.global_theme.background = 'white'
   pyvista.global_theme.window_size = [600, 400]
   pyvista.global_theme.axes.show = True
   pyvista.global_theme.smooth_shading = True
   

.. jupyter-execute::
   
   import pyvista
   import os
   #filepath = os.path.abspath("./_static/20_LV_Cube1.ply")
   #mesh = pyvista.read(filepath)

   mesh = pyvista.Cube()

   plotter = pyvista.Plotter()    # instantiate the plotter
   plotter.add_mesh(mesh)    # add a mesh to the scene
   plotter.view_zy()
   plotter.show_axes()
   plotter.show_grid()
   plotter.show(jupyter_backend='pythreejs')            # show the rendering window

.. jupyter-execute::
   
   import matplotlib.pyplot as plt

   fig, ax = plt.subplots()

   fruits = ['apple', 'blueberry', 'cherry', 'orange']
   counts = [40, 100, 30, 55]
   bar_labels = ['red', 'blue', '_red', 'orange']
   bar_colors = ['tab:red', 'tab:blue', 'tab:red', 'tab:orange']

   ax.bar(fruits, counts, label=bar_labels, color=bar_colors)

   ax.set_ylabel('fruit supply')
   ax.set_title('Fruit supply by kind and color')
   ax.legend(title='Fruit color')

   plt.show()