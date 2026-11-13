# Prompt

Prompt: Probability-Conserved Cross Section Biasing Monte Carlo Particle Transport System. 

Introduction of system can be found at [Computer Physics Communications](https://doi.org/10.1016/j.cpc.2023.109004).

## Python API quick start

The fastest way to get Prompt is the pre-built conda package:

```
conda install csns::cinema-prompt
```

Simulations are defined in Python: subclass `Prompt` (serial) or `PromptMPI` (MPI-parallel), build the geometry in `makeWorld()`, then run it with `simulate()`:

```python
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class Simulation(PromptMPI):
    def makeWorld(self):
        world = Volume("world", Box(50, 50, 210))
        sample = Volume("sample", Box(10, 10, 1), matCfg='Ge_sg227.ncmat')
        world.placeChild("sample", sample, transf=Transformation3D(0, 0, 100))
        tof = TOFHelper("TOF", ptstate='ABSORB')
        tof.make(sample)
        self.setWorld(world)

gun = UniModeratorGun()
gun.setSource([10, 10, -200])
gun.setSlit([5, 5, -20])

sim = Simulation()
sim.makeWorld()
sim.simulate(gun, 1e6)

hist = sim.gatherHistData("TOF")   # fetch the histogram by scorer name
hist.savefig("tof.png")            # quick matplotlib export
```

Without the last two lines the run leaves no persistent output: results live in memory only, so gather them (or call `sim.save_all_scorers()`) before the process exits.

A complete, runnable version of this example (a Germanium single-crystal slab with a TOF scorer) is [doc/example_basic.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py). The full documentation — your first simulation, geometry, guns, scorers, histogram analysis — lives in the [wiki](https://code.ihep.ac.cn/cinema-developers/cinema/-/wikis/home).

## Installation 

Pick a package by use case (all from the csns channel):

- **With visualization (desktop)** — adds pyvista with the Qt VTK flavor:
  interactive windows and GPU rendering when a display is available.

  ```
  conda install -c csns cinema-prompt-viz
  ```

- **Headless / server (x86)** — software-rendered VTK (osmesa) plus the
  trame web stack; works without X11, and `prompt ... --web` serves the
  visualisation in a browser.

  ```
  conda install -c csns cinema-prompt-viz-headless
  ```

- **Compute only, no visualization.**

  ```
  conda install -c csns cinema-prompt
  ```

Developers working on the source tree should use the [pixi workflow](#developers-guidelines) instead.

## Developers guidelines

The repository ships a `pixi.toml` that turns a fresh clone into a working dev
environment with two commands — no manual dependency installs. Dependencies
come from the same channel set as the conda package (csns + conda-forge), the
C++ extension builds incrementally, and the test suite runs hermetically.

Install pixi once (standalone binary, no conda required):

```
curl -fsSL https://pixi.sh/install.sh | sh
```

This puts `pixi` into `~/.pixi/bin`; reopen the shell so it is on `PATH`.
Then, from the repository root:

```
pixi install     # create .pixi/envs/default (re-installs are cache-fast)
pixi run build   # editable install + compile libprompt_core.so (ninja, incremental)
pixi run plugins # source-build the 3 NCrystal plugins (bzscope, sascsns, SANSND)
pixi run test    # full pytest suite (depends on build; runs with --forked)
```

Everyday commands:

| Command | Purpose |
|:--------|:--------|
| `pixi run build` | Rebuild after C++ edits; also stages the fresh `.so` into `src/python/Cinema/` so the loader never falls back to a stale build |
| `pixi run test` | `pytest src/pythontests -q --forked` with `CINEMAPATH`/`NCRYSTAL_DATA_PATH` preset — repo data and `ncmat/` files resolve automatically |
| `pixi run pytest src/pythontests/test_units.py -q --forked` | Run a single test file (skips the automatic rebuild of `test`) |
| `pixi run plugins` | (Re)install the NCrystal plugins; the two `code.ihep.ac.cn` ones need git credentials |
| `pixi shell` | Interactive shell with everything activated (compiler env vars included) |
| `pixi clean` | Remove the environment; `pixi install` recreates it quickly from the package cache |

Notes for this repository:

- `gcc` is pinned `<14` and `pytest` to `8.*` in `pixi.toml` — GCC 14+ breaks
  the current include set, and pytest 9 breaks `pytest-forked` (details in the
  manifest comments). Do not delete `pixi.lock` casually: a fresh solve jumps
  the toolchain to channel-latest and hits those breakages.
- All tasks scrub `PYTHONPATH`: one exported by an older source install would
  shadow this environment's numpy with a foreign Python build.
- `ncmat/` data files (e.g. `Cd.ncmat`) resolve through `NCRYSTAL_DATA_PATH`,
  which pixi activation exports for every task and for `pixi shell`.

## Runing simulations

> **Legacy (v1).** The GDML input workflow below (`prompt -g file.gdml`) and the auto-generated `*_view.py` plotting scripts are legacy v1 functionality, kept so that old workflows keep running. They must not be used for new work — define geometry, guns and scorers with the Python API above, which is the supported path.

### Input by GDML file
After installation, GDML formatted simulation input files can be launched by Prompt as   


```
prompt [-g file] [-s seed] [-n number] [-v]
```

| Option |  Defult  | Description |
|:-----:|:--------:|:------|
| -g   |  | Set GDML input file.  | 
| -s   |  4096  |   Set the seed for the random generator |
| -n   | 100 |    Set the number of primary neutron events |
| -v   |  | The flag to activate the visualisation |

Example of visualising the geometry defined in the total_scattering.gdml:
```
prompt -g total_scattering.gdml -v
```

The simulation will produce histogroms in the MCPL format only in the production run, if any scorers are specified. To run the simulation with 1e6 neutrons
```
prompt -g total_scattering.gdml -n 1e6
```

After the execution, seven histogrom files and accosiated python analysis template scripts will be generated. The reults can be plotted as 
```
python ScorerDeltaMomentum_PofQ_HW_view.py
```

There are many input examples are available in the gdml sub-directory. 


<h3 align="left">Connect with us:</h3>
<p align="left"><a href="mailto:cinema-users@outlook.com">cinema-users@outlook.com</a>
</p>
