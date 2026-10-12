#!/usr/bin/env python3

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


from ..Interface import *

import os
import warnings

_pt_Gidi_compiled = importFunc('pt_Gidi_compiled', type_bool, [])
_pt_GidiSetting_getInstance = importFunc('pt_GidiSetting_getInstance', type_voidp, [] )

_pt_GidiSetting_getGidiThreshold = importFunc('pt_GidiSetting_getGidiThreshold', type_dbl, [type_voidp] )
_pt_GidiSetting_setGidiThreshold = importFunc('pt_GidiSetting_setGidiThreshold', None, [type_voidp, type_dbl] )

_pt_GidiSetting_getGidiPops = importFunc('pt_GidiSetting_getGidiPops', type_cstr, [type_voidp] )
_pt_GidiSetting_setGidiPops = importFunc('pt_GidiSetting_setGidiPops', None, [type_voidp, type_cstr] )

_pt_GidiSetting_getGidiMap = importFunc('pt_GidiSetting_getGidiMap', type_cstr, [type_voidp] )
_pt_GidiSetting_setGidiMap = importFunc('pt_GidiSetting_setGidiMap', None, [type_voidp, type_cstr] )

_pt_GidiSetting_getEnableGidi = importFunc('pt_GidiSetting_getEnableGidi', type_bool, [type_voidp] )
_pt_GidiSetting_setEnableGidi = importFunc('pt_GidiSetting_setEnableGidi', None, [type_voidp, type_bool] )

_pt_GidiSetting_getEnableGidiPowerIteration = importFunc('pt_GidiSetting_getEnableGidiPowerIteration', type_bool, [type_voidp] )
_pt_GidiSetting_setEnableGidiPowerIteration = importFunc('pt_GidiSetting_setEnableGidiPowerIteration', None, [type_voidp, type_bool] )

_pt_GidiSetting_getGammaTransport = importFunc('pt_GidiSetting_getGammaTransport', type_bool, [type_voidp] )
_pt_GidiSetting_setGammaTransport = importFunc('pt_GidiSetting_setGammaTransport', type_bool, [type_voidp, type_bool] )


@singleton
class GidiSetting():
    # Introspection mirror of the C++ constructor defaults (PTGidiSetting.cc,
    # the single source of truth) for use with defaults(). The default
    # pops/map data roots are install-dependent, so they are read from the
    # live setting instead of being mirrored here.
    _DEFAULTS = {'enable': False, 'threshold': 5.0,
                 'sampleNonTransportingParticles': True,
                 'gammaTransport': False, 'powerIteration': False}

    def __init__(self):
        self.cobj = _pt_GidiSetting_getInstance()
        self.isCompiled = _pt_Gidi_compiled()

    # ---- P2.3 front-end API -------------------------------------------------
    # The default path of a simulation never touches anything below: a user
    # who never enables gidi stays completely unaware of it (no data probing,
    # no warnings), whether or not gidi was compiled in and data is present.
    # Compiled-in is not the same as runtime-usable: only available() answers
    # the data question, and only when explicitly called.

    def available(self):
        """True when gidi can actually run in this process: compiled in AND
        the configured data files (pops database, map) exist and are readable.

        Explicit introspection only — calling this never enables anything.
        The recommended pattern for optional use:

            gidi = GidiSetting()
            if gidi.available():
                gidi.enable()
        """
        if not self.isCompiled:
            return False
        return all(os.path.isfile(p) and os.access(p, os.R_OK)
                   for p in (self.getGidiPops(), self.getGidiMap()))

    def enable(self):
        """Turn gidi on, with an explicit contract (P2.4): the request must be
        honourable or loudly refused, never silently degraded.

        - gidi not compiled into this build: a RuntimeWarning says so (the
          enable flag is still set, but nothing will use it).
        - compiled, but the data files are missing/unreadable: ValueError
          with the current data root and how to point at another one.
        - otherwise: exactly setEnableGidi(True).
        """
        if not self.isCompiled:
            warnings.warn(
                "gidi.enable(): gidi is NOT compiled into this cinema build "
                "(built without --enablegidi). The flag is set but no gidi "
                "physics will run; rebuild with --enablegidi to use it.",
                RuntimeWarning, stacklevel=2)
        elif not self.available():
            pops, gmap = self.getGidiPops(), self.getGidiMap()
            raise ValueError(
                "gidi.enable(): the gidi data files are missing or unreadable, "
                f"pops: '{pops}', map: '{gmap}'. Install the gidi data package "
                "under the cinema data path, or point at an existing one with "
                "GidiSetting().setGidiPops(...) / .setGidiMap(...) before "
                "enabling. Check availability with GidiSetting().available().")
        self.setEnableGidi(True)

    def disable(self):
        """Turn gidi off (alias of setEnableGidi(False))."""
        self.setEnableGidi(False)

    def defaults(self):
        """Introspection: the default gidi settings this build ships with.

        The scalar defaults mirror the C++ constructor (PTGidiSetting.cc);
        the data roots are the ones this installation resolves to. Existing
        settings are not modified.
        """
        out = dict(self._DEFAULTS)
        out['pops'] = self.getGidiPops()
        out['map'] = self.getGidiMap()
        return out

    # ---- raw bindings (stable aliases, kept for the existing scripts) ------

    def getGidiThreshold(self):
        return _pt_GidiSetting_getGidiThreshold(self.cobj)
    
    def setGidiThreshold(self, t):
        _pt_GidiSetting_setGidiThreshold(self.cobj, t)

    # fixme: backslash in the path can not be decoded!
    def getGidiPops(self):
        return _pt_GidiSetting_getGidiPops(self.cobj).decode('utf-8')
    
    def setGidiPops(self, s):
        _pt_GidiSetting_setGidiPops(self.cobj, s.encode('utf-8'))

    def getGidiMap(self):
        return _pt_GidiSetting_getGidiMap(self.cobj).decode('utf-8')
    
    def setGidiMap(self, s):
        _pt_GidiSetting_setGidiMap(self.cobj, s.encode('utf-8'))

    def getEnableGidi(self):
        return _pt_GidiSetting_getEnableGidi(self.cobj)
    
    def setEnableGidi(self, b):
        _pt_GidiSetting_setEnableGidi(self.cobj, b)

    def getEnableGidiPowerIteration(self):
        return _pt_GidiSetting_getEnableGidiPowerIteration(self.cobj)
    
    def setEnableGidiPowerIteration(self, b):
        _pt_GidiSetting_setEnableGidiPowerIteration(self.cobj, b)
    
    def getGammaTransport(self):
        return _pt_GidiSetting_getGammaTransport(self.cobj)
    
    def setGammaTransport(self, b):
        _pt_GidiSetting_setGammaTransport(self.cobj, b)