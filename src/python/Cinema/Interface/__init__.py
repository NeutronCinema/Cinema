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

from .Utils import *

import ctypes
import numpy as np
import glob
import os
import pathlib

type_sizet, type_sizetp = (ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t))
type_bool = ctypes.c_bool
type_int = ctypes.c_int
type_intp = ctypes.POINTER(ctypes.c_int)
type_uint = ctypes.c_uint
type_uintp = ctypes.POINTER(ctypes.c_uint)
type_dbl = ctypes.c_double
type_dblp = ctypes.POINTER(ctypes.c_double)
type_cstr = ctypes.c_char_p
type_voidp = ctypes.c_void_p
type_pyobject = ctypes.py_object

type_npdbl1d=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags='C_CONTIGUOUS')
type_npdbl2d=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS')
type_npsbl2d=np.ctypeslib.ndpointer(dtype=np.float32,ndim=2,flags='C_CONTIGUOUS')
type_npdbl3d=np.ctypeslib.ndpointer(dtype=np.float64,ndim=3,flags='C_CONTIGUOUS')
type_npszt1d=np.ctypeslib.ndpointer(dtype=ctypes.c_size_t,ndim=1,flags='C_CONTIGUOUS')
type_npuint1d=np.ctypeslib.ndpointer(dtype=np.uintc,ndim=1,flags='C_CONTIGUOUS')
type_npcplx2d=np.ctypeslib.ndpointer(dtype=np.complex128,ndim=2,flags='C_CONTIGUOUS')

type_npint641d=np.ctypeslib.ndpointer(dtype=np.int64,ndim=1,flags='C_CONTIGUOUS')



def _getPromptLib():
    _ptpath = os.getenv('CINEMAPATH')
    try:
        libfile = glob.glob(_ptpath +'/cinemabin/src/cxx/libprompt_core.so')[0]
    except:
        try:
            libfile = glob.glob(_ptpath + os.sep + 'libprompt_core.so')[0]
        except:
            raise IOError('CINEMAPATH enviroment need to be configured')
    return ctypes.CDLL(libfile), _ptpath

_taklib, _ptpath = _getPromptLib()

def _findData(fileName):
    pass

def importFunc(funcName, resType, argType):
    func = getattr(_taklib, funcName)
    func.restype = resType
    func.argtypes = argType
    return func

def plotStyle(fontSize=16):
    import matplotlib.style
    import matplotlib, sys
    import matplotlib.pyplot as plt

    plt.rcParams.update({'font.size': fontSize})
    matplotlib.rcParams['lines.linewidth'] = 2


    _plt_legend_orig = plt.legend
    def _plt_legend(*args,**kwargs):
        notouchframelw = False
        if 'notouchframelw' in kwargs:
            notouchframelw = True
            del kwargs['notouchframelw']
        l = _plt_legend_orig(*args,**kwargs)
        if not notouchframelw:
            l.get_frame().set_linewidth(0.0)
        return l
    plt.legend=_plt_legend

def singleton(cls):
    _instance = {}

    def inner():
        if cls not in _instance:
            _instance[cls] = cls()
        return _instance[cls]
    return inner


try:
    import gvar as gv
except ImportError:
    print("The 'gvar' library is not installed. You can install it using pip or conda.")
    print("To install using pip, run: pip install gvar")
    print("To install using conda, run: conda install -c conda-forge gvar")
from scipy.interpolate import interp1d  # CinemaXY


import numpy as np
import gvar as gv
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

