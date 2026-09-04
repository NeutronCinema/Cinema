#!/usr/bin/env python3
"""
端到端测试：pyvista 建网格 → MCPL scorer 记录 → MeshScorer 读取 → POD 重构 → 抽样

流程：
1. 用 pyvista 创建一个简单的 3D 体网格（包含源区域）
2. 设置 Prompt 模拟：一个源、一个探测器（带 MCPL 输出）
3. 运行 MC 模拟，产生 mcpl 文件
4. 用 MeshScorer 读取 mcpl，bin 到网格，按时间分割
5. 导出 FunctionsList 给 pyforce
6. 用 POD 截断去噪
7. 提取源区域子网格，抽样

运行方式：
    cd scripts/pod_source_sampling
    python test_pipeline.py
"""

import numpy as np
import pyvista as pv

# 创建网格
def create_test_grid():
    """
    创建一个简单的 3D 体网格（六面体网格），包含：
    - 体网格：10×10×10 的六面体网格，范围 [-50, 50] mm
    - 源区域：中心附近的小体网格（3×3×3 cells）
    """
    # 均匀六面体网格
    grid = pv.UniformGrid(
        dims=(11, 11, 11),  # 10×10×10 cells
        spacing=(10.0, 10.0, 10.0),  # 10 mm 每个 cell
        origin=(-50.0, -50.0, -50.0)
    )

    # 转换为非结构化网格（pyforce 需要 UnstructuredGrid）
    ugrid = grid.cast_to_unstructured_grid()

    # 找到源区域 cell（中心 3×3×3 区域）
    cell_centers = np.array(ugrid.cell_centers().points)
    mask = (
        (np.abs(cell_centers[:, 0]) <= 15) &
        (np.abs(cell_centers[:, 1]) <= 15) &
        (np.abs(cell_centers[:, 2]) <= 15)
    )
    source_cell_indices = np.where(mask)[0]

    print(f"Grid created: {ugrid.n_cells} cells, {ugrid.n_points} points")
    print(f"Source region: {len(source_cell_indices)} cells (center 30×30×30 mm³)")

    return ugrid, source_cell_indices


def setup_prompt_simulation():
    """
    设置 Prompt 模拟：
    - 世界：大 Box
    - 源：各向同性点源，在网格中心
    - MCPL 记录器：记录所有进入世界盒子的粒子
    """
    from Cinema.Prompt import PromptMPI
    from Cinema.Prompt.geo import Volume, Transformation3D
    from Cinema.Prompt.solid import Box
    from Cinema.Prompt.gun import SimpleThermalGun
    from Cinema.Prompt.scorer import MCPLOutHelper, ParticleTracingState

    class TestSim(PromptMPI):
        def __init__(self, seed=4096, output_dir='.'):
            super().__init__(seed)
            self.output_dir = output_dir

        def makeWorld(self):
            # 世界盒子：100×100×100 mm³
            world_box = Box(100, 100, 100)
            self.world = Volume('World', world_box)

            # 设置世界为真空（默认材料）
            self.setWorld(self.world)

            # 添加 MCPL 记录器：记录所有进入世界的粒子
            mcpl_scorer = MCPLOutHelper(
                name='detMCPL',
                pdg=2112,  # 中子
                groupID=0,
                kill=False,  # 不杀死粒子，记录后继续追踪
                compress=True
            )
            mcpl_scorer.make(self.world)

        def setGun(self):
            # 简单热中子源，在中心位置
            gun = SimpleThermalGun()
            gun.setWavelength(1.8)  # Å
            gun.setPosition([0, 0, 0])  # 中心
            gun.setDirection([0, 0, 1])  # 沿 z 方向
            return gun

    return TestSim


