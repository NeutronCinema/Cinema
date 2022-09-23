Geometry
==========

.. jupyter-execute:: 
	:raises:

	import sys
	print(sys.path)
	import os
	print(os.environ.get('PYTHONPATH'))
	import pyvista
	pyvista.set_jupyter_backend('ipygany')
	import Cinema
	from Cinema.Prompt import Launcher, Visualiser
	import matplotlib.pyplot as plt
	import numpy as np
	from Cinema.Interface.Utils import findData

	inputfile='guide_1.gdml'
	printTraj=False

	if not os.path.isfile(inputfile):
		inputfile=findData(f'gdml/{inputfile}', '.')
		if not os.path.isfile(inputfile):
			raise IOError(f'The input GDML file is not found.')

	visualize = True

	if visualize is True:
		v = Visualiser('+', printWorld=False)
		v.show()