class ArrayCoreMixin:
    """Core array functionality mixin"""
    def __new__(cls, input_array, *args, **kwargs):
        obj = np.asarray(input_array).view(cls)
        # Store kwargs for later initialization
        obj._init_kwargs = kwargs
        return obj
        
    def __array_finalize__(self, obj):
        if obj is None: 
            # This is for new objects being created
            if hasattr(self, '_init_kwargs'):
                # Initialize with stored kwargs
                self.__init__(**self._init_kwargs)
            return
            
        # Copy all attributes from obj to new array
        for name in getattr(obj, '_custom_attrs', []):
            setattr(self, name, getattr(obj, name, None))
        
        # Explicitly copy gvar attribute if it exists
        if hasattr(obj, 'gvar'):
            self.gvar = obj.gvar
            
    def __array_wrap__(self, out_arr, context=None):
        """Ensure mathematical operations preserve attributes"""
        if isinstance(out_arr, np.ndarray):
            # Convert back to our class if needed
            if not isinstance(out_arr, type(self)):
                out_arr = out_arr.view(type(self))
            
            # Copy all custom attributes
            for name in getattr(self, '_custom_attrs', []):
                setattr(out_arr, name, getattr(self, name, None))
            
            # Preserve gvar status
            if hasattr(self, 'gvar'):
                out_arr.gvar = self.gvar
                
        return out_arr
    
    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        """Handle NumPy ufuncs properly"""
        args = [i.view(np.ndarray) if isinstance(i, type(self)) else i 
               for i in inputs]
        result = getattr(ufunc, method)(*args, **kwargs)
        
        if method == '__call__' and ufunc.__name__ in ['multiply', 'add', 'subtract', 'divide']:
            if isinstance(result, np.ndarray):
                result = result.view(type(self))
                # Copy attributes from first input array
                first_input = next(i for i in inputs if isinstance(i, type(self)))
                for name in getattr(first_input, '_custom_attrs', []):
                    setattr(result, name, getattr(first_input, name, None))
                if hasattr(first_input, 'gvar'):
                    result.gvar = first_input.gvar
        return result

class ArrayStatsMixin:
    """Statistical operations mixin"""
    @property
    def mean(self):
        if getattr(self, 'gvar', None):
            return np.vectorize(lambda x: x.mean if isinstance(x, gv.GVar) else x)(self)
        return self
        
    @property 
    def sdev(self):
        if getattr(self, 'gvar', None):
            return np.vectorize(lambda x: x.sdev if isinstance(x, gv.GVar) else 0)(self)
        return np.zeros_like(self)
        
    @classmethod
    def from_sdev(cls, mean, sdev=None, **kwargs):
        obj = cls(gv.gvar(mean, sdev) if sdev is not None else mean)
        obj.gvar = True
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj
        
    @classmethod
    def from_counts(cls, counts, **kwargs):
        obj = cls(gv.gvar(counts, np.sqrt(counts)))
        obj.gvar = True
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

class ArrayCoordinateMixin:
    """Coordinate system mixin"""
    def __init__(self, *args, x=None, **kwargs):
        self.x = np.asarray(x) if x is not None else np.arange(len(self))
        if len(self.x) != len(self):
            raise ValueError("x coordinates must match array length")
        # Register x as a custom attribute to be preserved
        if not hasattr(self, '_custom_attrs'):
            self._custom_attrs = []
        self._custom_attrs.append('x')
            
    def __array_finalize__(self, obj):
        super().__array_finalize__(obj)
        self.x = getattr(obj, 'x', None)
        
    def __getitem__(self, item):
        result = super().__getitem__(item)
        if isinstance(result, type(self)) and hasattr(self, 'x'):
            result.x = self.x[item] if isinstance(item, (int, slice)) else self.x[np.asarray(item)]
        return result

class ArrayPlotMixin:
    """Plotting functionality mixin"""
    def plot(self, ax=None, plot_errors=True, **kwargs):
        ax = ax or plt.gca()
        x = getattr(self, 'x', np.arange(len(self)))
        y = getattr(self, 'mean', np.asarray(self))
        
        plot_kwargs = {
            'marker': kwargs.pop('marker', 'o'),
            'linestyle': kwargs.pop('linestyle', 'none'),
            'capsize': kwargs.pop('capsize', 3),
            **kwargs
        }
        
        if plot_errors and hasattr(self, 'sdev'):
            yerr = getattr(self, 'sdev')
            ax.errorbar(x, y, yerr=yerr,**plot_kwargs)
        else:
            ax.plot(x, y, **plot_kwargs)
        return ax

