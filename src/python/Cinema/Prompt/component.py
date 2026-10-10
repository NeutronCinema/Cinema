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

import warnings

import numpy as np

from Cinema.Prompt.geo import Transformation3D
from .solid import Trapezoid, Tube, Box
from .geo import Volume, Transformation3D
from copy import deepcopy
from scipy.spatial.transform import Rotation as scipyRot
from .physics import DiskChopper as _DiskChopper

class DiskChopper(_DiskChopper):
    """Deprecated alias of :class:`Cinema.Prompt.physics.DiskChopper`.

    Kept as a working alias: it produces byte-identical configuration
    strings and shares the same C++ physics.
    """
    def __init__(self) -> None:
        warnings.warn("Cinema.Prompt.component.DiskChopper is deprecated, "
                      "use Cinema.Prompt.physics.DiskChopper instead.",
                      DeprecationWarning, stacklevel=2)
        super().__init__()


class Anchor:
    
    def __init__(self, refFrame = None, marker = '') -> None:
        '''
        An anchor is a point with spacial coordinates and reference frame.
        '''
        if refFrame == None:
            refFrame = Transformation3D()
        self.refFrame = refFrame
        self.marker = marker

    def setMarker(self, marker : str):
        self.marker = marker

    def setRefFrame(self, refFrame : Transformation3D):
        self.refFrame = deepcopy(refFrame)

    def getRelTransf(self, other):
        """Return the relative transformation from 'self' to 'other'.

        The returned Anchor's reference frame maps points from 'other's
        frame into 'self's frame: p_self = R_rel p + t_rel with
        R_rel = R_self^-1 R_other and t_rel = R_self^-1 (t_other - t_self).

        Args:
            other (Anchor): Target anchor

        Returns:
            Anchor: Anchor holding the relative transformation
        """
        sR = self.refFrame.getRotMatrix()
        oR = other.refFrame.getRotMatrix()
        sT = self.refFrame.getTranslation()
        oT = other.refFrame.getTranslation()
        sRinv = np.linalg.inv(sR)
        relT = sRinv.dot(oT - sT)
        rel = Transformation3D(relT[0], relT[1], relT[2])
        rel.applyRotbyMatrix(sRinv.dot(oR))
        transf = Anchor()
        transf.setRefFrame(rel)
        return transf
    
    # fixme: add inverse of Transformation 
    # fixme: add refresh of all members' anchor
    # def transform(self, frame: Transformation3D):
    #     self.refFrame = self.refFrame * frame

class Array(Anchor):

    def __init__(self, refFrame = Transformation3D(), marker = '') -> None:
        super().__init__(refFrame, marker)
        self.members = []

    def setMemberMarker(self):
        for i_mem in self.members:
            i_mem.setMarker(f'{self.marker}|{i_mem.marker}')
    
    def setAnchor(self, refFrame : Transformation3D):
        self.refFrame = refFrame
        for mem in self.members:
            mem.refFrame = self.refFrame * mem.refFrame

    # def getRelativeRefFrame(self):
    #     ancList = []
    #     for mem in self.members:
    #         anc = self.getRelTransf(mem)
    #         ancList.append(anc)
    #     return ancList    

