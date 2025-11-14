import numpy as np
from enum import Enum
from typing import Union, Tuple

from mcpl import MCPLFile
from .Prompt.histogram.Hist import Hist1D, Hist2D

try:
    from mcpl import MCPLFile
except ImportError:
    raise ImportError("Fail to import MCPLFile from module `mcpl`.")

class ParticleParameter(Enum):
    """
    Enumeration of available MCPL particle parameters.
    
    These parameters correspond to the properties available in MCPL particle blocks:
    - time: Time of flight (ms)
    - ekin: Kinetic energy (MeV)
    - x, y, z: Position coordinates (cm)
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
    
    def get_label(self) -> str:
        """
        Get appropriate axis label for this particle parameter using correct MCPL units.
        
        Returns:
            str: Formatted axis label with correct units
        """
        labels = {
            ParticleParameter.TIME: "Time of Flight (ms)",
            ParticleParameter.KINETIC_ENERGY: "Kinetic Energy (MeV)",
            ParticleParameter.X_POSITION: "X Position (cm)",
            ParticleParameter.Y_POSITION: "Y Position (cm)", 
            ParticleParameter.Z_POSITION: "Z Position (cm)",
            ParticleParameter.X_DIRECTION: "X Direction Cosine",
            ParticleParameter.Y_DIRECTION: "Y Direction Cosine",
            ParticleParameter.Z_DIRECTION: "Z Direction Cosine",
            ParticleParameter.X_POLARIZATION: "X Polarization",
            ParticleParameter.Y_POLARIZATION: "Y Polarization", 
            ParticleParameter.Z_POLARIZATION: "Z Polarization",
            ParticleParameter.PDG_CODE: "PDG Code",
            ParticleParameter.WEIGHT: "Weight",
            ParticleParameter.EVENT_ID: "Event ID",
            ParticleParameter.POSITION_VECTOR: "Position Vector",
            ParticleParameter.POLARIZATION_VECTOR: "Polarization Vector",
            ParticleParameter.DIRECTION_VECTOR: "Direction Vector"
        }
        
        return labels.get(self, self.value.replace('_', ' ').title())


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
    
    def plot(self, show=False, *args, **kwargs):
        """
        Enhanced plot method that automatically sets axis labels based on particle parameters.
        
        This method calls the underlying Hist1D.plot() method and adds appropriate
        axis labels based on the parameter type being analyzed.
        
        Args:
            show (bool): Whether to immediately display the plot
            *args: Positional arguments passed to the underlying plot method
            **kwargs: Keyword arguments passed to the underlying plot method
        """
        # Get parameter name for axis label using the enum's get_label method
        x_label = self.para.get_label()
        
        # Call the underlying plot method with show=False to prevent immediate display
        result = super().plot(show=False, *args, **kwargs)
        
        # Set axis labels if not already set
        import matplotlib.pyplot as plt
        ax = plt.gca()
        if not ax.get_xlabel():
            ax.set_xlabel(x_label)
        if not ax.get_ylabel():
            ax.set_ylabel("Weight")
        
        # Handle display if requested
        if show:
            plt.show()
        
        return result


class MCPL_Analyzer_2D(Hist2D):
    """
    A class for analyzing MCPL files that inherits from Hist2D.
    
    This class reads MCPL files and fills two specified particle parameters into
    a 2D histogram for analysis and visualization.
    """
    
    def __init__(self, xpara : Union[ParticleParameter, str] = ParticleParameter.TIME,
                 ypara : Union[ParticleParameter, str] = ParticleParameter.KINETIC_ENERGY,
                 xmin=0.0, xmax=10.0, xnum=100,
                 ymin=0.0, ymax=10.0, ynum=100,
                 auto_range_file : str = ''):
        
        # Convert parameters to enum if they are strings
        if isinstance(xpara, str):
            self.xpara = ParticleParameter(xpara)
        elif isinstance(xpara, ParticleParameter):
            self.xpara = xpara
        else:
            raise ValueError(f"Invalid x parameter type: {type(xpara)}. Must be either a ParticleParameter enum member or a string.")
        
        if isinstance(ypara, str):
            self.ypara = ParticleParameter(ypara)
        elif isinstance(ypara, ParticleParameter):
            self.ypara = ypara
        else:
            raise ValueError(f"Invalid y parameter type: {type(ypara)}. Must be either a ParticleParameter enum member or a string.")
        
        # Auto-range detection if specified
        if auto_range_file:
            xmin_val, xmax_val = self.getRange1D(auto_range_file, self.xpara)
            ymin_val, ymax_val = self.getRange1D(auto_range_file, self.ypara)
            super().__init__(xmin_val*0.9, xmax_val*1.1, xnum, 
                            ymin_val*0.9, ymax_val*1.1, ynum)
        else:
            super().__init__(xmin, xmax, xnum, ymin, ymax, ynum)
    
    def getRange1D(self, filename, para: ParticleParameter) -> Tuple[float, float]:
        """
        Get the minimum and maximum values of a specified particle parameter
        across all particle blocks in the MCPL file.
        
        Args:
            filename (str): Path to the MCPL file to analyze
            para (ParticleParameter): The parameter to analyze
            
        Returns:
            Tuple[float, float]: (min_value, max_value) of the parameter
            
        Raises:
            FileNotFoundError: If the specified file does not exist
            ValueError: If no particle data is found in the file
        """
        file = MCPLFile(filename)
        
        # Initialize min and max values
        min_val = float('inf')
        max_val = float('-inf')
        has_data = False
        
        for pb in file.particle_blocks:
            # Get the parameter values for this particle block
            param_values = getattr(pb, para.value)
            
            if len(param_values) > 0:
                has_data = True
                # Update min and max values
                min_val = min(min_val, np.min(param_values))
                max_val = max(max_val, np.max(param_values))
        
        if not has_data:
            raise ValueError(f"No particle data found in file: {filename}")
        
        return min_val, max_val
    
    def getRange2D(self, filename) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Get the 2D range (x and y min/max) of the specified particle parameters.
        
        Args:
            filename (str): Path to the MCPL file to analyze
            
        Returns:
            Tuple[Tuple[float, float], Tuple[float, float]]: 
                ((x_min, x_max), (y_min, y_max))
        """
        x_range = self.getRange1D(filename, self.xpara)
        y_range = self.getRange1D(filename, self.ypara)
        return x_range, y_range
    
    def analyze(self, filename):
        """
        Analyze the MCPL file and fill the 2D histogram with the specified parameters.
        
        Args:
            filename (str): Path to the MCPL file to analyze
        """
        file = MCPLFile(filename)
        
        for pb in file.particle_blocks:
            # Get the parameter values for x and y axes
            x_values = np.asarray(getattr(pb, self.xpara.value), dtype=np.float64)
            y_values = np.asarray(getattr(pb, self.ypara.value), dtype=np.float64)
            weights = np.asarray(pb.weight, dtype=np.float64)
            
            # Fill the 2D histogram
            self.fillmany(x_values, y_values, weights)
    
    def plot(self, show=False, *args, **kwargs):
        """
        Enhanced plot method that automatically sets axis labels based on particle parameters.
        
        This method calls the underlying Hist2D.plot() method and adds appropriate
        axis labels based on the parameter types being analyzed.
        
        Args:
            show (bool): Whether to immediately display the plot
            *args: Positional arguments passed to the underlying plot method
            **kwargs: Keyword arguments passed to the underlying plot method
            
        Returns:
            matplotlib.pyplot: The pyplot object for further customization
        """
        # Get parameter names for axis labels using the enum's get_label method
        x_label = self.xpara.get_label()
        y_label = self.ypara.get_label()
        
        # Call the underlying plot method with show=False to prevent immediate display
        result = super().plot(show=False, *args, **kwargs)
        
        # Set axis labels
        import matplotlib.pyplot as plt
        fig = plt.gcf()
        ax = fig.get_axes()[0]  # Get the first axes in the figure
        
        # Set axis labels
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        
        # Handle display if requested
        if show:
            plt.show()
        
        return result