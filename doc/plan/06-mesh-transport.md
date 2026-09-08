# 通用能力 — Solid → pyvista 网格 → Tessellated 回输运

> 立项 2026-09-07。独立于 POD 管线交付（见 [README.md](README.md)）；
> 后续 `run_moderator` 若要 CAD/网格慢化器几何可直接复用。

## 目标

任意 Cinema `Solid`（基本体 + CSG 布尔结果）→ 表面网格（`pv.PolyData`）→
清洗 → `Tessellated` solid → 回到 `Volume` 树进 C++ 输运。即打通：

```
Solid(pt_solid_* / CSG)
  → Solid.to_polydata(n)     # VecGeom CreateMesh3D 抽取表面网格（mixin 方法）
  → [可选: pyvista 侧加工/布尔/decimate]
  → Solid.clean_for_tessellated()  # 三角化+去退化+闭合性断言（staticmethod）
  → Tessellated(mesh)        # solid.py 现成入口（含 >4 顶点面守卫）
  → Volume('name', solid)    # 与 Box/Tube 完全同路: ResourceManager/ActiveVolume
```

## 已核实事实（2026-09-07，含行号）

| 事实 | 位置 |
|---|---|
| 回输运入口**已存在**：`Tessellated(polydata, tranMat)` 只收 `pv.PolyData`，faces 用 VTK 平铺格式 `[n, i₁..iₙ, ...]`，单位 mm，>100 faces 打警告 | `solid.py:322-348` |
| C++ 端逐面片 `AddTriangularFacet/AddQuadrilateralFacet` → `vg::UnplacedTessellated`（VecGeom 原生曲面体，非近似） | `PTVecGeom.cc:128-160` |
| CSG 布尔 solid 的 `cobj` 就是布尔 UnplacedVolume，可直接 `Volume(name, solid)` | `solid.py:75-77`，`PTVecGeom.cc` `pt_solid_{intersection,union,subtraction}` |
| 反向抽取现成：`pt_getMesh` = `CreateMesh3D(matrix, nSegments)`，Visualiser 生产在用 | `PTMeshHelper.cc:271-318` |
| **但 `pt_getMesh` 依赖 GeoTree**（GDML 链路概念）；v2 python 建几何（`pt_Volume_new/placeChild`）**不写 GeoTree**——GeoTree 是 Singleton，ctor 里 `makeTree()` 一次性从 GeoManager 快照。裸 Solid 在无世界树时抽不出网格 | `PTGeoTree.cc:57-59`，`PTVecGeom.cc:245-275` |
| ~~`pt_getMesh` 顶点 quirk~~ **已解**（2026-09-07 读 VecGeom 源码）：`Polyhedron::fVert` 是**共享顶点池**，每个 `Polygon` 持池引用 + 索引 `fInd`，`GetVertex(i)=fVert[fInd[i]]`——只遍历首个 polygon 的 fVert 正确 | `PTMeshHelper.cc:294-309`，`VecGeom/base/Utils3D.h:99-247` |
| `CreateMesh3D` 基类默认 **nullptr**，22 个基本体实现（Box 忽略 nSegments 精确 8点6面；Tube 只分 φ；Sphere θ/φ 同一 nSegments；Tessellated 恒等导出）；**布尔体未实现 → nullptr** → 布尔 solid 必须走 pyvista 基本体网格 + trimesh(manifold3d) 网格布尔 | `VecGeom/volumes/UnplacedVolume.h:279`，`source/Unplaced*.cpp` |
| `TessellatedStruct::Close()` 用 `AddVertex` 去重顶点，容差 `kTolerance`=**1e-9 mm**（double 构建）→ float32 往返坐标（~1e-7）**不会合并 → 裂缝**；新绑定必须出 double | `VecGeom/volumes/TessellatedStruct.h:267-289`，`VecGeom/base/Math.h:27` |
| 容量对比可用：`pt_Volume_capacity` → `VUnplacedVolume::Capacity()`；Tessellated 的 Capacity 是闭合网格体积 → CSG vs mesh 的**几何保真度量化指标** | `PTVecGeom.cc:282-285` |
| Sphere/Tube 的 `CreateMesh3D` 在 φ 缝合线与两极环产出**坐标重合（差 ~1e-16）但索引不同**的顶点 → pyvista 默认 exact 合并焊不上（实测 Sphere n=30 留 176 条开边）→ 必须 `clean(tolerance=1e-9, absolute=True)` 绝对容差焊接；1e-9 恰好对齐 VecGeom `Close()` 去重容差 | 实测 2026-09-07；`clean_for_tessellated(weld_tolerance=1e-9)` |
| `external/vtkbool` **已删除**（2026-09-07 决策：不留备选布尔引擎，唯一引擎 trimesh/manifold3d，见下文"布尔网格引擎现状"节） | `git log external/` |
| ~~工作区 `Mesh.py` 是用户在途回退版~~ **已恢复并迁移**：用户还原 Mesh.py 后，其布尔可视化后端 `VtkBoolWrapper`（vtkbool，已随 external/ 删除失效）→ `MeshBoolWrapper`（trimesh/manifold3d），见"实现状态" | `src/python/Cinema/Prompt/Mesh.py` |

