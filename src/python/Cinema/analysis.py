import numpy as np
from enum import Enum
from typing import Union, Tuple

from .Prompt.histogram.Hist import Hist1D

try:
    from mcpl import MCPLFile
except ImportError:
    raise ImportError("Fail to import MCPLFile from module `mcpl`.")

class ParticleParameter(Enum):
    """
    Enumeration of available MCPL particle parameters.
    
    These parameters correspond to the properties available in MCPL particle blocks:
    - time: Time of flight (seconds)
    - ekin: Kinetic energy (eV)
    - x, y, z: Position coordinates (mm)
    - ux, uy, uz: Direction cosines
    - polx, poly, polz: Polarization components
    - pdgcode: Particle Data Group code
    - weight: Particle weight
    - userflags: User-defined flags
    - position: Combined position vector (x, y, z)
    - polarisation: Combined polarization vector (polx, poly, polz)
    - direction: Combined direction vector (ux, uy, uz)
    """
    TIME = 'time'
    KINETIC_ENERGY = 'ekin'
    X_POSITION = 'x'
    Y_POSITION = 'y'
    Z_POSITION = 'z'
    X_DIRECTION = 'ux'
    Y_DIRECTION = 'uy'
    Z_DIRECTION = 'uz'
    X_POLARIZATION = 'polx'
    Y_POLARIZATION = 'poly'
    Z_POLARIZATION = 'polz'
    PDG_CODE = 'pdgcode'
    WEIGHT = 'weight'
    EVENT_ID = 'userflags' # the userflag is used to store neutron source event ID
    POSITION_VECTOR = 'position'
    POLARIZATION_VECTOR = 'polarisation'
    DIRECTION_VECTOR = 'direction'


class MCPL_Analyzer_1D(Hist1D):
    """
    A class for analyzing MCPL files that inherits from Hist1D.
    
    This class reads MCPL files and fills specified particle parameters into
    the histogram for analysis and visualization.
    """
    
    def __init__(self, para : Union [ParticleParameter, str] = ParticleParameter.TIME, 
                 binmin=0.0, binmax=10.0, binnum=100, linear=True, auto_range_file : str = ''):
        
        if isinstance(para, str):
            self.para = ParticleParameter(para)
        elif isinstance(para, ParticleParameter):
            self.para = para
        else:
            raise ValueError(f"Invalid parameter type: {type(para)}. Must be either a ParticleParameter enum member or a string.")
        
        if auto_range_file:
            min_val, max_val = self.getRange(auto_range_file)
            super().__init__(min_val*0.9, max_val*1.1, binnum, linear=linear)
        else:
            super().__init__(binmin, binmax, binnum, linear=linear)


    def getRange(self, filename) -> Tuple[float, float]:
        file = MCPLFile(filename)
        
        # Initialize min and max values
        min_val = float('inf')
        max_val = float('-inf')
        has_data = False
        
        for pb in file.particle_blocks:
            # Get the parameter values for this particle block
            param_values = getattr(pb, self.para.value)
            
            if len(param_values) > 0:
                has_data = True
                # Update min and max values
                min_val = min(min_val, np.min(param_values))
                max_val = max(max_val, np.max(param_values))
        
        if not has_data:
            raise ValueError(f"No particle data found in file: {filename}")
        
        return min_val, max_val
    
    def analyze(self, filename):
        file = MCPLFile(filename)
        
        for pb in file.particle_blocks:
            self.fillmany(np.asarray( getattr(pb, self.para.value), dtype=np.float64), np.asarray(pb.weight, dtype=np.float64) )