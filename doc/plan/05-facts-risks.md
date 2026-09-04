# 已核实关键事实与风险对策

## 一、已核实关键事实（实现时直接引用，勿重复探索）

### 触发机制

- `KillerMCPL` 硬编码 `ScorerType::ENTRY`（`PTKillerMCPL.cc:25`）；基类 `Scorer1D`
  ctor 本就收 `ScorerType`（`PTScorer1D.hh:32`）→ 只需加默认参数。
- `ResourceManager::addScorer`（`PTResourceManager.cc:196-201`）按 `getType()` 分发；
  PEA_POST → propagate_post + exit + absorb 三列表，**C++ 路由无需改**。
- `scorePropagatePost` 仅 `if(sameVolume && scattered)`（`PTActiveVolume.cc:359`）→
  **PEA_POST 无吸收双记**（PEA_PRE 有，FIXME 在 `:350`）。
- ENTRY 对出生体积不触发（`PTLauncher.cc:131` `if(!isFirstStep)`）。
- `kill=True` + PEA_POST → 首次碰撞即杀 → python helper 拒绝该组合。
- python `ParticleTracingState.value_num` 与 C++ 枚举 int 一致（SURFACE=0 … ABSORB=7）。

### 单位（最高风险区）

| 端 | pos | ekin | time |
|---|---|---|---|
| Prompt 内部 | mm | eV | s |
| MCPL 文件（规范） | cm | MeV | ms |
| `MCPLGun::generate()`（canonical 往返，`PTMCPLGun.cc:84-96`） | ×10 | ×1e6 | ×1e-3 |
| pip `mcpl` 读回 | cm | MeV | ms（**无转换**） |

- `PTMCPL`（`src/python/Cinema/Prompt/mcpl.py`）不做转换，docstring 标 mm/eV 是**错的**。
- `MCPLBinaryWrite::write(const Particle&)`（`:155`）正确 ×0.1/×1e-6/×1e3；
  `write(const Particle&, int)`（KillerMCPL 路径）pos/ekin 对、**time 漏 ×1e3**（`:112`）。
- 新管线转换常量唯一出处：`podfield.py` 的 `CM2MM, MEV2EV, MS2S`。

### MCPL python 写路径

- pip `mcpl`（mcpl-core）**无写 API**（只有 MCPLFile/MCPLParticle/MCPLParticleBlock 读侧）。
- repo `files.py` 的绑定 ABI 损坏（按值 vs 指针、userflags uint64、假 read 绑定）→ 不用。
- **推荐**：ctypes 直包 `libmcpl.so`——`libprompt_core.so` 已 NEEDED 它（soname 就是
  `libmcpl.so`），Cinema.Interface 加载主库后 `ctypes.CDLL("libmcpl.so")` 命中同一镜像。
- `mcpl_particle_t`：`#pragma pack(push,1)`，字段序 ekin / polarisation[3] / position[3] /
  direction[3] / time / weight / pdgcode(int32) / userflags(uint32)，**packed 104 字节**
  （`external/mcpl/install/include/mcpl.h:37-54`）。

### 测试模式

- MCPL 产出 scorer 只在进程退出 finalize（`~KillerMCPL`；scorer 在 `~ResourceManager`
  才销毁，`PTResourceManager.cc:13-24`）→ **产文件测试必须 subprocess `prompt -g`**
  （模式见 `test_prompt_scorer.py`）；纯 python 模块测试可 in-process。
- `prompt -g x.py`：脚本须恰含一个 Prompt/PromptMPI 子类 + ≥1 个 Gun 子类；
  `--gun ClassName` 选 gun，ctor 参数变 `--param` 选项；`-s` 种子、`-n` 粒子数。

### 其它

- pyvista 0.45：`DataSet.find_containing_cell(points)` 接受 (N,3) 矩阵，向量化返回 int 数组。
- MPI → per-rank 文件 `name_pro{rank}.mcpl.gz`；`scripts/merge_mcpl.py`（`pt_merge_mcpl`）合并。
- KillerMCPL 存储默认单精度（`enable_double=false`），polarisation + userflags 开启。
- `src/python/Cinema/Prompt/Mesh.py` 是工作区里的 ABI 损坏旧版回滚——**绝不 import**。
- 环境：`. env.sh`（CINEMAPATH/PATH/PYTHONPATH）；构建 `cimbuild -r`；
  库在 `cinemabin/src/cxx/libprompt_core.so`；pytest 规范 cwd 是 `cinemabin/`。

## 二、风险与对策

| # | 风险 | 对策 |
|---|---|---|
| 1 | **单位错误**（10×/1e6×/1e3×） | 转换常量只在 podfield/mcplout；双向往返测试；time 修复改变旧文件语义 → MR + field.npz meta 写明 |
| 2 | legacy `files.py` 写绑定 ABI 损坏 | 不用；新 ctypes wrapper；files.py 修复另开小 PR 不混入 |
| 3 | **真空欠采样**：PEA_POST 场是碰撞密度（∝Σφ）非注量；真空只得边界记录 | scorer 挂材料体（默认）；稀释气体填充为文档化备选；trigger 记入 meta；对相对采样权重无影响 |
| 4 | **文件体积**：每碰撞都记，1e8 histories → GB 级 | 单精度已默认；限定挂载体积；开发期 1e5–1e6；gzip（默认 compress=True）；流式分块读 |
| 5 | **POD 负值**（截断引入） | clip 到 0 并上报 neg_clip_fraction；比例大 → 提高 k 或关 centering |
| 6 | **POD 全局谱被近源高计数区支配**（MC 噪声异方差：方差 ∝ 计数） | 截断误差只在源区 mask 上算；首选 rank 切分 out-of-sample 误差；必要时方差稳定化加权（后续研究项） |
| 7 | MPI 多 rank 文件 | glob `*_pro*` 或先 merge；rank 切分做训练/验证 |
| 8 | in-process 不 finalize | 所有产文件测试/驱动走 subprocess `prompt -g` |
| 9 | 网格/数据不匹配 | 统计并警告网格外粒子比例；要求 grid bbox ⊇ 源区 |
| 10 | 时间平均抹掉脉冲结构 | 每 time-bin 独立场（不做全时段平均）；bin 宽 ≤ 脉冲结构尺度 |

## 三、与旧实现（已删除 `mesh_scorer.py`）的教训对照

| 旧实现问题 | 新设计对策 |
|---|---|
| `_find_cells_bruteforce` 用 `pos[4]`（越界）、y/z 界互换 | 向量化索引算术 / `find_containing_cell`，无暴力法 |
| scorer 挂世界体 → ENTRY 不触发 → 空 mcpl | 挂材料体 + PEA_POST；测试断言 nparticles > histories |
| 无单位转换 | podfield/mcplout 双端转换 + 往返测试 |
| time 记录本身有 bug（:112） | Phase 1 先修 |
