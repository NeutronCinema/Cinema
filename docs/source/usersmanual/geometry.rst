Geometry
==========

.. jupyter-execute:: 
    :raises:

    import os, sys
    import pyvista
    import stdout_redirect as rd
    from contextlib import redirect_stdout

    pyvista.set_jupyter_backend('panel')
    pyvista.global_theme.axes.show = True
    pyvista.global_theme.show_edges = True
    pyvista.global_theme.background = 'white'

    import Cinema
    from Cinema.Prompt import Launcher, Visualiser
    import matplotlib.pyplot as plt
    import numpy as np
    from Cinema.Interface.Utils import findData

    inputfile=os.path.join('simple_geo.gdml')
    printTraj=False

    if not os.path.isfile(inputfile):
            inputfile=findData(f'gdml/{inputfile}', '.')
            if not os.path.isfile(inputfile):
                    raise IOError(f'The input GDML file is not found.')
    with rd.jupyter2terminal():
            with open('output.txt', 'w') as fto:
                    with rd.stdout_redirected(fto, sys.__stdout__):
                            with redirect_stdout(fto):
                                    myLcher=Launcher()
                                    myLcher.setSeed(1)
                                    myLcher.loadGeometry(inputfile)

                                    visualize = True

                                    if visualize is True:
                                            v = Visualiser('+', printWorld=False)
                                            v.show()
