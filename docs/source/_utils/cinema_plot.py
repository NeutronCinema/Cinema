
def tutorial(fn):
    
    import os, sys
    import pyvista
    import stdout_redirect as rd
    from contextlib import redirect_stdout

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
        
    with rd.jupyter2terminal():
        with open('output.txt', 'w') as fto:
            with rd.stdout_redirected(fto, sys.__stdout__):
                with redirect_stdout(fto):
                    myLcher=Launcher()
                    myLcher.loadGeometry(inputfile)
                    v = Visualiser('+', printWorld=False)
                    v.plotter.show_bounds()
                    v.plotter.show_axes()
                    v.plotter.show()