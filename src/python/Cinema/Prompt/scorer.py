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
"""
A Scorer defines how the neutron interactions are counted/scored.

This module provides classes and utilities for particle scoring and detection in the
Cinema particle tracing framework. It includes:
1. ParticleTracingState: denotes the particle tracing states, defines
   the interaction type of a particle-Volume system, acts as the trigger
   for the Scorer to count.
2. Scorer Helper classes: Utility classes for creating and managing scorers

"""

from .configstr import ConfigString
from .launcher import Launcher

import os
import warnings
from enum import Enum, auto

class ParticleTracingState(Enum):
    """
    Enumeration of particle tracing states.
    Particle tracing states define the interaction type of a particle-Volume system.
        
    Attributes:
        SURFACE (0): particle state when an interaction happens at the suface of a Volume,
                      e.g. surface transmission, or optics physics (mirror, chopper).
        ENTRY (1): particle state when it enters a Volume
        PROPAGATE_PRE (2): particle state before propagation (scattering with bulk material) in a Volume
        PROPAGATE_POST (3): particle state after propagation (scattering with bulk material) in a Volume
                            energy and momentum are updated after scattering.
        EXIT (4): Particle state at exiting a Volume
        PEA_PRE (5): particle state of propagate_pre, exit or absorb, both of these 3 trigger the counting action
        PEA_POST (6): particle state of propagate_post, exit or absorb, both of these 3 trigger the counting action
        ABSORB (7): particle state at absorption
    
    Methods:
        value_num: Returns numerical representation of the particle tracing state
        from_string: Creates enum instance from string
        to_string: Converts enum instance to string representation
    """
    SURFACE = auto()
    ENTRY = auto()
    PROPAGATE_PRE = auto()
    PROPAGATE_POST = auto()
    EXIT = auto()
    PEA_PRE = auto()
    PEA_POST = auto()
    ABSORB = auto()
    
    @property
    def value_num(self):
        """Return the corresponding numerical representation"""
        mapping = {
            ParticleTracingState.SURFACE: 0,
            ParticleTracingState.ENTRY: 1,
            ParticleTracingState.PROPAGATE_PRE: 2,
            ParticleTracingState.PROPAGATE_POST: 3,
            ParticleTracingState.EXIT: 4,
            ParticleTracingState.PEA_PRE: 5,
            ParticleTracingState.PEA_POST: 6,
            ParticleTracingState.ABSORB: 7
        }
        return mapping[self]
    
    @classmethod
    def from_string(cls, state_str):
        """Create enum instance from string

        Raises:
            ValueError: if state_str does not name a valid tracing state
        """
        try:
            return cls[state_str.upper()]
        except KeyError:
            valid = ', '.join(member.name for member in cls)
            raise ValueError(f"Unknown particle tracing state '{state_str}'. "
                             f"Valid states: {valid}") from None

    def to_string(self):
        """Convert enum instance to string representation"""
        mapping = {
            ParticleTracingState.SURFACE: 'SURFACE',
            ParticleTracingState.ENTRY: 'ENTRY',
            ParticleTracingState.PROPAGATE_PRE: 'PROPAGATE_PRE',
            ParticleTracingState.PROPAGATE_POST: 'PROPAGATE_POST',
            ParticleTracingState.EXIT: 'EXIT',
            ParticleTracingState.PEA_PRE: 'PEA_PRE',
            ParticleTracingState.PEA_POST: 'PEA_POST',
            ParticleTracingState.ABSORB: 'ABSORB'
        }
        return mapping[self]




