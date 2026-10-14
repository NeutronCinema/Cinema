
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

# _pt_call_python_method = importFunc('pt_call_python_method', type_pyobject, [type_pyobject, type_cstr])

# def call_python_method(obj, name):
#     return _pt_call_python_method(obj, name.encode('utf-8'))

_pt_nccalNumDensity = importFunc('pt_nccalNumDensity', type_dbl, [type_cstr] )

def nccalNumDensity(s):
    return _pt_nccalNumDensity(s.encode('utf-8'))