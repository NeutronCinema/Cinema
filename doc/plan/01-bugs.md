# Phase 0 — 现存 bug 清单与修复建议

> 全部已对照当前工作区源码逐一确认（2026-09-04，分支 `feat-pod-source-sampling`）。
> 行号为当前工作区行号。

## Bug 1（单位，必修）— KillerMCPL 写 MCPL 时 time 漏 s→ms 转换

**位置**：`src/cxx/MCPL/libsrc/PTMCPLBinaryWrite.cc:112`

```cpp
//time in milliseconds:
m_particleInFile->time = p.getTime();        // ← :112，漏了 *1e3
```

- 所在重载 `write(const Particle &p, int scatterNumber)` 是 **KillerMCPL 唯一走的一条路径**
  （`PTKillerMCPL.cc:43/46`）。
- Prompt 内部时间单位是**秒**（`PTUnitSystem.hh`），MCPL 规范要求**毫秒**——注释写着
  "time in milliseconds:" 但代码没转。
- 另一重载 `write(const Particle&)` 在 `:155` 是正确的：`p.getTime()*1e3`。

**影响**（已逐一扫描 `scripts/` 下所有读 mcpl time 的脚本，2026-09-04）：

文件里存的数值 = 真实时间的**秒数**，但 MCPL 规范承诺该字段是**毫秒** → 文件不合规范。
下游分裂成三类：

| 类 | 脚本 | 行为 | 现状 |
|---|---|---|---|
| a. 不读 time（多数） | `scripts/TMR/kdsgen.py`、`scripts/sans_csns/monitor/kdsgen.py`（geometry 只有 Energy/Lethargy+SurfXY）、`surfsrc.py`、`primary.py`、`mcplplotter.py` | 不消费 time 字段 | 不受影响 |
| b. 把数值**当秒**用（与 bug 意外自洽，违反规范） | `scripts/prompt_mantid/examples/sxd/ana_multscatt.py:16-18`、`abs_abs.py:16-17` | `pb.time` 直接填 TOF 直方图，xlabel "Time-of-Flight, s"，量程 2e-5–4e-2 s | 目前物理上碰巧对；**修复 C++ 后会错 1000×，需补 ×1e-3** |
| c. 按规范**当 ms** 用（真错） | C++ `MCPLGun`（`time*Unit::ms`）及其用户 `scripts/tmr_and_sans/tmrsans.py`（MCPLGun+TOFHelper）、`scripts/bl9/*`；`scripts/px_ml_generator.py`（`kds.geom.Decade()` 用 var=7，按 ms 取 log10） | 回放/变换时间 = 真实/1000 | **TOF 被压 1000×**（Decade 尺度差 3 个 decade；训练/采样同源时 KDE 内部自洽但语义错） |

**决策（2026-09-04，用户拍板）：不修**。理由：规范输出可以直接用 `write(const Particle&)`
（`:132`，单位全对 ×0.1/×1e-6/×1e3）这条重载来写 mcpl。已在 `:89` 重载上方加 fixme 注释说明
（该 hunk 已暂存）：

```cpp
//fixme: this overload writes time in seconds (p.getTime()), violating the MCPL
//millisecond convention - the write(const Particle&) overload below converts
//correctly (*1e3). Kept as-is because existing output files and downstream
//scripts interpret the stored value as seconds. Use write(const Particle&)
//for spec-compliant mcpl output.
```

**对本 POD 管线的直接后果（重要）**：
- KillerMCPL 产出的文件 time 字段存的是**秒**（不合规范）——`podfield.py` 读取时
  **不能**按规范 ×1e-3；time 单位要做成显式参数（`time_unit='s'` 为 KillerMCPL 文件默认，
  `'ms'` 用于规范文件如 `mcplout.py` 写出的），并在 `field.npz` meta 里记录。
- (b) 类 sxd 脚本维持现状（把值当秒用，与本行为自洽）。
- (c) 类 `MCPLGun` 直接回放 KillerMCPL 文件的时间仍是真实值 1/1000——若管线要用
  `MCPLGun` 复演 KillerMCPL 原始文件，需在生成端或复演端做补偿（另行决策）。

---

## Bug 2（注释/文档错）— polarisation[2] 注释称 MeV 实为 eV

**位置**：`src/cxx/MCPL/libsrc/PTMCPLBinaryWrite.cc:125`

```cpp
m_particleInFile->polarisation[2] = (p.getEKin0()-p.getEKin()); // energy loss in MeV   ← 注释错
```

