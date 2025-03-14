
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
from .solid import Box

from .configstr import ConfigString

class Scorer(ConfigString):
    pass

class PSD(ConfigString):
    def __init__(self) -> None:
        super().__init__()
        self.cfg_Scorer='PSD'
        self.cfg_name = 'PSD'
        self.cfg_xmin = -1.
        self.cfg_xmax = 1.
        self.cfg_numbin_x = 10 
        self.cfg_ymin = -1.
        self.cfg_ymax = 1.
        self.cfg_numbin_y = 10 
        self.cfg_ptstate = 'ENTRY' 
        self.cfg_type = 'XZ'

class WlSpectrum(ConfigString):
    def __init__(self) -> None:
        super().__init__()
        self.cfg_Scorer='WlSpectrum'
        self.cfg_name = 'WlSpectrum'
        self.cfg_min = 0.0
        self.cfg_max = 5
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'

class ESpectrum(ConfigString):
    def __init__(self) -> None:
        super().__init__()
        self.cfg_Scorer='ESpectrum'
        self.cfg_name = 'ESpectrum'
        self.cfg_scoreTransfer = 0
        self.cfg_min = 1e-5
        self.cfg_max = 0.25
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'

class TOF(ConfigString):
    def __init__(self) -> None:
        super().__init__()
        self.cfg_Scorer='TOF'
        self.cfg_name = 'TOF'
        self.cfg_min = 0.0025
        self.cfg_max = 0.008
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'

class VolFluence(ConfigString):
    def __init__(self) -> None:
        super().__init__()
        self.cfg_Scorer='VolFluence'
        self.cfg_name = 'VolFluence'
        self.cfg_min = 0
        self.cfg_max = 1
        self.cfg_numbin = 100
        self.cfg_ptstate = 'ENTRY'
        self.cfg_linear = 'yes'

# FIXME: scorer object construction moves from strings to ctype
# the following class name move to *V1
class ScorerHelperV1:
    def __init__(self, name, min, max, numbin, ptstate) -> None:
        self.name = name
        self.min = min
        self.max = max
        self.numbin = numbin
        self.ptstate = ptstate

    def __realinit(self):
        self.score.cfg_name = self.name
        self.score.cfg_min = self.min
        self.score.cfg_max = self.max
        self.score.cfg_numbin = self.numbin
        self.score.cfg_ptstate = self.ptstate
        
    def make(self, vol):
        vol.addScorer(self.score.cfg)

class ESpectrumHelperV1(ScorerHelperV1): 
    def __init__(self, name, min=1e-5, max=1, numbin = 100, ptstate: str = 'ENTRY', energyTransfer=False) -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = ESpectrum()
        if energyTransfer:
            self.score.cfg_scoreTransfer = 1
        else:
            self.score.cfg_scoreTransfer = 0
        self._ScorerHelperV1__realinit()
    
class WlSpectrumHelperV1(ScorerHelperV1): 
    def __init__(self, name, min=0.1, max=10, numbin = 100, ptstate: str = 'ENTRY') -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = WlSpectrum()
        self._ScorerHelperV1__realinit()
    
class TOFHelperV1(ScorerHelperV1): 
    def __init__(self, name, min=0, max=40e-3, numbin = 100, ptstate: str = 'ENTRY') -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = TOF()
        self._ScorerHelperV1__realinit()

class VolFluenceHelperV1(ScorerHelperV1): 
    def __init__(self, name, min=1e-6, max=10, numbin = 100, ptstate: str = 'PEA_PRE', linear = False) -> None:
        super().__init__(name, min, max, numbin, ptstate)
        self.score = VolFluence()
        if linear:
            self.score.cfg_linear = 'yes'
        else: 
            self.score.cfg_linear = 'no'
        self._ScorerHelperV1__realinit()


