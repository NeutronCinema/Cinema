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

"""
Unit conversion functions for neutron scattering calculations.

All energy parameters use eV as the base unit. Functions automatically handle
both scalar and numpy array inputs.
"""

from Cinema.Interface import *
import numpy as np

# Basic conversion functions (using eV units)
_eKin2k = importFunc('pt_eKin2k', type_dbl, [type_dbl])
_angleCosine2Q = importFunc('pt_angleCosine2Q', type_dbl, [type_dbl, type_dbl, type_dbl])
_wl2ekin = importFunc('pt_wl2ekin', type_dbl, [type_dbl])
_ekin2wl = importFunc('pt_ekin2wl', type_dbl, [type_dbl])
_ekin2v = importFunc('pt_ekin2speed', type_dbl, [type_dbl])
_v2ekin = importFunc('pt_speed2ekin', type_dbl, [type_dbl])

# Create vectorized versions for array processing
_eKin2k_vec = np.vectorize(_eKin2k)
_angleCosine2Q_vec = np.vectorize(_angleCosine2Q)
_wl2ekin_vec = np.vectorize(_wl2ekin)
_ekin2wl_vec = np.vectorize(_ekin2wl)
_ekin2v_vec = np.vectorize(_ekin2v)
_v2ekin_vec = np.vectorize(_v2ekin)

# Unit conversion constants
_eV2MeV = 1e-6
_MeV2eV = 1e6
_eV2keV = 1e-3
_keV2eV = 1e3
_eV2meV = 1e-3
_meV2eV = 1e3

def _is_array_like(x):
    """Check if input is array-like (numpy array, list, tuple, etc.)."""
    return hasattr(x, '__iter__') and not isinstance(x, (str, bytes))

def eKin2k(ekin_eV):
    """Convert kinetic energy to wave number.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        ekin_eV: Kinetic energy in eV (scalar or array)
        
    Returns:
        Wave number in Å⁻¹ (same shape as input)
    """
    if _is_array_like(ekin_eV):
        return _eKin2k_vec(ekin_eV)
    else:
        return _eKin2k(ekin_eV)

def angleCosine2Q(angle_cos, enin_eV, enout_eV=None):
    """Calculate momentum transfer Q from scattering angle cosine.
    
    Automatically handles both scalar and array inputs. Arrays are broadcasted.
    
    Args:
        angle_cos: Cosine of scattering angle (scalar or array)
        enin_eV: Incident energy in eV (scalar or array)
        enout_eV: Outgoing energy in eV (if None, elastic scattering is assumed)
        
    Returns:
        Momentum transfer Q in Å⁻¹ (broadcasted shape)
    """
    if enout_eV is None:
        enout_eV = enin_eV  # Elastic scattering
    
    # Handle array inputs
    if _is_array_like(angle_cos) or _is_array_like(enin_eV) or _is_array_like(enout_eV):
        return _angleCosine2Q_vec(angle_cos, enin_eV, enout_eV)
    else:
        return _angleCosine2Q(angle_cos, enin_eV, enout_eV)

def wl2ekin(wl_angstrom):
    """Convert wavelength to kinetic energy.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        wl_angstrom: Wavelength in Å (scalar or array)
        
    Returns:
        Kinetic energy in eV (same shape as input)
    """
    if _is_array_like(wl_angstrom):
        return _wl2ekin_vec(wl_angstrom)
    else:
        return _wl2ekin(wl_angstrom)

def ekin2wl(ekin_eV):
    """Convert kinetic energy to wavelength.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        ekin_eV: Kinetic energy in eV (scalar or array)
        
    Returns:
        Wavelength in Å (same shape as input)
    """
    if _is_array_like(ekin_eV):
        return _ekin2wl_vec(ekin_eV)
    else:
        return _ekin2wl(ekin_eV)

def ekin2v(ekin_eV):
    """Convert kinetic energy to velocity.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        ekin_eV: Kinetic energy in eV (scalar or array)
        
    Returns:
        Velocity in mm/s (same shape as input)
    """
    if _is_array_like(ekin_eV):
        return _ekin2v_vec(ekin_eV)
    else:
        return _ekin2v(ekin_eV)