# DepositionHelper is a special class that skipped the traditional string based initialisation.
# A C++ object is directly created in  
from ..Interface import *
_pt_ScorerDeposition_new = importFunc('pt_ScorerDeposition_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_bool, type_int])
_pt_ScorerESpectrum_new = importFunc('pt_ScorerESpectrum_new', type_voidp, [type_cstr, type_bool, type_dbl, type_dbl, type_uint, type_uint, type_int, type_int, type_bool ])
_pt_ScorerTOF_new = importFunc('pt_ScorerTOF_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_int ])
_pt_ScorerWlSpectrum_new = importFunc('pt_ScorerWlSpectrum_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_int, type_bool ])
_pt_ScorerVolFluence_new = importFunc('pt_ScorerVolFluence_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_bool, type_int])
_pt_ScorerDeltaMomentum_new = importFunc('pt_ScorerDeltaMomentum_new',type_voidp, [type_cstr, type_dbl, type_dbl, type_dbl, type_uint,
                                                                                   type_uint, type_dbl, type_dbl, type_dbl, 
                                                                                   type_dbl, type_dbl, type_dbl, type_int, type_int, type_bool])
_pt_ScorerMultiScat_new = importFunc('pt_ScorerMultiScat_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int])
_pt_ScorerDirectSqw_new = importFunc('pt_ScorerDirectSqw_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, 
                                                                            type_dbl, type_dbl, type_uint,
                                                                            type_uint, type_int, type_dbl, type_dbl,
                                                                            type_dbl, type_dbl, type_dbl, 
                                                                            type_dbl, type_dbl, type_dbl, 
                                                                            type_int, type_bool])
_pt_ScorerPSD_new = importFunc('pt_ScorerPSD_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint,
                                                                type_dbl, type_dbl, type_uint,
                                                                type_uint, type_int, type_int, type_int, type_bool])
_pt_addMultiScatter1D = importFunc('pt_addMultiScatter1D', None, [type_voidp, type_voidp, type_int])
_pt_addMultiScatter2D = importFunc('pt_addMultiScatter2D', None, [type_voidp, type_voidp, type_int])

_pt_KillerMCPL_new = importFunc('pt_KillerMCPL_new', type_voidp, [type_cstr, type_uint, type_int, type_bool, type_bool])

# Validate the scoring range in Python, before any ctypes call: a range mistake
# would otherwise only surface as an uncatchable C++ abort (SIGABRT) at make() time.
def _checkScorerRange(name, minVal, maxVal, logBinning=False, axis=''):
    lbl = f'{axis}-axis ' if axis else ''
    if not minVal < maxVal:
        raise ValueError(f"Scorer {name}: {lbl}range min ({minVal}) must be smaller than max ({maxVal}).")
    if logBinning and minVal <= 0:
        raise ValueError(f"Scorer {name}: {lbl}min ({minVal}) must be positive for logarithmic binning.")

# Resolve the binning-shape keyword: `log` is canonical, the polarity-inverted
# `linear` keyword is still accepted but deprecated.
def _resolveLogBinning(scorerName, log, linear, defaultLinear):
    if linear is not None:
        warnings.warn(f"{scorerName}: the 'linear' keyword is deprecated, use 'log' "
                      "(log=True is equivalent to linear=False)", DeprecationWarning, stacklevel=3)
        if log is None:
            log = not linear
    if log is None:
        log = not defaultLinear
    return log

class ScorerHelper:
    """
    ScorerHelper Class Documentation
    
    Base class for particle tracing scorers in the Cinema framework. Provides common configuration
    and validation logic for various types of particle detectors and scoring mechanisms.
    
    Constructor Parameters:
        name (str): Unique identifier for the scorer instance
        min (float): Minimum value of the scoring range
        max (float): Maximum value of the scoring range
        numbin (int): Number of bins to divide the scoring range into
        pdg (int, optional): Particle Data Group code, defaults to 2112 (neutron)
        ptstate (str or ParticleTracingState, optional): Particle tracing state, defaults to None
        groupID (int, optional): Group identifier for organizing multiple scorers, defaults to 0
    
    Important Behavior Notes:
    
    ptstate Parameter Validation:
        - Default Value: ptstate=None - This means derived classes MUST explicitly provide a valid value
        - Type Checking: The constructor performs strict type validation:
            * If ptstate is a ParticleTracingState enum, it calls to_string() to convert to string
            * If ptstate is a string, it uses it directly
            * If ptstate is any other type (including None), it raises a TypeError
        - Derived Class Requirement: Since the default is None, all derived classes must:
            * Pass a valid ptstate value in their super().__init__() call
            * Ensure the value is either a string or ParticleTracingState enum
    
    ParticleTracingState Enum Values:
        SURFACE (0): Surface interaction
        ENTRY (1): Volume entry
        PROPAGATE_PRE (2): Pre-propagation
        PROPAGATE_POST (3): Post-propagation
        EXIT (4): Volume exit
        PEA_PRE (5): Pre-point of equal arrival
        PEA_POST (6): Post-point of equal arrival
        ABSORB (7): Absorption
    
    Instance Attributes:
        name: Scorer identifier
        min: Minimum scoring range
        max: Maximum scoring range
        numbin: Number of bins
        pdg: Particle type code
        ptstate: Particle tracing state (always stored as string)
        groupID: Group identifier
        linear: Flag indicating linear binning (vs logarithmic), defaults to True
    
    Example Usage:
        # Valid usage in derived classes
        class MyScorer(ScorerHelper):
            def __init__(self, name, min, max, numbin):
                # Must provide ptstate explicitly - using enum
                super().__init__(name, min, max, numbin, ptstate=ParticleTracingState.ENTRY)
        
        # Or using string directly
        class MyScorer2(ScorerHelper):
            def __init__(self, name, min, max, numbin):
                super().__init__(name, min, max, numbin, ptstate="ENTRY")
        
        # Invalid usage (will raise TypeError)
        class BadScorer(ScorerHelper):
            def __init__(self, name, min, max, numbin):
                # Missing ptstate - will fail validation
                super().__init__(name, min, max, numbin)  # TypeError!
    
    Error Handling:
        The constructor will raise a TypeError with a descriptive message if:
            - ptstate is None (not provided)
            - ptstate is not a string or ParticleTracingState enum
            - The type cannot be converted to a valid string representation
    
    This design ensures type safety and forces derived classes to be explicit about the particle
    tracing state they intend to use.
    """

    def __init__(self, name, min, max, numbin, pdg = 2112, ptstate=None, groupID=0) -> None:
        self.name = name
        self.min = min
        self.max = max
        self.numbin = numbin
        self.pdg = pdg
        if isinstance(ptstate, ParticleTracingState):
            self.ptstate = ptstate.to_string()
        elif isinstance(ptstate, str):
            self.ptstate = ptstate
        else:
            raise TypeError(f"ptstate must be a string or ParticleTracingState enum, got {type(ptstate)}")
        self.groupID = groupID
        self.linear = True
        # canonical binning flag; `linear` above is kept as the inverted legacy mirror
        self.log = False
        # fail fast on an inverted range instead of an uncatchable C++ abort at make()
        _checkScorerRange(name, min, max)

    def __realinit(self):
        self.score.cfg_name = self.name
        self.score.cfg_min = self.min
        self.score.cfg_max = self.max
        self.score.cfg_numbin = self.numbin
        self.score.cfg_ptstate = self.ptstate

    def getHistogram(self):
        launcher = Launcher()
        return launcher.getHist(self.name)
    
    @property
    def ptsNum(self):
        """Numerical value of the particle tracing state.
        """
        # delegated to the ParticleTracingState table to keep a single mapping
        try:
            return ParticleTracingState[self.ptstate].value_num
        except KeyError:
            raise RuntimeError(f'Scorer type {self.ptstate} is undefined.')
        
    def make(self, vol):
        vol.addScorer(self.score.cfg)

class ScorerHelper2D(ScorerHelper):
    def __init__(self, name, xmin, xmax, xnumbin, ymin, ymax, ynumbin, pdg = 2112, ptstate = 'ENTRY', groupID=0) -> None:
        super().__init__(name, xmin, xmax, xnumbin, pdg, ptstate, groupID)
        self.ymin = ymin
        self.ymax = ymax
        self.ynumbin = ynumbin
        _checkScorerRange(name, ymin, ymax, axis='y')

class MultiScatMixin1D():
    def __init__(self) -> None:
        pass

    def addScatterCounter(self, scatterCounter, scatterNumberRequired=-2):
        """
        Associate a multi-scattering counter with this scorer to filter particles based on scattering count.
        
        This method enables particle filtering by requiring that particles have undergone a specific
        number of scattering events before being counted by this scorer. The scattering counter
        tracks the number of scatterings each particle experiences within a specified volume.
        
        Parameters:
        -----------
        scatterCounter : MultiScatCounter
            An instance of MultiScatCounter that tracks scattering events for particles.
            This counter must be attached to the volume where scatterings are counted.
            
        scatterNumberRequired : int, optional
            The required number of scatterings for particles to be counted by this scorer.
            Special values:
                -2: Count all particles (default)
                -1: Count only particles that do not enter the region of interest
                0: Count only particles that have entered the region of interest but not scattered
                >0: Count only particles that have scattered exactly n times (n > 0)
            
        Notes:
        ------
        - The scatter counter must be properly initialized and attached to a volume before use
        - Multiple scorers can share the same scatter counter with different scattering requirements
        - This filtering mechanism is particularly useful for analyzing multiple scattering effects
          in neutron scattering experiments
        - The method delegates to the underlying C++ implementation via _pt_addMultiScatter1D
        
        Example:
        --------
        # Create a scatter counter for a sample volume
        scatter_counter = MultiScatCounter("SampleScatterCounter")
        sample_volume.addScorer(scatter_counter, scatter_counter.make(sample_volume))
        
        # Create a 1D scorer that only counts particles with exactly 1 scattering
        scorer_1d = ESpectrumHelper("EnergySpectrum", min=1e-5, max=1, numbin=100)
        scorer_1d.addScatterCounter(scatter_counter, scatterNumberRequired=1)
        
        See Also:
        ---------
        MultiScatCounter : Helper class for counting scattering events
        MultiScatMixin2D.addScatterCounter : 2D version of this method
        """
        _pt_addMultiScatter1D(scatterCounter.cobj, self.cobj, scatterNumberRequired)

class MultiScatMixin2D():
    def __init__(self) -> None:
        pass

    def addScatterCounter(self, scatterCounter, scatterNumberRequired=-2):
        """
        Associate a multi-scattering counter with this scorer to filter particles based on scattering count.
        
        This method enables particle filtering by requiring that particles have undergone a specific
        number of scattering events before being counted by this scorer. The scattering counter
        tracks the number of scatterings each particle experiences within a specified volume.
        
        Parameters:
        -----------
        scatterCounter : MultiScatCounter
            An instance of MultiScatCounter that tracks scattering events for particles.
            This counter must be attached to the volume where scatterings are counted.
            
        scatterNumberRequired : int, optional
            The required number of scatterings for particles to be counted by this scorer.
            Special values:
                -2: Count all particles (default)
                -1: Count only particles that do not enter the region of interest
                0: Count only particles that have entered the region of interest but not scattered
                >0: Count only particles that have scattered exactly n times (n > 0)
            
        Notes:
        ------
        - The scatter counter must be properly initialized and attached to a volume before use
        - Multiple scorers can share the same scatter counter with different scattering requirements
        - This filtering mechanism is particularly useful for analyzing multiple scattering effects
          in neutron scattering experiments
        - The method delegates to the underlying C++ implementation via _pt_addMultiScatter2D
        
        Example:
        --------
        # Create a scatter counter for a sample volume
        scatter_counter = MultiScatCounter("SampleScatterCounter")
        sample_volume.addScorer(scatter_counter, scatter_counter.make(sample_volume))
        
        # Create a 2D scorer that only counts particles with exactly 2 scatterings
        scorer_2d = Some2DScorerHelper("MyScorer", ...)
        scorer_2d.addScatterCounter(scatter_counter, scatterNumberRequired=2)
        
        See Also:
        ---------
        MultiScatCounter : Helper class for counting scattering events
        MultiScatMixin1D.addScatterCounter : 1D version of this method
        """
        _pt_addMultiScatter2D(scatterCounter.cobj, self.cobj, scatterNumberRequired)

# Counter 
class MultiScatCounter(ScorerHelper):
    """
        Multi-scattering counter (MSC) Helper class.
        A multi-scattering counter counts the number of scatterings inside a Volume of each particle.
        Use `aScorer.addScatterCounter(MSC, scatterNumberRequired)` to filter the particles counted 
    with required number of scatterings for `aScorer`.
    """
    def __init__(self, name="ScatterCounter") -> None:
        super().__init__(name, min=-2.5, max=100.5, numbin=103, pdg=2112, ptstate = 'PEA_POST', groupID=0)

    def make(self, vol):
        cobj = _pt_ScorerMultiScat_new(self.name.encode('utf-8'), 
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.groupID)
        vol.addScorer(self, cobj)
        self.cobj = cobj
        
# 1D Scorer
class ESpectrumHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name, min=1e-5, max=1, numbin = 100, pdg : int = 2112,
                 ptstate: str = 'ENTRY', energyTransfer=False, groupID=0, linear = None, log = None) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)
        self.energyTransfer = energyTransfer
        # `log` is the canonical binning flag; `linear` stays as a deprecated alias
        self.log = _resolveLogBinning('ESpectrumHelper', log, linear, defaultLinear=False)
        self.linear = not self.log
        _checkScorerRange(name, min, max, logBinning=self.log)

    def make(self, vol):
        cobj = _pt_ScorerESpectrum_new(self.name.encode('utf-8'), 
                                        self.energyTransfer,
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.groupID,
                                        self.linear
                                        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

     
    
class WlSpectrumHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name, min=0.1, max=10, numbin = 100, pdg : int = 2112,
                 ptstate : str = 'ENTRY', groupID : int = 0, linear = None, log = None) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)
        # `log` is the canonical binning flag; `linear` stays as a deprecated alias
        self.log = _resolveLogBinning('WlSpectrumHelper', log, linear, defaultLinear=False)
        self.linear = not self.log
        _checkScorerRange(name, min, max, logBinning=self.log)

    def make(self, vol):
        cobj = _pt_ScorerWlSpectrum_new(self.name.encode('utf-8'), 
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.groupID,
                                        self.linear
                                        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

class VolFluenceHelper(ScorerHelper, MultiScatMixin1D):
    """Track-length (fluence) scorer, pinned to PEA_PRE.

    Every particle track segment inside the volume - the flight to each
    collision and the final flight out - is binned by its flight energy with
    weight ``step_length``. The histogram therefore accumulates **track
    length** (in mm) per source particle, the estimator of ``integral of
    flux over the volume``; divide by the volume once after the run to get
    the fluence (track length per unit volume)::

        hist = sim.gatherHistData('name')
        hist.scale(1.0 / vol.getCapacity())   # fluence per mm^3

    PEA_PRE is required because it is the only hook that sees *every* track
    segment: PROPAGATE_PRE/POST fire at interaction sites only, so they
    would silently drop the boundary-exit tracks (the C++ side rejects
    those ptstate values for this scorer).
    """

    def __init__(self, name, min = 1e-6, max = 10, numbin = 100, pdg = 2112, linear = None, groupID : int = 0, log = None) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate = 'PEA_PRE', groupID = groupID)
        # `log` is the canonical binning flag; `linear` stays as a deprecated alias
        self.log = _resolveLogBinning('VolFluenceHelper', log, linear, defaultLinear=False)
        self.linear = not self.log
        _checkScorerRange(name, min, max, logBinning=self.log)

    def make(self, vol):
        # pre-check mirroring the C++ constructor guard: the raw ctypes bridge
        # cannot transport a C++ exception (it would abort the interpreter), so
        # an overridden ptstate must fail here as a plain Python error instead
        if self.ptstate.strip().upper() in ('PROPAGATE_PRE', 'PROPAGATE_POST'):
            raise ValueError(
                f"VolFluence '{self.name}': ptstate={self.ptstate} is not allowed. "
                "PROPAGATE_PRE/POST only fire at interaction sites, so the boundary-exit "
                "tracks would be silently dropped and the flux undercounted. "
                "Use the default PEA_PRE (every track segment, pre-collision energy) or "
                "PEA_POST (post-collision energy), and divide the histogram by the volume "
                "after the run: hist.scale(1.0 / vol.getCapacity()).")
        cobj = _pt_ScorerVolFluence_new(
            self.name.encode('utf-8'),
            self.min,
            self.max,
            self.numbin,
            self.pdg,
            self.ptsNum,
            self.linear,
            self.groupID
        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

class DirectSqHelper(ScorerHelper, MultiScatMixin1D):
    """
    Helper class for calculating direct scattering structure factors S(Q) in neutron scattering experiments.
    
    This scorer computes the momentum transfer (Q) distribution for particles interacting with
    a sample, providing the direct scattering structure factor S(Q) which characterizes
    the spatial correlations in the sample material.
    
    Inherits from:
        ScorerHelper: Base class for particle scoring functionality
        MultiScatMixin1D: Mixin for 1D multiple scattering analysis
    """
    def __init__(self, name, qmin, qmax, numbin, mod_smp_dist, pdg=2112,
                 refDir=(0.,0.,1.), samplePos=(0.,0.,0.), ptstate='ENTRY', method=0,
                 linear=None, groupID=0, log=None):
        """
        Initialize a DirectSqHelper instance for direct scattering structure factor calculation.
        
        Parameters:
        -----------
        name : str
            Unique identifier for this scorer instance
        qmin : float
            Minimum momentum transfer Q value (Å⁻¹) for the histogram binning
        qmax : float
            Maximum momentum transfer Q value (Å⁻¹) for the histogram binning
        numbin : int
            Number of bins for Q-value histogram
        mod_smp_dist : float
            Distance from moderator to sample (mm) - critical for flight path calculations.
            Stored as the attribute ``distanceMS`` for backward compatibility
            (DirectSqwHelper names the same quantity ``mod_smp_dist``)
        pdg : int, optional
            Particle Data Group code for particle type (default: 2112 for neutron)
        refDir : sequence, optional
            Reference direction vector [x,y,z] of the incident beam, i.e. the mean
            incident direction (named ``mean_incident_dir`` in DirectSqwHelper)
            (default: (0,0,1))
        samplePos : sequence, optional
            Sample position coordinates [x,y,z] in the simulation geometry
            (named ``sample_position`` in DirectSqwHelper) (default: (0,0,0))
        ptstate : str, optional
            Particle tracing state when scoring occurs. Options: 'ENTRY', 'EXIT', 'PROPAGATE_POST', etc.
            (default: 'ENTRY')
        method : int, optional
            Calculation method for momentum transfer:
                0 = Dynamic Energy Transfer Method (uses actual particle energy transfer)
                1 = Static Approximation Method (assumes zero energy transfer)
            (default: 0)
        linear : bool, optional
            If True, use linear binning; if False, use logarithmic binning (default: False)
        groupID : int, optional
            Group identifier for organizing multiple scorers (default: 0)
        
        Notes:
        ------
        - The momentum transfer Q is calculated using the neutron scattering angle and energy transfer
        - Method 0 provides more accurate results for inelastic scattering processes
        - Method 1 is faster but less accurate, suitable for elastic scattering approximations
        - The structure factor S(Q) is proportional to the Fourier transform of the pair correlation function
        - Distance parameters use millimeters (mm) for consistency with typical neutron scattering setups
        """
        super().__init__(name, qmin, qmax, numbin, pdg, ptstate, groupID)
        # attribute kept as `distanceMS` for backward compatibility (see docstring)
        self.distanceMS = mod_smp_dist
        # immutable tuple defaults: a mutable class-level list default would share
        # in-place user mutations across all future instances
        self.refDir = tuple(refDir)
        self.samplePos = tuple(samplePos)
        self.method = method
        # `log` is the canonical binning flag; `linear` stays as a deprecated alias
        self.log = _resolveLogBinning('DirectSqHelper', log, linear, defaultLinear=False)
        self.linear = not self.log
        _checkScorerRange(name, qmin, qmax, logBinning=self.log)

    def make(self, vol):
        cobj = _pt_ScorerDeltaMomentum_new(
            self.name.encode('utf-8'),
            self.distanceMS,
            self.min,
            self.max,
            self.numbin,
            self.pdg,
            self.refDir[0],
            self.refDir[1],
            self.refDir[2],
            self.samplePos[0],
            self.samplePos[1],
            self.samplePos[2],
            self.ptsNum,
            self.method,
            self.linear
        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

class DepositionHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name : str, min, max, numbin, pdg, ptstate, linear = None, groupID : int = 0, log = None) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)
        # `log` is the canonical binning flag; `linear` stays as a deprecated alias
        self.log = _resolveLogBinning('DepositionHelper', log, linear, defaultLinear=False)
        self.linear = not self.log
        _checkScorerRange(name, min, max, logBinning=self.log)

    def make(self, vol):
        # enum class ScorerType {SURFACE, ENTRY, PROPAGATE, EXIT, PEA, ABSORB};
        cobj = _pt_ScorerDeposition_new(self.name.encode('utf-8'), 
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.linear,
                                        self.groupID)
        vol.addScorer(self, cobj)
        self.cobj = cobj


    # ScorerDirectSqw(const std::string &name, double qmin, double qmax, unsigned xbin,
    #   double ekinmin, double ekinmax, unsigned nybins,
    #   unsigned int pdg, int group_id,
    #   double mod_smp_dist, double mean_ekin, const Vector& mean_incident_dir, const Vector& sample_position, 
    #   ScorerType stype=Scorer::ScorerType::ENTRY);


class TOFHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name : str, min : float = 0., max : float = 40e-3, numbin : int = 100, 
                 pdg : int = 2112, ptstate : str = 'ENTRY', groupID : int = 0) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)

    def make(self, vol):
        cobj = _pt_ScorerTOF_new(self.name.encode('utf-8'),
                                 self.min,
                                 self.max,
                                 self.numbin,
                                 self.pdg,
                                 self.ptsNum,
                                 self.groupID)
        vol.addScorer(self, cobj)
        self.cobj = cobj


# 2D Scorer
class PSDHelper(ScorerHelper2D, MultiScatMixin2D):
    def __init__(self, name, xmin=-10., xmax=10., xnumbin=100, 
                 ymin=-10, ymax=10, ynumbin=100, pdg=2112, 
                 ptstate='ENTRY', psdtype='XY', groupID=0, isGlobal = False) -> None:
        super().__init__(name, xmin, xmax, xnumbin, 
                         ymin, ymax, ynumbin, pdg, ptstate, groupID)
        self.psdtype = psdtype
        self.isGlobal = isGlobal

    @property
    def psdTypeNum(self):
        if self.psdtype=='XY':
            return 0
        elif self.psdtype=='XZ':
            return 1
        elif self.psdtype=='YZ':
            return 2
        else:
            raise RuntimeError(f'PSD type {self.psdtype} is undefined.') 

    def make(self, vol):
        cobj = _pt_ScorerPSD_new(self.name.encode('utf-8'),
                                 self.min,
                                 self.max,
                                 self.numbin,
                                 self.ymin,
                                 self.ymax,
                                 self.ynumbin,
                                 self.pdg,
                                 self.ptsNum,
                                 self.psdTypeNum,
                                 self.groupID,
                                 self.isGlobal)
        vol.addScorer(self, cobj)
        self.cobj = cobj

