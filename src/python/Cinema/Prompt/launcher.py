#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################

import os
import socket
import sys
import warnings

__all__ = ['Launcher']

from ..Interface import *
from .histogram import Hist1D, Hist2D, _pt_HistBase_dimension

_pt_Launcher_getInstance = importFunc('pt_Launcher_getInstance', type_voidp, [] )
_pt_Launcher_setSeed = importFunc('pt_Launcher_setSeed', None, [type_voidp, type_sizet] )
# loadGeometry/go/setGun are bridged (int status + pt_last_error message,
# surfaced through raiseOnBridgeError) so a C++ cfg rejection raises a normal
# RuntimeError instead of aborting the process at the ctypes boundary
_pt_Launcher_loadGeometry = importFunc('pt_Launcher_loadGeometry', type_int, [type_voidp, type_cstr] )
_pt_Launcher_getTrajSize = importFunc('pt_Launcher_getTrajSize', type_sizet, [type_voidp])
_pt_Launcher_getTrajectory = importFunc('pt_Launcher_getTrajectory', None, [type_voidp, type_npdbl2d])
_pt_Launcher_go = importFunc('pt_Launcher_go', type_int, [type_voidp, type_sizet, type_dbl, type_bool, type_bool, type_bool])
_pt_Launcher_setGun = importFunc('pt_Launcher_setGun', type_int, [type_voidp, type_cstr])
_pt_Launcher_goWithSecondStack = importFunc('pt_Launcher_goWithSecondStack', type_sizet, [type_voidp, type_sizet])

_pt_ResourceManager_getHist = importFunc('pt_ResourceManager_getHist', type_voidp, [type_cstr])

_pt_setWorld = importFunc('pt_setWorld', None, [type_voidp])

_pt_Launcher_simOneEvent = importFunc('pt_Launcher_simOneEvent', None, [type_voidp, type_bool])

# Shared by Launcher.setWorld and Prompt.setWorld. Do not suggest clear() as a
# remedy here: clear() would destroy the world another Prompt instance in this
# process may still be using.
_WORLD_EXIST_MSG = ('World exist already: only one world can be set per process '
                    '(Launcher is a process-wide singleton shared by every Prompt '
                    'instance, so a second Prompt() in the same process hits this '
                    'too). Run each world in its own process, e.g. a separate '
                    'script or mpirun rank.')


_display_state = {'checked': False, 'forced_headless': False}


def ensureDisplayUsable(timeout=2.0):
    """Make sure the DISPLAY environment, if set, is actually usable.

    A set-but-unreachable DISPLAY (dead X forwarding, stale remote host) makes
    matplotlib block indefinitely in backend initialisation and VTK block in
    XOpenDisplay, which also stalls MPI jobs on the rank Barrier. When the
    probe fails, warn on stderr and degrade to headless rendering: force the
    matplotlib 'Agg' backend (must happen before the first pyplot use) and
    unset DISPLAY so VTK falls back to off-screen EGL instead of X11. When
    DISPLAY is unset or reachable, behaviour is unchanged.

    Returns True if a display is available (or none is needed), False when
    headless mode was forced. The probe runs at most once per process.
    """
    if _display_state['checked']:
        return not _display_state['forced_headless']
    _display_state['checked'] = True
    display = os.environ.get('DISPLAY')
    if not display:
        return True # no DISPLAY: matplotlib already defaults headless
    host, _, disp = display.rpartition(':')
    if not disp.split('.')[0].isdigit():
        return True # malformed DISPLAY fails fast on its own, leave it alone
    try:
        if host in ('', 'unix'): # local X server, e.g. DISPLAY=:0
            reachable = os.path.exists(f'/tmp/.X11-unix/X{int(disp.split(".")[0])}')
        else: # remote X server, e.g. DISPLAY=host:12.0
            reachable = False
            with socket.create_connection((host, 6000 + int(disp.split('.')[0])), timeout=timeout):
                reachable = True
    except OSError:
        reachable = False
    if reachable:
        return True
    _display_state['forced_headless'] = True
    print(f'WARNING: DISPLAY={display} is set but not reachable within {timeout}s, '
          'forcing headless rendering (matplotlib Agg backend, VTK off-screen); '
          'interactive show() is disabled.', file=sys.stderr)
    os.environ.pop('DISPLAY', None) # let VTK skip X11 and use its EGL fallback
    try:
        import matplotlib
        matplotlib.use('Agg', force=True)
    except ImportError:
        pass
    return False


ensureDisplayUsable()


