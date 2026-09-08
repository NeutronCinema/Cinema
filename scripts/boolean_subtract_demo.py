#!/usr/bin/env python3
"""布尔减（Solid 级）输运 demo —— prompt CLI 运行。

建模入口只有 Solid：H2O 外筒与挖孔内筒都是解析 Solid，经
``SolidSubtraction(outer, hole, Transformation3D(...))`` 组合成 CSG 布尔体
（右操作数摆放 = 平移/旋转，多重摆放用嵌套）。该布尔体走两条路对比：

1. 网格路：``csg.to_polydata()`` 对布尔体自动拆操作数（``pt_solid_boolInfo``）、
   各乘自己的摆放变换、trimesh/manifold3d 网格布尔（``Solid.boolean``），
   清洗后建 Tessellated mesh volume 进 C++ 输运；
2. 真值路：同一 CSG 布尔体直接进输运（VecGeom 原生导航布尔体，解析真值）。

两侧 ENTRY 谱应在 Poisson 统计内一致 —— 即"网格布尔 ≈ CSG 真值"的端到端
验证，也是 Transformation3D 在网格链路真正生效的验证
（见 doc/plan/06-mesh-transport.md）。

用法（仓库根目录）::

    . env.sh
    prompt -g scripts/boolean_subtract_demo.py --gun MyGun -n 1e4
    prompt -g scripts/boolean_subtract_demo.py -h                  # 构造参数即 CLI 选项
    prompt -g scripts/boolean_subtract_demo.py --gun MyGun -n 5e4 --r_hole 25 --nseg 96
    prompt -g scripts/boolean_subtract_demo.py --gun MyGun -n 1e4 --hole_x 8 --hole_tilt 10
    prompt -g scripts/boolean_subtract_demo.py --gun MyGun -n 20 -v   # 可视化几何+轨迹
    mpirun -np 4 prompt -g scripts/boolean_subtract_demo.py --gun MyGun -n 4e6

构造参数（--r_outer/--r_hole/--height/--nseg/--dist/--hole_x/--hole_tilt/
--no-with_csg_control）由 CLI 反射 __init__ 签名生成；scorer 输出
（es_mesh.h5 / es_csg.h5）写在当前工作目录，可用 ``ptplot es_mesh.h5+es_csg.h5``
对比。

注意 prompt-CLI 脚本的两条契约（本脚本已遵守）：
1. 继承 ``PromptMPI``（``save_all_scorers`` 读 ``self.rank``，普通 ``Prompt``
   没有该属性）；单进程直接跑即可，MPI 下自动按 rank 分摊。
2. scorer 用 ``*Helper(...).make(vol)`` 模式（``addScorer(helper, cobj)`` 走
   cppScorer 分支，``scorer_dict`` 键==值）；直接 ``addScorer(scorer_obj)``
   会让 ``save_all_scorers`` 的 ``gatherHistData(cfg串)`` KeyError。

依赖：pyvista + trimesh + manifold3d（布尔引擎，可选依赖，
``pip install trimesh manifold3d``；注意 trimesh 5.x 需 manifold3d>=3.5，
2.3.1 有 API 断裂）。
"""

import numpy as np

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.physics import Material
from Cinema.Prompt.scorer import ESpectrumHelper
from Cinema.Prompt.solid import Box, Tube, SolidSubtraction, Tessellated
from Cinema.Prompt.Mesh import BoolSolidMeshHandlerMixin

WATER = 'vacuum.ncmat'


class MyGun(IsotropicGun):
    """各向同性热点源：位于两体积对称中心下方（两体积外的真空里）。"""

    def __init__(self, energy: float = 0.0253):
        super().__init__()
        self.setEnergy(energy)          # eV，热中子
        self.setPosition([0, 0, -130])  # mm，在两个体积之外 -> ENTRY 触发


class MySim(PromptMPI):
    def __init__(self, seed=4096, r_outer: float = 50., r_hole: float = 20.,
                 height: float = 150., nseg: int = 64, dist: float = 150.,
                 hole_x: float = 0., hole_tilt: float = 0.,
                 with_csg_control: bool = True):
        super().__init__(seed)
        self._r_outer, self._r_hole, self._height = r_outer, r_hole, height
        self._dist, self._with_control = dist, with_csg_control

        # --- Solid 级布尔减：右操作数（挖孔筒）用 Transformation3D 摆放，
        #     内筒半长 20% 穿出两端 -> 干净的通孔；hole_tilt 为绕 x 轴倾角（度）---
        csg = SolidSubtraction(Tube(0., r_outer, height / 2),
                               Box(r_outer * 0.5, r_hole * 2, height * 0.2),
                               Transformation3D(x=r_hole * 1.5  ))

        # --- 网格路：csg.to_polydata() 自动拆操作数 + 乘各自摆放 + trimesh 布尔；
        #     clean_for_tessellated 负责焊接/去退化/watertight 断言。
        #     （一步到位也可直接 csg.to_tessellated(n_segments=nseg)）---
        self._mesh = BoolSolidMeshHandlerMixin.clean_for_tessellated(csg.to_polydata(nseg))
        self._solid = Tessellated(self._mesh)

        deficit = 1 - (nseg / (2 * np.pi)) * np.sin(2 * np.pi / nseg)
        print(f'boolean-subtracted mesh: {self._mesh.n_points} points, '
              f'{self._mesh.n_faces_strict} faces, open_edges={self._mesh.n_open_edges}')
        if hole_x == 0. and hole_tilt == 0.:
            analytic = np.pi * (r_outer**2 - r_hole**2) * height
            print(f'mesh volume={self._mesh.volume:.2f} mm^3, '
                  f'analytic annulus={analytic:.2f} mm^3, '
                  f'ratio={self._mesh.volume / analytic:.5f} '
                  f'(内接 {nseg} 边形亏差理论值 {deficit:.1e})')
        else:
            print(f'mesh volume={self._mesh.volume:.2f} mm^3 '
                  f'(hole offset x={hole_x} mm, tilt {hole_tilt} deg; '
                  '同轴解析公式不适用，几何对照看 CSG 真值侧)')

        self.makeWorld()

    def makeWorld(self):
        water = Material(WATER)
        world = Volume('world', Box(500, 300, 300))

        # 左：布尔减网格体积（Tessellated）
        meshvol = Volume('boolmesh', self._solid, matCfg=water)
        ESpectrumHelper('es_mesh').make(meshvol)
        world.placeChild('boolmeshP', meshvol)

        self.setWorld(world)

    def simulate(self, gun, num=0):
        super().simulate(gun, num)

        hit_mesh = float(np.asarray(self.gatherHistData('es_mesh').getHit()).sum())
        print(f'ENTRY hits (boolean mesh): {hit_mesh:.0f}')
        if self._with_control:
            hit_csg = float(np.asarray(self.gatherHistData('es_csg').getHit()).sum())
            sigma3 = 3 * np.sqrt(hit_mesh + hit_csg)
            ok = abs(hit_mesh - hit_csg) < sigma3
            print(f'ENTRY hits (CSG control) : {hit_csg:.0f}')
            print(f'|diff| = {abs(hit_mesh - hit_csg):.0f} vs 3*sqrt(N) = {sigma3:.0f}'
                  f'  ->  {"AGREE (mesh boolean == CSG truth)" if ok else "DISAGREE"}')