# Base array class
class CinemaArray(ArrayCoreMixin, ArrayStatsMixin, np.ndarray):
    pass

# Extended class with coordinates and plotting
class CinemaXY(ArrayCoordinateMixin, ArrayPlotMixin, CinemaArray):
    def interpolate(self, new_x, kind='linear'):
        new_x = np.asarray(new_x)
        if getattr(self, 'gvar', None):
            interp_mean = interp1d(self.x, self.mean, kind=kind)(new_x)
            interp_sdev = interp1d(self.x, self.sdev, kind=kind)(new_x)
            return type(self).from_sdev(interp_mean, interp_sdev, x=new_x)
        return type(self)(interp1d(self.x, self, kind=kind)(new_x), x=new_x)
    
    @classmethod
    def from_hist1d(cls, hist1d):
        """Initialize from a C++ histogram object with statistical data.
        
        Args:
            hist1d: histogram object with methods:
                    - getWeight() -> mean values
                    - getSdev() -> standard deviations
                    - getCentre() -> bin centers
        
        Returns:
            CinemaXY instance with statistical data and coordinates
        """
        return cls.from_sdev(
            mean=hist1d.getWeight(),
            sdev=hist1d.getSdev(),
            x=hist1d.getCentre()
        )


from scipy.interpolate import RegularGridInterpolator

class Array2DCoordinateMixin:
    """2D coordinate system mixin"""
    def __init__(self, *args, x=None, y=None, **kwargs):
        self.x = np.asarray(x) if x is not None else np.arange(self.shape[1])
        self.y = np.asarray(y) if y is not None else np.arange(self.shape[0])
        
        # Check dimensions - note the order is (y, x) for array shape
        if len(self.x) != self.shape[1] or len(self.y) != self.shape[0]:
            raise ValueError(
                f"Coordinate dimensions don't match array shape. "
                f"Expected x length {self.shape[1]} (got {len(self.x)}), "
                f"y length {self.shape[0]} (got {len(self.y)})"
            )
            
        # Register coordinates as custom attributes
        if not hasattr(self, '_custom_attrs'):
            self._custom_attrs = []
        self._custom_attrs.extend(['x', 'y'])
        
    def __array_finalize__(self, obj):
        super().__array_finalize__(obj)
        self.x = getattr(obj, 'x', None)
        self.y = getattr(obj, 'y', None)
        
    def __getitem__(self, item):
        result = super().__getitem__(item)
        if isinstance(result, type(self)) and hasattr(self, 'x') and hasattr(self, 'y'):
            # Handle 2D slicing - this is simplified and may need refinement
            if isinstance(item, tuple):
                y_slice, x_slice = item
                if isinstance(y_slice, (int, slice)) and isinstance(x_slice, (int, slice)):
                    result.y = self.y[y_slice]
                    result.x = self.x[x_slice]
            elif isinstance(item, (int, slice)):
                result.y = self.y[item]
                result.x = self.x
        return result