## 模块分工：pyvista vs VecGeom（哪步用谁）

原则一句话：**VecGeom 管几何真值与输运，pyvista 管网格的生成、加工、质检与可视化**。
两者只在两个翻译入口交接：`Solid.to_polydata()`（VecGeom→pyvista，mixin 实例方法）与
`Solid.to_tessellated()`/`Tessellated`（pyvista→VecGeom）；数据边界是过 ABI 的
`double 点数组 + 面索引数组`（零拷贝，坐标在 solid 局部系）。

| 步骤 | 用谁 | API | 为什么是它 |
|---|---|---|---|
| 参数直造网格（结构化圆柱/球…、读 STL/CAD） | **pyvista** | `Solid.structured_cylinder()` 直构、`pv.Cylinder` 等 primitives、`pv.read()` | θ 可非均匀局部加密（VecGeom `CreateMesh3D` 只支持均匀 φ）；CAD/STL 入口只有 pyvista 有 |
| 解析 Solid → 表面网格 | **VecGeom** | 新绑定 `pt_solid_getMesh` → `CreateMesh3D`（22 基本体） | 分段逻辑与几何定义/导航同源，保真度语义自洽；pyvista 无从 Cinema Solid 抽网格的能力 |
| CSG 布尔——几何定义层 | **VecGeom** | `pt_solid_{union,intersection,subtraction}` | 布尔结果仍是解析真值（Capacity 精确、可导航）；网格级布尔只是近似 |
| CSG 布尔——网格层 | **Solid 自动 fallback（BoolSolidMeshHandlerMixin，嵌入 Solid 基类）** | `布尔Solid.to_polydata()` → `pt_solid_boolInfo` 拆操作数（含各自 Transformation3D 摆放）→ 递归抽取 → `pt_Transformation3D_inverseTransform` 施加摆放 → `Solid.boolean`（trimesh/manifold3d 引擎，staticmethod）→ 清洗 | VecGeom 对布尔体 `CreateMesh3D` 返回 nullptr（已验证）；用户侧全程 Solid API，不再手拼 pyvista 操作数；布尔**真值**用 VecGeom，布尔**网格**用 trimesh（pyvista 原生布尔官方承认不可靠） |
| 网格清洗/修复/简化 | **pyvista** | `triangulate`/`clean`/`decimate`/去退化/`n_open_edges` 断言 | VecGeom 只消费不修复；n>4 面片在 C++ 端**静默丢弃** → triangulate 必须最先做 |
| 网格 → solid（过 ABI） | **Cinema ctypes 绑定** | `pt_Tessellated_new(faces, points)` | 逐面片 Add{Triangular,Quadrilateral}Facet，坐标 double |
| 顶点池化 + 导航加速 | **VecGeom（自动）** | `Tessellated::Close()`：1e-9 去重 + 均匀网格 + 聚类 | 使用者无感；但要求同一顶点坐标逐位一致 → 直构单一点数组 |
| 摆放 + 输运 | **VecGeom**（Cinema 包装） | `Volume` + `Transformation3D`、ActiveVolume/ResourceManager | 输运引擎本体；网格在 solid 局部系，由 Transformation3D 摆放（无双重变换） |
| 容量（几何真值） | **VecGeom** | `Volume.getCapacity()` → `VUnplacedVolume::Capacity()` | 解析 solid 精确；网格 solid 走表面积分 |
| 网格体积（交叉验证） | **pyvista** | `PolyData.volume` | 与 VecGeom Capacity 各自独立实现，实测同面片集严格相等 → `roundtrip_report` 的 ratio 可信 |
| 可视化 | **pyvista** | `pv.plot` | VecGeom 无可视化能力 |