class EntityArray(Array):

    def __init__(self, element, refFrame = Transformation3D(), marker = 'Entity'):
        super().__init__(refFrame, marker)
        self.element = element
        if hasattr(self.element, 'marker'):
            self.marker = self.marker + '|' + self.element.marker
        self.eleAncs = []
        
    def __check(self):
        if not isinstance(self.element, Volume):
            raise TypeError("Object type f{self.element.__class__.__name__} do not match type 'Volume'!")
    
    def selectByZ(self, zMin, zMax):
        # members are Anchors: read the placement through the frame accessor
        # (Anchors have no .translation attribute)
        toRemove = []
        for i_mem, member in enumerate(self.members):
            loc = member.refFrame.getTranslation()
            if loc[2] < zMin or loc[2] > zMax:
                toRemove.append(i_mem)
        for i_mem in reversed(toRemove):
            self.members.pop(i_mem)

    def setAnchor(self, refFrame : Transformation3D):
        super().setAnchor(refFrame)
        for eleAnc in self.eleAncs:
            eleAnc[1].refFrame = self.refFrame * eleAnc[1].refFrame

    def make(self):
        anc = Anchor()
        if isinstance(self.element, Volume):
            anc.setRefFrame(Transformation3D())
        else:
            anc.setRefFrame(self.element.refFrame)
        self.eleAncs.append((self.element, anc))
        self.members.append(anc)
    
    def create(self, transf):
        anc = Anchor()
        anc.setRefFrame(transf)
        self.eleAncs.append((self.element, anc))
        self.members.append(anc)
        self.setMemberMarker()

    def repeat(self, direction = [0, 0, 1], gap = 1000., num = 1):
        new_anchors = []
        for i_anc in self.members:
            origin_transf = deepcopy(i_anc.refFrame)
            for i_num in np.arange(1, num):
                off = gap * i_num
                new_anc = Transformation3D(direction[0] * off, direction[1] * off, direction[2] * off) * origin_transf
                new_anchors.append(new_anc)
        for i_new_anc in new_anchors:
            self.create(i_new_anc)

    def reflect(self, plane = 'XY', plane_location = 0.):
        """Add members mirrored through the plane 'XY', 'YZ' or 'XZ'.

        Only the member positions are mirrored. A mirrored ORIENTATION is an
        improper rotation (det = -1), which Transformation3D (scipy
        Rotation + VecGeom) cannot represent, so orientations are carried
        over unchanged and a warning is emitted when a member is rotated:
        verify that the member solids are symmetric under the mirroring.
        """
        if plane not in ('XY', 'YZ', 'XZ'):
            raise ValueError(f'plane should be XY, YZ or XZ, but got {plane}.')
        # index of the coordinate normal to the mirroring plane
        normalAxis = {'XY': 2, 'XZ': 1, 'YZ': 0}[plane]
        new_anchors = []
        for mem in self.members:
            absTrans = self.refFrame * mem.refFrame
            transl = absTrans.getTranslation().copy()
            transl[normalAxis] = 2 * plane_location - transl[normalAxis]
            rotMat = absTrans.getRotMatrix()
            if np.abs(rotMat - np.eye(3)).max() > 1e-9:
                warnings.warn(
                    f"EntityArray.reflect: member '{mem.marker}' is rotated; "
                    f"the mirrored placement keeps its orientation because a "
                    "mirrored orientation is not representable. Check the "
                    "member solid for symmetry under the mirroring.",
                    RuntimeWarning, stacklevel=2)
            new_anc = Anchor()
            new_anc.refFrame = Transformation3D(transl[0], transl[1], transl[2]).setSciRot(scipyRot.from_matrix(rotMat))
            relAnc = self.getRelTransf(new_anc)
            new_anchors.append(relAnc)
        for i_new_anc in new_anchors:
            self.create(i_new_anc.refFrame)
            

    def rotate_z(self, angle):
        self.setRefFrame(Transformation3D().applyRotZ(angle) * self.refFrame)


    def make_rotate_z(self, angle, num, x= 0, y = 0):
        """Add num rotated copies of every member around the z axis
        through (x, y), stepping by `angle` degrees."""
        new_anchors = []
        for mem in self.members:
            absTrans = self.refFrame * mem.refFrame
            absR = absTrans.getRotMatrix()
            transl = absTrans.getTranslation()
            u = np.array([0,0,1.])
            originTrans = np.array([x,y,0])
            v = transl - originTrans
            v_para = (v * u) * u
            vt = v - v_para
            for i_num in np.arange(1, num + 1):
                angle_in = angle * i_num / 180 * np.pi
                # Rodrigues rotation of the position about u through (x, y, 0)
                transl_rot = v_para + np.sin(angle_in) * np.cross(u, vt) + np.cos(angle_in) * vt
                transl_rot = originTrans + transl_rot
                skew_u = [[0, - u[2], u[1]],
                          [u[2], 0, - u[0]],
                          [- u[1], u[0], 0]]
                skew_u = np.array(skew_u)
                rot_mat = np.cos(angle_in) * scipyRot.identity().as_matrix() + (1-np.cos(angle_in)) * np.outer(u, u) + np.sin(angle_in) * skew_u
                absAnc = Anchor()
                # the orientation is rotated by the same proper rotation:
                # R_new = Rz(angle) . R_abs
                absAnc.refFrame = (Transformation3D(transl_rot[0], transl_rot[1], transl_rot[2])
                                   .setSciRot(scipyRot.from_matrix(rot_mat.dot(absR))))
                relAnc = self.getRelTransf(absAnc)
                new_anchors.append(relAnc)
        for i_new_anc in new_anchors:
            self.create(i_new_anc.refFrame)