class DirectSqwHelper(ScorerHelper2D, MultiScatMixin2D):
    """
    Helper class for calculating dynamic scattering structure factors S(Q,ω) in neutron scattering experiments.
    
    This scorer computes the 2D distribution of momentum transfer (Q) versus energy transfer (ω),
    providing the dynamic structure factor S(Q,ω) which characterizes both spatial and temporal
    correlations in the sample material.
    
    Inherits from:
        ScorerHelper2D: Base class for 2D particle scoring functionality
        MultiScatMixin2D: Mixin for 2D multiple scattering analysis
    """
    def __init__(self, name, mod_smp_dist, mean_ekin, mean_incident_dir=(0.,0.,1.), sample_position=(0.,0.,0.),
                 qmin = 1e-1, qmax = 10, num_qbin = 50,
                 ekinmin=-0.1 , ekinmax=0.1,  num_ebin = 30,
                 pdg = 2112, groupID  = 0, logx=None, ptstate = 'ENTRY', log = None) -> None:
        """
        Initialize a DirectSqwHelper instance for dynamic scattering structure factor calculation.
        
        Parameters:
        -----------
        name : str
            Unique identifier for this scorer instance
        mod_smp_dist : float
            Distance from moderator to sample (mm) - critical for flight path calculations
        mean_ekin : float
            Mean kinetic energy of incident neutrons (eV) - defines the incident energy 
        mean_incident_dir : array-like, optional
            Mean incident direction vector [x,y,z] for the neutron beam (default: [0,0,1])
        sample_position : array-like, optional
            Sample position coordinates [x,y,z] in the simulation geometry (default: [0,0,0])
        qmin : float, optional
            Minimum momentum transfer Q value (Å⁻¹) for the Q-axis histogram binning (default: 0.1)
        qmax : float, optional
            Maximum momentum transfer Q value (Å⁻¹) for the Q-axis histogram binning (default: 10)
        num_qbin : int, optional
            Number of bins for Q-value histogram (default: 50)
        ekinmin : float, optional
            Minimum energy transfer value (eV) for the ω-axis histogram binning (default: -0.1)
        ekinmax : float, optional
            Maximum energy transfer value (eV) for the ω-axis histogram binning (default: 0.1)
        num_ebin : int, optional
            Number of bins for energy transfer histogram (default: 30)
        pdg : int, optional
            Particle Data Group code for particle type (default: 2112 for neutron)
        groupID : int, optional
            Group identifier for organizing multiple scorers (default: 0)
        logx : bool, optional
            Deprecated alias for `log`. If True, requests logarithmic binning for the
            Q-axis (default: None)
        ptstate : str, optional
            Particle tracing state when scoring occurs. Options: 'ENTRY', 'EXIT', 'PROPAGATE_POST', etc.
            (default: 'ENTRY')
        log : bool, optional
            Canonical binning flag: if True, request logarithmic binning for the Q-axis;
            if False, use linear binning (default: False).
            Note: the C++ scorer does not support a binning-shape switch yet, so the
            Q-axis stays linearly binned for now and a UserWarning is emitted when True
        
        Notes:
        ------
        - The dynamic structure factor S(Q,ω) provides information about both spatial correlations (via Q)
          and temporal correlations (via ω) in the sample material
        - Energy transfer ω = E_initial - E_final: positive values indicate energy loss
          (neutron loses energy to the sample, downscatter) and negative values indicate
          energy gain (upscatter)
        - This is particularly useful for studying inelastic scattering processes, phonons,
          and other dynamic phenomena in materials
        - The 2D histogram provides a comprehensive view of scattering dynamics across
          different momentum and energy transfer regimes
        - Distance parameters use millimeters (mm) for consistency with typical neutron scattering setups
        """
        super().__init__(name, qmin, qmax, num_qbin, ekinmin, ekinmax, num_ebin, pdg, ptstate, groupID)
        self.mod_smp_dist = mod_smp_dist
        self.mean_ekin = mean_ekin
        # immutable tuple defaults: a mutable class-level array default would share
        # in-place user mutations across all future instances
        self.mean_incident_dir = tuple(mean_incident_dir)
        self.sample_position = tuple(sample_position)
        # `log` is the canonical binning flag; `logx` stays as a deprecated alias
        if logx is not None:
            warnings.warn("DirectSqwHelper: the 'logx' keyword is deprecated, use 'log'",
                          DeprecationWarning, stacklevel=2)
            if log is None:
                log = logx
        if log is None:
            log = False
        self.log = log
        self.logx = log  # deprecated alias attribute, kept for backward compatibility
        # keep the inherited flags consistent; the C++ scorer ignores the binning
        # shape for now (see the note in make()), so no log-positivity check on the
        # Q range here yet - add _checkScorerRange(..., logBinning=self.log) to the
        # Q axis once the C++ side supports logarithmic binning
        self.linear = not log
        if log:
            warnings.warn("DirectSqwHelper: logarithmic Q-axis binning is not supported by the "
                          "C++ scorer yet, the Q axis stays linearly binned", UserWarning, stacklevel=2)

    def make(self, vol):
        # NOTE: the trailing self.logx flag is currently ignored by the C side
        # (pt_ScorerDirectSqw_new takes no binning-shape argument), the Q-axis
        # binning is always linear for now
        cobj = _pt_ScorerDirectSqw_new(
            self.name.encode('utf-8'),
            self.min, self.max, self.numbin,
            self.ymin, self.ymax, self.ynumbin,
            self.pdg, self.groupID,
            self.mod_smp_dist, self.mean_ekin,
            self.mean_incident_dir[0], self.mean_incident_dir[1], self.mean_incident_dir[2],
            self.sample_position[0], self.sample_position[1], self.sample_position[2],
            self.ptsNum, self.logx
        )
        vol.addScorer(self, cobj)
        self.cobj = cobj


