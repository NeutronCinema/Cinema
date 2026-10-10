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

import ctypes
import numbers
import os
import re
import sys
import warnings

from .configstr import ConfigString

# Matches data file references (bare names or absolute/relative paths) ending
# in '.ncmat' inside a material configuration string. Separators such as ';',
# '=', '@' and ':' are not part of the character class and thus end a match.
_ncmatFileRegex = re.compile(r'[A-Za-z0-9_.+/-]+\.ncmat')

# Names of the data files embedded inside the NCrystal library itself,
# resolved lazily on first use (an empty set means they could not be
# determined, in which case no file is ever rejected)
_ncrystalStdlibFiles = None


def _ncrystalDataRoots():
    """Directories in which NCrystal data files may be located."""
    roots = [os.getcwd()]
    dataPath = os.environ.get('NCRYSTAL_DATA_PATH')
    if dataPath:
        roots += [p for p in re.split('[;:]', dataPath) if p]
    cinemaPath = os.environ.get('CINEMAPATH')
    if cinemaPath:
        roots.append(os.path.join(cinemaPath, 'ncmat'))
    return roots


def _findNcmatFile(fname, roots):
    if os.path.isabs(fname):
        return os.path.isfile(fname)
    return any(os.path.isfile(os.path.join(root, fname)) for root in roots)


def _isNcrystalStdlibFile(fname):
    """Check a file name against the data files embedded in libNCrystal.

    The standard NCrystal data files (e.g. Ge_sg227.ncmat or void.ncmat) are
    embedded in the shared library itself and exist in no data directory.
    Whenever the library or the embedded names cannot be determined, return
    True so valid configurations are never rejected here (fail-open).
    """
    global _ncrystalStdlibFiles
    if _ncrystalStdlibFiles is None:
        _ncrystalStdlibFiles = set()
        libCandidates = [os.environ.get('NCRYSTAL_LIB'),
                         os.path.join(sys.base_prefix, 'lib', 'libNCrystal.so'),
                         os.path.join(sys.prefix, 'lib', 'libNCrystal.so')]
        ldPath = os.environ.get('LD_LIBRARY_PATH')
        if ldPath:
            libCandidates += [os.path.join(p, 'libNCrystal.so')
                              for p in ldPath.split(':') if p]
        for candidate in libCandidates:
            try:
                if candidate and os.path.isfile(candidate):
                    with open(candidate, 'rb') as fobj:
                        content = fobj.read().decode('latin-1', errors='ignore')
                    _ncrystalStdlibFiles = set(_ncmatFileRegex.findall(content))
                    break
            except OSError:
                pass
    return fname in _ncrystalStdlibFiles if _ncrystalStdlibFiles else True


def _validateNccfgFiles(cfg):
    """Pre-check that data files referenced in an NCrystal config string exist.

    NCrystal errors (e.g. NCrystal::Error::FileNotFound) cross the bare
    extern "C" ctypes wrappers and abort the whole process without any
    Python exception, so catch the most common typo class - a missing data
    file - here and raise a normal ValueError instead. Configurations which
    cannot be decided (virtual materials, plugin-provided or stdlib-embedded
    files) are always accepted.
    """
    if not isinstance(cfg, str) or '.ncmat' not in cfg:
        return
    roots = _ncrystalDataRoots()
    for match in _ncmatFileRegex.finditer(cfg):
        fname = match.group()
        prevChar = cfg[match.start() - 1] if match.start() > 0 else ''
        if prevChar and prevChar in '@:':
            continue  # @-section / virtual material scheme, not a plain file
        if _findNcmatFile(fname, roots):
            continue
        if _isNcrystalStdlibFile(os.path.basename(fname)):
            continue
        raise ValueError(
            f"Material data file '{fname}' referenced in the configuration "
            f"'{cfg}' could not be found (searched: {', '.join(roots)}). "
            "This pre-check avoids an uncatchable process abort inside "
            "NCrystal.")


# --- NCrystal cfg content pre-validation ------------------------------------
#
# Cinema's C++ core loads materials through NCrystal's C++ API whose
# exceptions cannot cross the extern "C" ctypes wrappers: they terminate the
# whole process (uncatchable SIGABRT, no traceback). The NCrystal C API
# reports errors through an error flag instead, so validating the cfg through
# it first turns content errors into normal Python exceptions. Both check
# levels are needed: ncrystal_create_info covers parsing errors (unknown
# parameter, broken NCMAT data, ...), while ncrystal_create_scatter builds
# the full scattering model - exactly what the C++ core does on acceptance -
# and also catches constraints enforced only by the model factory (e.g.
# "must set all or none of mos, dir1 and dir2 parameters"). The C++ side
# itself uses the C++ API, whose behaviour is unaffected by the error
# handler configured here.

_ncrystalCApi = None
_ncrystalCApiTried = False

# data-file cfgs that already passed the factory-level check (each check
# builds the scattering model, so cache successes to keep large assemblies
# with a shared matCfg string cheap)
_scatterValidatedCfgs = set()