不重叠、不留空隙的自查：布尔（真值=VecGeom / 网格=trimesh+manifold3d）、去重（修复=pyvista clean /
消费侧池化=VecGeom Close）、坐标变换（抽取传恒等=局部系 / 摆放=Transformation3D）——
每对职责都只有一个执行者。

## 设计

### 新 C++ 绑定（小改动，绕开 GeoTree/世界树）

`PTVecGeom.cc` 或 `PTMeshHelper.cc` 增加（仿 `pt_meshInfo`/`pt_getMesh` 主体，去掉 tree/node 逻辑）：

```cpp
// 两段式协议：先问大小（size_t* 出参），python 分配后再取；返回 status
//   0 = ok, 1 = CreateMesh3D 未实现（布尔体 nullptr）, 2 = 空网格
int pt_solid_meshInfo(void* unplaced, size_t nSegments,
                      size_t* npoints, size_t* npolygons, size_t* faceSize);
int pt_solid_getMesh(void* unplaced, size_t nSegments,
                     double* points, size_t* faces);   // faces 平铺 VTK 格式 [n, i1..in, ...]
double pt_solid_capacity(void* unplaced);              // 裸 solid 解析容量，无需 Volume/世界
// 坐标输出 solid 的【局部坐标系】（pt_getMesh 是全局系，因它乘了树矩阵）——
// 正好适配 Tessellated：网格建好后用 Volume 的 Transformation3D 正常摆放，无双重变换
```

关键点：直接对 `solid.cobj`（`vg::VUnplacedVolume*`）调 `CreateMesh3D`，所以
**裸 Solid 一律可抽**，不需要 setWorld；布尔 solid 会拿到 nullptr（基类未实现）——
绑定侧转成明确的 Python 报错并提示走 pyvista+trimesh fallback。点数组出 **double**
（`Tessellated::Close()` 去重容差 1e-9，float32 缝合点不合并会裂缝）。状态码而非
C++ 异常（PROMPT_THROW 跨 ctypes 是 UB）。

### ~~新模块 `src/python/Cinema/Prompt/meshtools.py`~~ → 并入 `Mesh.py`（2026-09-07 用户决定：不另开模块；下述 API 全部落在 `Mesh.py` 的 transport 段，`meshtools.py` 已删除）

```python
# 全部住在 Solid 基类上（BoolSolidMeshHandlerMixin，Mesh.py 定义后混入 solid.py）
solid.to_polydata(n_segments=30) -> pv.PolyData
    # pt_solid_meshInfo → 分配 → pt_solid_getMesh → np 点/面 → pv.PolyData
solid.capacity() -> float                     # 裸 solid 解析容量（布尔体为 MC 估计）
solid.to_tessellated(n_segments=30) -> Tessellated
    # 一站式: 抽取+清洗+建 Tessellated；返回可直接 Volume('name', s.to_tessellated())
solid.roundtrip_report(n_segments=30) -> dict
    # {'nfacets', 'capacity_csg', 'capacity_mesh', 'ratio', ...}
    # n_segments 扫描给出 保真度↔面数 曲线 → 性能预算依据
Solid.clean_for_tessellated(mesh, min_edge_ratio=1e-6, weld_tolerance=1e-9)
    # triangulate() → clean()（绝对容差焊接）→ 塌缩短边（保闭合）→ 断言 watertight
Solid.structured_cylinder(r, h, ntheta, nz, thetas=None) -> pv.PolyData
Solid.boolean(mesh_a, mesh_b, operation)      # trimesh/manifold3d 引擎（staticmethod）
Tessellated(polydata, tranMat)                # pyvista→VecGeom 入口（含 >4 顶点面守卫）
```

### 不改的东西

- `solid.py` 的 `Tessellated` 类本身（已够用）
- `Visualiser` 路径（`Mesh.py` 布尔后端已迁移，见"实现状态"）
- GDML/GeoLoader

## 测试 `src/pythontests/test_solid_mesh_roundtrip.py`

1. **Box**：8 面片，capacity 比值 == 1（rtol 1e-12，平面体精确）
2. **Sphere/Tube**：n_segments=30/100 两档 capacity 比值 ≥0.98/≥0.999 且单调↑
3. **布尔**：`SolidSubtraction(Tube, Tube)`（同轴挖洞）抽取→重建→capacity 比值；
   若 `CreateMesh3D` 对布尔体失败 → 记录并启用 fallback（pyvista 基本体 + trimesh/manifold3d 布尔）
4. **清洗**：人造退化面片被剔除；`n_open_edges == 0`
5. **输运冒烟**（in-process，无需 subprocess——不产 mcpl 文件）：同 seed 同材料
   （H2O），CSG 球 vs 网格球 + `IsotropicGun` 1e4 histories →
   ESpectrum/总吸收一致（3σ 内）
