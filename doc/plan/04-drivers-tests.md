# Phase 5–6 — 驱动脚本、测试与验证

## Phase 5 — `scripts/pod_source_sampling/` 驱动脚本

### `run_moderator.py` — 慢化器模拟（PEA_POST 记录）

仿 `scripts/TMR/simpleModerator.py`（PromptMPI + para-H 慢化器 + Al 壳）：

```python
scorer = MCPLOutHelper('podsrc', kill=False, ptstate='PEA_POST')
moderator_volume.addScorer(scorer)      # 挂材料体（CHM + Al 壳）
```

**决策点（脚本头注释记录）**：scorer 挂**材料体**——PEA_POST 场是碰撞密度，
真空区只有边界穿越记录（点在面上，不构成体场）。备选（文档化）：给真空区充稀释气体。

运行：

```bash
prompt -g run_moderator.py --gun MyGun -n 1e7            # 或 mpirun 走 PromptMPI
python ../merge_mcpl.py podsrc -o podsrc                  # 合并 per-rank 文件
```

### `pod_denoise.py` — 读取 → binning → POD

```
--mcpl 'podsrc*.mcpl.gz'  --grid grid_spec.json
--time-bins 100  --energy-ratio 0.99  [--center]  [--train-fraction 0.5]
```

- 网格：`pv.ImageData` 覆盖慢化器 bbox（json/py spec 给 origin/dimensions/spacing）。
- `--train-fraction 0.5`：半数文件（MPI rank 切分）训练、半数验证 → 真 out-of-sample
  截断误差曲线。
- 输出 `field.npz`：snapshot / recon / time_edges / grid spec / meta（trigger、单位、
  k、energy_ratio、neg_clip_fraction、各文件名）。
- 诊断图：能量谱、截断误差曲线、若干时间切片（raw vs 重构）、neg-clip 比例。

### `sample_source.py` — 场采样

```
--field field.npz  --n 1e6  -o sampled.mcpl.gz  [--time-mode raw]  [--seed 42]
```

用 `PODSourceSampler` + `MCPLOutWriter` 写出。

### `replay_validate.py` — 下游三路对比

下游几何（guide + 探测器，TOF / WlSpectrum / PSD scorers），三路跑：

1. 完整慢化器直跑（金标准，贵）；
2. `MCPLGun(raw.mcpl.gz)` 直接回放（基线：衡量"记录-回放"本身的信息损失）；
3. `MCPLGun(sampled.mcpl.gz)` POD 采样源（本方案）。

对比输出：探测器谱叠加图、每 time-bin 相对误差、χ²/dof 表。
2 与 3 的差 = POD 管线引入的误差；1 与 2 的差 = 记录触发方式的系统差。

**注意**：`MCPLGun` 在记录位置生成粒子 → 复演几何必须有一个 vacuum 体覆盖源区
（粒子从体积中部出发；ENTRY 对出生体积不触发的 caveat 不影响下游 scoring）。

## Phase 6 — pytest 测试（`src/pythontests/`）

| 文件 | 内容 |
|---|---|
| `test_podfield_binning.py` | 合成粒子打在 ImageData 上：`snapshot.sum()==weight.sum()`（网格外排除并计数）、cell/bin 索引正确、单位转换常数正确 |
| `test_pod.py` | 合成 rank-k 场：k 处精确重构、误差曲线单调不增、neg_clip_fraction 正确上报 |
| `test_mcplout_writer.py` | 已知粒子（mm/eV/s）写入 → pip `mcpl.MCPLFile` 读回，断言 cm/MeV/ms 往返、nparticles、gzip 产物 |
| `test_pod_source_sampling.py` | **集成，subprocess 模式**（见下） |

### 集成测试模式（重要）

MCPL 产出型 scorer 只在**进程退出**时 finalize（`~KillerMCPL` → `~ResourceManager`），
in-process 跑完拿不到完整文件 → 必须仿 `test_prompt_scorer.py` 用 subprocess：

```python
# tmp_path 里生成小脚本（H2O 球 + MCPLOutHelper('k', ptstate='PEA_POST') + IsotropicGun）
subprocess.run(['prompt', '-g', script, '-s', '113', '-n', '1e4'], cwd=tmp_path, check=True)
# 然后 in-process：bin → POD → 重构 → 采样 → 写 → 读回：
#   断言每 time-bin Σw 守恒（rtol 1e-6）、采样位置全在网格内、能量在 raw 支撑集内
#   再 in-process MCPLGun(sampled) 小复演，总权重与 raw 回放一致（统计容差内）
```

## 端到端验证命令

```bash
. env.sh && cimbuild -r
cd cinemabin

# 单元（Phase 2–4）
python -m pytest ../src/pythontests/test_podfield_binning.py \
                  ../src/pythontests/test_pod.py \
                  ../src/pythontests/test_mcplout_writer.py -v

# 集成（Phase 6）
python -m pytest ../src/pythontests/test_pod_source_sampling.py -v

# 端到端小规模
cd ../scripts/pod_source_sampling
prompt -g run_moderator.py --gun MyGun -n 1e6
python ../../scripts/merge_mcpl.py podsrc -o podsrc
python pod_denoise.py --mcpl 'podsrc*.mcpl.gz' --time-bins 50 --energy-ratio 0.99
python sample_source.py --field field.npz --n 1e5 -o sampled.mcpl.gz
python replay_validate.py
```

## 生产级验证（论文用）

- 1e7–1e8 histories，MPI 多 rank，`merge_mcpl.py` 合并；
- 半 rank 训练 / 半 rank 验证的截断误差曲线（out-of-sample）；
- 与 KDSource 链（`scripts/TMR/simpleModerator.py` → `kdsgen.py` → source.xml → MCPLGun）
  同场景对比：重构精度、采样速度、下游谱偏差；
- 上报：neg-clip 比例、网格外粒子比例、每 time-bin 计数（噪声水平）。
