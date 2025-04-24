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


from ..Interface import *

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
    def __init__(self):
        self.cobj = _pt_GidiSetting_getInstance()
        self.isCompiled = _pt_Gidi_compiled()

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