6. conftest：pyvista/tetgen 缺失时进 `collect_ignore`

## 风险与对策

| 风险 | 对策 |
|---|---|
| ~~`CreateMesh3D` 布尔支持未验证~~ **已验证：不支持**（返回 nullptr） | 布尔 solid 直接走 fallback：pyvista 基本体网格 + trimesh(manifold3d) 布尔（`external/vtkbool` 已删除，不留备选） |
| ~~Utils3D 顶点池语义误读~~ **已解** | fVert 共享池 + fInd 索引；Box 用例仍先钉死 |
| ~~float 单精度抽取~~ **升级为硬要求** | `TessellatedStruct::Close()` 去重容差 1e-9，float32 坐标不合并 → 新绑定直接出 double |
| 面数 → VecGeom 导航性能 | `roundtrip_report` 输出保真度↔面数曲线；文档建议曲面 n_segments ≤ ~64（单形体面数 ~1e3-1e4 量级） |
| 曲面体（球/管）网格化后**表面变成多面体**，表面物理（mirror）行为改变 | 文档明示：Tessellated 化适合**体输运**；mirror/surface process 场景仍用解析 solid |

## 验证命令

```bash
. env.sh && cimbuild -r
cd cinemabin
python -m pytest ../src/pythontests/test_solid_mesh_roundtrip.py -v
```

## pyvista 划分网格方法的支持矩阵（2026-09-07 实测）

进输运的唯一契约：**watertight PolyData（点 + 3/4 边形面）**——VecGeom 的"体"由闭合
表面隐式定义，体网格的内部单元无用（外壳才有用）。实测结论：

| pyvista 方法 | 结论 |
|---|---|
| 原生 primitives（`pv.Cylinder` 等） | ✅ 但**必须 `.triangulate()`**：侧面是 triangle strip；且 C++ 端 n>4 面片**静默丢弃**（`PTVecGeom.cc:157` 无 else 分支）。另实测端盖环与侧面环顶点**重合不合并**（stock Cylinder 有 256 条开边）→ `Solid.boolean` 内部已统一 1e-9 绝对容差焊接，直传即可 |
| **StructuredGrid θ×z 结构化圆柱** | ✅ 推荐单一点数组**直构 PolyData**（拓扑共享→坐标逐位一致，绕开 VecGeom 1e-9 去重与 clean 容差问题）；`extract_surface()+merge+clean` 路线实测留开边（24 条），不推荐 |
| 体网格（delaunay_3d/voxelize 等） | 外壳 `extract_surface()` 可用，但 delaunay 实测留 2 条开边 → 必须 `n_open_edges==0` 断言 |
| 布尔 / decimate / subdivide | ✅ 布尔用 **trimesh(manifold3d)**（实测开箱 watertight）；**pyvista 原生 `boolean_*` 禁用**（官方承认不可靠，#8632）；产出仍是 PolyData，走同一契约 |

直构结构化圆柱实测（nth=64, nz=10, R=50, H=200）：768 面（640 四边形 + 128 端盖
三角），`open_edges=0`，`Tessellated→Volume→getCapacity()` 与 pyvista `volume` 严格
相等，相对解析值差 1.61e-3 = 内接 64 边形理论亏差（`(n/2π)·sin(2π/n)`）。端盖用
θ 环点扇形直构（独立 `pv.Circle` 的顶点与环点不重合，merge 焊不上）。θ 间距可
**非均匀**（局部加密），比 VecGeom `CreateMesh3D` 的均匀 φ 更灵活。
`meshtools` 增加 `structured_cylinder(r, h, ntheta, nz, thetas=None) -> PolyData`。

## 布尔网格引擎现状（2026-09-04 调研 + 本机实测）

结论：**布尔网格唯一引擎 = trimesh + manifold3d**（2026-09-07 决策：不留备选，曾 vendor 的 `external/vtkbool` 已删除），pyvista 原生布尔禁用。