# Legacy convenience wrapper over the deprecated string-based PSD scorer.
# Kept for backward compatibility; PSDHelper covers the same need properly.
def makePSD(name, vol, numbin_dim1=1, numbin_dim2=1, ptstate : str = 'ENTRY', type : str = 'XY'):
    warnings.warn("makePSD is deprecated and only supports Box solids, use PSDHelper instead",
                  DeprecationWarning, stacklevel=2)
    # the implementation below reads the hx/hy/hz half-lengths, which only Box provides
    solid = vol.solid
    if not all(hasattr(solid, attr) for attr in ('hx', 'hy', 'hz')):
        raise TypeError(f"makePSD only supports Box solids (with hx/hy/hz half-lengths), "
                        f"got {solid.__class__.__name__}; use PSDHelper instead")
    det = PSD()
    det.cfg_name = name
    det.cfg_numbin_x = numbin_dim1 
    det.cfg_numbin_y = numbin_dim2 
    det.cfg_ptstate = ptstate
    det.cfg_type = type
    if type == 'XY':
        det.cfg_xmin = -vol.solid.hx
        det.cfg_xmax = vol.solid.hx
        det.cfg_ymin = -vol.solid.hy
        det.cfg_ymax = vol.solid.hy
    elif type == 'XZ':
        det.cfg_xmin = -vol.solid.hx
        det.cfg_xmax = vol.solid.hx
        det.cfg_ymin = -vol.solid.hz
        det.cfg_ymax = vol.solid.hz
    elif type == 'YZ':
        det.cfg_xmin = -vol.solid.hy
        det.cfg_xmax = vol.solid.hy
        det.cfg_ymin = -vol.solid.hz
        det.cfg_ymax = vol.solid.hz
    vol.addScorer(det.cfg)

        
