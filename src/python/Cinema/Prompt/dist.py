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

from Cinema.Interface import *
import numpy as np

_pt_PointwiseDist_new = importFunc(
    "pt_PointwiseDist_new", 
    type_voidp, 
    [type_npdbl1d, type_npdbl1d, type_sizet]
)

_pt_PointwiseDist_delete = importFunc(
    "pt_PointwiseDist_delete",  
    None, 
    [type_voidp]
)

_pt_PointwiseDist_percentile = importFunc(
    "pt_PointwiseDist_percentile",  
    type_dbl, 
    [type_voidp, type_dbl]
)   

_pt_PointwiseDist_percentile_many = importFunc(
    "pt_PointwiseDist_percentile_many",  
    None, 
    [type_voidp, type_npdbl1d, type_npdbl1d, type_sizet]
)

class PointwiseDist:
    def __init__(self, x: np.ndarray, y: np.ndarray):   
        xview = np.asarray(x, dtype=np.float64)
        yview = np.asarray(y, dtype=np.float64)
        if xview.ndim != 1 or yview.ndim != 1: 
            raise ValueError("x and y must be 1D arrays.")
        if xview.size != yview.size:
            raise ValueError("x and y must have the same length.")
        self._obj = _pt_PointwiseDist_new(
           xview, 
           yview, 
           xview.size)

    def __del__(self):
        if hasattr(self, "_obj") and self._obj:
            _pt_PointwiseDist_delete(self._obj)
            self._obj = None

    def percentile(self, p):
        if isinstance(p, float):
            if not (0.0 <= p <= 1.0):
                raise ValueError("p must be in [0, 1].")
            return _pt_PointwiseDist_percentile(self._obj, p)   
        if isinstance(p, (list, np.ndarray)):
            pview = np.asarray(p, dtype=np.float64)
            if pview.ndim != 1:
                raise ValueError("p must be a 1D array.")
            out = np.empty_like(pview)
            _pt_PointwiseDist_percentile_many(
                self._obj,
                pview,
                out,
                pview.size)
            return out