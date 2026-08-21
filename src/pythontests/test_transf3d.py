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



from Cinema.Prompt.geo import Transformation3D
import numpy as np


def test_transf3d():
    np.set_printoptions(precision=15)
    for i in np.arange(10):
        angles=np.random.random(3)*np.pi
        mat1 = Transformation3D(rot_z=angles[0], rot_new_x=angles[1], rot_new_z=angles[2])
        mat2 = Transformation3D()
        mat2.set_euler_ZXZ(rot_z=angles[0], rot_new_x=angles[1], rot_new_z=angles[2])

        data = np.random.random([100,3])

        dataout = mat1.transform(data)
        dataout2 = mat2.transform_py(data)
        np.testing.assert_allclose(dataout, dataout2, rtol=1e-15, atol=1e-15)


    for i in np.arange(10):
        angles=np.random.random(3)*np.pi
        mat1 = Transformation3D(rot_z=angles[0], rot_new_x=angles[1], rot_new_z=angles[2])
        mat2 = Transformation3D()
        mat2.set_euler_ZXZ(rot_z=angles[0], rot_new_x=angles[1], rot_new_z=angles[2])
        np.testing.assert_allclose(mat1.getRotMatrix(), mat2.getRotMatrix(), rtol=1e-15, atol=1e-15)

        data = np.random.random([1000,3])
        data2 = np.copy(data)

        np.testing.assert_allclose(data, data2, rtol=1e-15, atol=1e-15)

        dataout = mat1.transform(data)
        dataout2 = mat2.transform(data2)
        np.testing.assert_allclose(dataout, dataout2, rtol=1e-15, atol=1e-15)

    # # Transformation operation
    # def test1():
    #     t1 = Transformation3D(0,0,1)
    #     t2 = Transformation3D(0,1,0)
    #     t3 = t1.dot(t2)
    #     np.testing.assert_allclose(t3.getTranslation(), np.array([0,1,1]), rtol=1e-15, atol=1e-15)
    #     np.testing.assert_allclose(t3.euler_xyz, np.array([0,0,0]), rtol=1e-15, atol=1e-15)

    # def test2():
    #     # translation then rotation
    #     t1 = Transformation3D().applyRotX(90).dot(Transformation3D(0,0,1))
    #     # print(t1.quad_matrix)
    #     t2qm = np.array([[1,0,0,0],
    #                      [0,0,-1,-1],
    #                      [0,1,0,0],
    #                      [0,0,0,1]])
    #     np.testing.assert_allclose(t1.quad_matrix, t2qm, rtol=1e-15, atol=1e-15)

    # def test3():
    #     # translation then multiple rotations, then a translation again
    #     t1 = Transformation3D(0,2,1)
    #     t2 = Transformation3D().applyRotX(30)
    #     t3 = Transformation3D().applyRotY(45)
    #     t4 = Transformation3D().applyRotZ(60)
    #     t5 = Transformation3D(1,3,5)

    #     # code_str = f"np.array({t5.quad_matrix.tolist()})"
    #     # print(code_str)
    #     t1qm = np.array([[1., 0., 0., 0.],[0., 1., 0., 2.],[0., 0., 1., 1.],[0., 0., 0., 1.]])
    #     t2qm = np.array([[ 1.,  0.,  0.,  0.,],[ 0.,  0.866025403784439, -0.5, 0.,],[ 0.,  0.5, 0.866025403784439,  0.,],[ 0.,  0.,  0.,  1.,]])
    #     t3qm = np.array([[0.7071067811865475, 0.0, 0.7071067811865476, 0.0], [0.0, 1.0, 0.0, 0.0], [-0.7071067811865476, 0.0, 0.7071067811865475, 0.0], [0.0, 0.0, 0.0, 1.0]])
    #     t4qm = np.array([[0.5000000000000002, -0.8660254037844386, 0.0, 0.0], [0.8660254037844386, 0.5000000000000002, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
    #     t5qm = np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 3.0], [0.0, 0.0, 1.0, 5.0], [0.0, 0.0, 0.0, 1.0]])

    #     t21 = t2qm.dot(t1qm)
    #     np.testing.assert_allclose(t2.dot(t1).quad_matrix, t21, rtol=1e-15, atol=1e-15)

    #     t321 = t3qm.dot(t2qm).dot(t1qm)
    #     np.testing.assert_allclose(t3.dot(t2).dot(t1).quad_matrix, t321, rtol=1e-15, atol=1e-15)

    #     t4321 = t4qm.dot(t3qm).dot(t2qm).dot(t1qm)
    #     np.testing.assert_allclose(t4.dot(t3).dot(t2).dot(t1).quad_matrix, t4321, rtol=1e-15, atol=1e-15)

    #     t4321[0,3] += 1
    #     t4321[1,3] += 3
    #     t4321[2,3] += 5
    #     t54321 = t4321
    #     np.testing.assert_allclose(t5.dot(t4).dot(t3).dot(t2).dot(t1).quad_matrix, t54321, rtol=1e-15, atol=1e-15)


    # test1()
    # test2()
    # test3()