class MCPLOutHelper(MultiScatMixin1D):
    def __init__(self, name, pdg : int = 2112, groupID : int = 0, kill : bool = False, compress : bool = True) -> None:
        def get_rank_id():
            try:
                # Initialize the MPI environment
                from mpi4py import MPI
                comm = MPI.COMM_WORLD
                rank = comm.Get_rank()
                return rank
            except:
                return None
        
        process_id = get_rank_id()

        if process_id is None:
            self.use_mpi=False
        else:
            self.use_mpi=True
            self.name_mpi = name+f'_pro{process_id}' 

        self.name = name
        self.pdg = pdg 
        self.groupID = groupID
        self.kill = kill
        self.compress = compress

    def make(self, vol):
        fname = self.name_mpi if self.use_mpi else self.name
        fdir = os.path.dirname(fname) or os.curdir
        # pre-check the output location so that a bad path raises a normal Python
        # exception naming the path, instead of a bare "MCPL ERROR: Unable to
        # open output file!" from the C side
        if not os.path.isdir(fdir):
            raise ValueError(f"MCPL output directory '{fdir}' does not exist (output file '{fname}').")
        if not os.access(fdir, os.W_OK):
            raise ValueError(f"MCPL output directory '{fdir}' is not writable (output file '{fname}').")
        cobj = _pt_KillerMCPL_new(fname.encode('utf-8'),
                                        self.pdg,
                                        self.groupID,
                                        self.kill,
                                        self.compress
                                        )
        vol.addScorer(self, cobj)
        self.cobj = cobj