def main():
    import os
    import tempfile
    import shutil

    # 创建临时目录
    tmpdir = tempfile.mkdtemp(prefix='pod_test_')
    print(f"Working directory: {tmpdir}")

    try:
        # ===== Step 1: 创建网格 =====
        print("\n" + "="*60)
        print("Step 1: Create pyvista grid")
        print("="*60)
        grid, source_indices = create_test_grid()

        # ===== Step 2: 运行 Prompt 模拟 =====
        print("\n" + "="*60)
        print("Step 2: Run Prompt simulation")
        print("="*60)
        # 注意：模拟需要在 Prompt 环境内运行
        # 这里只做结构展示，实际模拟需要 prompt 命令
        print("To run the simulation:")
        print(f"  cd {tmpdir}")
        print("  prompt -g test_pipeline.py -n 100000")
        print()

        # 保存网格供后续使用
        grid_path = os.path.join(tmpdir, 'test_grid.vtk')
        grid.save(grid_path)
        print(f"Grid saved to {grid_path}")

        # ===== Step 3: 模拟完成后处理 mcpl =====
        print("\n" + "="*60)
        print("Step 3: Read mcpl with MeshScorer")
        print("="*60)

        mcpl_path = os.path.join(tmpdir, 'detMCPL_pro0.mcpl.gz')
        if os.path.exists(mcpl_path):
            from pod_source_sampling.mesh_scorer import MeshScorer

            # 读取网格
            grid = pv.read(grid_path)

            # 创建 MeshScorer
            scorer = MeshScorer(grid, gdim=3)

            # 读取 mcpl，按 50 个时间 bin 分割
            scorer.read_mcpl(mcpl_path, n_time_bins=50)

            # 查看快照矩阵
            X = scorer.snapshot_matrix
            print(f"Snapshot matrix shape: {X.shape}")  # (N_cells, 50)

            # ===== Step 4: 导出 FunctionsList =====
            print("\n" + "="*60)
            print("Step 4: Export to FunctionsList")
            print("="*60)
            fl, pod = scorer.to_functionslist(field_name='fluence')
            print(f"FunctionsList: {fl.shape()[0]} dofs, {fl.shape()[1]} snapshots")

            # ===== Step 5: POD 分解 =====
            print("\n" + "="*60)
            print("Step 5: POD decomposition")
            print("="*60)

            # 方案 A：用 pyforce 的 POD 类（L² 加权）
            pod.fit(fl, verbose=True)
            K = 10
            pod.compute_basis(fl, rank=K)
            print(f"Computed {K} POD modes")

            # 方案 B：直接用 numpy SVD
            print("\n-- Alternative: numpy SVD --")
            U, S, Vt = np.linalg.svd(X, full_matrices=False)
            energy = np.cumsum(S**2) / np.sum(S**2)
            K2 = np.searchsorted(energy, 0.99) + 1
            print(f"Energy: 99% with {K2} modes (out of {len(S)})")

            # ===== Step 6: 重构 =====
            print("\n" + "="*60)
            print("Step 6: Reconstruct and extract source region")
            print("="*60)

            # 用 numpy SVD 重构
            U_K = U[:, :K2]
            coeffs = np.diag(S[:K2]) @ Vt[:K2, :]
            X_denoised = U_K @ coeffs  # (N_cells, 50)

            # 提取源区域 - 使用所有时间步的平均值
            source_field = scorer.extract_subgrid(source_indices, time_idx=None)
            print(f"Source region field: {len(source_field)} cells, "
                  f"mean={source_field.mean():.4f}, "
                  f"std={source_field.std():.4f}")

            # ===== Step 7: 抽样 =====
            print("\n" + "="*60)
            print("Step 7: Sample from source region")
            print("="*60)

            positions, weights = scorer.sample_source(
                source_indices,
                time_idx=None,
                n_particles=10000
            )
            print(f"Sampled {len(positions)} particles")
            print(f"Position range: "
                  f"x [{positions[:, 0].min():.1f}, {positions[:, 0].max():.1f}], "
                  f"y [{positions[:, 1].min():.1f}, {positions[:, 1].max():.1f}], "
                  f"z [{positions[:, 2].min():.1f}, {positions[:, 2].max():.1f}]")

        else:
            print(f"mcpl file not found: {mcpl_path}")
            print("Run the simulation first, then re-run this script.")
            print("Simulation command:")
            print(f"  cd {tmpdir}")
            print("  prompt -g test_pipeline.py -n 100000")

    finally:
        print(f"\nTemp directory: {tmpdir}")
        print("Clean up with: rm -rf", tmpdir)


if __name__ == '__main__':
    main()
