
def tutorial_plot(fn):
    
    import os, sys
    import pyvista
    import stdout_redirect as rd
    from contextlib import redirect_stdout

    pyvista.set_jupyter_backend('ipyvtklink')
    pyvista.global_theme.background = 'white'
    # pyvista.global_theme.window_size = [300, 200]
    
    import Cinema
    from Cinema.Prompt import Launcher, Visualiser
    import matplotlib.pyplot as plt
    import numpy as np
    from Cinema.Interface.Utils import findData

    printTraj=False
    inputfile = os.path.join(os.environ["CDOCGDML"], 'volumes', fn)

    if not os.path.isfile(inputfile):
        raise IOError('gdml not found: ' + inputfile)
    with rd.jupyter2terminal():
        with open('output.txt', 'w') as fto:
            with rd.stdout_redirected(fto, sys.__stdout__):
                with redirect_stdout(fto):
                    myLcher=Launcher()
                    myLcher.loadGeometry(inputfile)

                    visualize = True

                    if visualize is True:
                        v = Visualiser('+', printWorld=False)
                        v.plotter.show_bounds()
                        v.plotter.show_grid()
                        v.plotter.show()