@singleton
class Launcher():
    def __init__(self):
        self.cobj = _pt_Launcher_getInstance()
        self.worldExist = False        

    def setSeed(self, seed):
        _pt_Launcher_setSeed(self.cobj, seed)

    def loadGeometry(self, fileName):
        raiseOnBridgeError(_pt_Launcher_loadGeometry(self.cobj, fileName.encode('utf-8')))

    def setWorld(self, logicalvol):
        if self.worldExist:
            raise RuntimeError(_WORLD_EXIST_MSG)
        # setup the vecgeom world
        _pt_setWorld(logicalvol.cobj)
        self.worldExist = True
    
    def showWorld(self, gun, particles=None, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False, **kwargs):
        from .Visualiser import Visualiser
        ensureDisplayUsable() # no-op unless DISPLAY is set but unreachable
        if not self.worldExist:
            raise RuntimeError('World is not set')
        v = Visualiser([], printWorld=False, mergeMesh=mergeMesh, byMat=byMat, addLegend=addLegend, geoClip=geoClip, **kwargs)
        v.plotter.set_scale(xscale, yscale, zscale )
        v.plotter.add_axes_at_origin(labels_off=True)
        v.set_plotter_style()

        if particles is None:
            v.show()
        else:
            if hasattr(gun, 'items'):
                self.setGun(gun.cfg)
                for i in range(particles):
                    self.go(1, recordTrj=True, timer=False, save2Disk=False)
                    trj = self.getTrajectory()
                    v.addTrj(trj)
            elif isinstance(gun, str):
                self.setGun(gun)
                for i in range(particles):
                    self.go(1, recordTrj=True, timer=False, save2Disk=False)
                    trj = self.getTrajectory()
                    v.addTrj(trj)
            else:
                for i in range(particles):
                    gun.generate()
                    self.simOneEvent(recordTrj=True)                    
                    trj = self.getTrajectory()
                    v.addTrj(trj)
            # try:
            #     v.addTrj(trj)
            # except ValueError:
            #     # print(trj)
            #     # print("skip ValueError in File '/Prompt/scripts/prompt', in <module>, v.addLine(trj)")
            #     pass
            v.show()

    def setGun(self, cfg):
        raiseOnBridgeError(_pt_Launcher_setGun(self.cobj, cfg.encode('utf-8')))
        

    def getTrajSize(self):
        return _pt_Launcher_getTrajSize(self.cobj)

    def getTrajectory(self):
        trjsize = self.getTrajSize()
        trj = np.zeros([trjsize, 3])
        _pt_Launcher_getTrajectory(self.cobj, trj)
        return trj

    def go(self, numPrimary, printPercent=0.1, recordTrj=False, timer=True, save2Disk=True, printPrecent=None, save2Dis=None):
        # 'printPrecent' and 'save2Dis' were long-standing typos of the two
        # parameters above; keep them working as deprecated aliases
        if printPrecent is not None:
            warnings.warn("Launcher.go() argument 'printPrecent' is a typo, use 'printPercent' (alias kept for backward compatibility)",
                          DeprecationWarning, stacklevel=2)
            printPercent = printPrecent
        if save2Dis is not None:
            warnings.warn("Launcher.go() argument 'save2Dis' is a typo, use 'save2Disk' (alias kept for backward compatibility)",
                          DeprecationWarning, stacklevel=2)
            save2Disk = save2Dis
        raiseOnBridgeError(_pt_Launcher_go(self.cobj, numPrimary, printPercent, recordTrj, timer, save2Disk))

    def goWithSecondStack(self, numPrimary):
        return _pt_Launcher_goWithSecondStack(self.cobj, numPrimary)


    def getHist(self, cfg):
        # Validate the name in Python before the ctypes call: the C++ lookup
        # throws for unknown names and the exception crosses ctypes as
        # std::terminate (uncatchable SIGABRT). Every scorer registered through
        # the Python API goes through Volume.addScorer, whose dict values are
        # exactly the valid names. GDML-declared scorers (loadGeometry) are
        # registered on the C++ side only, so the check is skipped when no
        # Python-API world exists.
        from .geo import Volume
        known = set(Volume.scorer_dict.values())
        if self.worldExist and cfg not in known:
            raise KeyError(f"no scorer named '{cfg}'; registered scorers: {sorted(known)}")
        cobj = _pt_ResourceManager_getHist(cfg.encode('utf-8'))
        dim = _pt_HistBase_dimension(cobj)

        if dim == 1:
            return Hist1D(cobj=cobj)
        elif dim == 2:
            return Hist2D(cobj=cobj)
        else:
            raise RuntimeError("no implemented")
        
    def simOneEvent(self, recordTrj=False):
        _pt_Launcher_simOneEvent(self.cobj, recordTrj)