# DepositionHelper is a special class that skipped the traditional string based initialisation.
# A C++ object is directly created in  
from ..Interface import *
_pt_ScorerDeposition_new = importFunc('pt_ScorerDeposition_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_bool, type_int])
_pt_ScorerESpectrum_new = importFunc('pt_ScorerESpectrum_new', type_voidp, [type_cstr, type_bool, type_dbl, type_dbl, type_uint, type_uint, type_int, type_int, type_bool ])
_pt_ScorerTOF_new = importFunc('pt_ScorerTOF_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_int ])
_pt_ScorerWlSpectrum_new = importFunc('pt_ScorerWlSpectrum_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int, type_int ])
_pt_ScorerVolFluence_new = importFunc('pt_ScorerVolFluence_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_dbl, type_uint, type_int, type_bool, type_int])
_pt_ScorerDeltaMomentum_new = importFunc('pt_ScorerDeltaMomentum_new',type_voidp, [type_cstr, type_dbl, type_dbl, type_dbl, type_uint,
                                                                                   type_uint, type_dbl, type_dbl, type_dbl, 
                                                                                   type_dbl, type_dbl, type_dbl, type_int, type_int, type_bool])
_pt_ScorerMultiScat_new = importFunc('pt_ScorerMultiScat_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, type_uint, type_int])
_pt_ScorerDirectSqw_new = importFunc('pt_ScorerDirectSqw_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint, 
                                                                            type_dbl, type_dbl, type_uint,
                                                                            type_uint, type_int, type_dbl, type_dbl,
                                                                            type_dbl, type_dbl, type_dbl,
                                                                            type_dbl, type_dbl, type_dbl, type_int, type_bool])
_pt_ScorerPSD_new = importFunc('pt_ScorerPSD_new', type_voidp, [type_cstr, type_dbl, type_dbl, type_uint,
                                                                type_dbl, type_dbl, type_uint,
                                                                type_uint, type_int, type_int, type_int, type_bool])

_pt_addMultiScatter1D = importFunc('pt_addMultiScatter1D', None, [type_voidp, type_voidp, type_int])
_pt_addMultiScatter2D = importFunc('pt_addMultiScatter2D', None, [type_voidp, type_voidp, type_int])

_pt_KillerMCPL_new = importFunc('pt_KillerMCPL_new', type_voidp, [type_cstr, type_uint, type_int])
class ScorerHelper:
    def __init__(self, name, min, max, numbin, pdg = 2112, ptstate = 'ENTRY', groupID=0) -> None:
        self.name = name
        self.min = min
        self.max = max
        self.numbin = numbin
        self.pdg = pdg
        self.ptstate = ptstate
        self.groupID = groupID
        self.linear = True

    def __realinit(self):
        self.score.cfg_name = self.name
        self.score.cfg_min = self.min
        self.score.cfg_max = self.max
        self.score.cfg_numbin = self.numbin
        self.score.cfg_ptstate = self.ptstate

    @property
    def ptsNum(self):
        """Enum of particle tracing state.
        """
        if self.ptstate=='SURFACE':
            return 0
        elif self.ptstate=='ENTRY':
            return 1
        elif self.ptstate=='PROPAGATE_PRE':
            return 2
        elif self.ptstate=='PROPAGATE_POST':
            return 3
        elif self.ptstate=='EXIT':
            return 4
        elif self.ptstate=='PEA_PRE':
            return 5
        elif self.ptstate=='PEA_POST':
            return 6
        elif self.ptstate=='ABSORB':
            return 7
        else:
            raise RuntimeError(f'Scorer type {self.ptstate} is undefined.') 
        
    def make(self, vol):
        vol.addScorer(self.score.cfg)

class ScorerHelper2D(ScorerHelper):
    def __init__(self, name, xmin, xmax, xnumbin, ymin, ymax, ynumbin, pdg = 2112, ptstate = 'ENTRY', groupID=0) -> None:
        super().__init__(name, xmin, xmax, xnumbin, pdg, ptstate, groupID)
        self.ymin = ymin
        self.ymax = ymax
        self.ynumbin = ynumbin

class MultiScatMixin1D():
    def __init__(self) -> None:
        pass

    def addScatterCounter(self, scatterCounter, scatterNumberRequired):
        _pt_addMultiScatter1D(scatterCounter.cobj, self.cobj, scatterNumberRequired)

class MultiScatMixin2D():
    def __init__(self) -> None:
        pass

    def addScatterCounter(self, scatterCounter, scatterNumberRequired):
        _pt_addMultiScatter2D(scatterCounter.cobj, self.cobj, scatterNumberRequired)

# Counter 
class MultiScatCounter(ScorerHelper):
    def __init__(self) -> None:
        super().__init__(name="ScatterCounter", min=0., max=1., numbin=1, pdg=2112, groupID=0)

    def make(self, vol):
        cobj = _pt_ScorerMultiScat_new(self.name.encode('utf-8'), 
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.groupID)
        vol.addScorer(self, cobj)
        self.cobj = cobj
        
# 1D Scorer
class ESpectrumHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name, min=1e-5, max=1, numbin = 100, pdg : int = 2112, 
                 ptstate: str = 'ENTRY', energyTransfer=False, groupID=0, linear = False) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)
        self.energyTransfer = energyTransfer
        self.linear = linear

    def make(self, vol):
        cobj = _pt_ScorerESpectrum_new(self.name.encode('utf-8'), 
                                        self.energyTransfer,
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.groupID,
                                        self.linear
                                        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

     
    
class WlSpectrumHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name, min=0.1, max=10, numbin = 100, pdg : int = 2112, ptstate : str = 'ENTRY', groupID : int = 0) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)

    def make(self, vol):
        cobj = _pt_ScorerWlSpectrum_new(self.name.encode('utf-8'), 
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.groupID
                                        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

class VolFluenceHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name, min = 1e-6, max = 10, numbin = 100, pdg = 2112, linear : bool = False, groupID : int = 0) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate = 'PEA_PRE', groupID = groupID)
        self.linear = linear

    def make(self, vol):
        volCapacity = vol.getCapacity()
        cobj = _pt_ScorerVolFluence_new(
            self.name.encode('utf-8'), 
            self.min,
            self.max,
            self.numbin,
            volCapacity,
            self.pdg,
            self.ptsNum,
            self.linear,
            self.groupID
        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

class DirectSqHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name, qmin, qmax, numbin, distanceMS, pdg=2112, 
                 refDir=[0,0,1], samplePos=[0,0,0], ptstate='ENTRY', method=0, linear=False, groupID=0):
        super().__init__(name, qmin, qmax, numbin, pdg, ptstate, groupID)
        self.distanceMS = distanceMS
        self.refDir = refDir
        self.samplePos = samplePos
        self.method = method
        self.linear = linear

    def make(self, vol):
        cobj = _pt_ScorerDeltaMomentum_new(
            self.name.encode('utf-8'),
            self.distanceMS,
            self.min,
            self.max,
            self.numbin,
            self.pdg,
            self.refDir[0],
            self.refDir[1],
            self.refDir[2],
            self.samplePos[0],
            self.samplePos[1],
            self.samplePos[2],
            self.ptsNum,
            self.method,
            self.linear
        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

class DepositionHelper(ScorerHelper, MultiScatMixin1D):
    def __init__(self, name : str, min, max, numbin, pdg, ptstate, linear : bool = False, groupID : int = 0) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)
        self.linear = linear

    def make(self, vol):
        # enum class ScorerType {SURFACE, ENTRY, PROPAGATE, EXIT, PEA, ABSORB};
        cobj = _pt_ScorerDeposition_new(self.name.encode('utf-8'), 
                                        self.min,
                                        self.max,
                                        self.numbin,
                                        self.pdg,
                                        self.ptsNum,
                                        self.linear,
                                        self.groupID)
        vol.addScorer(self, cobj)
        self.cobj = cobj


    # ScorerDirectSqw(const std::string &name, double qmin, double qmax, unsigned xbin,
    #   double ekinmin, double ekinmax, unsigned nybins,
    #   unsigned int pdg, int group_id,
    #   double mod_smp_dist, double mean_ekin, const Vector& mean_incident_dir, const Vector& sample_position, 
    #   ScorerType stype=Scorer::ScorerType::ENTRY);