- `getEKin()` 返回 Prompt 内部单位 **eV**，存进去的值就是 eV。
- 读者按注释当 MeV 解释 → 差 1e6 倍。
- `src/python/Cinema/Prompt/mcpl.py` 里 PTMCPL 的 `differential_energy` 字段同样没标单位。

**修复**：只改注释/文档为 eV，**不改存储值**（改值会再破坏一批旧文件兼容）。

---

## Bug 3（ABI 损坏，本管线绕开）— `files.py` 的 MCPL python 写绑定多重损坏

**位置**：`src/python/Cinema/Prompt/files.py:43-58`

三个独立问题：

| # | 问题 | 细节 |
|---|---|---|
| a | struct 定义错 | `files.py:51` `userflags=c_uint64`，C 端是 `uint32_t`（`external/mcpl/install/include/mcpl.h:51`）；且缺 `_pack_=1`（mcpl.h:37 `#pragma pack(push,1)`）→ python 结构 120 字节 vs C 端 packed 104 字节，偏移/大小全错 |
| b | 按值/按指针不匹配 | `files.py:57` 把 write 绑定成 `[type_voidp, POINTER(MCPLParticle)]`，但 C 端 `pt_MCPLBinaryWrite_write(void* obj, mcpl_particle_t par)`（`src/cxx/Python/libsrc/PTMCPL.cc:35`）**按值**收 struct → argtype 不符，调用即 `ArgumentError`；即使强行传，指针位模式会被 C 端当 struct 内容解读 |
| c | 假 reader 绑定 | `files.py:58` `_pt_MCPLBinaryWrite_read = importFunc('pt_MCPLBinaryWrite_write', POINTER(MCPLParticle), [type_voidp])` —— 把**写函数**重复绑定为"读函数"（C 端不存在任何 reader）→ 调用即崩 |

**修复策略**：本管线**不修它**——Phase 4 的 `mcplout.py` 用 ctypes 直包 `libmcpl.so`
（按 mcpl.h 正确 packed 定义 104 字节 struct）。
`files.py` 可另开小 PR 修（`_pack_=1` + `c_uint32` + 按值 argtypes + 删假 read 绑定），
不混入本管线。

**另注意**：C++ 侧 `write(const mcpl_particle_t&)`（`PTMCPLBinaryWrite.cc:85`，memcpy 路径）
**无任何单位转换**——调用方必须自己提供 cm/MeV/ms 原生单位的 struct。

---

## Bug 4（健壮性，随 Phase 1 修）— `ParticleTracingState.from_string` 静默回落 ENTRY

**位置**：`src/python/Cinema/Prompt/scorer.py:97`

```python
return mapping.get(state_str.upper(), cls.ENTRY)   # 未知串不报错，静默变 ENTRY
```

- `ptstate='PEA_POSS'` 之类拼错不报错，按 ENTRY 记录 → 数据为空/错却极难排查。

**修复**：未知串直接 `raise ValueError`（用 `mapping[...]` 或显式检查）。

---

## Bug 5（文档，随新 reader 修）— PTMCPL 无单位转换且文档误导

**位置**：`src/python/Cinema/Prompt/mcpl.py`

- pip `mcpl` 包返回 MCPL **原生单位 cm/MeV/ms**；PTMCPL 不做任何转换，
  字段命名（及旧 docstring）暗示 Prompt 单位（mm/eV/s）。
- 用户按 mm/eV/s 使用 → 位置差 10 倍、能量差 1e6 倍。

**修复**：PTMCPL docstring 明确标注 MCPL 原生单位；
实际转换统一放在新模块 `podfield.py`（常量唯一出处 `CM2MM, MEV2EV, MS2S = 10.0, 1e6, 1e-3`）。

---

## 功能缺口（非 bug，Phase 1 主改动）— KillerMCPL 硬编码 ENTRY

**位置**：`src/cxx/Ana/libsrc/PTKillerMCPL.cc:25`

```cpp
:Scorer1D("KillerMCPL_"+name, Scorer::ScorerType::ENTRY, ...)   // ← 硬编码
```

- 基类 `Scorer1D` ctor 本就接受 `ScorerType`；加一个默认参数即可选 PEA_POST。
- C++ 路由（`ResourceManager::addScorer` / `ActiveVolume` 的 PEA 分发）**已就绪，无需改**。
- 附加约束：`kill=True` 配 PEA_POST 会在**首次碰撞**即杀粒子（propagate_post 每次碰撞触发）
  → python 端必须拒绝该组合。

修复方案见 [02-cpp-changes.md](02-cpp-changes.md)。