- **pyvista 官方已承认 VTK 布尔不可靠**（issue #8632，2026-05，maintainer 提出）：`boolean_*`/`intersection`
  包装的 `vtkBooleanOperationPolyDataFilter`/`vtkIntersectionPolyDataFilter` 多年产出错误结果、
  non-manifold、静默失败甚至段错误（汇总 14 个 2021–2026 年 bug：#1560/#2788/#6688/#4843/#7548/
  #4810/#3290/#4059/#1120/#5995/#4973/#4936/#6780/#3430）。提案：文档警告 + 运行时 warning +
  **post-hoc `n_open_edges` 检查**（"能抓住清单里每一个错结果 bug"——恰好印证我们把
  `n_open_edges==0` 断言放进 `clean_for_tessellated` 的设计）；"核弹选项"是废弃这些 API 指向
  **pyvista-manifold**（Manifold 精确算术 CSG 引擎的 wrapper；0.1.x 刚起步，本机与 stable 环境的
  旧 pyvista 冲突装不上，等其进 pyvista 主线再评估）。
- **vtkbool 始终未合入 VTK**（9.3 起 release notes 无踪影），仍是第三方（zippy84/vtkbool）；
  VTK 原生 filter 没换过。曾 vendor 于 `external/vtkbool` 作备选，2026-09-07 决策删除
  （trimesh+manifold3d 已实测开箱 watertight，无理由维护第二个引擎）。
- **trimesh 4+/5.x 的默认/推荐布尔后端就是 manifold3d**（替代 Blender 后端）；注意
  manifold3d==2.3.1 有 API 断裂（trimesh #2112），依赖要钉版本。
- **本机实测**（cinemavirenv, trimesh 5.1.0 + manifold3d 3.5.2，测后已卸载还原）：同轴
  Tube−Tube 挖孔 difference 512 faces `is_watertight=True`、union 302 faces watertight，
  体积 vs 解析值相对误差均 1.61e-3 = 64 边形内接亏差（与直构圆柱结论一致 → 误差来自离散化
  而非布尔引擎）。**开箱 watertight**，对比 pyvista 原生实测的开边/焊接失败。
- 依赖落点：`trimesh`+`manifold3d` 作为布尔 fallback 的**可选依赖**（pyproject optional 或
  驱动脚本层），不进核心必需依赖。

## 实现状态（2026-09-07，已实施）

### 第四批（2026-09-08）：BoolSolidMeshHandlerMixin 合并进 Solid

- **用户指令**：不保留模块级函数，`SolidMeshHandler` + `MeshBoolWrapper`
  合并为一个 `BoolSolidMeshHandlerMixin`，嵌入 `Solid` 基类（solid.py），
  让 Solid 处理布尔时直接调用。
- **类布局**（Mesh.py 定义、`class Solid(BoolSolidMeshHandlerMixin)`）：
  5 个 ctypes 绑定收为类属性；实例方法 `to_polydata/capacity/
  to_tessellated/roundtrip_report`（self 即 Solid）；staticmethod 吸收原
  模块函数 `clean_for_tessellated/_collapse_short_edges/_face_sizes/
  structured_cylinder` 与引擎 `boolean/_weld`。**mixin 不定义
  `__init__`**（构造完全归宿主类）。旧→新 API：
  `solid_to_polydata(s,n)`→`s.to_polydata(n)`、`solid_capacity(s)`→`s.capacity()`、
  `mesh_solid(s,n)`→`s.to_tessellated(n)`、`roundtrip_report(s,n)`→`s.roundtrip_report(n)`、
  `polydata_to_solid(m)`→`Tessellated(m)`、`MeshBoolWrapper.boolean`→`Solid.boolean`。
- **`Tessellated.__init__` 吸收 >4 顶点面守卫**（原 `polydata_to_solid`
  里，C++ 端静默丢弃大面片）；顺带删除 `Tessellated`/`Tetrahedron` 的
  `super().__init__()`（Solid 无 `__init__`，纯空操作）。
- **op 码单点映射**：viz `pt_meshInfo` 的 boolOp 与 transport
  `pt_solid_boolInfo` 的 op 同用 VecGeom BooleanOp_t 编码，统一走
  `_BOOL_OP_NAMES`（**Subtraction=2 → 'difference'**，防错配）；viz
  `Mesh.getMesh` 布尔分支从 `MeshBoolWrapper |/-/&` 改为直调静态引擎。
- **`_WELD_MM`/`_BOOL_HINT` 留模块级**（前者被 `boolean()` 内闭包按模块
  全局解析，做成类属性会 NameError）；`__or__/__and__/__sub__` 运算符
  删除（挂在 Solid 上会与 CSG `SolidUnion` 语义混淆）。
- **导入环安全**：solid→geo→Mesh 既有链路下，solid.py 顶层
  `from .Mesh import BoolSolidMeshHandlerMixin` 不成环（Mesh 保持零
  模块级 solid/geo 导入，`Tessellated` 延迟导入移入
  `to_tessellated`/`roundtrip_report` 函数体）；pyvista 本就经 geo 成为
  solid 的传递性硬依赖，无新增破坏。