class TOFHelper(ScorerHelper, MultiScatMixin2D):
    def __init__(self, name : str, min : float = 0., max : float = 40e-3, numbin : int = 100, 
                 pdg : int = 2112, ptstate : str = 'ENTRY', groupID : int = 0) -> None:
        super().__init__(name, min, max, numbin, pdg, ptstate, groupID)

    def make(self, vol):
        cobj = _pt_ScorerTOF_new(self.name.encode('utf-8'),
                                 self.min,
                                 self.max,
                                 self.numbin,
                                 self.pdg,
                                 self.ptsNum,
                                 self.groupID)
        vol.addScorer(self, cobj)
        self.cobj = cobj


# 2D Scorer
class PSDHelper(ScorerHelper2D, MultiScatMixin2D):
    def __init__(self, name, xmin=-10., xmax=10., xnumbin=100, 
                 ymin=-10, ymax=10, ynumbin=100, pdg=2112, 
                 ptstate='ENTRY', psdtype='XY', groupID=0, isGlobal = False) -> None:
        super().__init__(name, xmin, xmax, xnumbin, 
                         ymin, ymax, ynumbin, pdg, ptstate, groupID)
        self.psdtype = psdtype
        self.isGlobal = isGlobal

    @property
    def psdTypeNum(self):
        if self.psdtype=='XY':
            return 0
        elif self.psdtype=='XZ':
            return 1
        elif self.psdtype=='YZ':
            return 2
        else:
            raise RuntimeError(f'PSD type {self.psdtype} is undefined.') 

    def make(self, vol):
        cobj = _pt_ScorerPSD_new(self.name.encode('utf-8'),
                                 self.min,
                                 self.max,
                                 self.numbin,
                                 self.ymin,
                                 self.ymax,
                                 self.ynumbin,
                                 self.pdg,
                                 self.ptsNum,
                                 self.psdTypeNum,
                                 self.groupID,
                                 self.isGlobal)
        vol.addScorer(self, cobj)
        self.cobj = cobj