def _getNcrystalCApi():
    """Bind the NCrystal C-API entry points used for validation.

    Returns a tuple (lib,) or None when the shared library cannot be located
    or lacks the C API; callers skip the content check in that case
    (fail-open, the C++ side keeps deciding).
    """
    global _ncrystalCApi, _ncrystalCApiTried
    if _ncrystalCApiTried:
        return _ncrystalCApi
    _ncrystalCApiTried = True
    try:
        candidates = [os.environ.get('NCRYSTAL_LIB'),
                      os.path.join(sys.prefix, 'lib', 'libNCrystal.so'),
                      os.path.join(sys.base_prefix, 'lib', 'libNCrystal.so')]
        ldPath = os.environ.get('LD_LIBRARY_PATH')
        if ldPath:
            candidates += [os.path.join(p, 'libNCrystal.so')
                           for p in ldPath.split(':') if p]
        lib = None
        for candidate in candidates:
            # loading the same file the C++ core already linked is a no-op
            # (dlopen returns the existing instance)
            if candidate and os.path.isfile(candidate):
                lib = ctypes.CDLL(candidate)
                break
        if lib is None:
            return None

        class NCInfo(ctypes.Structure):
            _fields_ = [('internal', ctypes.c_void_p)]

        lib.ncrystal_sethaltonerror.argtypes = [ctypes.c_int]
        lib.ncrystal_setquietonerror.argtypes = [ctypes.c_int]
        lib.ncrystal_error.restype = ctypes.c_int
        lib.ncrystal_lasterror.restype = ctypes.c_char_p
        lib.ncrystal_lasterrortype.restype = ctypes.c_char_p
        lib.ncrystal_clearerror.argtypes = []
        lib.ncrystal_create_info.argtypes = [ctypes.c_char_p]
        lib.ncrystal_create_info.restype = NCInfo
        lib.ncrystal_create_scatter.argtypes = [ctypes.c_char_p]
        lib.ncrystal_create_scatter.restype = NCInfo
        lib.ncrystal_unref.argtypes = [ctypes.c_void_p]
        # errors must set the error flag instead of aborting the process
        lib.ncrystal_sethaltonerror(0)
        lib.ncrystal_setquietonerror(1)
        _ncrystalCApi = (lib,)
    except Exception:
        _ncrystalCApi = None
    return _ncrystalCApi


def _validateNccfgContent(cfg):
    """Pre-check an NCrystal config string against the real NCrystal parser.

    Raises ValueError with the NCrystal error message on rejection. Fails
    open (no check) when the NCrystal library is unavailable.
    """
    if not isinstance(cfg, str) or not cfg:
        return
    api = _getNcrystalCApi()
    if api is None:
        return
    lib = api[0]
    try:
        cfgBytes = cfg.encode('utf-8')
    except UnicodeEncodeError:
        return
    lib.ncrystal_clearerror()
    try:
        info = lib.ncrystal_create_info(cfgBytes)
        hasError = bool(lib.ncrystal_error())
        errType, errMsg = '', ''
        if hasError:
            errType = (lib.ncrystal_lasterrortype() or b'Error').decode('utf-8', 'replace')
            errMsg = (lib.ncrystal_lasterror() or b'unknown NCrystal error').decode('utf-8', 'replace')
            lib.ncrystal_clearerror()
        else:
            # info handles are returned with an owned reference
            lib.ncrystal_unref(ctypes.addressof(info))
            # info-level parsing misses constraints enforced later by the
            # model factory, so data-file cfgs also get a trial build of the
            # scattering model (the same thing the C++ core does when it
            # accepts a cfg). Cinema-specific material families (freegas::,
            # solid::, plugin schemes) never name a data file and keep
            # failing open to the C++ side, which owns them.
            if '.ncmat' in cfg and cfg not in _scatterValidatedCfgs:
                scat = lib.ncrystal_create_scatter(cfgBytes)
                hasError = bool(lib.ncrystal_error())
                if hasError:
                    errType = (lib.ncrystal_lasterrortype() or b'Error').decode('utf-8', 'replace')
                    errMsg = (lib.ncrystal_lasterror() or b'unknown NCrystal error').decode('utf-8', 'replace')
                    lib.ncrystal_clearerror()
                elif scat.internal:
                    # unref takes the address of the handle struct (the C
                    # API invalidates it in place); it must run exactly once
                    lib.ncrystal_unref(ctypes.addressof(scat))
                    _scatterValidatedCfgs.add(cfg)
    except Exception:
        # fail-open: the C API is unusable in this process, let the C++
        # side decide (at the cost of its uncatchable abort behaviour)
        return
    if hasError:
        raise ValueError(
            f"NCrystal rejected the material config '{cfg}': "
            f"[{errType}] {errMsg.splitlines()[0] if errMsg else errMsg}. "
            "This pre-check avoids an uncatchable process abort inside "
            "NCrystal.")


# quoted nccfg part of a Material-style string
_nccfgQuoteRegex = re.compile(r"nccfg='([^']*)'")