# TODO:
# Legacy Scorer class, to be reviewed and potentially deprecated
class Scorer(ConfigString):
    """
    Base class for all scorers using string-based configuration.
    
    This class provides the foundation for scorers that use configuration strings
    for setup. Derived classes should implement specific scoring functionality.
    """
    pass

class PSD(ConfigString):
    """
    Position Sensitive Detector scorer for 2D position measurements.
    
    Measures particle positions in a 2D grid, typically used for imaging applications.
    
    Attributes:
        cfg_Scorer (str): Scorer type identifier ('PSD')
        cfg_name (str): Scorer instance name
        cfg_xmin (float): Minimum X coordinate
        cfg_xmax (float): Maximum X coordinate
        cfg_numbin_x (int): Number of bins in X direction
        cfg_ymin (float): Minimum Y coordinate
        cfg_ymax (float): Maximum Y coordinate
        cfg_numbin_y (int): Number of bins in Y direction
        cfg_ptstate (str): Particle tracing state ('ENTRY')
        cfg_type (str): Detector orientation type ('XZ')

    Note:
        This string-based legacy scorer API is deprecated and kept only for backward
        compatibility; its defaults deliberately differ from PSDHelper
        (xmin/xmax +-10, 100 bins, psdtype 'XY'). Use PSDHelper instead.
    """
    def __init__(self) -> None:
        warnings.warn("PSD string-based scorer configuration is deprecated, use PSDHelper instead",
                      DeprecationWarning, stacklevel=2)
        super().__init__()
        self.cfg_Scorer='PSD'
        self.cfg_name = 'PSD'
        self.cfg_xmin = -1.
        self.cfg_xmax = 1.
        self.cfg_numbin_x = 10 
        self.cfg_ymin = -1.
        self.cfg_ymax = 1.
        self.cfg_numbin_y = 10 
        self.cfg_ptstate = 'ENTRY' 
        self.cfg_type = 'XZ'

class WlSpectrum(ConfigString):
    """
    Wavelength spectrum scorer for measuring particle wavelength distributions.
    
    Records the wavelength distribution of particles interacting with the detector.
    
    Attributes:
        cfg_Scorer (str): Scorer type identifier ('WlSpectrum')
        cfg_name (str): Scorer instance name
        cfg_min (float): Minimum wavelength (default: 0.0)
        cfg_max (float): Maximum wavelength (default: 5.0)
        cfg_numbin (int): Number of wavelength bins (default: 100)
        cfg_ptstate (str): Particle tracing state ('ENTRY')

    Note:
        This string-based legacy scorer API is deprecated and kept only for backward
        compatibility; its default range deliberately differs from WlSpectrumHelper
        (min=0.1, max=10). Use WlSpectrumHelper instead.
    """
    def __init__(self) -> None:
        warnings.warn("WlSpectrum string-based scorer configuration is deprecated, use WlSpectrumHelper instead",
                      DeprecationWarning, stacklevel=2)
        super().__init__()
        self.cfg_Scorer='WlSpectrum'
        self.cfg_name = 'WlSpectrum'
        self.cfg_min = 0.0
        self.cfg_max = 5
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'

class ESpectrum(ConfigString):
    """
    Energy spectrum scorer for measuring particle energy distributions.
    
    Records the energy distribution of particles, with optional energy transfer scoring.
    
    Attributes:
        cfg_Scorer (str): Scorer type identifier ('ESpectrum')
        cfg_name (str): Scorer instance name
        cfg_scoreTransfer (int): Flag for energy transfer scoring (0=off, 1=on)
        cfg_min (float): Minimum energy (default: 1e-5)
        cfg_max (float): Maximum energy (default: 0.25)
        cfg_numbin (int): Number of energy bins (default: 100)
        cfg_ptstate (str): Particle tracing state ('ENTRY')

    Note:
        This string-based legacy scorer API is deprecated and kept only for backward
        compatibility; its default range deliberately differs from ESpectrumHelper
        (min=1e-5, max=1). Use ESpectrumHelper instead.
    """
    def __init__(self) -> None:
        warnings.warn("ESpectrum string-based scorer configuration is deprecated, use ESpectrumHelper instead",
                      DeprecationWarning, stacklevel=2)
        super().__init__()
        self.cfg_Scorer='ESpectrum'
        self.cfg_name = 'ESpectrum'
        self.cfg_scoreTransfer = 0
        self.cfg_min = 1e-5
        self.cfg_max = 0.25
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'

class TOF(ConfigString):
    """
    Time-of-Flight scorer for measuring particle arrival times.
    
    Records the time distribution of particles reaching the detector.
    
    Attributes:
        cfg_Scorer (str): Scorer type identifier ('TOF')
        cfg_name (str): Scorer instance name
        cfg_min (float): Minimum time (default: 0.0025)
        cfg_max (float): Maximum time (default: 0.008)
        cfg_numbin (int): Number of time bins (default: 100)
        cfg_ptstate (str): Particle tracing state ('ENTRY')

    Note:
        This string-based legacy scorer API is deprecated and kept only for backward
        compatibility; its default range deliberately differs from TOFHelper
        (min=0, max=40e-3). Use TOFHelper instead.
    """
    def __init__(self) -> None:
        warnings.warn("TOF string-based scorer configuration is deprecated, use TOFHelper instead",
                      DeprecationWarning, stacklevel=2)
        super().__init__()
        self.cfg_Scorer='TOF'
        self.cfg_name = 'TOF'
        self.cfg_min = 0.0025
        self.cfg_max = 0.008
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'

