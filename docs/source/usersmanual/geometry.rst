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
   :raises:

   import pyvista as pv
   from pyvista import examples
   pv.set_jupyter_backend('pythreejs')

   mesh = pv.Cube()
   mesh.plot(show_edges=True)

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