- **行为保持验证**：12+1 测试全过；嵌套布尔 `SolidUnion(SolidSubtraction(
  Tube(0,50,100), Tube(0,10,120)), Sphere(0,60), z=60)` 新旧代码 A/B
  **逐位一致**（872 点 / 1740 faces / ratio 0.9909485998889124，capacity_csg
  的 MC 估计跨进程确定性成立）；CLI `prompt -g boolean_subtract_demo.py
  -n 5e3 --no-with_csg_control` 348 faces watertight、ratio 0.99973。
- **demo 在途注记**：boolean_subtract_demo.py 为用户在途修改版（挖孔
  操作数改 Box、CSG 对照体积已从 makeWorld 删除但 `simulate` 仍读
  `es_csg`），默认 `with_csg_control=True` 会 KeyError——预先存在，
  与本重构无关，故 CLI 验证用 `--no-with_csg_control`。

### 第三批（2026-09-08）：SolidMeshHandler 收拢 solid→mesh

- **C++ 绑定归位**：`pt_solid_{meshInfo,getMesh,capacity,boolInfo}` 与
  `pt_Transformation3D_inverseTransform` 从 `PTVecGeom.hh/.cc` 移入
  **`PTMeshHelper.hh/.cc`**（mesh-helper 域；include 本就齐全，
  `vecgeom::` 命名随文件惯例；`boolInfo` 的 op 码改用
  `BooleanOp_t::Union` 等枚举名而非裸数字）。PTVecGeom 回归纯
  solid/volume 构造器绑定。
- **Python `SolidMeshHandler`**（Mesh.py）：solid→mesh 全链路一个
  handler 类包装——5 个 ctypes 绑定收为类属性，`to_polydata(solid)`
  两段式抽取，`capacity(solid)`，布尔 fallback（`_boolean_fallback`
  拆操作数 + `_apply_placement` 摆放，从 MeshBoolWrapper 迁入）。
  `solid_to_polydata`/`solid_capacity` 降为薄委托，`_polydata_from_unplaced`
  删除。
- **职责切分**：`MeshBoolWrapper` = 纯 mesh×mesh 布尔引擎
  （`boolean()` + `|`/`-`/`&` + 焊接，viz 与 handler 共用）；
  `SolidMeshHandler` = solid→mesh（拆包/摆放/递归）→ 调引擎组合。
  重构行为保持：13 测试全过，嵌套布尔 roundtrip ratio 逐位不变
  （0.9922546654774896），handler 直连偏移孔质心 −0.625 精确。

### 第二批（2026-09-07）：Solid 级布尔 × Transformation3D 贯通

- **模块合并**（用户决定）：`meshtools.py` 全部内容并入
  `Mesh.py`（"transport-grade mesh path" 段），模块删除；引用方
  （demo ×2、测试）import 改 `from Cinema.Prompt.Mesh import ...`。
  循环导入用**函数体延迟 import** `from .solid import Tessellated` 解决
  （geo → Mesh → solid → geo 成环）。
- **布尔 fallback 全程 Solid API**：`solid_to_polydata` 遇布尔体（status 1）
  走布尔拆包 fallback（初版收在 `MeshBoolWrapper.from_unplaced`，第三批
  起迁入 `SolidMeshHandler`）：`pt_solid_boolInfo` 拆出操作数
  unplaced + 各自摆放 `vg::Transformation3D*`（placed volume 成员，
  泄漏式存活随 solid 全程有效）→ 递归抽取
  （嵌套布尔自动展开）→ `_apply_placement` 施加摆放 → 按 op 码
  （Union=1/Subtraction=2/Intersection=3，`PTMeshHelper.hh` BooleanOp_t）
  走 `|`/`-`/`&` 运算符 → trimesh/manifold3d。
- **变换方向事实**（读 VecGeom 源码钉死）：`Transformation3D::Transform` 是
  **master→local**（`Transformation3D.h:395-427`），`InverseTransform` 才是
  **pose**（local→master，`R·p+t`，R 的行 = 存储分量平铺首三元组——python
  `update_cpp_rot` 按行传 scipy 矩阵 ⇒ vg 存的**就是 pose 本身**）。把摆放
  烘焙进操作数局部网格点必须用 **InverseTransform**（VecGeom 自家
  `SolidMesh::TransformVertices` 同款，`SolidMesh.cpp:20-30`）——新绑定
  `pt_Transformation3D_inverseTransform`。初版误用 `Transform` 导致偏移孔
  镜像到 −x，靠质心断言（散度定理）抓出。
