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


__all__ = ['Hist1D', 'Hist2D', 'SpectrumEstimator', 'NumpyHist1D', 'NumpyHist2D', 'Est1D', '_pt_HistBase_dimension']


from Cinema.Interface import *
import numpy as np

_pt_Hist1D_new = importFunc('pt_Hist1D_new', type_voidp, [type_dbl, type_dbl, type_uint, type_bool])
_pt_Hist1D_delete = importFunc('pt_Hist1D_delete', None, [type_voidp])
_pt_Hist1D_getEdge = importFunc('pt_Hist1D_getEdge', None, [type_voidp, type_npdbl1d])
_pt_Hist1D_getHit = importFunc('pt_Hist1D_getHit', None, [type_voidp, type_npdbl1d])
_pt_Hist1D_getWeight = importFunc('pt_Hist1D_getWeight', None, [type_voidp, type_npdbl1d])
_pt_Hist1D_fill = importFunc('pt_Hist1D_fill', None, [type_voidp, type_dbl, type_dbl])
_pt_Hist1D_fill_many = importFunc('pt_Hist1D_fillmany', None, [type_voidp, type_sizet, type_npdbl1d, type_npdbl1d])
_pt_Hist1D_getNumBin = importFunc('pt_Hist1D_getNumBin', type_uint, [type_voidp])

# Prompt::Hist2D
_pt_Hist2D_new = importFunc('pt_Hist2D_new', type_voidp, [type_dbl, type_dbl, type_uint, type_dbl, type_dbl, type_uint])
_pt_Hist2D_delete = importFunc('pt_Hist2D_delete', None, [type_voidp])
_pt_Hist2D_getWeight = importFunc('pt_Hist2D_getWeight', None, [type_voidp, type_npdbl2d])
_pt_Hist2D_getHit = importFunc('pt_Hist2D_getHit', None, [type_voidp, type_npdbl2d])
_pt_Hist2D_getDensity = importFunc('pt_Hist2D_getDensity', None, [type_voidp, type_npdbl2d])
_pt_Hist2D_fill = importFunc('pt_Hist2D_fill', None, [type_voidp, type_dbl, type_dbl, type_dbl])
_pt_Hist2D_merge = importFunc('pt_Hist2D_merge', None, [type_voidp, type_voidp])
_pt_Hist2D_fill_many = importFunc('pt_Hist2D_fillmany', None, [type_voidp, type_sizet, type_npdbl1d, type_npdbl1d, type_npdbl1d])
_pt_Hist2D_getWeight = importFunc('pt_Hist2D_getWeight', None, [type_voidp, type_npdbl2d])
_pt_Hist2D_getYMin = importFunc('pt_Hist2D_getYMin', type_dbl, [type_voidp])
_pt_Hist2D_getYMax = importFunc('pt_Hist2D_getYMax', type_dbl, [type_voidp])
_pt_Hist2D_getNBinX = importFunc('pt_Hist2D_getNBinX', type_uint, [type_voidp])
_pt_Hist2D_getNBinY = importFunc('pt_Hist2D_getNBinY', type_uint, [type_voidp])

# Prompt::HistBase
_pt_HistBase_merge = importFunc('pt_HistBase_merge', None, [type_voidp, type_voidp])
_pt_HistBase_getXMin = importFunc('pt_HistBase_getXMin', type_dbl, [type_voidp])
_pt_HistBase_getXMax = importFunc('pt_HistBase_getXMax', type_dbl, [type_voidp])
_pt_HistBase_getTotalWeight = importFunc('pt_HistBase_getTotalWeight', type_dbl, [type_voidp])
_pt_HistBase_getAccWeight = importFunc('pt_HistBase_getAccWeight', type_dbl, [type_voidp])
_pt_HistBase_getOverflow = importFunc('pt_HistBase_getOverflow', type_dbl, [type_voidp])
_pt_HistBase_getUnderflow = importFunc('pt_HistBase_getUnderflow', type_dbl, [type_voidp])
_pt_HistBase_getTotalHit = importFunc('pt_HistBase_getTotalHit', type_dbl, [type_voidp])
_pt_HistBase_getDataSize = importFunc('pt_HistBase_getDataSize', type_sizet, [type_voidp])
_pt_HistBase_scale = importFunc('pt_HistBase_scale', None, [type_voidp, type_dbl])
_pt_HistBase_reset = importFunc('pt_HistBase_reset', None, [type_voidp])
_pt_HistBase_getRaw = importFunc('pt_HistBase_getRaw', None, [type_voidp, type_npdbl1d])
_pt_HistBase_getHit = importFunc('pt_HistBase_getHit', None, [type_voidp, type_npdbl1d])
_pt_HistBase_getww = importFunc('pt_HistBase_getww', None, [type_voidp, type_npdbl1d])
_pt_HistBase_getww2d = importFunc('pt_HistBase_getww_2dalias', None, [type_voidp, type_npdbl2d])