class FlatAnalyser(EntityArray):

    def __init__(self, element, spacings = None, refFrame = Transformation3D(), marker = 'FlatAna'):
        super().__init__(element, refFrame, marker)
        self.spacing = spacings

    def make_trape_plane(self, upper_l, lower_l, height, cur_h=0, cur_v=0):
        points = self.set_trape_position(upper_l, lower_l, height)
        self.make_plane(cur_h, cur_v, points)

    def make_rect_plane(self, num_h, num_v, cur_h=0, cur_v=0):
        points = self.set_rect_position(num_h, num_v)
        self.make_plane(cur_h, cur_v, points)

    def set_rect_position(self, num_h, num_v):
        if num_h < 1 or num_v < 1:
            raise ValueError(f'num_h and num_v should be >= 1, '
                             f'got num_h={num_h}, num_v={num_v}.')
        xx = np.arange(0, num_h) * self.spacing[0]
        yy = np.arange(0, num_v) * self.spacing[1]
        midx = xx[-1] * 0.5
        midy = yy[-1] * 0.5
        xx = xx - midx
        yy = yy - midy
        # num_v rows along y, each holding num_h points along x; a plain list
        # of lists because make_plane iterates over the points twice
        return [[[x, y] for x in xx] for y in yy]

    def set_trape_position(self, upper_l, lower_l, height): # fixme: need another algorithm 
        positions = []
        num_y = height // self.spacing[1]
        for row in np.arange(num_y):
            height_r = row * self.spacing[1]
            length_r = height_r / height * ((lower_l - upper_l)) + upper_l
            num_x = length_r // self.spacing[0]
            origin_x = (length_r - upper_l) * 0.5 // self.spacing[0]
            xx = np.arange(- origin_x, num_x-origin_x) * self.spacing[0]
            positions_r = []
            for x in xx:
                y = row * self.spacing[1]
                positions_r.append([x, y])
            positions.append(positions_r)
        midx = upper_l * 0.5
        midy = height * 0.5
        for pos_row in positions:
            for pos in pos_row:
                pos[0] = pos[0] - midx
                pos[1] = pos[1] - midy
        return positions

    def make_plane(self, cur_h, cur_v, points):
        '''
        Make a plane double curve analyser component.
        '''
        ir = 0
        ys = [row[0][1] for row in points]
        height = max(ys)
        for row in points:
            ir += 1
            xs = [point[0] for point in row]
            length = max(xs)
        # self.anchor = Volume("Analyser", Box(length, height, 20))
            ic = 0
            for col in row:
                ic += 1
                ix = col[0]
                iy = col[1]
                marker = f'{self.element}_r{ir}c{ic}'
                vol = Volume(f'{marker}', self.element.solid, self.element.matCfg, self.element.surfaceCfg)
                # if abs((iy - height * 0.5) / cur_v) > 1.:
                #     raise ValueError(f'Too small cur_v: {cur_v}')
                # if abs((ix - length * 0.5) / cur_h) > 1.:
                #     raise ValueError(f'Too small cur_v: {cur_h}')
                if cur_h == 0 and cur_v == 0:
                    # print('Using plane array!')
                    tilt_h = 0
                    tilt_v = 0
                    pass
                elif cur_h == 0:
                    # print('Using vertical single curved surface')
                    tilt_h = 0
                    tilt_v = - np.arcsin((iy - height * 0.5) / cur_v) * np.rad2deg(1)
                elif cur_v == 0:
                    # print('Using horizontal single curved surface')
                    tilt_h = np.arcsin((ix - length * 0.5) / cur_h) * np.rad2deg(1)
                    tilt_v = 0
                else:
                    # print('Using double curved surface')
                    tilt_h = np.arcsin(ix / cur_h) * np.rad2deg(1)
                    tilt_v = - np.arcsin(iy / cur_v) * np.rad2deg(1)
                transf = Transformation3D(ix, iy, 0,).applyRotxyz(tilt_v, tilt_h, 0)
                anc = Anchor()
                anc.setRefFrame(transf * self.refFrame)
                anc.setMarker(f'{marker}')
                self.eleAncs.append((vol,anc))
                self.members.append(anc)


def make2CurveAnalyser(nums = [20, 20], lengths = [0, 0], spacings = [0, 0], curves = [0, 0], matCfg = 'freegas::H1/1e-26kgm3'):
    crystal_plate = Volume("crystal", Box(lengths[0] * 0.5, lengths[1] * 0.5, 1), matCfg='solid::Cd/8.65gcm3', surfaceCfg='physics=Mirror;m=2')
    analyser = EntityArray(crystal_plate, [nums[0], nums[1]], [lengths[0] + spacings[0], lengths[1] + spacings[1]], curves[0], curves[1])
    return analyser


        
def makeTrapezoidGuide(length, front_x, front_y, rear_x, rear_y, m, 
                 thickness=20., outer_mateiral='solid::Cd/8.65gcm3',
                 inner_mat='freegas::H1/1e-26kgm3'):
    inner = Volume('inner', Trapezoid(front_x, rear_x, front_y, rear_y, length), matCfg=inner_mat)
    outer = Volume('outer', Trapezoid(front_x+thickness, rear_x+thickness, 
                                      front_y+thickness, rear_y+thickness, length), 
                                      matCfg=outer_mateiral, 
                                      surfaceCfg=f'physics=Mirror;m={m}')
    outer.placeChild('ininout', inner) 
    return outer

def makeDiskChopper(r_outer, r_inner, phase, num_slit, freq, theta):

    vol = Volume('chopper', Tube(0., r_outer, 1e-2, 0., 360.))
    # the canonical physics.DiskChopper, no deprecation warning here
    chp = _DiskChopper()
    chp.cfg_rotFreq = freq
    chp.cfg_n = num_slit
    chp.cfg_phase = phase
    chp.cfg_r = r_inner
    chp.cfg_theta0 = theta
    vol.setSurface(chp.cfg)

    return vol
    