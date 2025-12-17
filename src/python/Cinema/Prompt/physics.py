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

from .configstr import ConfigString

class Material(ConfigString):
    def __init__(self, nccfg=None) -> None:
        super().__init__()
        self.cfg_physics='ncrystal'
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

    def setAbsorpInWeight(self, factor):  
        self.cfg_absorp_in_weight = factor

    def cfgMaterial(self, cfg):
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
    def __init__(self, rotFreq, r, theta0, n, phase) -> None:
        super().__init__()
        self.cfg_physics='DiskChopper'
        self.cfg_rotFreq = rotFreq 
        self.cfg_r = r
        self.cfg_theta0 = theta0
        self.cfg_n = n
        self.cfg_phase = phase