def v2ekin(v_mm_per_s):
    """Convert velocity to kinetic energy.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        v_mm_per_s: Velocity in mm/s (scalar or array)
        
    Returns:
        Kinetic energy in eV (same shape as input)
    """
    if _is_array_like(v_mm_per_s):
        return _v2ekin_vec(v_mm_per_s)
    else:
        return _v2ekin(v_mm_per_s)

# Unit conversion helper functions
def MeV2eV(energy_MeV):
    """Convert MeV to eV."""
    return energy_MeV * _MeV2eV

def eV2MeV(energy_eV):
    """Convert eV to MeV."""
    return energy_eV * _eV2MeV

def keV2eV(energy_keV):
    """Convert keV to eV."""
    return energy_keV * _keV2eV

def eV2keV(energy_eV):
    """Convert eV to keV."""
    return energy_eV * _eV2keV

def meV2eV(energy_meV):
    """Convert meV to eV."""
    return energy_meV * _meV2eV

def eV2meV(energy_eV):
    """Convert eV to meV."""
    return energy_eV * _eV2meV

# Convenient functions with unit support
def angleCosine2Q_units(angle_cos, enin, enin_unit='eV', enout=None, enout_unit='eV'):
    """Calculate momentum transfer Q with flexible unit support.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        angle_cos: Cosine of scattering angle (scalar or array)
        enin: Incident energy (scalar or array)
        enin_unit: Unit of incident energy ('eV', 'meV', 'keV', 'MeV')
        enout: Outgoing energy (if None, elastic scattering is assumed)
        enout_unit: Unit of outgoing energy
        
    Returns:
        Momentum transfer Q in Å⁻¹ (broadcasted shape)
    """
    # Convert to eV
    if enin_unit == 'meV':
        enin_eV = meV2eV(enin)
    elif enin_unit == 'keV':
        enin_eV = keV2eV(enin)
    elif enin_unit == 'MeV':
        enin_eV = MeV2eV(enin)
    else:  # Default eV
        enin_eV = enin
    
    if enout is None:
        enout_eV = enin_eV  # Elastic scattering
    else:
        if enout_unit == 'meV':
            enout_eV = meV2eV(enout)
        elif enout_unit == 'keV':
            enout_eV = keV2eV(enout)
        elif enout_unit == 'MeV':
            enout_eV = MeV2eV(enout)
        else:  # Default eV
            enout_eV = enout
    
    return angleCosine2Q(angle_cos, enin_eV, enout_eV)

def wl2ekin_units(wl_angstrom, ekin_unit='eV'):
    """Convert wavelength to kinetic energy with flexible output units.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        wl_angstrom: Wavelength in Å (scalar or array)
        ekin_unit: Output unit for kinetic energy ('eV', 'meV', 'keV', 'MeV')
        
    Returns:
        Kinetic energy in specified unit (same shape as input)
    """
    ekin_eV = wl2ekin(wl_angstrom)
    
    if ekin_unit == 'meV':
        return eV2meV(ekin_eV)
    elif ekin_unit == 'keV':
        return eV2keV(ekin_eV)
    elif ekin_unit == 'MeV':
        return eV2MeV(ekin_eV)
    else:  # Default eV
        return ekin_eV

def ekin2wl_units(ekin, ekin_unit='eV'):
    """Convert kinetic energy to wavelength with flexible input units.
    
    Automatically handles both scalar and array inputs.
    
    Args:
        ekin: Kinetic energy (scalar or array)
        ekin_unit: Input unit for kinetic energy ('eV', 'meV', 'keV', 'MeV')
        
    Returns:
        Wavelength in Å (same shape as input)
    """
    # Convert to eV
    if ekin_unit == 'meV':
        ekin_eV = meV2eV(ekin)
    elif ekin_unit == 'keV':
        ekin_eV = keV2eV(ekin)
    elif ekin_unit == 'MeV':
        ekin_eV = MeV2eV(ekin)
    else:  # Default eV
        ekin_eV = ekin
    
    return ekin2wl(ekin_eV)

# Export all functions
__all__ = [
    # Basic conversion functions (handle both scalar and arrays)
    'eKin2k', 'angleCosine2Q', 'wl2ekin', 'ekin2wl', 'ekin2v', 'v2ekin',
    
    # Unit conversion helpers
    'MeV2eV', 'eV2MeV', 'keV2eV', 'eV2keV', 'meV2eV', 'eV2meV',
    
    # Convenient functions with unit support
    'angleCosine2Q_units', 'wl2ekin_units', 'ekin2wl_units',
]