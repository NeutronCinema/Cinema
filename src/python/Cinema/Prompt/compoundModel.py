
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
from ctypes import Structure, c_int32, c_uint64



_pt_makeModelCollection = importFunc('pt_makeModelCollection', type_voidp, [type_cstr] )
_pt_deleteModelCollection = importFunc('pt_deleteModelCollection', None, [type_voidp] )
_pt_ModelCollection_getxs = importFunc('pt_ModelCollection_getxs', type_dbl, [type_voidp, type_int, type_dbl] )
_pt_ModelCollection_generate = importFunc('pt_ModelCollection_generate', type_dbl, [type_voidp, type_dbl] )

class ModelCollection:
    def __init__(self, cfg) -> None:
        self.cobj = _pt_makeModelCollection(cfg.encode('utf-8')) 

    def __del__(self):
        _pt_deleteModelCollection(self.cobj)
    
    def xs(self, ekin, pdg=2112):
        return _pt_ModelCollection_getxs(self.cobj, pdg, ekin)

    def generate(self, ekin):
        return _pt_ModelCollection_generate(self.cobj, ekin)
