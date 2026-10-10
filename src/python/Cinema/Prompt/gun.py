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

from ..Interface import *
from .configstr import ConfigString
from Cinema.convertor import wl2ekin

_pt_PythonGun_new = importFunc('pt_PythonGun_new', type_voidp, [type_int])
_pt_PythonGun_delete = importFunc('pt_PythonGun_delete', None, [type_voidp])
_pt_PythonGun_pushToStack = importFunc('pt_PythonGun_pushToStack', None, [type_voidp, type_npdbl1d])
_pt_PythonGun_pushToStackMany = importFunc('pt_PythonGun_pushToStackMany', None, [type_voidp, type_npdbl1d, type_uint])

# Memory layout of one particle as handed over ctypes to the C++ backend: 9
# packed float64 values which PTPythonGun.cc reads at fixed offsets and a
# stride of 9 doubles. Any other dtype would be read as garbage particles (or
# overread the buffer) without an error, so PythonGun validates pdata against
# this layout before every push.
_canonical_particle_dtype = np.dtype([
    ('ekin', np.float64),  # energy
    ('w', np.float64),     # weight
    ('t', np.float64),     # time
    ('pos', np.float64, 3), # position (x, y, z)
    ('dir', np.float64, 3)  # direction (dx, dy, dz)
])


class Gun():
    """
    Base class for all particle gun implementations.
    
    A particle gun is responsible for generating particle properties (energy, position, 
    direction, etc.) for Monte Carlo simulations.
    
    Attributes:
        pdg (int): Particle Data Group code identifying the particle type (default: 2112 for neutron)
    """
    def __init__(self):
        self.pdg = 2112  # Default to neutron (PDG code 2112)

class PythonGun(Gun):
    """
    Customizable particle gun implemented in Python with C++ backend integration.
    
    This class provides a flexible gun implementation where users can override
    sampling methods to customize particle generation behavior. It interfaces with
    C++ backend for efficient particle stacking.
    
    Attributes:
        pdg (int): Particle Data Group code
        cobj (void*): Pointer to C++ gun object
        particle_dtype (numpy.dtype): Packed layout of one particle: 9 float64
            values (ekin, w, t, pos[3], dir[3]). The C++ backend reads it at
            fixed offsets, so it must not be changed.
    """
    def __init__(self, pdg: int =2112, vectorized: int = 1):
        """
        Initialize PythonGun with specified particle type.
        
        Args:
            pdg (int, optional): Particle Data Group code. Defaults to 2112 (neutron).
        """
        self.pdg = pdg
        self.vectorized = vectorized
        self.cobj = _pt_PythonGun_new(int(self.pdg))
        self.particle_dtype = _canonical_particle_dtype
        if self.vectorized < 1:
            raise RuntimeError(f'vectorized must be a positive integer, got {self.vectorized}')
        self.pdata = np.zeros(self.vectorized, dtype=self.particle_dtype)
        self._validate_pdata(self.vectorized)
        
    def __del__(self):
        _pt_PythonGun_delete(self.cobj)

    def _validate_pdata(self, num):
        """
        Check self.pdata against the layout expected by the C++ backend.

        C++ reads each particle as 9 packed float64 values at fixed offsets
        (src/cxx/Gun/libsrc/PTPythonGun.cc). Any other dtype would be read as
        garbage particles or overread the buffer silently, so reject it here,
        in Python, while a proper error can still be raised.

        Args:
            num (int): Number of particles about to be pushed to C++
        """
        if self.pdata.dtype != _canonical_particle_dtype:
            raise ValueError(
                f'PythonGun.pdata must have the packed float64 layout {_canonical_particle_dtype} '
                f'(9 doubles per particle, read by C++ at fixed offsets), got {self.pdata.dtype}. '
                f'Do not override particle_dtype or change the field order/types of pdata.')
        if self.pdata.ndim != 1:
            raise ValueError(f'PythonGun.pdata must be a 1D array, got {self.pdata.ndim} dimensions.')
        if self.pdata.size < num:
            raise ValueError(f'PythonGun.pdata holds {self.pdata.size} particles, but {num} are requested.')

    def generate(self, num=None):
        """
        Generate a particle with implemented methods for energy, weight, time, position, and direction.
        
        Raises:
            RuntimeError: If sampled direction vector has zero magnitude
            ValueError: If pdata does not match the particle layout expected by the C++ backend
        """
        if num is not None and num != self.vectorized:
            if num<1:
                raise RuntimeError('num should be an integer')
            self.pdata = np.zeros(num, dtype=self.particle_dtype)
        self._validate_pdata(self.vectorized if num is None else num)

        # sample a parameters and norm
        self.sample(self.vectorized if num is None else num)  

        norm = np.linalg.norm(self.pdata['dir'], axis=1)
        if np.any(norm == 0.):
            raise RuntimeError('Sampled direction is zero')
        self.pdata['dir']  /= norm[:, np.newaxis]

        _pt_PythonGun_pushToStackMany(self.cobj, self.pdata.view(np.float64), self.vectorized if num is None else num)  # Push particle to C++ stack

        if num is not None and num != self.vectorized:
            self.pdata = np.zeros(self.vectorized, dtype=self.particle_dtype)
        
    def sample(self, sample_size):
        """Sample particle parameters directly into self.pdata"""

        # Call all sampling methods with consistent parameter
        self.sampleEnergy(sample_size)
        self.sampleWeight(sample_size)
        self.sampleTime(sample_size)
        self.samplePosition(sample_size)
        self.sampleDirection(sample_size)

    def sampleEnergy(self, num):
        """Sample particle energy. Default: 0.0253 eV."""
        # NumPy broadcasting will handle scalar to array conversion
        self.pdata['ekin'] = 0.0253

    def sampleWeight(self, num=None):
        """Sample particle weight. Default: 1.0."""
        self.pdata['w'] = 1.0
    
    def sampleTime(self, num=None):
        """Sample emission time. Default: 0.0."""
        self.pdata['t'] = 0.0
    
    def samplePosition(self, num=None):
        """Sample emission position. Default: origin."""
        # NumPy broadcasting will handle list to array conversion
        self.pdata['pos'] = [0., 0., 0.]
    
    def sampleDirection(self, num=None):
        """Sample emission direction. Default: +Z axis."""
        self.pdata['dir'] = [0., 0., 1.]


