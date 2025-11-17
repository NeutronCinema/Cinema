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


class ConfigString(dict):
    """
    A dictionary subclass that provides attribute-style access to configuration items.
        
    Examples:
        >>> config = ConfigString()
        >>> config.cfg_name = 'quantity'
        >>> config.cfg_value = 100
        >>> print(config.cfg)  # Output: 'name=quantity;value=100;'
        >>> print(config.cfg_name)  # Output: 'quantity'
    """
    
    # Enable attribute-style access to dictionary items
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def makeCfg(self):     
        """
        Generate a configuration string from items with 'cfg_' prefix.
        
        Returns:
            str: A semicolon-separated configuration string
            
        Examples:
            >>> config = ConfigString()
            >>> config.cfg_name = 'quantity'
            >>> config.cfg_value = 100
            >>> config.makeCfg()  # Returns: 'name=quantity;value=100;'
        """
        cfg = ''
        for k, v in self.items():
            if k.__contains__('cfg_'):
                if v is None:
                    raise RuntimeError(f'{self}. value for {k} is None. ')
                cfg += k.replace('cfg_','') 
                cfg += '='
                cfg += str(v)
                cfg += ';'
        return cfg
    
    @property
    def cfg(self) -> str: 
        """
        Property that returns the configuration string.

        Examples:
            >>> 'name=quantity;value=100;'
        """
        return self.makeCfg()