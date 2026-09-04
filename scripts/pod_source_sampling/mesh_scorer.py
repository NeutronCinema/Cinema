"""
MeshScorer: 将 mcpl 粒子态 bin 到 pyvista 网格，按时间步分割成快照。

用法：
    from pod_source_sampling.mesh_scorer import MeshScorer
    import pyvista as pv

    # 创建网格
    grid = pv.UnstructuredGrid(...)

    # 创建 scorer，读取 mcpl 并 bin
    scorer = MeshScorer(grid, gdim=3)
    scorer.read_mcpl('output.mcpl', n_time_bins=100)

    # 获取快照矩阵
    X = scorer.snapshot_matrix  # (N_cells, N_time_bins)

    # 导出 FunctionsList（pyforce 兼容）
    fl = scorer.to_functionslist()
"""

import numpy as np
import pyvista as pv
from Cinema.Prompt.mcpl import PTMCPL


class MeshScorer:
    """
    将 mcpl 粒子态 bin 到 pyvista 网格，按时间步分割成快照。

    Parameters
    ----------
    grid : pv.UnstructuredGrid
        pyvista 网格，粒子将被 bin 到 cell 上。
    gdim : int, optional
        几何维度，2 或 3，默认 3。
    """

    def __init__(self, grid: pv.UnstructuredGrid, gdim: int = 3):
        self.grid = grid
        self.gdim = gdim
        self.n_cells = grid.n_cells

        # 计算 cell 体积/面积（用于 POD 的 L² 加权）
        cell_sizes = grid.compute_cell_sizes()
        if gdim == 2:
            self.cell_sizes = np.array(cell_sizes['Area'], dtype=np.float64)
        elif gdim == 3:
            self.cell_sizes = np.array(cell_sizes['Volume'], dtype=np.float64)
        else:
            raise ValueError(f"gdim must be 2 or 3, got {gdim}")

        # 快照矩阵：形状 (N_cells, N_time_bins)
        self._snapshot_matrix = None
        self._time_bin_edges = None
        self._mcpl_files = []

    # ──────────────────────────────────────────────
    # 核心流程：mcpl → bin → 快照矩阵
    # ──────────────────────────────────────────────

    def read_mcpl(self, filename: str, n_time_bins: int = 100,
                  time_range: tuple = None, verbose: bool = True):
        """
        读取一个 mcpl 文件，按时间 bin 分割成快照。

        Parameters
        ----------
        filename : str
            mcpl 文件路径。
        n_time_bins : int, optional
            时间 bin 数，默认 100。
        time_range : tuple, optional
            时间范围 (t_min, t_max)，自动推断。
        verbose : bool, optional
            是否打印进度信息。
        """
        if verbose:
            print(f"Reading {filename}...")

        file = PTMCPL(filename)

        # 1. 收集所有粒子的数据
        all_positions = []
        all_weights = []
        all_times = []

        for pb in file.particle_blocks:
            if len(pb.ekin) == 0:
                continue

            pos = np.array(pb.position)
            if pos.ndim == 1:
                pos = pos.reshape(-1, 3)
            w = np.array(pb.weight, dtype=np.float64)
            t = np.array(pb.time, dtype=np.float64)

            if len(pos) > 0:
                all_positions.append(pos)
                all_weights.append(w)
                all_times.append(t)

        if len(all_positions) == 0:
            if verbose:
                print(f"  Warning: No particles found in {filename}")
            return

        positions = np.vstack(all_positions)
        weights = np.concatenate(all_weights)
        times = np.concatenate(all_times)

        # 2. 确定时间范围
        if time_range is None:
            t_min, t_max = times.min(), times.max()
        else:
            t_min, t_max = time_range

        # 3. 创建时间 bin 边界
        bin_edges = np.linspace(t_min, t_max, n_time_bins + 1)
        time_bin_indices = np.digitize(times, bin_edges) - 1
        time_bin_indices = np.clip(time_bin_indices, 0, n_time_bins - 1)

        # 4. 粒子 → cell 映射
        cell_ids = self._find_cells(positions)
        mask = cell_ids >= 0
        cell_ids = cell_ids[mask]
        weights = weights[mask]
        time_bin_indices = time_bin_indices[mask]

        if len(cell_ids) == 0:
            if verbose:
                print(f"  Warning: No particles fall inside the grid")
            return

        # 5. 填充快照矩阵
        if self._snapshot_matrix is None:
            # 初始化：所有 cell × 所有时间 bin
            self._snapshot_matrix = np.zeros((self.n_cells, n_time_bins), dtype=np.float64)
            self._time_bin_edges = bin_edges
        else:
            # 累加到已有矩阵上
            if self._snapshot_matrix.shape[1] != n_time_bins:
                raise ValueError(
                    f"Time bin count mismatch: existing {self._snapshot_matrix.shape[1]}, "
                    f"new {n_time_bins}"
                )

        np.add.at(self._snapshot_matrix, (cell_ids, time_bin_indices), weights)

        self._mcpl_files.append(filename)

        if verbose:
            n_in = mask.sum()
            n_total = len(mask)
            print(f"  Binned {n_in}/{n_total} particles into "
                  f"{self.n_cells} cells × {n_time_bins} time bins")

    def read_mcpl_many(self, file_list: list, n_time_bins: int = 100,
                       time_range: tuple = None, verbose: bool = True):
        """
        读取多个 mcpl 文件并累加。

        Parameters
        ----------
        file_list : list
            mcpl 文件路径列表。
        n_time_bins : int, optional
            时间 bin 数。
        time_range : tuple, optional
            时间范围。
        verbose : bool, optional
            是否打印进度信息。
        """
        for f in file_list:
            self.read_mcpl(f, n_time_bins=n_time_bins,
                           time_range=time_range, verbose=verbose)

    # ──────────────────────────────────────────────
    # 粒子 → grid cell 映射
    # ──────────────────────────────────────────────

    def _find_cells(self, positions: np.ndarray) -> np.ndarray:
        """
        找到每个粒子位置所在的 cell ID。

        Parameters
        ----------
        positions : np.ndarray
            粒子位置，形状 (N, 3)。

        Returns
        -------
        cell_ids : np.ndarray
            每个粒子所在的 cell ID，不在网格内的标记为 -1。
        """
        try:
            # 先用 pyvista 的 select_enclosed_points 找到在网格内的点
            # 再加 find_cells_within_points
            cells_dict = self.grid.find_cells_within_points(positions)
        except Exception as e:
            print(f"  Warning: find_cells_within_points failed ({e}), "
                  f"falling back to brute-force")
            return self._find_cells_bruteforce(positions)

        n_particles = positions.shape[0]
        cell_ids = np.full(n_particles, -1, dtype=np.int32)

        for cell_id, point_indices in cells_dict.items():
            cell_ids[point_indices] = cell_id

        return cell_ids

    def _find_cells_bruteforce(self, positions: np.ndarray) -> np.ndarray:
        """
        暴力搜索：对每个粒子，遍历所有 cell 检查是否在边界框内。
        """
        n_particles = positions.shape[0]
        cell_ids = np.full(n_particles, -1, dtype=np.int32)

        # 预计算每个 cell 的边界框
        bounds = np.array([
            self.grid.get_cell_bounds(i) for i in range(self.n_cells)
        ])

        for i in range(n_particles):
            pos = positions[i]
            for c in range(self.n_cells):
                b = bounds[c]
                if (b[0] <= pos[0] <= b[1] and
                        b[2] <= pos[2] <= b[3] and
                        b[4] <= pos[4] <= b[5]):
                    cell_ids[i] = c
                    break

        return cell_ids

    # ──────────────────────────────────────────────
    # 导出接口
    # ──────────────────────────────────────────────

    @property
    def snapshot_matrix(self) -> np.ndarray:
        """
        快照矩阵，形状 (N_cells, N_time_bins)。
        """
        if self._snapshot_matrix is None:
            raise ValueError("No snapshots available. Call read_mcpl() first.")
        return self._snapshot_matrix

    @property
    def time_bin_edges(self) -> np.ndarray:
        """
        时间 bin 边界，形状 (N_time_bins + 1,)。
        """
        if self._time_bin_edges is None:
            raise ValueError("No time bins available.")
        return self._time_bin_edges

    def to_functionslist(self, field_name: str = 'u'):
        """
        将快照矩阵导出为 pyforce 兼容的 FunctionsList。

        Parameters
        ----------
        field_name : str, optional
            字段名，默认 'u'。

        Returns
        -------
        fl : FunctionsList
            pyforce 的 FunctionsList 对象，每列是一个快照。
        pod : pyforce.offline.pod.POD
            POD 对象（需要先设置 grid）。
        """
        try:
            from pyforce.tools.functions_list import FunctionsList
            from pyforce.offline.pod import POD
            from pyforce.tools.backends import IntegralCalculator
        except ImportError:
            raise ImportError(
                "pyforce is required. Install it with: pip install pyforce"
            )

        X = self.snapshot_matrix

        fl = FunctionsList(dofs=self.n_cells)
        for i in range(X.shape[1]):
            fl.append(X[:, i].copy())

        # 创建 POD 对象
        calculator = IntegralCalculator(self.grid, gdim=self.gdim)
        pod = POD(grid=self.grid, gdim=self.gdim, varname=field_name)
        pod.calculator = calculator

        return fl, pod

    def extract_subgrid(self, cell_indices: np.ndarray, time_idx: int = None):
        """
        从快照矩阵中提取子网格的场值（用于抽样）。

        Parameters
        ----------
        cell_indices : np.ndarray
            子网格在全场网格中的 cell ID 数组。
        time_idx : int, optional
            时间步索引。如果 None，返回所有时间步的平均值。

        Returns
        -------
        field : np.ndarray
            子网格上的场值。
        """
        X = self.snapshot_matrix

        if time_idx is not None:
            return X[cell_indices, time_idx]
        else:
            return X[cell_indices, :].mean(axis=1)

    def sample_source(self, cell_indices: np.ndarray,
                      time_idx: int = None,
                      n_particles: int = 100000,
                      subgrid: pv.UnstructuredGrid = None):
        """
        从源区域子网格中抽样粒子。

        Parameters
        ----------
        cell_indices : np.ndarray
            源区域在全场网格中的 cell ID 数组。
        time_idx : int, optional
            时间步索引。None 则使用所有时间步的平均值。
        n_particles : int, optional
            抽样粒子数。
        subgrid : pv.UnstructuredGrid, optional
            子网格（用于亚网格采样）。如果 None，只从 cell 中心抽样。

        Returns
        -------
        positions : np.ndarray
            粒子位置，形状 (n_particles, 3)。
        weights : np.ndarray
            粒子权重，形状 (n_particles,)。
        """
        field = self.extract_subgrid(cell_indices, time_idx)

        # 获取 cell 面积/体积
        if subgrid is not None:
            sizes = np.array(
                subgrid.compute_cell_sizes()['Volume' if self.gdim == 3 else 'Area'],
                dtype=np.float64
            )
            centers = np.array(subgrid.cell_centers().points)
        else:
            sizes = self.cell_sizes[cell_indices]
            centers = np.array(self.grid.cell_centers().points)[cell_indices]

        # 构建 CDF
        weights = field * sizes
        weights = np.maximum(weights, 0)  # 确保非负
        if weights.sum() == 0:
            raise ValueError("Zero total weight in source region")
        weights /= weights.sum()

        cdf = np.cumsum(weights)

        # 抽样
        r = np.random.uniform(0, 1, n_particles)
        indices = np.searchsorted(cdf, r)

        positions = centers[indices]
        particle_weights = np.ones(n_particles)

        return positions, particle_weights


if __name__ == '__main__':
    print("MeshScorer module loaded successfully.")
    print("Usage: from pod_source_sampling.mesh_scorer import MeshScorer")
