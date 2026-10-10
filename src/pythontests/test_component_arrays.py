#!/usr/bin/env python3
# Placement operations of the component.py Anchor/Array/EntityArray helpers.
#
# EntityArray(None) is used for the pure-python cases so that no Volume and
# no physics is configured (members are plain Anchor objects); only the two
# factory cases build real volumes. All bodies are microsecond-level except
# the factories (~10 ms of C++ physics configuration each).

import math
import warnings

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as scipyRot

from Cinema.Prompt.component import Anchor, Array, EntityArray
from Cinema.Prompt.component import makeDiskChopper, makeTrapezoidGuide
from Cinema.Prompt.geo import Transformation3D


def _zArray(zPositions):
    """An EntityArray with unrotated members placed along z."""
    ea = EntityArray(None)
    for z in zPositions:
        ea.create(Transformation3D(0., 0., z))
    return ea


def _memberZs(ea):
    return sorted(float(mem.refFrame.getTranslation()[2]) for mem in ea.members)


# ------------------------------------------------------------------ selectByZ

def test_selectByZ_keeps_members_inside_window():
    ea = _zArray([-10., 0., 10.])
    ea.selectByZ(-5., 5.)
    assert len(ea.members) == 1
    assert float(ea.members[0].refFrame.getTranslation()[2]) == pytest.approx(0.)


def test_selectByZ_bounds_are_inclusive():
    # members exactly on zMin/zMax survive (the check is strict > / <)
    ea = _zArray([-1., 0., 5., 10., 11.])
    ea.selectByZ(0., 10.)
    assert _memberZs(ea) == pytest.approx([0., 5., 10.])


# --------------------------------------------------------------------- repeat

def test_repeat_two_members_single_gap():
    ea = _zArray([0.])
    ea.repeat(direction=[0., 0., 1.], gap=100., num=2)
    assert _memberZs(ea) == pytest.approx([0., 100.])


def test_repeat_three_members_two_gaps():
    ea = _zArray([0.])
    ea.repeat(direction=[0., 0., 1.], gap=100., num=3)
    assert _memberZs(ea) == pytest.approx([0., 100., 200.])


@pytest.mark.xfail(strict=True, reason='EntityArray.repeat multiplies the gap '
                      'cumulatively inside the placement loop (gap *= i_num), '
                      'so num=4 lands at 100/200/600 instead of 100/200/300; '
                      'remove this marker when the spacing is fixed')
def test_repeat_four_members_evenly_spaced():
    ea = _zArray([0.])
    ea.repeat(direction=[0., 0., 1.], gap=100., num=4)
    assert _memberZs(ea) == pytest.approx([0., 100., 200., 300.])


# -------------------------------------------------------------------- reflect

def test_reflect_rejects_unknown_plane():
    with pytest.raises(ValueError, match='XY'):
        EntityArray(None).reflect('XX')


def test_reflect_mirrors_positions():
    eaY = _zArray([])
    eaY.create(Transformation3D(1., 2., 3.))
    eaY.reflect('XY')  # plane normal is z
    assert eaY.members[-1].refFrame.getTranslation() == pytest.approx([1., 2., -3.])

    eaX = _zArray([])
    eaX.create(Transformation3D(1., 2., 3.))
    eaX.reflect('XZ')  # plane normal is y
    assert eaX.members[-1].refFrame.getTranslation() == pytest.approx([1., -2., 3.])


# ----------------------------------------------------- rotate about world z

def test_rotate_z_composes_parent_frame_rotation():
    ea = _zArray([])
    ea.create(Transformation3D(10., 0., 0.))
    ea.rotate_z(90.)
    # the array frame itself carries the rotation, members are untouched
    assert np.allclose(ea.refFrame.getRotMatrix(),
                       scipyRot.from_euler('z', 90., degrees=True).as_matrix(),
                       atol=1e-12)
    world = (ea.refFrame * ea.members[0].refFrame).getTranslation()
    assert world == pytest.approx([0., 10., 0.], abs=1e-9)


def test_make_rotate_z_moves_and_rotates_member():
    ea = _zArray([])
    ea.create(Transformation3D(10., 0., 0.))
    ea.make_rotate_z(90., 1, x=5.)
    mem = ea.members[-1]
    # (10, 0) rotated by 90 deg about the axis through (5, 0) lands on (5, 5)
    assert mem.refFrame.getTranslation() == pytest.approx([5., 5., 0.], abs=1e-9)
    # the orientation is rotated by the same proper rotation (Rz(90) . R_abs)
    assert np.allclose(mem.refFrame.getRotMatrix(),
                       scipyRot.from_euler('z', 90., degrees=True).as_matrix(),
                       atol=1e-12)


