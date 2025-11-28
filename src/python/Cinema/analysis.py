import numpy as np
from enum import Enum
from typing import Union, Tuple, Type, List, Optional, Callable
from abc import ABC, abstractmethod

from mcpl import MCPLFile
from .Prompt.histogram.Hist import Hist1D, Hist2D
from .convertor import angleCosine2Q, wl2ekin, ekin2wl, ekin2v, v2ekin, MeV2eV, eV2MeV, meV2eV, eV2MeV

try:
    from mcpl import MCPLFile
except ImportError:
    raise ImportError("Fail to import MCPLFile from module `mcpl`.")

class UNITEnum(Enum):
    @classmethod
    def _missing_(self, value):
        availables = [u.value for u in self]
        raise ValueError(f"Invalid unit '{value}' for {self.__name__}, availables: {availables}")

    @classmethod
    def get_default(cls) -> 'UNITEnum':
        raise NotImplementedError("Default unit not implemented.")

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert time to this unit.
        
        Returns:
            float: The conversion factor
        """
        raise NotImplementedError("Conversion factor not implemented.")
    
    @classmethod
    def from_str(cls, value: str):
        """
        Create a UNITEnum instance from a string value.
        
        Args:
            value (str): The string value to create the instance from.
        
        Returns:
            UNITEnum: The created instance.
        """
        return cls(value)
    
    def _convert_to_by_multiplication(self, value: Union[float, np.ndarray], target_unit: 'UNITEnum') -> Union[float, np.ndarray]:
        return value * target_unit.conversion_factor / self.conversion_factor
    
    def convert_to(self):
        raise NotImplementedError("Unit conversion not implemented.")
    
class NotImplementedUnit(UNITEnum):
    """
    Placeholder for unit not implemented.
    """
    @classmethod
    def from_str(cls, value):
        raise NotImplementedError(f"Unit '{value}' not implemented.")
    
    @classmethod
    def get_default(cls) -> 'NotImplementedUnit':
        raise NotImplementedError("Unit not implemented.")

    @property
    def conversion_factor(self) -> float:
        raise NotImplementedError("Unit not implemented.")
    
class TimeUnit(UNITEnum):
    """
    Enumeration of available time units.
    """
    SECOND = 's'
    MILLISECOND = 'ms'
    MICROSECOND = 'us'
    NANOSECOND = 'ns'

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert time to this unit.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            TimeUnit.SECOND: 1e-3,
            TimeUnit.MILLISECOND: 1,
            TimeUnit.MICROSECOND: 1e3,
            TimeUnit.NANOSECOND: 1e6,
        }
        return factors[self]

    @classmethod
    def get_default(cls) -> 'TimeUnit':
        return cls.MILLISECOND

    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'TimeUnit') -> Union[float, np.ndarray]:
        return self._convert_to_by_multiplication(value, target_unit)

class EnergyUnit(UNITEnum):
    """
    Enumeration of available energy units.
    """
    MEGAEV = 'MeV'
    KILOEV = 'keV'
    EV = 'eV'
    MILLIEV = 'meV'
    NANOEV = 'neV'

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert energy to this unit.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            EnergyUnit.MEGAEV: 1,
            EnergyUnit.KILOEV: 1e3,
            EnergyUnit.EV: 1e6,
            EnergyUnit.MILLIEV: 1e9,
            EnergyUnit.NANOEV: 1e12,
        }
        return factors[self]

    @classmethod
    def get_default(cls) -> 'EnergyUnit':
        return cls.MEGAEV
    
    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'EnergyUnit') -> Union[float, np.ndarray]:
        return self._convert_to_by_multiplication(value, target_unit)

class LengthUnit(UNITEnum):
    """
    Enumeration of available length units.
    """
    METER = 'm'
    CENTIMETER = 'cm'
    MILLIMETER = 'mm'
    MICROMETER = 'μm'

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert length to this unit.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            LengthUnit.METER: 0.01,
            LengthUnit.CENTIMETER: 1,
            LengthUnit.MILLIMETER: 10,
            LengthUnit.MICROMETER: 10000,
        }
        return factors[self]

    @classmethod
    def get_default(cls) -> 'LengthUnit':
        return cls.CENTIMETER
    
    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'LengthUnit') -> Union[float, np.ndarray]:
        return self._convert_to_by_multiplication(value, target_unit)
    
class AngleUnit(UNITEnum):
    """
    Enumeration of available direction cosine representations.
    
    Direction cosines are unitless, but can be represented in different formats.
    """
    COSINE = ''  # Standard cosine value between -1 and 1
    DEGREES = 'deg'  # Converted to degrees (arccos)
    RADIANS = 'rad'  # Converted to radians (arccos)

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert direction cosine to this representation.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            AngleUnit.COSINE: 1, 
            AngleUnit.DEGREES: np.arccos(1),  # Convert to degrees
            AngleUnit.RADIANS: 1,  # Convert to radians (same as standard for arccos)
        }
        return factors[self]
    
    @classmethod
    def get_default(cls) -> 'AngleUnit':
        return cls.COSINE

    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'AngleUnit') -> Union[float, np.ndarray]:
        if self == target_unit:
            return value
        
        if self == AngleUnit.COSINE:
            if target_unit == AngleUnit.DEGREES:
                return np.arccos(value) * 180 / np.pi
            elif target_unit == AngleUnit.RADIANS:
                return np.arccos(value)
            
        elif self == AngleUnit.DEGREES:
            if target_unit == AngleUnit.COSINE:
                return np.cos(value * np.pi / 180)
            elif target_unit == AngleUnit.RADIANS:
                return value * np.pi / 180
            
        elif self == AngleUnit.RADIANS:
            if target_unit == AngleUnit.COSINE:
                return np.cos(value)
            elif target_unit == AngleUnit.DEGREES:
                return value * 180 / np.pi

class MomentumTransferUnit(UNITEnum):
    """
    Enumeration of available momentum transfer units.
    """
    ANGSTROM_INVERSE = 'Å⁻¹'
    NANOMETER_INVERSE = 'nm⁻¹'

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert momentum transfer to this unit.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            MomentumTransferUnit.ANGSTROM_INVERSE: 1,
            MomentumTransferUnit.NANOMETER_INVERSE: 10,
        }
        return factors[self]

    @classmethod
    def get_default(cls) -> 'MomentumTransferUnit':
        return cls.ANGSTROM_INVERSE
    
    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'MomentumTransferUnit') -> Union[float, np.ndarray]:
        return self._convert_to_by_multiplication(value, target_unit)

class WavelengthUnit(UNITEnum):
    """
    Enumeration of available wavelength units.
    """
    ANGSTROM = 'Å'
    NANOMETER = 'nm'
    MICROMETER = 'μm'

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert wavelength to this unit.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            WavelengthUnit.ANGSTROM: 1,
            WavelengthUnit.NANOMETER: 0.1,
            WavelengthUnit.MICROMETER: 0.0001,
        }
        return factors[self]

    @classmethod
    def get_default(cls) -> 'WavelengthUnit':
        return cls.ANGSTROM
    
    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'WavelengthUnit') -> Union[float, np.ndarray]:
        return self._convert_to_by_multiplication(value, target_unit)

class VelocityUnit(UNITEnum):
    """
    Enumeration of available velocity units.
    """
    METER_PER_SECOND = 'm/s'
    CENTIMETER_PER_SECOND = 'cm/s'
    MILLIMETER_PER_SECOND = 'mm/s'

    @property
    def conversion_factor(self) -> float:
        """
        Get the conversion factor to convert velocity to this unit.
        
        Returns:
            float: The conversion factor
        """
        factors = {
            VelocityUnit.METER_PER_SECOND: 0.001,
            VelocityUnit.CENTIMETER_PER_SECOND: 0.01,
            VelocityUnit.MILLIMETER_PER_SECOND: 1,
        }
        return factors[self]

    @classmethod
    def get_default(cls) -> 'VelocityUnit':
        return cls.MILLIMETER_PER_SECOND

    def convert_to(self, value: Union[float, np.ndarray], target_unit: 'VelocityUnit') -> Union[float, np.ndarray]:
        return self._convert_to_by_multiplication(value, target_unit)
        
class ParticleParameter(Enum):
    """
    Enumeration of available MCPL particle parameters and calculated parameters.
    """
    # Direct MCPL parameters
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
    EVENT_ID = 'userflags'
    POSITION_VECTOR = 'position'
    POLARIZATION_VECTOR = 'polarisation'
    DIRECTION_VECTOR = 'direction'
    
    # Calculated parameters
    MOMENTUM_TRANSFER_Q = 'momentum_transfer_q'
    ENERGY_TRANSFER_OMEGA = 'energy_transfer_omega'
    SCATTERING_ANGLE = 'scattering_angle'
    WAVELENGTH = 'wavelength'
    VELOCITY = 'velocity'
    
    @property
    def unit(self) -> Union[UNITEnum, str]:
        """
        Get the unit for this particle parameter.
        
        Returns:
            str: The unit string for this parameter
        """
        units = {
            # Direct MCPL parameters
            ParticleParameter.TIME: TimeUnit,  # Time of Flight in milliseconds
            ParticleParameter.KINETIC_ENERGY: EnergyUnit,
            ParticleParameter.X_POSITION: LengthUnit,
            ParticleParameter.Y_POSITION: LengthUnit,
            ParticleParameter.Z_POSITION: LengthUnit,
            ParticleParameter.X_DIRECTION: AngleUnit,  
            ParticleParameter.Y_DIRECTION: AngleUnit,  
            ParticleParameter.Z_DIRECTION: AngleUnit,  
            ParticleParameter.X_POLARIZATION: NotImplementedUnit,
            ParticleParameter.Y_POLARIZATION: NotImplementedUnit,
            ParticleParameter.Z_POLARIZATION: NotImplementedUnit,
            ParticleParameter.PDG_CODE: NotImplementedUnit,
            ParticleParameter.WEIGHT: NotImplementedUnit,
            ParticleParameter.EVENT_ID: NotImplementedUnit,
            ParticleParameter.POSITION_VECTOR: NotImplementedUnit, # 'cm'
            ParticleParameter.POLARIZATION_VECTOR: NotImplementedUnit,
            ParticleParameter.DIRECTION_VECTOR: NotImplementedUnit,
            
            # Calculated parameters
            ParticleParameter.MOMENTUM_TRANSFER_Q: MomentumTransferUnit,
            ParticleParameter.ENERGY_TRANSFER_OMEGA: EnergyUnit,
            ParticleParameter.SCATTERING_ANGLE: AngleUnit,
            ParticleParameter.WAVELENGTH: WavelengthUnit,
            ParticleParameter.VELOCITY: VelocityUnit,
        }
        
        return units.get(self, '')
    

    def get_label(self) -> str:
        """
        Get appropriate axis label for this particle parameter.
        """
        labels = {
            # Direct MCPL parameters
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
            ParticleParameter.DIRECTION_VECTOR: "Direction Vector",
            
            # Calculated parameters
            ParticleParameter.MOMENTUM_TRANSFER_Q: "Momentum Transfer Q (Å⁻¹)",
            ParticleParameter.ENERGY_TRANSFER_OMEGA: "Energy Transfer ω (eV)",
            ParticleParameter.SCATTERING_ANGLE: "Scattering Angle (rad)",
            ParticleParameter.WAVELENGTH: "Wavelength (Å)",
            ParticleParameter.VELOCITY: "Velocity (mm/s)",
        }
        
        return labels.get(self, self.value.replace('_', ' ').title())
    
    def is_calculated(self) -> bool:
        """
        Check if this parameter is a calculated parameter (not directly from MCPL).
        """
        calculated_params = {
            ParticleParameter.MOMENTUM_TRANSFER_Q,
            ParticleParameter.ENERGY_TRANSFER_OMEGA,
            ParticleParameter.SCATTERING_ANGLE,
            ParticleParameter.WAVELENGTH,
            ParticleParameter.VELOCITY
        }
        return self in calculated_params
    
    def get_required_incident_class(self) -> Type:
        """
        Get the required IncidentParameters subclass for this calculated parameter.
        
        Returns:
            Type: The required IncidentParameters subclass type
            
        Raises:
            ValueError: If this is not a calculated parameter
        """
        if not self.is_calculated():
            raise ValueError(f"Parameter {self} is not a calculated parameter")
        
        param_to_class = {
            ParticleParameter.MOMENTUM_TRANSFER_Q: MomentumTransferQParameters,
            ParticleParameter.ENERGY_TRANSFER_OMEGA: EnergyTransferOmegaParameters,
            ParticleParameter.SCATTERING_ANGLE: ScatteringAngleParameters,
            # WAVELENGTH and VELOCITY don't require incident parameters
            ParticleParameter.WAVELENGTH: None,
            ParticleParameter.VELOCITY: None
        }
        
        return param_to_class[self]


class IncidentParameters(ABC):
    """
    Base class for incident parameters required for calculated parameters.
    
    This class encapsulates the incident neutron properties needed to calculate
    derived parameters like Q, ω, etc.
    """
    
    def __init__(self, 
                incident_energy_eV: float = None,
                incident_wavelength_A: float = None,
                incident_direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
                sample_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        """
        Initialize incident parameters.
        
        Args:
            incident_energy_eV: Incident neutron energy in eV
            incident_wavelength_A: Incident neutron wavelength in Å
            incident_direction: Incident direction vector (ux, uy, uz) - should be normalized by caller
            sample_position: Sample position in cm (x, y, z)
            
        Raises:
            ValueError: If both energy and wavelength are provided, or neither is provided
        """
        # Validate that exactly one of energy or wavelength is provided
        if incident_energy_eV is not None and incident_wavelength_A is not None:
            raise ValueError("Cannot specify both incident_energy_eV and incident_wavelength_A. Choose one.")
        
        if incident_energy_eV is None and incident_wavelength_A is None:
            raise ValueError("Must specify either incident_energy_eV or incident_wavelength_A.")
        
        # Calculate energy from wavelength if wavelength is provided
        if incident_wavelength_A is not None:
            self.incident_energy_eV = wl2ekin(incident_wavelength_A)
            self.incident_wavelength_A = float(incident_wavelength_A)
        else:
            self.incident_energy_eV = float(incident_energy_eV)
            self.incident_wavelength_A = ekin2wl(self.incident_energy_eV)
        
        # Direction normalization is responsibility of the caller
        self.incident_direction = tuple(float(x) for x in incident_direction)
        self.sample_position = tuple(float(x) for x in sample_position)
# Validate inputs
        if self.incident_energy_eV <= 0:
            raise ValueError("Incident energy must be positive")
        
        if len(self.incident_direction) != 3:
            raise ValueError("Incident direction must be a 3-element tuple")
        
        if len(self.sample_position) != 3:
            raise ValueError("Sample position must be a 3-element tuple")
    
    @abstractmethod
    def calc(self, particle_data: dict) -> np.ndarray:
        """
        Calculate the parameter values from particle data.
        
        Args:
            particle_data: Dictionary containing particle properties
                - 'position': (x, y, z) positions in cm
                - 'direction': (ux, uy, uz) direction cosines
                - 'ekin': kinetic energy in MeV
                - 'weight': particle weights
                
        Returns:
            np.ndarray: Calculated parameter values
        """
        pass
    
    @classmethod
    def from_string(cls, params_str: str) -> 'IncidentParameters':
        """
        Create IncidentParameters instance from string.
        
        Args:
            params_str: String in format "inc_ekin=123.45;inc_wl=1.234;inc_dir=(0.1,0.2,0.3);inc_sample=(0.0,0.0,0.0)"
        
        Returns:
            IncidentParameters: Instance with parsed parameters
        """
        # Parse the string
        params = {}
        for param in params_str.split(';'):
            key, value = param.split('=')
            key = key.strip()
            value = value.strip()
            
            if key == 'incident_energy_eV' or key == 'incident_wavelength_A':
                params[key] = float(value)
            elif key == 'incident_direction' or key == 'sample_position':
                params[key] = tuple(float(x.strip()) for x in value.strip('()').split(','))
        
        return cls(**params)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(energy={self.incident_energy_eV:.3f}eV, wavelength={self.incident_wavelength_A:.3f}Å)"


class MomentumTransferQParameters(IncidentParameters):
    """
    Parameters for calculating momentum transfer Q.
    
    Required for: MOMENTUM_TRANSFER_Q
    """
    
    def __init__(self, 
                 incident_energy_eV: float = None,
                 incident_wavelength_A: float = None,
                 incident_direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
                 sample_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        """
        Initialize Q parameters.
        
        Args:
            incident_energy_eV: Incident neutron energy in eV
            incident_wavelength_A: Incident neutron wavelength in Å
            incident_direction: Incident direction vector
            sample_position: Sample position in cm
        """
        super().__init__(incident_energy_eV, incident_wavelength_A, incident_direction, sample_position)
    
    def calc(self, particle_data: dict) -> np.ndarray:
        """
        Calculate momentum transfer Q values.
        
        Q = neutronAngleCosine2Q(angle_cos, enin_eV, enout_eV)
        where angle_cos is the cosine of scattering angle.
        """
        positions = particle_data['position']  # (N, 3) array
        directions = particle_data['direction']  # (N, 3) array
        ekin_out_MeV = particle_data['ekin']  # (N,) array
        
        # Convert outgoing energy from MeV to eV using safe conversion function
        ekin_out_eV = MeV2eV(ekin_out_MeV)
        
        # Calculate scattering angle cosine
        # For simplicity, assume scattering from incident direction
        incident_dir = np.array(self.incident_direction)
        angle_cos = np.dot(directions, incident_dir)
        
        # Calculate Q using the conversion function
        Q_values = angleCosine2Q(angle_cos, self.incident_energy_eV, ekin_out_eV)
        
        return Q_values


class EnergyTransferOmegaParameters(IncidentParameters):
    """
    Parameters for calculating energy transfer ω.
    
    Required for: ENERGY_TRANSFER_OMEGA
    """
    
    def __init__(self, 
                 incident_energy_eV: float = None,
                 incident_wavelength_A: float = None):
        """
        Initialize energy transfer parameters.
        
        Args:
            incident_energy_eV: Incident neutron energy in eV
            incident_wavelength_A: Incident neutron wavelength in Å
        """
        # Call parent constructor with default values for direction and position
        super().__init__(incident_energy_eV, incident_wavelength_A, 
                         incident_direction=(0.0, 0.0, 1.0), 
                         sample_position=(0.0, 0.0, 0.0))
    
    def calc(self, particle_data: dict) -> np.ndarray:
        """
        Calculate energy transfer ω values.
        
        ω = enin_eV - enout_eV
        """
        ekin_out_MeV = particle_data['ekin']  # (N,) array
        
        # Convert outgoing energy from MeV to eV using safe conversion function
        ekin_out_eV = MeV2eV(ekin_out_MeV)
        
        # Calculate energy transfer
        omega_values = self.incident_energy_eV - ekin_out_eV
        
        return omega_values


class ScatteringAngleParameters(IncidentParameters):
    """
    Parameters for calculating scattering angle.
    
    Required for: SCATTERING_ANGLE
    """
    
    def calc(self, particle_data: dict) -> np.ndarray:
        """
        Calculate scattering angle values.
        
        angle = arccos(dot(incident_dir, scattered_dir))
        """
        directions = particle_data['direction']  # (N, 3) array
        
        # Calculate scattering angle cosine
        incident_dir = np.array(self.incident_direction)
        angle_cos = np.sum(directions * incident_dir, axis=1)
        
        # Calculate angle in cosine
        angle_values = np.clip(angle_cos, -1.0, 1.0)
        
        return angle_values


class MCPL_Analyzer_1D(Hist1D):
    """
    Enhanced 1D MCPL analyzer with support for calculated parameters.
    """
    
    def __init__(self, para: Union[ParticleParameter, str] = ParticleParameter.TIME, 
                 unit: Optional[str] = None,
                 incident_params: Optional[Union[IncidentParameters, str]] = None,
                 binmin=0.0, binmax=10.0, binnum=100, linear=True, 
                 auto_range_file: str = ''):
        """
        Initialize the 1D analyzer.
        Args:
            para: Particle parameter to analyze
            unit: Unit for the parameter
            incident_params: Incident parameters for calculated parameters
            binmin: Minimum bin value
            binmax: Maximum bin value  
            binnum: Number of bins
            linear: Whether bins are linear (True) or logarithmic (False)
            auto_range_file: File to use for automatic range detection
            
        Raises:
            ValueError: If parameter and incident parameters don't match
        """
        # Convert parameter to enum if it's a string
        if isinstance(para, str):
            self.para = ParticleParameter(para)
        elif isinstance(para, ParticleParameter):
            self.para = para
        else:
            raise ValueError(f"Invalid parameter type: {type(para)}")
        
        self.default_unit = self.para.unit.get_default()
        # Validate parameter and incident parameters compatibility
        if isinstance(incident_params, str):
            incident_params = self.para.get_required_incident_class().from_string(incident_params)
            
        self._validate_parameter_compatibility(incident_params)
        self.incident_params = incident_params
        
        # demanded unit
        if unit is None:
            self.demanded_unit = self.default_unit
        else:
            self.demanded_unit = self.para.unit.from_str(unit)

        # Auto-range detection if specified
        if auto_range_file:
            # In MCPL default unit
            min_val, max_val = self.get_range(auto_range_file)
            super().__init__(min_val*0.9, max_val*1.1, binnum, linear=linear)
        else:

            super().__init__(binmin, binmax, binnum, linear=linear)

    @property
    def unit_converter(self) -> Callable[[Union[float, np.ndarray]], Union[float, np.ndarray]]:
        return self._get_unit_converter()

    def _get_unit_converter(self) -> Callable[[Union[float, np.ndarray]], Union[float, np.ndarray]]:
        def convert(values: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
            return self.default_unit.convert_to(values, self.demanded_unit)
        return convert
    
    def _get_unit_recoverer(self) -> Callable[[Union[float, np.ndarray]], Union[float, np.ndarray]]:
        def recover(values: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
            return self.demanded_unit.convert_to(values, self.default_unit)
        return recover

    def _validate_parameter_compatibility(self, incident_params: IncidentParameters) -> None:
        """
        Validate that the parameter and incident parameters are compatible.
        
        Args:
            incident_params: Incident parameters to validate
            
        Raises:
            ValueError: If parameter and incident parameters don't match
