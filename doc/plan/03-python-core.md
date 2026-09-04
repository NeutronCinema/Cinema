# Phase 2–4 — 包内核心模块 API 草案

> 全部放 `src/python/Cinema/Prompt/`，平铺模块风格（与 repo 惯例一致）。
> 依赖：numpy / scipy / pyvista / pip `mcpl`（只读）。
> 单位约定：**模块对外一律 Prompt 单位（mm / eV / s）**；与 MCPL 的转换只发生在
> `podfield.py`（读入）和 `mcplout.py`（写出）。

## Phase 2 — `podfield.py`：MCPL 读取 + 时间 bin + 网格装箱

```python
# MCPL<->Prompt 单位唯一出处（勿在别处重复定义）
CM2MM, MEV2EV, MS2S = 10.0, 1e6, 1e-3

@dataclass
class ParticleSet:
    """转换单位后的原始记录（Prompt 单位）。"""
    pos      # (N,3) mm
    dir      # (N,3) 单位向量
    ekin     # (N,)  eV
    time     # (N,)  s
    weight   # (N,)
    eventid  # (N,)  int （来自 userflags）
    scatnum  # (N,)  int（来自 polarisation[1]，诊断用）
    nfiles   # 元数据：来源文件数

def load_mcpl_arrays(filenames, max_particles=None) -> ParticleSet
    # 流式读 pip mcpl 的 particle_blocks（每块 1e4 粒子）；
    # pos*CM2MM, ekin*MEV2EV, time*MS2S；
    # 接受单文件 / 列表 / glob 模式串（如 'podsrc*.mcpl.gz'，覆盖 MPI per-rank 文件）。

def points_to_cells(grid, points_mm) -> (N,) int
    # 返回 cell 索引，网格外 = -1。
    # pv.ImageData / StructuredGrid：向量化索引算术
    #   np.floor((p - origin) / spacing) + 边界检查；
    # 其它 pv.DataSet：grid.find_containing_cell(points)（pyvista 0.45 向量化）。
    # 不做暴力法回退——不支持就 NotImplementedError。

class MeshField:
    """(cell × time-bin) 快照矩阵 + 供条件采样的原始记录。"""
    def __init__(self, grid, time_edges, trigger='PEA_POST')
        # time_edges: (N_t+1,) 秒，单调递增
    def fill(self, pset: ParticleSet)
        # cell_idx = points_to_cells(...); bin_idx = np.searchsorted(time_edges, t) - 1
        # np.add.at(snapshot_flat, cell_idx*N_t + bin_idx, weight)
    snapshot      # (N_cells, N_t) float64，权重和
    counts        # (N_cells, N_t) int，记录数（噪声诊断用）
    cell_volumes  # (N_cells,)，grid.compute_cell_sizes()
    n_outside     # int，网格外粒子数（警告阈值）
    trigger       # 元数据 str
    raw           # 供条件采样的原始记录（按 cell*N_t+bin 排序）：
                  #   cell_idx, bin_idx, dir(N,3), ekin, time, weight
```

## Phase 3 — `pod.py`：POD 去噪

```python
@dataclass
class PODResult:
    U                  # (N_cells, k) 空间模态
    sigma              # (k,) 奇异值
    Vt                 # (k, N_t) 时间模态
    mean               # (N_cells,) 或 None（center=True 时）
    energy_spectrum    # (k,) σ²/Σσ²
    cumulative_energy  # (k,) 累计占比
    meta               # 触发器/单位/网格信息

def pod_decompose(X, center=False) -> PODResult
    # N_cells > N_t（典型场景）时用 method of snapshots：
    #   eigh(X_centered.T @ X_centered) → V, σ；U = X_centered V / σ
    # 否则直接 np.linalg.svd(X_centered, full_matrices=False)。

def truncation_curve(podres, X_ref=None, source_mask=None) -> (ks, err)
    # 重构误差 vs 截断阶数 k。
    # X_ref：留出的另一半 MPI rank 数据 → 真 out-of-sample 误差（首选）；
    # 无 X_ref 时用自身重构误差（训练误差，偏乐观，标注清楚）。
    # source_mask：只在源区 cell（field>0）上算误差——全局误差会被近源高计数区支配。

def pod_reconstruct(podres, k=None, energy_ratio=0.99) -> np.ndarray
    # 按 k 或累计能量占比截断重构 (N_cells, N_t)；
    # 负值 clip 到 0，返回/记录 neg_clip_fraction（ clipping 偏置要上报）。
```