_pt_HistBase_dimension = importFunc('pt_HistBase_dimension', type_uint, [type_voidp])
_pt_HistBase_getName = importFunc('pt_HistBase_getName', type_cstr, [type_voidp])
_pt_HistBase_setWeight = importFunc('pt_HistBase_setWeight', None, [type_voidp, type_npdbl1d, type_sizet])
_pt_HistBase_setHit = importFunc('pt_HistBase_setHit', None, [type_voidp, type_npdbl1d, type_sizet])
_pt_HistBase_setWW  = importFunc('pt_HistBase_setWW', None, [type_voidp, type_npdbl1d, type_sizet])

class HistBase():
    def __init__(self, cobj) -> None:
        self.cobj = cobj

    def merge(self, anotherhist):
        _pt_HistBase_merge(self.cobj, anotherhist.cobj)

    def setWeight(self, w: np.ndarray):
        if w.size != self.getDataSize():
            raise RuntimeError('')
        _pt_HistBase_setWeight(self.cobj, w.flatten(), w.size)

    def setHit(self, h: np.ndarray):
        if h.size != self.getDataSize():
            raise RuntimeError('')
        _pt_HistBase_setHit(self.cobj, h.flatten(), h.size)

    def setWW(self, h: np.ndarray):
        if h.size != self.getDataSize():
            raise RuntimeError('')
        _pt_HistBase_setWW(self.cobj, h.flatten(), h.size)
    

    def getXMin(self):
        return _pt_HistBase_getXMin(self.cobj)
    
    def getXMax(self):
        return _pt_HistBase_getXMax(self.cobj)

    def getTotalWeight(self):
        return _pt_HistBase_getTotalWeight(self.cobj)

    def getAccWeight(self):
        return _pt_HistBase_getAccWeight(self.cobj)
    
    def getOverflow(self):
        return _pt_HistBase_getOverflow(self.cobj)
    
    def getUnderflow(self):
        return _pt_HistBase_getUnderflow(self.cobj)
    
    def getTotalHit(self):
        return _pt_HistBase_getTotalHit(self.cobj)

    def getDataSize(self):
        return _pt_HistBase_getDataSize(self.cobj)
    
    def scale(self, scale):
        _pt_HistBase_scale(self.cobj, scale)

    def reset(self):
        _pt_HistBase_reset(self.cobj)

    def getSdev(self):
        return np.sqrt(self.getWW())
    
    def getWW(self):
        d = np.zeros(self.getDataSize())
        _pt_HistBase_getww(self.cobj, d)
        return d
    
    def getWeight(self):
        d = np.zeros(self.getDataSize())
        _pt_HistBase_getRaw(self.cobj, d)
        return d
    
    def getHit(self):
        d = np.zeros(self.getDataSize())
        _pt_HistBase_getHit(self.cobj, d)
        return d
    
    def dimension(self):
        return _pt_HistBase_dimension(self.cobj)
    
    def getName(self):
        return _pt_HistBase_getName(self.cobj).decode('utf-8')
    

    