class VolFluence(ConfigString):
    """
    Track-length (fluence) scorer for volumes.

    Each fill accumulates the particle track length (weight * step length)
    binned by flight energy, so the histogram is the volume integral of the
    flux; divide it by the volume after the run to obtain the fluence.

    Attributes:
        cfg_Scorer (str): Scorer type identifier ('VolFluence')
        cfg_name (str): Scorer instance name
        cfg_min (float): Minimum value (default: 0)
        cfg_max (float): Maximum value (default: 1)
        cfg_numbin (int): Number of bins (default: 100)
        cfg_ptstate (str): Particle tracing state ('ENTRY')
        cfg_linear (str): Linear binning flag ('yes'/'no')

    Note:
        This string-based legacy scorer API is deprecated and kept only for backward
        compatibility; its defaults deliberately differ from VolFluenceHelper
        (min=1e-6, max=10, ptstate 'PEA_PRE', linear=no). Use VolFluenceHelper instead.
    """
    def __init__(self) -> None:
        warnings.warn("VolFluence string-based scorer configuration is deprecated, use VolFluenceHelper instead",
                      DeprecationWarning, stacklevel=2)
        super().__init__()
        self.cfg_Scorer='VolFluence'
        self.cfg_name = 'VolFluence'
        self.cfg_min = 0
        self.cfg_max = 1
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'
        self.cfg_linear = 'yes'

# FIXME: scorer object construction moves from strings to ctype
# the following class name move to *V1
class ScorerHelperV1:
    """
    Legacy helper class for string-based scorer configuration (Version 1).
    
    This class provides a helper interface for creating scorers using string-based
    configuration. It's being phased out in favor of direct C++ object creation.
    
    Args:
        name (str): Unique identifier for the scorer
        min (float): Minimum value of scoring range
        max (float): Maximum value of scoring range
        numbin (int): Number of bins in the scoring range
        ptstate (str or ParticleTracingState): Particle tracing state
    
    Methods:
        make: Adds the scorer to a volume

    Note:
        Deprecated: prefer the current *Helper classes (e.g. ESpectrumHelper).
        Constructing a V1 helper (or the legacy string-config scorer classes)
        emits a DeprecationWarning.
    """
    def __init__(self, name, min, max, numbin, ptstate) -> None:
        self.name = name
        self.min = min
        self.max = max
        self.numbin = numbin
        if isinstance(ptstate, ParticleTracingState):
            self.ptstate = ptstate.to_string()
        elif isinstance(ptstate, str):
            self.ptstate = ptstate
        else:
            raise TypeError(f"ptstate must be a string or ParticleTracingState enum, got {type(ptstate)}")

    def __realinit(self):
        self.score.cfg_name = self.name
        self.score.cfg_min = self.min
        self.score.cfg_max = self.max
        self.score.cfg_numbin = self.numbin
        self.score.cfg_ptstate = self.ptstate
        
    def make(self, vol):
        vol.addScorer(self.score.cfg)

class ESpectrumHelperV1(ScorerHelperV1): 
    """
    Legacy helper for energy spectrum scorers (Version 1).
    
    Args:
        name (str): Scorer name
        min (float): Minimum energy (default: 1e-5)
        max (float): Maximum energy (default: 1.0)
        numbin (int): Number of bins (default: 100)
        ptstate (str): Particle tracing state (default: 'ENTRY')
        energyTransfer (bool): Enable energy transfer scoring (default: False)

    Note:
        Deprecated: prefer ESpectrumHelper, which has the same defaults. When the
        wrapped ESpectrum string class is used directly it keeps its own historical
        default max=0.25 (see the ESpectrum docstring).
    """
    def __init__(self, name, min=1e-5, max=1, numbin = 100, ptstate: str = 'ENTRY', energyTransfer=False) -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = ESpectrum()
        if energyTransfer:
            self.score.cfg_scoreTransfer = 1
        else:
            self.score.cfg_scoreTransfer = 0
        self._ScorerHelperV1__realinit()
    
class WlSpectrumHelperV1(ScorerHelperV1): 
    """
    Legacy helper for wavelength spectrum scorers (Version 1).
    
    Args:
        name (str): Scorer name
        min (float): Minimum wavelength (default: 0.1)
        max (float): Maximum wavelength (default: 10.0)
        numbin (int): Number of bins (default: 100)
        ptstate (str): Particle tracing state (default: 'ENTRY')
    """
    def __init__(self, name, min=0.1, max=10, numbin = 100, ptstate: str = 'ENTRY') -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = WlSpectrum()
        self._ScorerHelperV1__realinit()
    
class TOFHelperV1(ScorerHelperV1): 
    """
    Legacy helper for time-of-flight scorers (Version 1).
    
    Args:
        name (str): Scorer name
        min (float): Minimum time (default: 0.0)
        max (float): Maximum time (default: 40e-3)
        numbin (int): Number of bins (default: 100)
        ptstate (str): Particle tracing state (default: 'ENTRY')
    """
    def __init__(self, name, min=0, max=40e-3, numbin = 100, ptstate: str = 'ENTRY') -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = TOF()
        self._ScorerHelperV1__realinit()

class VolFluenceHelperV1(ScorerHelperV1): 
    """
    Legacy helper for volume fluence scorers (Version 1).
    
    Args:
        name (str): Scorer name
        min (float): Minimum value (default: 1e-6)
        max (float): Maximum value (default: 10.0)
        numbin (int): Number of bins (default: 100)
        ptstate (str): Particle tracing state (default: 'PEA_PRE')
        linear (bool): Use linear binning (default: False)
    """
    def __init__(self, name, min=1e-6, max=10, numbin = 100, ptstate: str = 'PEA_PRE', linear = False) -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = VolFluence()
        if linear:
            self.score.cfg_linear = 'yes'
        else: 
            self.score.cfg_linear = 'no'
        self._ScorerHelperV1__realinit()