class IsotropicGun(Gun, ConfigString):
    """
    Monoenergetic point source, uniformly distributed in all directions.
    Energy and position configurable. Not for direction
    
    Attributes:
        cfg_gun (str): Gun type identifier ('IsotropicGun')
        cfg_position (str): Emission position as 'x,y,z' string
        cfg_energy (float): Particle energy in eV
    """
    def __init__(self) -> None:
        """Initialize with default isotropic gun configuration."""
        super().__init__()
        self.cfg_gun='IsotropicGun'
        self.cfg_position = '0,0,0.'
        self.cfg_energy = 0

    def setPosition(self, pos):
        """
        Set the emission position.
        
        Args:
            pos (array-like): 3D position coordinates [x, y, z]
        """
        self.cfg_position = f'{pos[0]}, {pos[1]}, {pos[2]}'

    def setEnergy(self, ekin):
        """
        Set particle kinetic energy.
        
        Args:
            ekin (float): Kinetic energy in eV
        """
        self.cfg_energy = ekin

    def setWavelength(self, wl):
        """
        Set particle wavelength (converts to energy).
        
        Args:
            wl (float): Wavelength in Ångström
        """
        self.cfg_energy = wl2ekin(wl)

class SimpleThermalGun(IsotropicGun):
    """
    Monoenergetic point source with fixed emission direction.
    Energy, positon, direction configurable.
    
    Attributes:
        cfg_direction (str): Emission direction as 'dx,dy,dz' string
    """
    def __init__(self) -> None:
        """Initialize with default thermal gun configuration."""
        super().__init__()
        self.cfg_gun='SimpleThermalGun'
        self.cfg_direction = '0,0,1.'

    def setDirection(self, dir):
        """
        Set the emission direction.
        
        Args:
            dir (array-like): 3D direction vector [dx, dy, dz]
        """
        self.cfg_direction = f'{dir[0]}, {dir[1]}, {dir[2]}'

class SurfaceSource(Gun, ConfigString):
    """
    Base class for surface-based particle sources.
    
    Modeling sources generating particles from source opening to slit opening.
    Commonly used for moderator and collimator simulations.
    
    Example:

        >>> src = SurfaceSource()
        >>> src.setSource([100, 100, 10])
        >>> src.setSlit([50, 50, 5])
    The above example create a source from a 100x100 mm source opening at 10 mm (global coordinate) 
    to a 50x50 mm slit opening at 15 mm (global coordinate),
    where both the openings center at the origin (0,0,0).

    """
    def __init__(self, src_whz=None, slit_whz=None):
        """
        Initialize surface source with optional dimensions.
        
        Args:
            src_whz (array-like, optional): Source dimensions [width, height, src_zcoord]
            slit_whz (array-like, optional): Slit dimensions [width, height, slit_zcoord]
        """
        super().__init__()
        if src_whz:
            self.setSource(src_whz)
        if slit_whz:
            self.setSlit(slit_whz)

    def setSource(self, whz):
        """
        Set source dimensions.
        
        Args:
            whz (array-like): Source dimensions [width, height, depth]
        """
        self.cfg_src_w = whz[0]
        self.cfg_src_h = whz[1]
        self.cfg_src_z = whz[2]

    def setSlit(self, whz):
        """
        Set slit collimator dimensions.
        
        Args:
            whz (array-like): Slit dimensions [width, height, distance]
        """
        self.cfg_slit_w = whz[0]
        self.cfg_slit_h = whz[1]
        self.cfg_slit_z = whz[2]