class Hist1D(HistBase):
    def __init__(self, xmin=None, xmax=None, num=None, linear=True, cobj=None):
        if all(item is not None for item in [xmin, xmax, num]):
            self.managedBySelf = True
            cobj = _pt_Hist1D_new(xmin, xmax, num, linear)
        elif cobj is not None:  
            self.managedBySelf = False 

        if not hasattr(self, 'managedBySelf'):
            raise RuntimeError('Failed to create Hist1D')

        super().__init__(cobj)     
        self.numbin = _pt_Hist1D_getNumBin(self.cobj)

    def __del__(self):
        # the object is not borrowed from C++, so delete it by python
        if self.managedBySelf: 
            _pt_Hist1D_delete(self.cobj)

    def getEdge(self):
        edge = np.zeros(self.numbin+1)
        _pt_Hist1D_getEdge(self.cobj, edge)
        return edge

    def getCentre(self):
        edge = self.getEdge()
        center = edge[:-1]+np.diff(edge)*0.5
        return center

    def getMean(self):
        if self.getAccWeight()==0:
            return 0
        else:
            return (self.getCentre() * self.getWeight()).sum()/self.getAccWeight()


    def fill(self, x, weight=1.):
        _pt_Hist1D_fill(self.cobj, x, weight)

    def fillmany(self, x, weight=None):
        if weight is None:
            weight = np.ones(x.size)
        if(x.size !=weight.size):
            raise RunTimeError('fillnamy different size')
        
        _pt_Hist1D_fill_many(self.cobj, x.size, np.ascontiguousarray(x), np.ascontiguousarray(weight) )

    def plot(self, show=False, label=None, title=None, log=False, sigma=1):
        try:
            import matplotlib.pyplot as plt
            from Cinema.Interface import plotStyle
            plotStyle()
            center = self.getCentre()
            w = self.getWeight()
            err = self.getSdev()
            plt.errorbar(center, w, yerr=err*sigma, fmt='s-', label=f'Weight {w.sum()}' if label is None else f'{label} {w.sum()}')
            if isinstance(log, list):
                if list[0]:
                    plt.xscale('log')
                if list[1]:
                    plt.yscale('log')
            elif log:
                plt.yscale('log')
                plt.xscale('log')
            plt.title(_pt_HistBase_getName(self.cobj).decode('utf-8') if title is None else title)

            plt.legend(loc=0)
            if show:                
                plt.show()
            else: 
                return plt
        except Exception as e:
            print (e)
    
    def savefig(self, fname, title="Histogram", log = False):
        plt = self.plot(False, title=title, log = log)
        plt.savefig(fname=fname, dpi=300)
        plt.close()

    def save(self, fn):
        import h5py
        f0=h5py.File(fn,"w")
        f0.create_dataset("center", data=self.getCentre(), compression="gzip")
        f0.create_dataset("weight", data=self.getWeight(), compression="gzip")
        f0.create_dataset("hit", data=self.getHit(), compression="gzip")
        f0.create_dataset("sdev", data=self.getSdev(), compression="gzip")
        f0.close()

