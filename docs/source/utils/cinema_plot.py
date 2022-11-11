
def tutorial(fn):
    
    import os, sys
    import pyvista
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