#!/usr/bin/env python3
"""Visualiser 渲染主题 demo（issue #48）。

同一套嵌套圆柱 moderator 几何，依次用两个内置主题各开一个交互窗口，
关闭当前窗口（q）看下一个：

- ``ghost``（默认）：depth-peeling 半透明，透过铝壳看到内部水体 —— 查嵌套结构
- ``solid``：全不透明 + 阴影贴图 + 轮廓描边 + 高光 —— 汇报/截图

用法（仓库根目录）::

    . env.sh
    python scripts/theme_demo.py

``theme=`` 也接受自定义 ``VizTheme`` 实例，任何外观参数都可单独调::

    from Cinema.Prompt.Visualiser import VizTheme
    mine = VizTheme(opacity=0.6, depth_peeling=True, background=('#ffffff', '#d8e2ec'))
    v = Visualiser(['void.ncmat'], theme=mine)

注意：``sim.show`` 的底层 ``Launcher.showWorld`` 当前不屏蔽 void 体积
（pod 分支在途状态），demo 因此直接用 ``Visualiser`` 传 blacklist，
避免世界盒在 solid 模式下遮挡几何。

无头/软件渲染（OSMesa，如设置了 ``pyvista.OFF_SCREEN``）时 solid 的
阴影 pass 会报 ``vtkShaderProgram`` 着色器错误并退化为普通光照，
交互窗口（硬件 GL）下正常 —— demo 打印的两行报错属此情况，可忽略。
"""

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Tube, SolidUnion
from Cinema.Prompt.physics import Material
from Cinema.Prompt.Visualiser import Visualiser, VIZ_THEMES


class ThemeDemo(Prompt):
    """嵌套圆柱 moderator：ghost 半透明层次与 solid 阴影的标准展示件。"""

    def __init__(self, seed=4096) -> None:
        super().__init__(seed)
        self.mat_water = Material("LiquidWaterH2O_T293.6K.ncmat")
        self.mat_al = Material("Al_sg225.ncmat")
        self.chm_radius = 75.
        self.chm_halfheight = 50.
        self.chm_shell_radius = self.chm_radius + 4
        self.chm_shell_halfheight = self.chm_halfheight + 4
        self.prem_shell_radius = 89.
        self.prem_shell_halfheight = self.chm_shell_halfheight + 19

    def makeWorld(self):
        self.clear()
        world = Volume("world", Box(500, 500, 500), "void.ncmat")
        simbox = Volume("simbox", Box(499, 499, 499), "void.ncmat")

        sol_chm = Tube(0, self.chm_radius, self.chm_halfheight)
        sol_chm_shell = Tube(0, self.chm_shell_radius, self.chm_shell_halfheight)
        vol_chm = Volume("chm_water", sol_chm, matCfg=self.mat_water)
        vol_chm_shell = Volume("chm_shell", sol_chm_shell, matCfg=self.mat_al)
        vol_chm_shell.placeChild('P_chm_water', vol_chm)

        sol_premod_shell = Tube(self.chm_shell_radius + 4, self.prem_shell_radius,
                                self.prem_shell_halfheight)
        sol_top = Tube(0, self.prem_shell_radius, 14)
        sol_bot = Tube(0, self.prem_shell_radius, 9)
        sol_premod = SolidUnion(sol_premod_shell, sol_bot,
                                Transformation3D(z=self.prem_shell_halfheight - 9))
        sol_premod = SolidUnion(sol_premod, sol_top,
                                Transformation3D(z=-(self.prem_shell_halfheight - 14)))
        vol_premod = Volume("premod", sol_premod, matCfg=self.mat_al)

        simbox.placeChild('PHYchm', vol_chm_shell, Transformation3D(z=4 + 14))
        simbox.placeChild('PHYpremod', vol_premod)
        world.placeChild('PHYsimbox', simbox, Transformation3D().applyRotX(90))
        self.setWorld(world)


sim = ThemeDemo()
sim.makeWorld()

print(f'available themes: {sorted(VIZ_THEMES)}')
for theme in ('ghost', 'solid'):
    print(f"\n=== theme={theme!r} — close the window (q) for the next one ===")
    v = Visualiser(['void.ncmat'], printWorld=False, nSegments=200, byMat=True, theme=theme)
    v.show()
