
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
from ctypes import Structure, c_int32, c_uint64, POINTER, byref



_pt_makeModelCollection = importFunc('pt_makeModelCollection', type_voidp, [type_cstr] )
_pt_deleteModelCollection = importFunc('pt_deleteModelCollection', None, [type_voidp] )
_pt_ModelCollection_getxs = importFunc('pt_ModelCollection_getxs', type_dbl, [type_voidp, type_int, type_dbl] )
_pt_ModelCollection_generate = importFunc('pt_ModelCollection_generate', type_dbl, [type_voidp, type_dbl, type_dbl, type_dbl, type_dbl] )

# Checked creation bridge (0/1/2 status + pt_last_error, the protocol of the
# Launcher/Volume bridges): a rejected cfg (unknown physics= name, missing or
# unreadable nccfg file, ...) surfaces as a RuntimeError naming the offender
# instead of the C++ exception aborting the whole process. Bound defensively
# like pt_HistBase_clone in histogram/Hist.py because the symbol only exists
# in libraries rebuilt after its introduction; on a stale library the
# constructor falls back to the raw bridge above, which keeps the happy path
# working and still aborts on a rejected cfg (pinned red-until-gate in
# test_cov_compound_model.py).
try:
    _pt_makeModelCollection_checked = importFunc('pt_makeModelCollection_checked', type_int,
                                                 [type_cstr, POINTER(type_voidp)])
except AttributeError:
    _pt_makeModelCollection_checked = None

class ModelCollection:
    def __init__(self, cfg) -> None:
        if _pt_makeModelCollection_checked is not None:
            cobj = type_voidp()
            raiseOnBridgeError(
                _pt_makeModelCollection_checked(cfg.encode('utf-8'), byref(cobj)))
            self.cobj = cobj.value
        else:
            self.cobj = _pt_makeModelCollection(cfg.encode('utf-8'))

    def __del__(self):
        # nothing to free when construction failed before cobj was set
        cobj = getattr(self, 'cobj', None)
        if cobj is not None:
            _pt_deleteModelCollection(cobj)

    def xs(self, ekin, pdg=2112):
        return _pt_ModelCollection_getxs(self.cobj, pdg, ekin)

    def generate(self, ekin, dir=(0., 0., 1.)):
        """Sample one reaction at kinetic energy `ekin` (eV) along `dir`.

        Unlike xs(), generate() always performs a real sampling: internally the
        total cross section for (ekin, dir) is evaluated first, so the call is
        self-contained and no longer depends on a preceding xs() call having
        armed the cross-section cache. Returns the sampled final kinetic
        energy in eV (previously the return value was a constant 0).

        The null direction is rejected here with a ValueError: a null
        direction sent into the direction samplers makes them divide by zero
        and loop forever, and a C++ exception crossing the raw ctypes
        boundary would abort the whole process (same caveat as xs()).
        """
        if dir[0] == 0. and dir[1] == 0. and dir[2] == 0.:
            raise ValueError('null incident direction: the direction samplers '
                             'would divide by zero and loop forever')
        return _pt_ModelCollection_generate(self.cobj, ekin,
                                            float(dir[0]), float(dir[1]), float(dir[2]))
