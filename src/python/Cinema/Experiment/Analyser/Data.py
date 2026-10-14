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

from enum import Enum, unique
import numpy as np
from .DataLoader import DataLoader

# class DataLoader():
#     def __init__(self):
#         self.tof = 1 #vector
#         self.pid = 1 #vector
#         self.tofpidMat = 1 #matrix
#         self.tofMonitor = 1  #vector or matrix
#         self.protonPulse = 1 #vector
#         self.protonCharge = 1 #vector
#         self.distMod2Monitor = 1 #vector
#         self.distMod2Sample =1 #double

@unique
class Normalise(Enum):
    skip = 0
    byMonitor = 1
    byMonitorTOF = 2
    byProtonCharge = 3

class RunData(DataLoader):
    def __init__(self, fname, moduleName, tofcut=30, normMethod = Normalise.byMonitor):
        super().__init__(fname, moduleName, tofcut)
        self.normalise(normMethod)
        self.moduleName = moduleName

    # += operator
    def __iadd__(self, other):
        self.detErrPro += other.detErrPro
        self.moniErrPro += other.moniErrPro
        return self

    # -= operator
    def __isub__(self, other):
        self.detErrPro -= other.detErrPro
        self.moniErrPro += other.moniErrPro
        return self
    
     # /= operator
    def __itruediv__(self, other):
        self.detErrPro /= other.detErrPro
        return self

    def normalise(self, normMethod):
        if normMethod == Normalise.skip:
            pass
        elif normMethod == Normalise.byMonitor:
            totMonitor  = self.moniErrPro.weight.sum()
            self.detErrPro.scale(1./totMonitor)

        else:
            raise RuntimeError('Unknown normalise method')
        
    def plot(self, show=False, logscale=False):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.colors as colors
            fig=plt.figure()
            ax = fig.add_subplot(111)
            H = self.detErrPro.weight
            pidNum = self.detErrPro.xcentre.shape[0]
            pidIdx = np.linspace(1, pidNum, num=pidNum, endpoint=True)

            X, Y = np.meshgrid(self.tofCentre, pidIdx)
            if logscale:
                pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=H.max()*1e-10, vmax=H.max()), shading='auto')
            else:
                pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet, shading='auto')
            fig.colorbar(pcm, ax=ax)
            plt.grid()
            plt.title(f'{self.moduleName} integral {H.sum()}')
            if show:
                plt.show()

        except Exception as e:
            print(e)



class SampleData(RunData):
    def __init__(self, fname, moduleName, bkgRun=None, holderRun=None):
        super().__init__(fname, moduleName)
        if bkgRun:
            self -= bkgRun
        if holderRun:
            self -= holderRun
