#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2024 Prompt developers                                     ##
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

__all__ = ['Launcher']

from ..Interface import *
from .histogram import Hist1D, Hist2D, _pt_HistBase_dimension

_pt_Launcher_getInstance = importFunc('pt_Launcher_getInstance', type_voidp, [] )
_pt_Launcher_setSeed = importFunc('pt_Launcher_setSeed', None, [type_voidp, type_sizet] )
_pt_Launcher_loadGeometry = importFunc('pt_Launcher_loadGeometry', None, [type_voidp, type_cstr] )
_pt_Launcher_getTrajSize = importFunc('pt_Launcher_getTrajSize', type_sizet, [type_voidp])
_pt_Launcher_getTrajectory = importFunc('pt_Launcher_getTrajectory', None, [type_voidp, type_npdbl2d])
_pt_Launcher_go = importFunc('pt_Launcher_go', None, [type_voidp, type_sizet, type_dbl, type_bool, type_bool, type_bool])
_pt_Launcher_setGun = importFunc('pt_Launcher_setGun', None, [type_voidp, type_cstr])
_pt_Launcher_goWithSecondStack = importFunc('pt_Launcher_goWithSecondStack', type_sizet, [type_voidp, type_sizet])

_pt_ResourceManager_getHist = importFunc('pt_ResourceManager_getHist', type_voidp, [type_cstr])

_pt_setWorld = importFunc('pt_setWorld', None, [type_voidp])

_pt_Launcher_simOneEvent = importFunc('pt_Launcher_simOneEvent', None, [type_voidp, type_bool])


@singleton
class Launcher():
    def __init__(self):
        self.cobj = _pt_Launcher_getInstance()
        self.worldExist = False        

    def setSeed(self, seed):
        _pt_Launcher_setSeed(self.cobj, seed)

    def loadGeometry(self, fileName):
        _pt_Launcher_loadGeometry(self.cobj, fileName.encode('utf-8'))

    def setWorld(self, logicalvol):
        if self.worldExist:
            raise RuntimeError('World exist already')
        # setup the vecgeom world
        _pt_setWorld(logicalvol.cobj)
        self.worldExist = True
    
    def showWorld(self, gun, particles=None, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False):
        from .Visualiser import Visualiser
        if not self.worldExist:
            raise RuntimeError('World is not set')
        v = Visualiser([], printWorld=False, mergeMesh=mergeMesh, byMat=byMat, addLegend=addLegend, geoClip=geoClip) 
        v.plotter.set_scale(xscale, yscale, zscale )
        v.plotter.add_axes_at_origin(labels_off=True)
        if particles is None:
            v.show()
        else:
            if hasattr(gun, 'items'):
                self.setGun(gun.cfg)
                for i in range(particles):
                    self.go(1, recordTrj=True, timer=False, save2Dis=False)
                    trj = self.getTrajectory()
                    v.addTrj(trj)
            elif isinstance(gun, str):
                self.setGun(gun)
                for i in range(particles):
                    self.go(1, recordTrj=True, timer=False, save2Dis=False)
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
        _pt_Launcher_setGun(self.cobj, cfg.encode('utf-8'))      
        

    def getTrajSize(self):
        return _pt_Launcher_getTrajSize(self.cobj)

    def getTrajectory(self):
        trjsize = self.getTrajSize()
        trj = np.zeros([trjsize, 3])
        _pt_Launcher_getTrajectory(self.cobj, trj)
        return trj

    def go(self, numPrimary, printPrecent=0.1, recordTrj=False, timer=True, save2Dis=True):
        _pt_Launcher_go(self.cobj, numPrimary, printPrecent, recordTrj, timer, save2Dis)

    def goWithSecondStack(self, numPrimary):
        return _pt_Launcher_goWithSecondStack(self.cobj, numPrimary)


    def getHist(self, cfg):
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
