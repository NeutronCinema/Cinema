# POD 源项采样管线 — 总体计划

> 分支：`feat-pod-source-sampling`
> 日期：2026-09-04
> 状态：已批准，待实现

## 1. 背景与目标

中子仪器模拟（CSNS / Cinema-Prompt）中，慢化器出口处的脉冲源项是下游一切模拟的输入。
传统做法（KDSource 链）：MC 记录源面粒子 → KDE 密度估计 → 抽样。
本计划探索另一条路线：**POD（本征正交分解）去噪 + 网格场抽样**——

1. 用 MCPL 在**体积内**记录粒子态（PEA 触发：每次碰撞后/出体/吸收都记一条）；
2. 把记录按 (空间网格 cell × 时间 bin) 装箱成快照矩阵 X ∈ R^(N_cells × N_t)；
3. SVD/POD 截断去噪（文献：Loi et al. 2024，TRIGA 堆 OpenMC 快照，截断前 20 阶把
   2.54% MC 噪声压到 ~0.5%）；
4. 在源项位置取重构场，从中采样**完整粒子源项**（位置 + 方向 + 能量 + 时间 + 权重）；
5. 写回 MCPL，用 `MCPLGun` 在下游模拟中复演，与基线对比验证。

文献依据与方法细节见 `subgitmodule/srec/research/`（idea.md / method.md / theory.md / review.md）。

上一版实现（`scripts/pod_source_sampling/mesh_scorer.py`，git `691257e3`）已删除——
其 MCPL 解析与网格定位有 bug，且把 scorer 挂在世界体（ENTRY 对出生体积不触发，记录为空）。
本计划为全新实现。

## 2. 已确认决策

| 决策点 | 选择 |
|---|---|
| 代码位置 | **混合**：可复用核心进 `src/python/Cinema/Prompt/`（带 pytest）；驱动脚本放 `scripts/pod_source_sampling/` |
| 记录后端 | **MCPL**（`KillerMCPL` 加 ScorerType 触发参数）；不动未提交的 H5PL 工作 |
| POD 核心 | numpy/scipy（method of snapshots）；pyforce 只做可选适配器 |
| 网格 | pyvista 直接构建；**不用**工作区里 ABI 损坏的 `src/python/Cinema/Prompt/Mesh.py` |
| PEA 触发 | **PEA_POST**（propagate_post + exit + absorb；无 PEA_PRE 的吸收双记问题） |

## 3. 管线流程

```
run_moderator.py                       pod_denoise.py                sample_source.py        replay_validate.py
┌──────────────────┐   mcpl(cm/MeV/ms) ┌────────────────────┐  field.npz ┌──────────────┐ sampled.mcpl.gz ┌─────────────────┐
│ Prompt 模拟       │ ───────────────▶ │ 读取+单位转换        │ ─────────▶ │ 场采样        │ ──────────────▶ │ MCPLGun 下游复演  │
│ MCPLOutHelper    │   per-rank files  │ 时间 bin → 网格 cell │            │ (x,Ω,E,t,w)  │                 │ 三路对比验证       │
│ ptstate=PEA_POST │   (merge_mcpl.py) │ POD 截断去噪         │            │ 权重守恒       │                 │ 谱/TOF/χ²        │
└──────────────────┘                   └────────────────────┘            └──────────────┘                 └─────────────────┘
```

## 4. 文档索引

| 文件 | 内容 |
|---|---|
| [01-bugs.md](01-bugs.md) | 实现前发现的现存 bug 清单与修复建议（Phase 0） |
| [02-cpp-changes.md](02-cpp-changes.md) | Phase 1：C++ ScorerType 透传 + time 单位修复 + python helper |
| [03-python-core.md](03-python-core.md) | Phase 2–4：包内核心模块（podfield / pod / mcplout / sourcesampler）API 草案 |
| [04-drivers-tests.md](04-drivers-tests.md) | Phase 5–6：驱动脚本、pytest 测试、端到端验证 |
| [05-facts-risks.md](05-facts-risks.md) | 已核实关键事实（单位/ABI/MPI/测试模式）与风险对策 |

## 5. 新增文件地图

```
src/python/Cinema/Prompt/
├── podfield.py        # MCPL 读取 + 单位转换 + 时间 bin + 网格装箱（MeshField）
├── pod.py             # POD 分解 / 截断曲线 / 重构（PODResult）
├── mcplout.py         # ctypes 直包 libmcpl.so 的 MCPL 写出器（MCPLOutWriter）
└── sourcesampler.py   # 从重构场采样完整源项（PODSourceSampler）

scripts/pod_source_sampling/
├── run_moderator.py   # 慢化器模拟（PEA_POST 记录）
├── pod_denoise.py     # 读取→binning→POD→field.npz + 诊断图
├── sample_source.py   # field.npz → sampled.mcpl.gz
└── replay_validate.py # 下游三路对比验证

src/pythontests/
├── test_podfield_binning.py
├── test_pod.py
├── test_mcplout_writer.py
└── test_pod_source_sampling.py   # 集成（subprocess 模式）

doc/plan/              # 本计划文档
```

修改的现有文件见 [02-cpp-changes.md](02-cpp-changes.md)。

## 6. 验证总览

```bash
. env.sh && cimbuild -r
cd cinemabin
python -m pytest ../src/pythontests/test_podfield_binning.py ../src/pythontests/test_pod.py \
  ../src/pythontests/test_mcplout_writer.py -v          # 单元（Phase 2–4）
python -m pytest ../src/pythontests/test_pod_source_sampling.py -v   # 集成（Phase 6）
```

端到端小规模冒烟与生产级验证命令见 [04-drivers-tests.md](04-drivers-tests.md)。