class MaxwellianGun(SurfaceSource):
    """
    Maxwell-Boltzmann energy distribution surface gun.
    
    Attributes:
        cfg_temperature (float): Temperature in Kelvin for Maxwellian distribution
    """
    def __init__(self, src_whz=None, slit_whz=None, temperature=293.15):
        """
        Initialize Maxwellian gun with temperature and dimensions.
        
        Args:
            src_whz (array-like, optional): Source dimensions [width, height, src_zcoord]
            slit_whz (array-like, optional): Slit dimensions [width, height, slit_zcoord]
            temperature (float, optional): Temperature in K. Default: 293.15 (room temp)
        """
        super().__init__(src_whz, slit_whz)
        self.setTemperature(temperature)
        self.cfg_gun='MaxwellianGun'
        
    def setTemperature(self, temp):
        """
        Set temperature for Maxwellian distribution.
        
        Args:
            temp (float): Temperature in Kelvin
        """
        self.cfg_temperature = temp

class UniModeratorGun(SurfaceSource):
    """
    Uniformly distributed wavelength gun.
    
    Attributes:
        cfg_mean_wl (float): Central wavelength in Ångström
        cfg_range_wl (float): Wavelength range around mean, 
            resulting in a uniform distribution of wavelengths U[mean-range, mean+range]
    """
    def __init__(self, src_whz=None, slit_whz=None, wl_mean=1., wl_range=0.0001):
        """
        Initialize uniform moderator gun.
        
        Args:
            src_whz (array-like, optional): Source dimensions [width, height, src_zcoord]
            slit_whz (array-like, optional): Slit dimensions [width, height, slit_zcoord]
            wl_mean (float, optional): Central wavelength. Default: 1.0 Å
            wl_range (float, optional): Wavelength window. Default: 0.0001 Å
        """
        super().__init__(src_whz, slit_whz)
        self.setWlMean(wl_mean)
        self.setWlRange(wl_range)
        self.cfg_gun='UniModeratorGun'
    
    def setWlMean(self, wl):
        """
        Set central wavelength.
        
        Args:
            wl (float): Central wavelength in Ångström
        """
        self.cfg_mean_wl = wl

    def setWlRange(self, wl_range):
        """
        Set wavelength distribution range.
        
        Args:
            wl_range (float): Wavelength range around mean in Ångström, 
                resulting in a uniform distribution of wavelengths U[mean-range, mean+range]
        """
        self.cfg_range_wl = wl_range

class MCPLGun(Gun, ConfigString):
    """
    Gun that reads particles from MCPL (Monte Carlo Particle List) files.
    
    Allows reusing previously simulated particle data. Useful for source
    term recycling and variance reduction techniques.
    
    Attributes:
        cfg_mcplfile (str): Path to MCPL input file
    """
    def __init__(self, mcplfile = None) -> None:
        """
        Initialize MCPL gun with optional file.
        
        Args:
            mcplfile (str, optional): Path to MCPL file
        """
        super().__init__()
        if mcplfile:
            self.setMCPLFile(mcplfile)
        self.cfg_gun='MCPLGun'

    def setMCPLFile(self, mcplfile):
        """
        Set MCPL input file.
        
        Args:
            mcplfile (str): Path to MCPL file

        Raises:
            FileNotFoundError: If mcplfile does not exist
        """
        if not os.path.isfile(mcplfile):
            raise FileNotFoundError(f'MCPL input file not found: {mcplfile}')
        self.cfg_mcplfile = mcplfile

class MPIGun(SurfaceSource):
    """
    A built-in gun.
    """
    def __init__(self, src_whz=None, slit_whz=None):
        """Initialize MPI gun with optional dimensions."""
        super().__init__(src_whz, slit_whz)
        self.cfg_gun='MPIGun'

class SANSGun(SurfaceSource):
    """
    A built-in gun.
    """
    def __init__(self, src_whz=None, slit_whz=None):
        """Initialize SANS gun with optional dimensions."""
        super().__init__(src_whz, slit_whz)
        self.cfg_gun='SANSGun'