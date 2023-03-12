#!python

import numpy as np
import pyvista 

def tutorial(fn):
    
    import os, sys
    import stdout_redirect as rd
    import contextlib

    # configure global theme
    # panel is the only jupyter backend working good
    # a new backend might be avaible in the future,
    # see https://github.com/pyvista/pyvista/issues/3348#issuecomment-1255282449
    pyvista.set_jupyter_backend('panel')
    pyvista.global_theme.background = '#f3f6f6'
    
    from Cinema.Prompt import Launcher, Visualiser
    from Cinema.Interface.Utils import findData
    
    if os.environ['CDOCGDML']:
        try:
            inputfile = os.path.join(os.environ["CDOCGDML"], 'volumes', fn)
        except:
            raise OSError(f'file not found: {inputfile}')
    else:
        raise OSError(f'Check environment variable CDOCGDML:{os.environ["CDOCGDML"]}')

    if not os.path.isfile(inputfile):
        raise IOError('gdml not found: ' + inputfile)
    
    # redirection of stdout from: 
    # 1.jupyter to terminal; 2.terminal to nothing at file descriptor level;
    # 3.python stdout to nothing
    with rd.jupyter2terminal():
        with rd.stdout_redirected(stdout=sys.__stdout__):
            with open(os.devnull, 'w') as f:
                with contextlib.redirect_stdout(f):
                    myLcher=Launcher()
                    myLcher.loadGeometry(inputfile)
                    v = Visualiser('+', printWorld=False)
                    v.plotter.show_bounds()
                    v.plotter.show_axes()
                    v.plotter.show()


# Monkey patching to overwrite plot style
import pyvista.jupyter.notebook as jp
jp.build_panel_bounds = lambda actor: add_axes(actor)

def add_axes(actor):
    """
    Build a panel bounds actor using the plotter cube_axes_actor.
    """
    bounds = {}

    n_ticks = 5
    if actor.GetXAxisVisibility():
        xmin, xmax = actor.GetXRange()
        bounds['xticker'] = {'ticks': np.linspace(xmin, xmax, n_ticks)}

    if actor.GetYAxisVisibility():
        ymin, ymax = actor.GetYRange()
        bounds['yticker'] = {'ticks': np.linspace(ymin, ymax, n_ticks)}

    if actor.GetZAxisVisibility():
        zmin, zmax = actor.GetZRange()
        bounds['zticker'] = {'ticks': np.linspace(zmin, zmax, n_ticks)}

    bounds['origin'] = [xmin, ymin, zmin]
    bounds['grid_opacity'] = 1.
    bounds['show_grid'] = True
    bounds['digits'] = 1
    bounds['fontsize'] = 14

    return bounds