"""
        if self.para.is_calculated():
            # Special case: WAVELENGTH and VELOCITY don't require incident parameters
            # as they only depend on outgoing energy
            if self.para in {ParticleParameter.WAVELENGTH, ParticleParameter.VELOCITY}:
                # These parameters can work without incident parameters
                # If incident_params is provided, we'll ignore it for these parameters
                pass
            else:
                # For other calculated parameters, incident parameters are required
                if incident_params is None:
                    raise ValueError(f"Calculated parameter {self.para} requires incident parameters")
                
                required_class = self.para.get_required_incident_class()
                if not isinstance(incident_params, required_class):
                    raise ValueError(
                        f"Parameter {self.para} requires {required_class.__name__}, "
                        f"but got {type(incident_params).__name__}"
                    )
        else:
            if incident_params is not None:
                raise ValueError(
                    f"Direct parameter {self.para} does not require incident parameters"
                )
    
    def get_range(self, filename) -> Tuple[float, float]:
        """
        Get the range of parameter values in the MCPL file.
        """
        if self.para.is_calculated():
            return self._get_calculated_range(filename)
        else:
            return self._get_direct_range(filename)
    
    def _get_direct_range(self, filename) -> Tuple[float, float]:
        """Get range for direct MCPL parameters."""
        file = MCPLFile(filename)
        
        min_val = float('inf')
        max_val = float('-inf')
        has_data = False
        
        for pb in file.particle_blocks:
            param_values = getattr(pb, self.para.value)
            # Convert parameter values to demanded unit
            param_values = self.unit_converter(param_values)
            
            if len(param_values) > 0:
                has_data = True
                min_val = min(min_val, np.min(param_values))
                max_val = max(max_val, np.max(param_values))
        
        if not has_data:
            raise ValueError(f"No particle data found in file: {filename}")
        
        return min_val, max_val
    
    def _get_calculated_range(self, filename) -> Tuple[float, float]:
        """Get range for calculated parameters."""
        # Calculate values for all particles to determine range
        values = self._calculate_parameter_values(filename)
        # Convert values to demanded unit
        values = self.unit_converter(values)
        
        if len(values) == 0:
            raise ValueError(f"No particle data found in file: {filename}")
        
        return np.min(values), np.max(values)
    
    def _calculate_parameter_values(self, filename) -> np.ndarray:
        """
        Calculate parameter values for all particles in the file.
        """
        file = MCPLFile(filename)
        
        all_values = []
        for pb in file.particle_blocks:
            if len(pb.ekin) == 0:
                continue
            
            # Prepare particle data for calculation - use existing attributes
            particle_data = {
                'position': np.array(pb.position),  
                'direction': np.array(pb.direction), 
                'ekin': np.array(pb.ekin),
                'weight': np.array(pb.weight)
            }
            
            # Calculate parameter values based on parameter type
            if self.para == ParticleParameter.WAVELENGTH:
                # Wavelength calculation: convert energy to wavelength
                ekin_out_eV = MeV2eV(particle_data['ekin'])
                values = ekin2wl(ekin_out_eV)
            elif self.para == ParticleParameter.VELOCITY:
                # Velocity calculation: convert energy to velocity
                ekin_out_eV = MeV2eV(particle_data['ekin'])
                values = ekin2v(ekin_out_eV)
            else:
                # For other calculated parameters, use incident parameters
                if self.incident_params is None:
                    raise ValueError(f"Incident parameters required for {self.para}")
                values = self.incident_params.calc(particle_data)
            
            all_values.extend(values)
        
        return np.array(all_values)
    
    def analyze(self, filename):
        """
        Analyze the MCPL file and fill the histogram.
        """
        if self.para.is_calculated():
            self._analyze_calculated(filename)
        else:
            self._analyze_direct(filename)
    
    def _analyze_direct(self, filename):
        """Analyze direct MCPL parameters."""
        file = MCPLFile(filename)
        
        for pb in file.particle_blocks:
            param_values = getattr(pb, self.para.value)
            param_values = self.unit_converter(param_values)
            if len(param_values) > 0:
                self.fillmany(
                    np.asarray(param_values, dtype=np.float64), 
                    np.asarray(pb.weight, dtype=np.float64)
                )
    
    def _analyze_calculated(self, filename):
        """Analyze calculated parameters."""
        file = MCPLFile(filename)
        
        for pb in file.particle_blocks:
            if len(pb.ekin) == 0:
                continue
            
            # Prepare particle data for calculation - use existing attributes
            particle_data = {
                'position': np.array(pb.position),  
                'direction': np.array(pb.direction),  
                'ekin': np.array(pb.ekin),
                'weight': np.array(pb.weight)
            }
            
            # Calculate parameter values based on parameter type
            if self.para == ParticleParameter.WAVELENGTH:
                # Wavelength calculation: convert energy to wavelength
                ekin_out_eV = MeV2eV(particle_data['ekin'])
                values = ekin2wl(ekin_out_eV)
            elif self.para == ParticleParameter.VELOCITY:
                # Velocity calculation: convert energy to velocity
                ekin_out_eV = MeV2eV(particle_data['ekin'])
                values = ekin2v(ekin_out_eV)
            else:
                # For other calculated parameters, use incident parameters
                if self.incident_params is None:
                    raise ValueError(f"Incident parameters required for {self.para}")
                values = self.incident_params.calc(particle_data)
            values = self.unit_converter(values)
            # Fill histogram with calculated values
            if len(values) > 0:
                self.fillmany(
                    np.asarray(values, dtype=np.float64), 
                    np.asarray(particle_data['weight'], dtype=np.float64)
                )


class MCPL_Analyzer_2D(Hist2D):
    """
    Enhanced 2D MCPL analyzer with support for calculated parameters.
    """
    
    def __init__(self, 
                 x_para: Union[ParticleParameter, str] = ParticleParameter.TIME,
                 y_para: Union[ParticleParameter, str] = ParticleParameter.KINETIC_ENERGY,
                 x_incident_params: IncidentParameters = None,
                 y_incident_params: IncidentParameters = None,
                 x_binmin=0.0, x_binmax=10.0, x_binnum=100,
                 y_binmin=0.0, y_binmax=10.0, y_binnum=100,
                 auto_range_file: str = ''):
        """
        Initialize the 2D analyzer.
        
        Args:
            x_para: X-axis particle parameter to analyze
            y_para: Y-axis particle parameter to analyze
            x_incident_params: Incident parameters for x-axis calculated parameters
            y_incident_params: Incident parameters for y-axis calculated parameters
            x_binmin: Minimum x bin value
            x_binmax: Maximum x bin value  
            x_binnum: Number of x bins
            y_binmin: Minimum y bin value
            y_binmax: Maximum y bin value  
            y_binnum: Number of y bins
            auto_range_file: File to use for automatic range detection
            
        Raises:
            ValueError: If parameters and incident parameters don't match
        """
        # Convert parameters to enum if they're strings
        if isinstance(x_para, str):
            self.x_para = ParticleParameter(x_para)
        elif isinstance(x_para, ParticleParameter):
            self.x_para = x_para
        else:
            raise ValueError(f"Invalid x parameter type: {type(x_para)}")
            
        if isinstance(y_para, str):
            self.y_para = ParticleParameter(y_para)
        elif isinstance(y_para, ParticleParameter):
            self.y_para = y_para
        else:
            raise ValueError(f"Invalid y parameter type: {type(y_para)}")
        
        # Validate parameters and incident parameters compatibility
        self._validate_parameter_compatibility(self.x_para, x_incident_params, "x")
        self._validate_parameter_compatibility(self.y_para, y_incident_params, "y")
        
        self.x_incident_params = x_incident_params
        self.y_incident_params = y_incident_params
        
        # Auto-range detection if specified
        if auto_range_file:
            x_min, x_max = self.get_x_range(auto_range_file)
            y_min, y_max = self.get_y_range(auto_range_file)
            
            # Apply small margins to the ranges
            x_min = x_min * 0.9 if x_min > 0 else x_min * 1.1
            x_max = x_max * 1.1 if x_max > 0 else x_max * 0.9
            y_min = y_min * 0.9 if y_min > 0 else y_min * 1.1
            y_max = y_max * 1.1 if y_max > 0 else y_max * 0.9
            
            # Call Hist2D constructor with correct parameters (no linear arguments)
            super().__init__(x_min, x_max, x_binnum, y_min, y_max, y_binnum)
        else:
            # Call Hist2D constructor with correct parameters (no linear arguments)
            super().__init__(x_binmin, x_binmax, x_binnum, y_binmin, y_binmax, y_binnum)
    
    def _validate_parameter_compatibility(self, para: ParticleParameter, 
                                         incident_params: IncidentParameters, 
                                         axis: str) -> None:
        """
        Validate that the parameter and incident parameters are compatible.
        
        Args:
            para: Particle parameter to validate
            incident_params: Incident parameters to validate
            axis: Axis identifier ('x' or 'y')
            
        Raises:
            ValueError: If parameter and incident parameters don't match
        """
        if para.is_calculated():
            # Special case: WAVELENGTH and VELOCITY don't require incident parameters
            # as they only depend on outgoing energy
            if para in {ParticleParameter.WAVELENGTH, ParticleParameter.VELOCITY}:
                # These parameters can work without incident parameters
                # If incident_params is provided, we'll ignore it for these parameters
                pass
            else:
                # For other calculated parameters, incident parameters are required
                if incident_params is None:
                    raise ValueError(f"Calculated {axis}-axis parameter {para} requires incident parameters")
                
                required_class = para.get_required_incident_class()
                if not isinstance(incident_params, required_class):
                    raise ValueError(
                        f"{axis}-axis parameter {para} requires {required_class.__name__}, "
                        f"but got {type(incident_params).__name__}"
                    )
        else:
            if incident_params is not None:
                raise ValueError(
                    f"Direct {axis}-axis parameter {para} does not require incident parameters"
                )
    
    def get_x_range(self, filename) -> Tuple[float, float]:
        """
        Get the range of x-axis parameter values in the MCPL file.
        """
        if self.x_para.is_calculated():
            return self._get_calculated_range(filename, self.x_para, self.x_incident_params)
        else:
            return self._get_direct_range(filename, self.x_para)
    
    def get_y_range(self, filename) -> Tuple[float, float]:
        """
        Get the range of y-axis parameter values in the MCPL file.
        """
        if self.y_para.is_calculated():
            return self._get_calculated_range(filename, self.y_para, self.y_incident_params)
        else:
            return self._get_direct_range(filename, self.y_para)
    
    def _get_direct_range(self, filename, para: ParticleParameter) -> Tuple[float, float]:
        """Get range for direct MCPL parameters."""
        file = MCPLFile(filename)
        
        min_val = float('inf')
        max_val = float('-inf')
        has_data = False
        
        for pb in file.particle_blocks:
            param_values = getattr(pb, para.value)
            
            if len(param_values) > 0:
                has_data = True
                min_val = min(min_val, np.min(param_values))
                max_val = max(max_val, np.max(param_values))
        
        if not has_data:
            raise ValueError(f"No particle data found in file: {filename}")
        
        return min_val, max_val
    
    def _get_calculated_range(self, filename, para: ParticleParameter, 
                            incident_params: IncidentParameters) -> Tuple[float, float]:
        """Get range for calculated parameters."""
        # Calculate values for all particles to determine range
        values = self._calculate_parameter_values(filename, para, incident_params)
        
        if len(values) == 0:
            raise ValueError(f"No particle data found in file: {filename}")
        
        return np.min(values), np.max(values)
    
    def _calculate_parameter_values(self, filename, para: ParticleParameter, 
                                 incident_params: IncidentParameters) -> np.ndarray:
        """
        Calculate parameter values for all particles in the file.
        """
        file = MCPLFile(filename)
        
        all_values = []
        for pb in file.particle_blocks:
            if len(pb.ekin) == 0:
                continue
            
            # Prepare particle data for calculation - use existing attributes
            particle_data = {
                'position': np.array(pb.position),  
                'direction': np.array(pb.direction), 
                'ekin': np.array(pb.ekin),
                'weight': np.array(pb.weight)
            }
            
            # Calculate parameter values based on parameter type
            if para == ParticleParameter.WAVELENGTH:
                # Wavelength calculation: convert energy to wavelength
                ekin_out_eV = MeV2eV(particle_data['ekin'])
                values = ekin2wl(ekin_out_eV)
            elif para == ParticleParameter.VELOCITY:
                # Velocity calculation: convert energy to velocity
                ekin_out_eV = MeV2eV(particle_data['ekin'])
                values = ekin2v(ekin_out_eV)
            else:
                # For other calculated parameters, use incident parameters
                if incident_params is None:
                    raise ValueError(f"Incident parameters required for {para}")
                values = incident_params.calc(particle_data)
            
            all_values.extend(values)
        
        return np.array(all_values)
    
    def analyze(self, filename):
        """
        Analyze the MCPL file and fill the 2D histogram.
        """
        file = MCPLFile(filename)
        
        for pb in file.particle_blocks:
            if len(pb.ekin) == 0:
                continue
            
            # Get x values
            if self.x_para.is_calculated():
                x_values = self._get_values_for_block(pb, self.x_para, self.x_incident_params)
            else:
                x_values = getattr(pb, self.x_para.value)
            
            # Get y values
            if self.y_para.is_calculated():
                y_values = self._get_values_for_block(pb, self.y_para, self.y_incident_params)
            else:
                y_values = getattr(pb, self.y_para.value)
            
            # Fill histogram with valid pairs
            if len(x_values) > 0 and len(y_values) > 0 and len(x_values) == len(y_values):
                self.fillmany(
                    np.asarray(x_values, dtype=np.float64),
                    np.asarray(y_values, dtype=np.float64),
                    np.asarray(pb.weight, dtype=np.float64)
                )
    
    def _get_values_for_block(self, pb, para: ParticleParameter, 
                            incident_params: IncidentParameters) -> np.ndarray:
        """
        Get parameter values for a particle block.
        """
        if len(pb.ekin) == 0:
            return np.array([])
        
        # Prepare particle data for calculation - use existing attributes
        particle_data = {
            'position': np.array(pb.position),  
            'direction': np.array(pb.direction), 
            'ekin': np.array(pb.ekin),
            'weight': np.array(pb.weight)
        }
        
        # Calculate parameter values based on parameter type
        if para == ParticleParameter.WAVELENGTH:
            # Wavelength calculation: convert energy to wavelength
            ekin_out_eV = MeV2eV(particle_data['ekin'])
            values = ekin2wl(ekin_out_eV)
        elif para == ParticleParameter.VELOCITY:
            # Velocity calculation: convert energy to velocity
            ekin_out_eV = MeV2eV(particle_data['ekin'])
            values = ekin2v(ekin_out_eV)
        else:
            # For other calculated parameters, use incident parameters
            if incident_params is None:
                raise ValueError(f"Incident parameters required for {para}")
            values = incident_params.calc(particle_data)
        
        return values
    
    def plot(self, show=False, title=None, log=True, logx=False, dynrange=1e-3, ax=None):
        """
        Plot the 2D histogram with enhanced labeling.
        """
        # Create default title if not provided
        if title is None:
            title = f"{self.x_para.get_label()} vs {self.y_para.get_label()}"
        
        # Call parent plot method with enhanced title
        return super().plot(show=show, title=title, log=log, logx=logx, 
                          dynrange=dynrange, ax=ax)