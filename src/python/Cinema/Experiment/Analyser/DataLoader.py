#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Prompt (see https://gitlab.com/xxcai1/Prompt)        ##
##                                                                            ##
##  Copyright 2021-2022 Prompt developers                                     ##
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

from Cinema.Interface import *

#!/usr/bin/env python3
import numpy as np
import h5py

def readKeys(content, file):
    try:
        for key in file.keys():
            content.append(file[key].name)
            subfile=file.get(file[key].name)
            readKeys(content,subfile)
    except AttributeError as e:
        print(e)

class ErrorPropagator():
    def __init__(self, weight,  xcentre, ycentre=None,  count=None, error = None):
        self.xcentre = np.copy(xcentre)
        self.weight = np.copy(weight)
        if error is not None:
            self.error = error
        else:
            uncet = np.sqrt(count/10.)
            self.error = np.divide(weight, uncet, where=(uncet!=0.))
        if ycentre is not None:
            self.ycentre = np.copy(ycentre)
            
    def sum(self, axisIdx):
        return self.weight.sum(axis=axisIdx)

    def compatible(self, xcentre, ycentre):
        np.testing.assert_almost_equal(self.xcentre, xcentre)
        if ycentre is not None:
            np.testing.assert_almost_equal(self.ycentre, ycentre)

    def add(self, weight, error, xcentre,  ycentre=None):
        self.compatible(xcentre, ycentre)
        self.weight = self.weight + weight
        othererror = error
        self.error = np.sqrt(self.error*self.error + othererror*othererror)

    def __iadd__(self, other):
        if hasattr(other, 'ycentre'):
            self.add(other.weight, other.error, other.xcentre, other.ycentre)
        else:
            self.add(other.weight, other.error, other.xcentre)
        return self

    def substract(self, weight, error, xcentre,  ycentre=None):
        self.compatible(xcentre, ycentre)
        self.weight = self.weight - weight
        othererror = error
        self.error = np.sqrt(self.error*self.error + othererror*othererror)

    def __isub__(self, other):
        if hasattr(other, 'ycentre'):
            self.substract(other.weight, other.error, other.xcentre, other.ycentre)
        else:
            self.substract(other.weight, other.error, other.xcentre)
        return self

    def divide(self, weight, error, xcentre,  ycentre=None):
        self.compatible(xcentre, ycentre)
        selferr = np.divide(self.error, self.weight, where=(self.weight!=0.))
        otherw = weight
        othererr = np.divide(error, otherw, where=(otherw!=0.))
        self.weight = np.divide(self.weight, otherw, where=(otherw!=0.))
        self.error = np.sqrt(selferr*selferr + othererr*othererr)*np.abs(self.weight)

    def __itruediv__(self, other):
        if hasattr(other, 'ycentre'):
            self.divide(other.weight, other.error, other.xcentre, other.ycentre)
        else:
            self.divide(other.weight, other.error, other.xcentre)
        return self

    def scale(self, factor):
        self.weight = self.weight*factor
        self.error = self.error*np.abs(factor)


    def plot(self, show=False, label=None, idx = 2000):
        try:
            import matplotlib.pyplot as plt
            print(f'{self.xcentre.shape}, {self.weight.shape}')
            if self.weight.ndim == 1:
                plt.errorbar(self.xcentre, self.weight, yerr=self.error, fmt='o', label=label)
            elif self.weight.ndim == 2:
                plt.errorbar(self.xcentre, self.weight[:,idx], yerr=self.error[:,idx], fmt='o', label=label)
            if show:
                plt.show()
        except Exception as e:
            print (e)


class DataLoader():
    def __init__(self, fname, moduleName, tofcut=30, printContent=False):
        hf=h5py.File(fname,'r')
        if printContent:
            keys=[]
            readKeys(keys, hf)
            print(keys)

        tof = hf[f'/csns/instrument/{moduleName}/time_of_flight'][()]*1.e-6 #vector, to second
        pid = hf[f'/csns/instrument/{moduleName}/pixel_id'][()].flatten() #vector
        tofpidMat = hf[f'/csns/instrument/{moduleName}/histogram_data'][()] #matrix
        tofpidMat[:, :tofcut] = 0
        self.tof = tof
        self.tofCentre = tof[:-1]+np.diff(tof)*0.5 #vector

        self.detErrPro = ErrorPropagator(tofpidMat, pid, tof, tofpidMat)

        tofMonitor = hf[f'/csns/histogram_data/monitor01/histogram_data'][()][0]  #vector or matrix
        tofMonitor[:tofcut] = 0
        self.moniErrPro = ErrorPropagator(tofMonitor, tof, count=tofMonitor)

        hf.close()