# Phase 1 — C++ PEA 触发 + time 单位修复 + python helper

## 目标

让 `KillerMCPL`（及其 python 包装 `MCPLOutHelper`）可以选择任意 `ScorerType` 触发
（重点是 **PEA_POST**：propagate_post + exit + absorb），并顺手修掉 time 单位 bug。

## 已核实的触发机制（无需改动的部分）

- `ResourceManager::addScorer`（`src/cxx/Geometry/libsrc/PTResourceManager.cc:196-201`）按
  `sc->getType()` 分发：PEA_POST → (propagate_post + exit + absorb) 三个 scorer 列表。
- `ActiveVolume`（`src/cxx/Geometry/libsrc/PTActiveVolume.cc`）分发条件：
  - `:352` `sameVolume` → scorePropagatePre（碰撞点）
  - `:359` `sameVolume && scattered` → scorePropagatePost（散射后碰撞点，**无吸收双记**）
  - `:374` `!sameVolume` → scoreExit
- PEA_PRE 的已知 FIXME（吸收时 propagate/absorb 双记，`PTActiveVolume.cc:350`）不影响 PEA_POST。
- ENTRY 对出生体积不触发（`src/cxx/Core/libsrc/PTLauncher.cc:131` `if(!isFirstStep)`）。

## 改动表

| 文件 | 修改 |
|---|---|
| `src/cxx/Ana/libinc/PTKillerMCPL.hh:32` | ctor 加尾参：`ScorerType type = ScorerType::ENTRY` |
| `src/cxx/Ana/libsrc/PTKillerMCPL.cc:24` | 透传 `type` 给 `Scorer1D(...)` 基类（替换硬编码 ENTRY） |
| `src/cxx/Python/libinc/PTPythonScorer.hh:61` | `pt_KillerMCPL_new(..., int type)` |
| `src/cxx/Python/libsrc/PTPythonScorer.cc:129` | `static_cast<pt::Scorer::ScorerType>(type)` 透传（仿 `:68` 的 `pt_ScorerMultiScat_new` 惯用法） |
| `src/cxx/MCPL/libsrc/PTMCPLBinaryWrite.cc:89` | **time 不修（用户决策 2026-09-04）**：在 `write(const Particle&, int)` 上方加 fixme 注释（已暂存）；规范输出走 `:132` 的 `write(const Particle&)` 重载（单位全对）。Bug 2 注释同样不动 |
| `src/python/Cinema/Prompt/scorer.py:817` | `MCPLOutHelper.__init__(..., ptstate='ENTRY')`：`ParticleTracingState.from_string` 验证（**显式 raise 未知串**，Bug 4）；`make()` 尾传 type_int；`kill and type != ENTRY` → `ValueError` |

> **状态注记（2026-09-04）**：曾实现的 time 修复 + 下游 sxd 脚本适配（×1e-3）已按用户决定回退，
> 只保留 fixme。下游影响分类见 [01-bugs.md](01-bugs.md)。
> **对 Phase 2 的后果**：`podfield.py` 读 KillerMCPL 文件时 time 按**秒**解释（做成显式
> `time_unit` 参数，`'ms'` 只用于规范文件），不能默认 MCPL 规范单位。
> PEA 触发透传（表内其余行）同样处于已回退状态，待确认后重新应用。

### python helper 细节（`scorer.py` 的 `MCPLOutHelper`）

```python
def __init__(self, name, pdg=2112, groupID=0, kill=False, compress=True, ptstate='ENTRY'):
    state = ParticleTracingState.from_string(ptstate)   # from_string 改为未知串 raise
    self.ptsNum = state.value_num                        # 与 C++ 枚举 int 一致（SURFACE=0…ABSORB=7）
    if kill and self.ptsNum != ParticleTracingState.ENTRY.value_num:
        raise ValueError("kill=True only makes sense with ENTRY (would kill at every collision)")
```

`make(vol)` 把 `self.ptsNum` 作为尾参传给 `_pt_KillerMCPL_new`。

**注意**：`from_string`（`scorer.py:97`）当前 `mapping.get(s, cls.ENTRY)` 静默回落，
要先改成未知串 raise——它是公共 API，其他调用方传的都是合法串，行为不变。

## 不做的事

- **不动**未提交的 H5PL 工作（`src/cxx/Ana/libinc/PTH5PL.hh`、`libsrc/PTH5PL.cc`、
  `PTHDF5BinaryWrite.{hh,cc}`、scorer.py 的 `H5OutputHelper`）。
  给 H5PL 镜像 ScorerType 参数是以后单独的事。
- 不加 `pt_KillerMCPL_close` 之类的 finalize 绑定（产文件测试统一走 subprocess 模式）。

## 构建与回归

```bash
. env.sh && cimbuild -r
cd cinemabin
python -m pytest ../src/pythontests/test_prompt_scorer_class.py ../src/pythontests/test_mcplgun.py -v
```

（默认 ENTRY 不变，现有测试应全绿。）

## 冒烟验证

写一个小脚本 `tiny_pea.py`：H2O 球 + `MCPLOutHelper('k', ptstate='PEA_POST')` 挂在球体上 +
`IsotropicGun`：

```bash
prompt -g tiny_pea.py -s 113 -n 1e3
```

检查：

1. 控制台打印 "Added PEA_POST type scorer"（ResourceManager 注册信息）；
2. `k.mcpl.gz` 存在，`mcpltool k.mcpl.gz | head` 显示 nparticles ≫ 1000
   （每次碰撞 + 出体 + 吸收都记录）；
3. 时间量级为 ms（~1e0–1e2）→ 验证 time 单位修复生效。