- **布尔 Capacity 是 MC 估计**：`UnplacedBooleanVolume::Capacity()` =
  `EstimateCapacity(1000000)`（`UnplacedBooleanVolume.h:91-96`）——
  `solid_capacity(布尔)` 只做 ~1e-2 宽松 sanity，严格对照用解析公式
  （同轴环筒）或 pyvista 参照。
- **`clean_for_tessellated` 修复**：原"删退化面片"会捅开网格（manifold3d
  sliver 三角形删 24 个 → 48 条开边）；改为**塌缩短边**（`_collapse_short_edges`：
  scipy 稀疏图连通分量合并近点 + 组均值，退化为重复顶点的三角形随之剔除），
  表面保持封闭。顺带修了 `np.full(tris.shape[0], 3)` 用过滤前计数的 shape bug。
- **测试**：12/12 passed——新增 `test_boolean_transform_offset`
  （偏移孔质心 x ≈ −15·r_h²/(r_o²−r_h²)，体积对变换丢失不敏感、质心敏感）
  与方向敏感的 `test_boolean_transform_rotation`（非方截面操作数
  rot_z=30+x=10，pyvista `rotate_z(30).translate` 参照 1e-6 + CSG MC 容量
  1e-2 双锚点；±90° 对称几何判不出方向，勿改回）。嵌套布尔冒烟
  `SolidUnion(SolidSubtraction(Tube,Tube), Sphere, z=60)`：watertight 1200 faces，
  mesh/CSG-MC = 0.992。
- **CLI 端到端**（`scripts/boolean_subtract_demo.py` Solid 级重写后）：
  默认几何 ENTRY 341 vs CSG 409 < 3σ；`--hole_x 8 --hole_tilt 10`
  686 vs 759 < 3σ（AGREE）——Transformation3D 在网格链路真正生效。
- **无关发现（预先存在）**：同进程建第二个世界必段错误——
  `pt_setWorld`→`CloseGeometry()` 后 `fIsClosed` 永不复位，新
  `LogicalVolume` 不注册（`GeoManager.cpp:31-38` 仅警告），
  `ResourceManager::addScorer` 里 `FindLogicalVolume(volID)` 返回 NULL
  直接解引用（`PTResourceManager.cc:136-137`，最小脚本复现，与本分支
  无关）。ctest 的 `--forked` 一直掩盖它；`test_transport_csg_vs_mesh_smoke`
  加 `@pytest.mark.forked` 做好公民，非 forked 合跑不再炸
  （roundtrip+scorer_class 同进程 13 passed）。

## 第一批实现记录（2026-09-07）

- **C++ 绑定**（初版 `PTVecGeom.hh/.cc`，第三批起移入 `PTMeshHelper.hh/.cc`）：
  `pt_solid_meshInfo` / `pt_solid_getMesh` / `pt_solid_capacity` 按上一节签名落地；
  `SolidMesh*` 用后即 `delete`（`CreateMesh3D` 每次返回新对象，调用方持有）。
- **`src/python/Cinema/Prompt/meshtools.py`**：`solid_capacity` / `solid_to_polydata` /
  `clean_for_tessellated(min_edge_ratio=1e-6, weld_tolerance=1e-9)` /
  `polydata_to_solid`（>4 顶点面片显式拒绝——C++ 端会静默丢弃）/ `mesh_solid` /
  `roundtrip_report`（含 `capacity_polydata` 交叉验证列）/ `structured_cylinder` /
  `polydata_boolean`（trimesh/manifold3d，惰性导入）。
  与草案的差异：`clean_for_tessellated` 增加绝对容差焊接（见事实表 Sphere 缝合线行，
  草案里的 `clean()` 不带参焊不上极点/缝合线顶点）。
- **测试** `src/pythontests/test_solid_mesh_roundtrip.py`：10 项，**9 passed /
  1 skipped**（trimesh 缺失时布尔 fallback 测试按设计跳过；用 `importorskip`
  而非 conftest `collect_ignore`——粒度到单测试更合适）。冒烟测试用对称世界
  （CSG 球左 vs 网格球右，同枪同材料）ESpectrum 3σ 一致。