class DirectSqwHelper(ScorerHelper2D, MultiScatMixin2D):
    def __init__(self, name, mod_smp_dist, mean_ekin, mean_incident_dir=np.array([0,0,1]), sample_position=np.array([0,0,0]),
                 qmin = 1e-1, qmax = 10, num_qbin = 50, 
                 ekinmin=-0.1 , ekinmax=0.1,  num_ebin = 30,
                 pdg = 2112, groupID  = 0, logx=False, ptstate = 'ENTRY') -> None:
        super().__init__(name, qmin, qmax, num_qbin, ekinmin, ekinmax, num_ebin, pdg, ptstate, groupID)
        self.mod_smp_dist = mod_smp_dist
        self.mean_ekin = mean_ekin
        self.mean_incident_dir = mean_incident_dir
        self.sample_position = sample_position
        self.logx = logx

    def make(self, vol):
        cobj = _pt_ScorerDirectSqw_new(
            self.name.encode('utf-8'), 
            self.min, self.max, self.numbin,
            self.ymin, self.ymax, self.ynumbin,
            self.pdg, self.groupID,
            self.mod_smp_dist, self.mean_ekin,
            self.mean_incident_dir[0], self.mean_incident_dir[1], self.mean_incident_dir[2],
            self.sample_position[0], self.sample_position[1], self.sample_position[2],
            self.ptsNum, self.logx
        )
        vol.addScorer(self, cobj)
        self.cobj = cobj


# fixme: what is the function followed used for??? x.
def makePSD(name, vol, numbin_dim1=1, numbin_dim2=1, ptstate : str = 'ENTRY', type : str = 'XY'):
    if not isinstance(vol.solid, Box):
        raise TypeError('makePSD only used for "Box" type volume')
    det = PSD()
    det.cfg_name = name
    det.cfg_numbin_x = numbin_dim1 
    det.cfg_numbin_y = numbin_dim2 
    det.cfg_ptstate = ptstate
    det.cfg_type = type
    if type == 'XY':
        det.cfg_xmin = -vol.solid.hx
        det.cfg_xmax = vol.solid.hx
        det.cfg_ymin = -vol.solid.hy
        det.cfg_ymax = vol.solid.hy
    elif type == 'XZ':
        det.cfg_xmin = -vol.solid.hx
        det.cfg_xmax = vol.solid.hx
        det.cfg_ymin = -vol.solid.hz
        det.cfg_ymax = vol.solid.hz
    elif type == 'YZ':
        det.cfg_xmin = -vol.solid.hy
        det.cfg_xmax = vol.solid.hy
        det.cfg_ymin = -vol.solid.hz
        det.cfg_ymax = vol.solid.hz
    vol.addScorer(det.cfg)

        
class KillMCPLHelper(MultiScatMixin1D):
    def __init__(self, name, pdg : int = 0, groupID : int = 0) -> None:
        def get_rank_id():
            try:
                # Initialize the MPI environment
                from mpi4py import MPI
                comm = MPI.COMM_WORLD
                rank = comm.Get_rank()
                return rank
            except:
                return None
        
        process_id = get_rank_id()

        if process_id is None:
            self.use_mpi=False
        else:
            self.use_mpi=True
            self.name_mpi = name+f'_pro{process_id}' 

        self.name = name
        self.pdg = pdg 
        self.groupID = groupID

    def make(self, vol):
        cobj = _pt_KillerMCPL_new(self.name_mpi.encode('utf-8') if self.use_mpi else self.name.encode('utf-8'), 
                                        self.pdg,
                                        self.groupID
                                        )
        vol.addScorer(self, cobj)
        self.cobj = cobj