def _validateMatCfg(cfg):
    """Validate a volume material cfg: data files and NCrystal cfg content.

    Only the NCrystal part of a `physics=ncrystal;nccfg='...'` string is
    content-checked; other physics families (e.g. idealElaScat) and raw
    compound-material cfgs are decided by the C++ side.
    """
    _validateNccfgFiles(cfg)
    if not isinstance(cfg, str):
        return
    match = _nccfgQuoteRegex.search(cfg)
    if match:
        if 'physics=ncrystal' in cfg:
            _validateNccfgContent(match.group(1))
    elif 'physics=' not in cfg:
        # no physics= key: the C++ parser falls back to treating the whole
        # string as a raw NCrystal cfg
        _validateNccfgContent(cfg)


def wrapRawNccfg(cfg):
    """Warn on (and wrap) a parameterised raw NCrystal cfg used as a material.

    A string that fails key=value parsing is applied by the C++ side as a raw
    NCrystal cfg. That form silently drops the bias options which only the
    `physics=ncrystal;nccfg='...'` form can carry, so such strings are wrapped
    with a warning. Bare raw strings (a single .ncmat file or a compound
    material like `solid::Cd/8.65gcm3`) carry no parameters and pass through
    unchanged.
    """
    if isinstance(cfg, str) and 'physics=' not in cfg and ';' in cfg:
        warnings.warn(
            f"Material configuration '{cfg}' looks like a raw NCrystal cfg. "
            "It is accepted, but the canonical matCfg is a Material-style "
            "string like physics=ncrystal;nccfg='<ncrystal cfg>'; only that "
            "form carries the bias options (scatter_bias, abs_bias, "
            "absorp_in_weight).",
            RuntimeWarning, stacklevel=3)
        return f"physics=ncrystal;nccfg='{cfg}'"
    return cfg


class Material(ConfigString):
    def __init__(self, nccfg=None) -> None:
        super().__init__()
        self.cfg_physics='ncrystal'
        _validateNccfgFiles(nccfg)
        _validateNccfgContent(nccfg)
        self.cfg_nccfg = nccfg
        self.cfg_scatter_bias = 1.
        self.cfg_abs_bias = 1.
        self.cfg_absorp_in_weight = False

    def setBiasScat(self, factor):
        self.cfg_scatter_bias = factor

    def setBiasAbsp(self, factor):
        # if self.cfg_absorp_in_weight:
        #     raise ValueError("Cannot set abs_bias when absorp_in_weight is set")
        self.cfg_abs_bias = factor

    def setAbsorpInWeight(self, enabled):
        """Set the absorption-in-weight flag.

        This is a boolean flag on the C++ side (absorp_in_weight=true/false),
        not a numeric factor: the old code truthiness-coerced any argument,
        so a "factor" of e.g. 0.5 silently enabled the flag. bools and
        numeric 0/1 are accepted; anything else raises TypeError.
        """
        if isinstance(enabled, bool):
            self.cfg_absorp_in_weight = enabled
            return
        if isinstance(enabled, numbers.Real) and float(enabled) in (0., 1.):
            self.cfg_absorp_in_weight = bool(enabled)
            return
        raise TypeError(
            f"setAbsorpInWeight expects a bool flag, got {enabled!r} "
            f"({type(enabled).__name__}). absorp_in_weight is not a numeric "
            "factor; see setBiasAbsp for weight-based absorption biasing.")

    def cfgMaterial(self, cfg):
        _validateNccfgFiles(cfg)
        _validateNccfgContent(cfg)
        self.cfg_nccfg = cfg
    
    @property
    def cfg(self):  # Update this property to include absorp_in_weight
        if self.cfg_nccfg is None:
            raise ValueError("Material config string is not set")
        
        cfg_str = f"physics={self.cfg_physics};nccfg='{self.cfg_nccfg}'"
        if self.cfg_scatter_bias != 1.:
            cfg_str += f";scatter_bias={self.cfg_scatter_bias}"
        if self.cfg_abs_bias != 1.:
            cfg_str += f";abs_bias={self.cfg_abs_bias}"
        if self.cfg_absorp_in_weight:  # Add this condition
            cfg_str += ";absorp_in_weight=true"
        
        return cfg_str


class Mirror(ConfigString):
    def __init__(self, m=1.) -> None:
        super().__init__()
        self.cfg_physics='Mirror'
        self.cfg_m = m


class DiskChopper(ConfigString):
    """Surface physics of a rotating disk chopper.

    This is the canonical DiskChopper class. The identical
    ``Cinema.Prompt.component.DiskChopper`` alias is deprecated.

    Args:
        rotFreq: Rotation frequency in Hz. Default: 25
        r: Radius of the slits (rotation axis to slit centre) in mm. Default: 100
        theta0: Angular width of each slit in deg. Default: 20
        n: Number of slits. Default: 1
        phase: Phase of the slits in deg. Default: 0
    """
    def __init__(self, rotFreq=25, r=100, theta0=20, n=1, phase=0) -> None:
        super().__init__()
        self.cfg_physics='DiskChopper'
        self.cfg_rotFreq = rotFreq
        self.cfg_r = r
        self.cfg_theta0 = theta0
        self.cfg_n = n
        self.cfg_phase = phase