class Hist2D(HistBase):
    def __init__(self, xmin=None, xmax=None, xnum=None, ymin=None, ymax=None, ynum=None, metadata=None, cobj=None):
        if all(item is not None for item in [xmin, xmax, xnum, ymin, ymax, ynum]):
            self.managedBySelf = True
            cobj = _pt_Hist2D_new(xmin, xmax, xnum, ymin, ymax, ynum)
        elif cobj is not None:  
            self.managedBySelf = False 

        if not hasattr(self, 'managedBySelf'):
            raise RuntimeError('Failed to create Hist1D')

        super().__init__(cobj)    

        self.xmin = _pt_HistBase_getXMin(self.cobj)
        self.xmax = _pt_HistBase_getXMax(self.cobj)

        self.ymin = _pt_Hist2D_getYMin(self.cobj)
        self.ymax = _pt_Hist2D_getYMax(self.cobj)

        self.xNumBin = _pt_Hist2D_getNBinX(self.cobj)
        self.yNumBin = _pt_Hist2D_getNBinY(self.cobj)

 
        self.xedge = np.linspace(self.xmin, self.xmax, self.xNumBin+1)
        self.xcenter = self.xedge[:-1]+np.diff(self.xedge)*0.5

        self.yedge = np.linspace(self.ymin, self.ymax, self.yNumBin+1)
        self.ycenter = self.yedge[:-1]+np.diff(self.yedge)*0.5

        self.metadata = metadata
    
    def __del__(self):
        # the object is not borrowed from C++, so delete it by python
        if self.managedBySelf: 
            _pt_Hist2D_delete(self.cobj)


    def getEdge(self):
        return self.xedge, self.yedge
    
    def getCentre(self):
        xedge = self.getEdge()[0]
        yedge = self.getEdge()[1]
        xcenter = xedge[:-1]+np.diff(xedge)*0.5
        ycenter = yedge[:-1]+np.diff(yedge)*0.5
        return xcenter, ycenter

    def getWeight(self):
        w = np.zeros([self.xNumBin, self.yNumBin])
        _pt_Hist2D_getWeight(self.cobj, w)
        return w
    
    def getWW(self):
        w = np.zeros([self.xNumBin, self.yNumBin])
        _pt_HistBase_getww2d(self.cobj, w)
        return w

    def getHit(self):
        hit = np.zeros([self.xNumBin,self.yNumBin])
        _pt_Hist2D_getHit(self.cobj, hit)
        return hit

    def getDensity(self):
        d = np.zeros([self.xNumBin, self.yNumBin])
        _pt_Hist2D_getWeight(self.cobj, d)
        return d

    def fill(self, x, y, weight=1.):
        _pt_Hist2D_fill(self.cobj, x, y, weight)

    def fillmany(self, x, y, weight=None):
        if weight is None:
            weight = np.ones(x.size)
        if x.size !=weight.size and x.size !=y.size:
            raise RunTimeError('fillnamy different size')
        _pt_Hist2D_fill_many(self.cobj, x.size, x, y, weight )

    def plot(self, show=False, title=None, log=True, logx=False, dynrange=1e-3):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.colors as colors
            from Cinema.Interface import plotStyle
            plotStyle()
            fig=plt.figure()
            ax = fig.add_subplot(111)
            H = self.getWeight().T

            X, Y = np.meshgrid(self.xcenter, self.ycenter)
            if log:
                pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet, norm=colors.LogNorm(vmin=H.max()*dynrange, vmax=H.max()), shading='auto')
            else:
                pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet, shading='auto')

            fig.colorbar(pcm, ax=ax)
            if logx:
                plt.xscale('log')

            plt.grid()
            plt.title((_pt_HistBase_getName(self.cobj).decode('utf-8') if title is None else title) + f', Weight {H.sum()}')

            if show:
                plt.show()
            else:
                return plt
                

        except Exception as e:
            print(e)

    def savefig(self, fname, title="Histogram", log=True):
        plt = self.plot(False, title=title, log=log)
        plt.savefig(fname=fname, dpi=300)
        plt.close()


    def save(self, fn):
        import h5py
        f0=h5py.File(fn,"w")
        f0.create_dataset("xcenter", data=self.xcenter, compression="gzip")
        f0.create_dataset("ycenter", data=self.ycenter, compression="gzip")
        f0.create_dataset("weight", data=self.getWeight(), compression="gzip")
        f0.create_dataset("hit", data=self.getHit(), compression="gzip")
        f0.create_dataset("sdev", data=self.getSdev(), compression="gzip")
        f0.close()

    def merge(self, hist2):
        if id(self.cobj) == id(hist2.cobj):
            raise RuntimeError('merging a histogram with itself. The histogram can be scaled up by 2 instead')
        _pt_Hist2D_merge(self.cobj, hist2.cobj)


_pt_Est1D_new = importFunc('pt_Est1D_new', type_voidp, [type_dbl, type_dbl, type_uint, type_bool])
_pt_Est1D_delete = importFunc('pt_Est1D_delete', None, [type_voidp])
_pt_Est1D_fill = importFunc('pt_Est1D_fill', None, [type_voidp, type_dbl, type_dbl, type_dbl])

class Est1D(Hist1D):
    def __init__(self, xmin, xmax, num, linear=True):
        super().__init__(xmin, xmax, num, linear)

    def __del__(self):
        _pt_Est1D_delete(self.cobj)

    def fill(self, x, w, e):
        _pt_Est1D_fill(self.cobj, x, w, e)

    def fillmany(self, x, w, e):
        vfillxwh = np.vectorize(self.fill)
        return vfillxwh(x, w, e)

    def getError(self):
        return self.getHit() #hit contains error in this class

    def plot(self, show=False, label=None):
        try:
            import matplotlib.pyplot as plt
            center = self.getCentre()
            w = self.getWeight()
            err = self.getError()
            plt.errorbar(center, w, yerr=err, fmt='o', label=label)
            if show:
                plt.show()
        except Exception as e:
            print (e)

