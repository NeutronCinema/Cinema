#!/usr/bin/env python3
# Transformation3D features not covered by test_transf3d.py / test_fix_geo.py:
# the extrinsic-xyz classmethod, the euler_xyz property, rotations about a
# generic axis and the degrees=False radian mode. Every case is checked
# against an independent scipy.spatial.transform reference.

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as scipyRot

from Cinema.Prompt.geo import Transformation3D


def test_from_euler_xyz_matches_scipy_extrinsic():
    # 'xyz' (lowercase) is the extrinsic convention: rotations about the
    # fixed world axes, applied x then y then z
    tf = Transformation3D.from_euler_xyz(1., 2., 3., 20., -35., 75.)
    ref = scipyRot.from_euler('xyz', [20., -35., 75.], degrees=True)
    assert np.allclose(tf.getRotMatrix(), ref.as_matrix(), atol=1e-13)
    assert tf.getTranslation() == pytest.approx([1., 2., 3.])


def test_euler_xyz_property_returns_construction_angles():
    tf = Transformation3D.from_euler_xyz(0., 0., 0., 20., -35., 75.)
    angles = tf.euler_xyz
    # the property reports degrees and reproduces the construction angles
    assert angles == pytest.approx([20., -35., 75.], abs=1e-9)
    # robust against an equivalent-but-different Euler representation: the
    # angles must at least rebuild the same rotation matrix
    back = Transformation3D.from_euler_xyz(0., 0., 0., *angles)
    assert np.allclose(back.getRotMatrix(), tf.getRotMatrix(), atol=1e-10)


def test_applyRotAxis_generic_axis_returns_self():
    tf = Transformation3D(1., 2., 3.)
    ret = tf.applyRotAxis(45., [1., 1., 0.])
    # chaining contract (returns self, like the applyRotX/Y/Z helpers)
    assert ret is tf
    axis = np.array([1., 1., 0.]) / np.linalg.norm([1., 1., 0.])
    ref = scipyRot.from_rotvec(45. * axis, degrees=True)
    assert np.allclose(tf.getRotMatrix(), ref.as_matrix(), atol=1e-13)
    # the translation is untouched by the rotation
    assert tf.getTranslation() == pytest.approx([1., 2., 3.])


def test_transform_does_not_mutate_input():
    tf = Transformation3D(5., -3., 2.).applyRotZ(33.)
    pts = np.array([[1., 2., 3.], [-4., 0.5, 8.]])
    ptsCopy = pts.copy()
    out = tf.transform(pts)
    # the input array must be left untouched
    assert np.array_equal(pts, ptsCopy)
    # and the C++ transform agrees with the python reference implementation
    assert out == pytest.approx(tf.transform_py(pts), abs=1e-9)


def test_from_euler_xyz_radians_mode():
    # degrees=False interprets the angles as radians
    tf = Transformation3D.from_euler_xyz(rx=np.pi / 4., ry=0.,
                                         rz=np.pi / 6., degrees=False)
    ref = scipyRot.from_euler('xyz', [np.pi / 4., 0., np.pi / 6.])
    assert np.allclose(tf.getRotMatrix(), ref.as_matrix(), atol=1e-13)