# ---------------------------------------------------------------- getRelTransf

def test_getRelTransf_self_is_identity():
    anchor = Anchor(Transformation3D(1., 2., 3.).applyRotZ(33.))
    rel = anchor.getRelTransf(anchor)
    assert rel.refFrame.getTranslation() == pytest.approx([0., 0., 0.], abs=1e-12)
    assert np.allclose(rel.refFrame.getRotMatrix(), np.eye(3), atol=1e-12)


def test_getRelTransf_maps_other_frame_points_into_self_frame():
    # documented law: p_self = R_rel p + t_rel with
    # R_rel = R_self^-1 R_other and t_rel = R_self^-1 (t_other - t_self)
    selfR = scipyRot.from_euler('ZXZ', [20., 30., 40.], degrees=True)
    selfT = np.array([1., -2., 3.])
    otherR = scipyRot.from_euler('z', -70., degrees=True)
    otherT = np.array([4., 5., -6.])
    selfAnc = Anchor(Transformation3D(*selfT).setSciRot(selfR))
    otherAnc = Anchor(Transformation3D(*otherT).setSciRot(otherR))

    rel = selfAnc.getRelTransf(otherAnc).refFrame
    assert np.allclose(rel.getRotMatrix(),
                       np.linalg.inv(selfR.as_matrix()).dot(otherR.as_matrix()),
                       atol=1e-12)
    assert rel.getTranslation() == pytest.approx(
        np.linalg.inv(selfR.as_matrix()).dot(otherT - selfT), abs=1e-9)

    # end-to-end: expressing an other-frame point through rel lands in the
    # self frame exactly as the other frame's own transform does
    p = np.array([0.3, -0.7, 1.1])
    lhs = selfR.as_matrix().dot(rel.getRotMatrix().dot(p) + rel.getTranslation()) + selfT
    rhs = otherR.as_matrix().dot(p) + otherT
    assert lhs == pytest.approx(rhs, abs=1e-10)


# ---------------------------------------------------------------- markers etc.

def test_setMemberMarker_prefixes_array_marker():
    ea = EntityArray(None, marker='parent')
    mem = Anchor(Transformation3D(1., 0., 0.))
    mem.setMarker('child')
    ea.members.append(mem)
    ea.setMemberMarker()
    assert mem.marker == 'parent|child'


def test_array_setAnchor_reanchors_members():
    # after setAnchor the member frame relative to the NEW parent equals
    # new_parent composed with the old relative frame
    arr = Array(Transformation3D(1., 2., 3.), marker='arr')
    mem = Anchor(Transformation3D(10., 0., 0.), marker='mem')
    arr.members.append(mem)

    newParent = Transformation3D(0., 0., 5.).applyRotZ(90.)
    arr.setAnchor(newParent)

    assert np.allclose(arr.refFrame.getRotMatrix(),
                       newParent.getRotMatrix(), atol=1e-12)
    expected = newParent * Transformation3D(10., 0., 0.)
    assert mem.refFrame.getTranslation() == pytest.approx(
        expected.getTranslation(), abs=1e-9)
    assert np.allclose(mem.refFrame.getRotMatrix(),
                       expected.getRotMatrix(), atol=1e-12)


# ------------------------------------------------------- volume-level factories

def test_makeTrapezoidGuide_outer_wraps_inner():
    guide = makeTrapezoidGuide(50., 8., 8., 5., 5., m=10)
    assert len(guide.child) == 1
    inner = guide.child[0]
    # the guide body must strictly contain the bore
    assert guide.getCapacity() > inner.getCapacity()


def test_makeDiskChopper_is_thin_tube_with_expected_capacity():
    # makeDiskChopper builds its volume without an explicit matCfg, which
    # warns once per process about the implicit dilute default material
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        chopper = makeDiskChopper(80., 30., 0., 2, 25., 10.)
    # the blanked disk is a full tube of half-thickness 1e-2 mm
    assert chopper.getCapacity() == pytest.approx(math.pi * 80.**2 * 2e-2)