class SpectrumEstimator(Hist1D):
    def __init__(self, xmin, xmax, num, linear=True):
        super().__init__(xmin, xmax, num, linear)
        self.hitCounter = Hist1D(xmin, xmax, num, linear)

    def fill(self, x, weight, hit):
        super().fill(x, weight)
        self.hitCounter.fill(x, hit)

    def fillmany(self, x, weight, hit):
        vfillxwh = np.vectorize(self.fill)
        return vfillxwh(x, weight, hit)

    def getError(self):
        uncet = np.sqrt(self.hitCounter.getHit()/10.)
        err = np.divide(self.getWeight(), uncet, where=(uncet!=0.))
        return err

    def plot(self, show=False, label=None):
        try:
            import matplotlib.pyplot as plt
            center = self.getCentre()
            w = self.getWeight()
            err = self.getError()
            plt.errorbar(center, w, yerr=err, fmt='o', label=label)
            if show:
                plt.show()
        except Exception as e:
            print (e)




# class CobjHist2(object):
#     def __init__(self, xmin, xmax, xnum, ymin, ymax, ynum):
#         super().__init__()
#         self.cobj =_pt_Hist2D_new(xmin, xmax, xnum, ymin, ymax, ynum)

#     def __del__(self):
#         _pt_Hist2D_delete(self.cobj)



# Class NumpyHist1D is written to validate the class Hist1D only. It shouldn't be used in practice due to its significantly slower performance.
class NumpyHist1D():
    def __init__(self, xbin, range):
        range=np.array(range)
        # if range.shape != 2:
        #     raise IOError('wrong range shape')
        self.range=range
        self.xedge=np.linspace(range[0], range[1], xbin+1)
        if range[0] == range[1]:
            raise IOError('wrong range input')
        self.xbinfactor=xbin/float(range[1]-range[0])
        self.xmin=range[0]
        self.xmax=range[1]
        self.hist =np.zeros([xbin])

    def fill(self, x, weights=None):
        h, xedge = np.histogram(x, bins=self.xedge, weights=weights)
        self.hist += h

    def getHistVal(self):
        return self.hist

    def getXedges(self):
        return self.xedge

    def getYedges(self):
        return self.yedge

# Class NumpyHist2D is written to validate the class Hist2D only. It shouldn't be used in practice due to its significantly slower performance.
class NumpyHist2D():
    def __init__(self, xbin, ybin, range):
        range=np.array(range)
        if range.shape != (2,2):
            raise IOError('wrong range shape')
        self.range=range
        self.xedge=np.linspace(range[0][0], range[0][1], xbin+1)
        self.yedge=np.linspace(range[1][0], range[1][1], ybin+1)
        if range[0][0] == range[0][1] or range[1][0] == range[1][1]:
            raise IOError('wrong range input')
        self.xbinfactor=xbin/float(range[0][1]-range[0][0])
        self.ybinfactor=ybin/float(range[1][1]-range[1][0])
        self.xmin=range[0][0]
        self.xmax=range[0][1]
        self.ymin=range[1][0]
        self.ymax=range[1][1]
        self.hist =np.zeros([xbin, ybin])

    def fill(self, x, y, weights=None):
        h, xedge, yedge = np.histogram2d(x, y, bins=[self.xedge, self.yedge], weights=weights)
        self.hist += h

    def getHistVal(self):
        return self.hist

    def getXedges(self):
        return self.xedge

    def getYedges(self):
        return self.yedge

    def show(self):
        import matplotlib.pyplot as plt
        fig=plt.figure()
        ax = fig.add_subplot(111)
        H = self.hist.T

        X, Y = np.meshgrid(self.xedge, self.yedge)
        import matplotlib.colors as colors
        pcm = ax.pcolormesh(X, Y, H, cmap=plt.cm.jet,  norm=colors.LogNorm(vmin=H.max()*1e-4, vmax=H.max()),)
        fig.colorbar(pcm, ax=ax)
        plt.xlabel('Q, Aa^-1')
        plt.ylabel('energy, eV')
        plt.show()