- **演示脚本** `scripts/mesh_transport_demo.py`（**2026-09-08 已删除**，
  下述数字为当时实测记录；基本体 roundtrip 现经 `roundtrip_report` 或
  `boolean_subtract_demo.py` 验证）：`--shape {cylinder,sphere,tube}`
  `-n` 粒子数、`--nseg/--nz` 离散、`--plot PNG`（离屏）/`--show`、`--analytic`
  对照组；可视化 = 半透明网格 + ENTRY 位置点云（PSD XZ）。实测：sphere nseg=64
  ratio=0.99779，ENTRY 计数 682 ≈ 立体角估算 ~670。
- **演示脚本** `scripts/boolean_subtract_demo.py`（2026-09-07）：`prompt -g` 可跑的
  布尔减 demo——pyvista 圆柱操作数 + trimesh/manifold3d difference →
  Tessellated 网格体积（穿孔 H2O 环筒）vs 解析 Tube 对照组，ENTRY 谱 3σ 一致；
  实测 512 faces watertight，capacity ratio 0.99839 = 64 边形内接亏差理论值。
  随之修的 `polydata_boolean` 健壮性：操作数入 trimesh 前先三角化 + 1e-9 绝对
  容差焊接（stock `pv.Cylinder` 端盖环/侧面环顶点重合不合并，manifold 引擎
  直接拒绝 "Not all meshes are volumes!"）+ 操作数 `is_volume` 预检报可读错误。
- **prompt-CLI 脚本契约**（写 demo 时核实）：① 继承 `PromptMPI`——
  `save_all_scorers` 读 `self.rank`，普通 `Prompt` 没有该属性会 AttributeError
  （guide.py 也是 PromptMPI）；② scorer 必须用 `*Helper(...).make(vol)` 模式
  （`addScorer(helper, cobj)` 走 cppScorer-int 分支，`scorer_dict` 键==值）——
  裸 `addScorer(scorer_obj)` 走 name→cfg 串分支，而 `save_all_scorers` 遍历
  `.values()` 把 cfg 串回传 `gatherHistData`（按键名查）→ KeyError。后者是
  promptCore.py:218 的**存量 bug**（两个用户脚本 sans_run.py/tmrsans.py 各自
  复制了同一份坏实现），与本管线无关，可另开小 PR 修（`values()`→`keys()`）。
- **`Mesh.py` 布尔可视化路径迁移**：`VtkBoolWrapper`（vtkbool 后端，已随
  `external/vtkbool` 删除而失效）→ `MeshBoolWrapper`，委托
  `meshtools.polydata_boolean`（trimesh/manifold3d 唯一引擎，与输运侧同源）。
  操作数来自 viz ABI 的 **float32** 网格，缝合线/极点重合顶点差 ~1e-6 相对 →
  布尔前按 bbox 对角线自适应绝对容差焊接（`max(1e-9, diag*1e-6)`）。
  实测 `SolidSubtraction(Tube,Tube)` 经 `Mesh().getMesh(30)` 抽取：240 faces，
  `open_edges=0`，volume/解析环筒 = 0.99271（nseg=30 内接亏差；若孔洞丢失
  对实心圆柱只有 0.834 → 布尔结果正确）。
- **promptcli bool 参数修复**：`_construct_argument_groups` 原把 `type=bool`
  传给 store_true/store_false action → `TypeError`，任何构造参数含 bool 的脚本
  `-h` 即崩；现按默认值方向生成 `--no-xxx`（default True）/`--xxx`，并 pop 掉
  type。真实 CLI 全链路验证：`prompt -g scripts/boolean_subtract_demo.py
  --gun MyGun -n 1e4`（ENTRY 361 vs CSG 398，|diff|<3σ，h5 落盘），
  `--r_hole 25 --nseg 96` 参数覆盖生效（768 faces，ratio 0.99929）。
- 已知无关失败：`test_prompt.py::test_simulation` 的 weight/hit 期望值因
  `PTMCPLBinaryWrite.cc` 在途单位修改（mm→cm、eV→MeV）偏移（edge 分量逐位
  一致），待该工作落盘后重生成基准——与本分支改动无关。
- 复现：`. env.sh && cimbuild -r && cd cinemabin && python -m pytest
  ../src/pythontests/test_solid_mesh_roundtrip.py -v`。

## 与 POD 管线的接口

本能力独立交付。后续 Phase 5 若需真实 CAD 慢化器：
`cad_solid.to_tessellated()` → `Volume('moderator', ...)` →
`MCPLOutHelper('podsrc', ptstate='PEA_POST')` 挂上网格体积（ptstate 参数
Phase 1 已进，commit 9f7afa61），其余管线不变。