class Array2DPlotMixin:
    """2D plotting functionality mixin"""
    def plot(self, ax=None, plot_errors=False, **kwargs):
        ax = ax or plt.gca()
        x = getattr(self, 'x', np.arange(self.shape[1]))
        y = getattr(self, 'y', np.arange(self.shape[0]))
        
        if plot_errors and hasattr(self, 'sdev'):
            # For 2D data with errors, we might want to show error bars or contours
            # This is a placeholder - you might want to implement something more sophisticated
            z = getattr(self, 'mean', np.asarray(self))
            zerr = getattr(self, 'sdev')
            im = ax.imshow(zerr, extent=[x[0], x[-1], y[0], y[-1]], 
                          origin='lower', aspect='auto', **kwargs)
            plt.colorbar(im, ax=ax, label='Standard Deviation')
        else:
            z = getattr(self, 'mean', np.asarray(self))
            im = ax.imshow(z, extent=[x[0], x[-1], y[0], y[-1]], 
                          origin='lower', aspect='auto', **kwargs)
            plt.colorbar(im, ax=ax)
        return ax, im
    
    def plot_surface(self, ax=None, **kwargs):
        """Create a 3D surface plot"""
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        elif not hasattr(ax, 'plot_surface'):
            raise ValueError("The provided axes must be a 3D axes (created with projection='3d')")
            
        x = getattr(self, 'x', np.arange(self.shape[1]))
        y = getattr(self, 'y', np.arange(self.shape[0]))
        X, Y = np.meshgrid(x, y)
        Z = getattr(self, 'mean', np.asarray(self))
        
        surf = ax.plot_surface(X, Y, Z, **kwargs)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('z')
        return ax, surf

class CinemaXYZ(Array2DCoordinateMixin, Array2DPlotMixin, CinemaArray):
    """2D array with coordinates and statistical operations"""
    def __init__(self, input_array, *args, x=None, y=None, **kwargs):
        # Initialize the array first
        super().__init__(input_array, *args, **kwargs)
        # Then initialize coordinates
        Array2DCoordinateMixin.__init__(self, x=x, y=y)
        
    def interpolate(self, new_x=None, new_y=None, method='linear'):
        """Interpolate onto a new grid using RegularGridInterpolator"""
        x = getattr(self, 'x', np.arange(self.shape[1]))
        y = getattr(self, 'y', np.arange(self.shape[0]))
        
        new_x = np.asarray(new_x) if new_x is not None else x
        new_y = np.asarray(new_y) if new_y is not None else y
        
        if getattr(self, 'gvar', None):
            # Handle gvar data by interpolating mean and sdev separately
            interp_mean = RegularGridInterpolator((y, x), self.mean, method=method)
            interp_sdev = RegularGridInterpolator((y, x), self.sdev, method=method)
            
            Y_new, X_new = np.meshgrid(new_y, new_x, indexing='ij')
            points = np.column_stack([Y_new.ravel(), X_new.ravel()])
            
            mean_interp = interp_mean(points).reshape(len(new_y), len(new_x))
            sdev_interp = interp_sdev(points).reshape(len(new_y), len(new_x))
            
            return type(self).from_sdev(mean_interp, sdev_interp, x=new_x, y=new_y)
        else:
            # Regular interpolation for non-gvar data
            interp = RegularGridInterpolator((y, x), self, method=method)
            Y_new, X_new = np.meshgrid(new_y, new_x, indexing='ij')
            points = np.column_stack([Y_new.ravel(), X_new.ravel()])
            interp_values = interp(points).reshape(len(new_y), len(new_x))
            return type(self)(interp_values, x=new_x, y=new_y)
    
    @classmethod
    def from_hist2d(cls, hist2d):
        """Initialize from a 2D C++ histogram object with statistical data.
        
        Args:
            hist2d: 2D histogram object with methods:
                    - getWeight() -> mean values (2D array)
                    - getSdev() -> standard deviations (2D array)
                    - getCentreX() -> x bin centers
                    - getCentreY() -> y bin centers
        
        Returns:
            CinemaXYZ instance with statistical data and coordinates
        """
        c = hist2d.getCentre()
        return cls.from_sdev(
            mean=hist2d.getWeight(),
            sdev=hist2d.getSdev(),
            x=c[0],
            y=c[1]
        )
    
    @classmethod
    def from_function(cls, func, x, y, **kwargs):
        """Create from a function evaluated on a grid"""
        # Use indexing='xy' to match mathematical convention (len(y) rows × len(x) columns)
        X, Y = np.meshgrid(x, y, indexing='xy')
        values = func(X, Y, **kwargs)
        return cls(values, x=x, y=y)