## Phase 4a — `mcplout.py`：ctypes 直包 libmcpl.so 的写出器

> 动机：pip `mcpl` 无写 API；repo 现有 `files.py` 绑定 ABI 损坏（见 01-bugs.md Bug 3）。
> `libmcpl.so` 已是 `libprompt_core.so` 的 NEEDED（soname 就是 `libmcpl.so`），
> Cinema.Interface 加载主库后 `ctypes.CDLL("libmcpl.so")` 解析到同一镜像，无路径硬编码。

```python
class MCPLParticle(Structure):
    _pack_ = 1                          # mcpl.h:37 pragma pack(push,1)
    _fields_ = [                        # 字段序严格按 mcpl.h:43-52，共 104 字节
        ("ekin", c_double),             # MeV
        ("polarisation", c_double * 3),
        ("position", c_double * 3),     # cm
        ("direction", c_double * 3),
        ("time", c_double),             # ms
        ("weight", c_double),
        ("pdgcode", c_int32),
        ("userflags", c_uint32),        # ← uint32，不是 uint64
    ]

class MCPLOutWriter:
    def __init__(self, filename, srcname='Prompt POD source sampler',
                 doubleprec=False, userflags=False, polarisation=False)
        # mcpl_create_outfile / mcpl_hdr_set_srcname / mcpl_enable_*
    def add_comment(self, text)          # mcpl_hdr_add_comment
    def write_batch(self, pos_mm, dir_, ekin_eV, time_s, weight, pdgcode=2112)
        # mm/eV/s → cm/MeV/ms（与 podfield 常量互逆）；复用一个 struct 实例逐个
        # mcpl_add_particle（C API 全是指针，干净）
    def close(self)                      # mcpl_closeandgzip_outfile
```

## Phase 4b — `sourcesampler.py`：从重构场采样完整源项

```python
class PODSourceSampler:
    def __init__(self, field: MeshField, recon: np.ndarray,
                 rng=None, min_pool=20, pool_neighbors=8)
        # p(cell, t) ∝ recon[c,t] * cell_volume[c]
        # scipy.spatial.cKDTree 建在已填充 cell 中心上；
        # 记录数 < min_pool 的稀疏 cell 池化最近 pool_neighbors 个邻居的 raw 记录。

    def sample(self, n_total, time_mode='raw') -> SampledSource
        # 位置：选中 cell 内均匀抖动（ImageData 精确均匀；UnstructuredGrid 用
        #   bbox-rejection + find_containing_cell 验证）
        # 方向/能量：从该 (cell,bin) 池化 raw 记录按权重有放回重采样
        # 时间：'raw' = 重采样 bin 内 raw 时间；'uniform' = U(bin)
        # 权重：bin 内均匀 w_t = W_raw_t / n_t，n_t ∝ W_raw_t
        #   → 每个 time-bin Σw 严格等于 raw 的 Σw（权重守恒，可断言）
```

## 设计要点

1. **权重守恒**是硬约束：采样后每 time-bin 的总权重必须等于 raw 记录的总权重
   （积分测试断言 rtol 1e-6）。这保证源项强度（每脉冲中子数）不变，POD 只重分布。
2. **条件采样**：POD 只去噪 (cell×t) 强度场；Ω/E 的条件分布直接用 raw 记录重采样——
   低维条件量不需要去噪，且保留全部物理关联（方向-能量-位置）。
3. **单位单一出处**：`podfield.py` 的三个常量 + `mcplout.py` 用其逆。PTMCPL docstring
   同步标注原生单位（Bug 5 修复）。
