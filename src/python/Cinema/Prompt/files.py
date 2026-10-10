
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

_pt_MCPLBinaryWrite_new = importFunc('pt_MCPLBinaryWrite_new', type_voidp, [type_cstr, type_bool, type_bool, type_bool] )
_pt_MCPLBinaryWrite_delete = importFunc('pt_MCPLBinaryWrite_delete', type_voidp, [type_voidp] )
_pt_MCPLBinaryWrite_close = importFunc('pt_MCPLBinaryWrite_close', None, [type_voidp] )

# mcpl definition of mcpl_particle_t
#   typedef struct {
#     double ekin;            /* kinetic energy [MeV]             */
#     double polarisation[3]; /* polarisation vector              */
#     double position[3];     /* position [cm]                    */
#     double direction[3];    /* momentum direction (unit vector) */
#     double time;            /* time-stamp [millisecond]         */
#     double weight;          /* weight or intensity              */
#     int32_t pdgcode;    /* MC particle number from the Particle Data Group (2112=neutron, 22=gamma, ...)        */
#     uint32_t userflags; /* User flags (if used, the file header should probably contain information about how). */
#   } mcpl_particle_t;



class MCPLParticle(Structure):
    _fields_ = [("ekin", type_dbl),
                ("polarisation_x", type_dbl), ("polarisation_y", type_dbl), ("polarisation_z", type_dbl),
                ("position_x", type_dbl), ("position_y", type_dbl), ("position_z", type_dbl),
                ("direction_x", type_dbl,), ("direction_y", type_dbl), ("direction_z", type_dbl),
                ("time", type_dbl),
                ("weight", type_dbl),
                ("pdgcode", c_int32),
                ("userflags", c_uint64)]
    
    def __repr__(self):
        return f'ekin {self.ekin}, polarisation_x {self.polarisation_x}, polarisation_y {self.polarisation_y}, polarisation_z {self.polarisation_z}, position_x {self.position_x}, position_y {self.position_y}, position_z {self.position_z}, direction_x {self.direction_x}, direction_y {self.direction_y}, direction_z {self.direction_z}, time {self.time}, weight {self.weight}, pdgcode {self.pdgcode}, userflags {self.userflags}'


_pt_MCPLBinaryWrite_write = importFunc('pt_MCPLBinaryWrite_write', type_voidp, [type_voidp, ctypes.POINTER(MCPLParticle)] )
_pt_MCPLBinaryRead_read = importFunc('pt_MCPLBinaryWrite_write', ctypes.POINTER(MCPLParticle), [type_voidp] )


class MCPLBinaryWrite:
    def __init__(self, fn, enable_double=False, enable_extra3double=False, 
                enable_extraUnsigned=False) -> None:
        self.cobj = _pt_MCPLBinaryWrite_new(fn.encode('utf-8'), enable_double, enable_extra3double, enable_extraUnsigned )

    def __del__(self):
        _pt_MCPLBinaryWrite_delete(self.cobj)
    
    def write(self, par : MCPLParticle):
        _pt_MCPLBinaryWrite_write(self.cobj, par)

    def close(self):
        _pt_MCPLBinaryWrite_close(self.cobj)