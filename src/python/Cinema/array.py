
try:
    import gvar as gv
except ImportError:
    print("The 'gvar' library is not installed. You can install it using pip or conda.")
    print("To install using pip, run: pip install gvar")
    print("To install using conda, run: conda install -c conda-forge gvar")
from scipy.interpolate import interp1d  # CinemaXY

from .convertor import *

import numpy as np
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
        """Handle NumPy ufuncs with proper error propagation"""
        # Convert CinemaArray inputs to plain ndarray views
        args = [i.view(np.ndarray) if isinstance(i, type(self)) else i 
                for i in inputs]
        
        # Handle out= parameter if present
        if 'out' in kwargs:
            out = kwargs['out']
            if isinstance(out, tuple):
                kwargs['out'] = tuple(o.view(np.ndarray) if isinstance(o, type(self)) else o 
                                    for o in out)
            else:
                kwargs['out'] = out.view(np.ndarray) if isinstance(out, type(self)) else out

        # Call ufunc on raw arrays
        result = getattr(ufunc, method)(*args, **kwargs)

        # Wrap result back into CinemaArray if needed
        if method == '__call__':
            if isinstance(result, np.ndarray):
                # Convert back to CinemaArray and preserve attributes
                result = result.view(type(self))
                first_input = next((i for i in inputs if isinstance(i, type(self))), None)
                if first_input is not None:
                    # Copy custom attributes
                    for attr in getattr(first_input, '_custom_attrs', []):
                        setattr(result, attr, getattr(first_input, attr))
                    if hasattr(first_input, 'gvar'):
                        result.gvar = first_input.gvar
                    if hasattr(first_input, 'x'):
                        result.x = first_input.x
        
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
        """Handle array indexing including tuple indices from matplotlib"""
        # Get base array result using parent method
        result = super().__getitem__(item)
        
        # If not array-like result or no x attribute, return as-is
        if not isinstance(result, np.ndarray) or not hasattr(self, 'x'):
            return result
            
        # Handle different index types
        if isinstance(item, (int, slice)):
            # Simple integer or slice
            if isinstance(result, type(self)):
                result.x = self.x[item]
        elif isinstance(item, tuple):
            # Multiple indices (e.g. from matplotlib)
            if isinstance(result, type(self)):
                result.x = self.x[item[0]]  # Use first index for x
        elif isinstance(item, np.ndarray):
            # Boolean or integer array indexing
            if isinstance(result, type(self)):
                result.x = self.x[item]
        
        return result

class ArrayPlotMixin:
    """Plotting functionality mixin"""
    def plot(self, ax=None, bar=False, **plot_kwargs):
        """Plot data points with error bars"""
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.gca()

        # Convert data to plain numpy arrays to avoid indexing issues
        x = np.asarray(self.x)
        y = np.asarray(self.mean if hasattr(self, 'mean') else self.y)
        yerr = np.asarray(self.sdev if hasattr(self, 'sdev') else self.err)          
    
        # Check if edges attribute exists
        if hasattr(self, 'edges') and bar:
            edges = np.asarray(self.edges)
            width = np.diff(edges)
            ax.bar(x, y, width=width, yerr=yerr, **plot_kwargs)
        else:
            # Create errorbar plot
            ax.errorbar(x, y, yerr=yerr, **plot_kwargs)
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
                    - getEdges() -> bin edges
        
        Returns:
            CinemaXY instance with statistical data and coordinates
        """
        return cls.from_sdev(
            mean=hist1d.getWeight(),
            sdev=hist1d.getSdev(),
            x=hist1d.getCentre(),
            edges=hist1d.getEdges()
        )
    
    @classmethod
    def from_hdf5(cls, fname, **kwargs):
        import h5py
        with h5py.File(fname, 'r') as f:
            w = f['weight'][:]
            sdev = f['sdev'][:]
            x = f['center'][:]
            edges = f['edge'][:]
            return cls.from_sdev(mean=w, sdev =sdev, x=x, edges=edges, **kwargs) 
        
    @classmethod
    def from_mcpl(cls, fn, **kwargs):
        """Initialize from a MCPL file.
        
        Args:
            fn: MCPL file path
            **kwargs: 
                - xpara: 
                - binmin: 
                - binmax: 
                - binnum: 
                - binscale: 
        
        Returns:
            CinemaXY instance with statistical data and coordinates
        """
        try:
            from mcpl import MCPLFile
        except ImportError:
            raise ImportError("module `mcpl` not found.")
        
        available_mcpl_stat = ['time', 'ekin', 'x', 'y', 'z', 'ux', 'uy', 'uz']
        xpara = kwargs.get('xpara')
        if xpara not in available_mcpl_stat:
            raise ValueError(f"xpara '{xpara}' not available in MCPL file. Available options: {available_mcpl_stat}")

        def set_default_warn(p, default):
            pv = kwargs.get(p)
            if pv is None:
                print(f"Warning: with {p} not specified, default to '{default}'")
                kwargs[p] = default
        
        def read_particle_paraminmax(fn, xpara):
            file = MCPLFile(fn)
            _first = True
            for pb in file.particle_blocks:
                quantphy = getattr(pb, xpara)
                if _first:
                    pmin = quantphy.min()
                    pmax = quantphy.max()
                else:
                    pmin = quantphy.min() if quantphy.min() < pmin else pmin
                    pmax = quantphy.max() if quantphy.max() > pmax else pmax
                _first = False
            
            return pmin, pmax

        file = MCPLFile(fn)
        result = []

        set_default_warn('xpara', 'time')
        xpara = kwargs.get('xpara')
        pmin, pmax = read_particle_paraminmax(fn, xpara)
        set_default_warn('binmin', pmin)
        set_default_warn('binmax', pmax)
        set_default_warn('binnum', 100)
        set_default_warn('binscale', 1.)
        
        binmin = kwargs.get('binmin')
        binmax = kwargs.get('binmax')
        binnum = kwargs.get('binnum')
        binscale = kwargs.get('binscale', 1.)
        
        bins_array = np.linspace(float(binmin), float(binmax), int(binnum) + 1) * float(binscale)  # +1 for bin edges
        
        for pb in file.particle_blocks:
            weight = getattr(pb, 'weight')
            quantphy = getattr(pb, xpara) * float(binscale)
            
            h, bins = np.histogram(quantphy, bins=bins_array, weights=weight)

            if result:
                result[0] += h
            else:
                result = [h, bins]

        qphy, scores = result[1], result[0]
        x, y = qphy, scores
        return cls.from_counts(y, x=x[:-1])


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
        edges = hist2d.getEdges()  # Get edges first
        return cls.from_sdev(
            mean=hist2d.getWeight(),
            sdev=hist2d.getSdev(),
            x=c[0],
            y=c[1],
            xedges=edges[0],  # Use keyword arguments consistently
            yedges=edges[1]
        )
    
    @classmethod
    def from_function(cls, func, x, y, **kwargs):
        """Create from a function evaluated on a grid"""
        # Use indexing='xy' to match mathematical convention (len(y) rows × len(x) columns)
        X, Y = np.meshgrid(x, y, indexing='xy')
        values = func(X, Y, **kwargs)
        return cls(values, x=x, y=y)