# Cinema/Prompt — start here

**Cinema/Prompt** ("Prompt") is a Monte-Carlo neutron particle-transport code built around
probability-conserving cross-section biasing: interaction cross sections can be scaled up or down
at will while a per-particle weight correction keeps the sampled physics exactly unbiased, so you
can spend compute where it matters (deep penetration, rare events, long instrument paths) without
distorting the result. A full description of the method was published in
[Computer Physics Communications](https://doi.org/10.1016/j.cpc.2023.109004)
(doi:10.1016/j.cpc.2023.109004).

Prompt is driven from Python: you write a short script that subclasses `Prompt` (serial) or
`PromptMPI` (MPI-parallel), build your geometry, materials, scorers and particle gun with Python
objects, then call `show()` to inspect or `simulate()` to run. Everything in this wiki follows that
Python API.

## Key capabilities at a glance

| Area | What you get |
|:---|:---|
| Materials | NCrystal physics from NCMAT files via config strings: crystals, single crystals with mosaicity and orientation, virtual materials (`freegas::`, `solid::` compounds), temperature/density overrides |
| Biasing | Probability-conserving `scatter_bias` / `abs_bias` on cross sections, implicit-capture absorption in weight — the unbiased histogram is preserved (regression-tested by direct comparison against unbiased runs) |
| Geometry | VecGeom-backed volumes: CSG solids (Box, Tube, Sphere, Cone, Polyhedron, Ellipsoid, tessellated shapes, ...), boolean solids, nested assemblies, rotated placements via `Transformation3D` |
| Scorers | Time-of-flight, energy/wavelength spectra, 1D/2D position-sensitive detectors, volume fluence, S(Q), S(Q,w), energy deposition, multi-scattering counters, MCPL particle output |
| Guns | Built-in primary generators (moderated and Maxwellian beams, isotropic, MCPL file input) plus `PythonGun` for custom numpy-vectorised sources |
| MCPL I/O | Read and write MCPL particle files, both as gun source and scorer output |
| MPI | `PromptMPI` splits events across ranks with independent per-rank seeds and collective histogram reduction |
| Visualisation | Interactive 3-D geometry and trajectory viewing with pyvista (`sim.show(gun, n)`) |
| Tuning | Optuna-based parameter optimisation (`Cinema.Prompt.parameterOptimizer.Optimiser`) for scanning/tuning simulation parameters |
| Analysis | Histogram classes with automatic error propagation and merging, plus interpolation on their array views (`CinemaArray`/`CinemaXYZ`); post-processing of MCPL and `.h5` outputs |

A typical application: beamline scientists model neutron scattering instruments — moderators,
guides, choppers, samples, detectors — with NCrystal describing the sample physics and scorers
recording what the detectors would see.

## A minimal simulation in five minutes

This is [doc/example_basic.py](https://code.ihep.ac.cn/cinema-developers/cinema/-/blob/master/doc/example_basic.py),
the canonical starter script — a Germanium single-crystal slab with a time-of-flight scorer, lit by
a moderated beam:

```python
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.physics import Material
from Cinema.Prompt.solid import Box
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.scorer import TOFHelper
from Cinema.Prompt.gun import UniModeratorGun

class Simulation(PromptMPI):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        # material defined in an NCrystal config string
        nccfg = 'Ge_sg227.ncmat;mos=0.0267deg;dir1=@crys_hkl:5,1,1@lab:0,0,1;dir2=@crys_hkl:0,1,-1@lab:1,0,0'
        mat = Material(nccfg)

        # volume defined with shape, size and material
        vol = Volume("sampleSolid", Box(10, 10, 1), matCfg=mat.cfg)

        # TOF scorer/counter, made capable of scoring neutrons absorbed by real physics
        tof = TOFHelper("TOF", ptstate='ABSORB')
        tof.make(vol)

        # coordinate transformation in the simulation world
        trf = Transformation3D(0, 0, 100).applyRotX(45)

        # world volume, then place the sample inside it
        world = Volume("world", Box(50, 50, 210))
        world.placeChild("samplePhyVol", vol, transf=trf)
        self.setWorld(world)

if __name__ == "__main__":
    gun = UniModeratorGun()
    gun.setSource([10, 10, -200])
    gun.setSlit([5, 5, -20])

    sim = Simulation()
    sim.makeWorld()

    # to visualize geometry + 100 trajectories (interactive window)
    sim.show(gun, 100)
    # or to run in production
    # sim.simulate(gun, 1e7)
```

The pattern is always the same five steps: subclass `PromptMPI`, build materials and volumes in
`makeWorld()`, attach scorers, place the geometry into a world, then feed a gun to `show()` or
`simulate()`. After a `simulate()` you read results with
`hist = sim.gatherHistData('TOF')` and e.g. `hist.savefig('tof.png')`.

For scale: this example transports 1e5 neutrons in about 0.4 s of transport time (about 3 s
including process start-up; measured on the development machine with the default seed 4096), so
the commented-out `sim.simulate(gun, 1e7)` production run takes roughly 40 s of transport time.

Continue with [Your first simulation](first-simulation) for a line-by-line walkthrough.

## The one rule: Python API first

> **Legacy notice.** Defining simulations through GDML input files (`prompt -g file.gdml`) is
> legacy v1 functionality, kept only so old workflows keep running. It is not covered by this wiki
> and must not be used for new work — define geometry, guns and scorers in Python as shown above.

## Quickstart

The fastest way to a working Prompt on Linux is the pre-built conda package:

```bash
conda install csns::cinema-prompt
python -c "from Cinema.Prompt import PromptMPI; print('ok')"
```

Source builds (with apt or conda prerequisites) are documented on
[Installation and environments](install).

## Wiki map

### Getting started

- [home](home) — this page
- [Installation and environments](install) — conda package, source builds, what `env.sh` does
- [Your first simulation](first-simulation) — line-by-line walkthrough, running and scaling it

### Tutorials

- [SANS with the SasCSNS plugin](tutorial-sans) — worked small-angle-scattering tutorial building on *Your first simulation*

### Reference

- [The Simulation class: lifecycle, seeds, MPI and outputs](simulation-lifecycle)
- [Geometry: volumes, solids and transformations](geometry)
- [Materials and physics](materials-physics)
- [Scoring: measuring particles](scorers)
- [Particle guns](guns)
- [The command line: `prompt` and `ptplot`](cli)
- [Visualisation: geometry and trajectory viewing](visualization)
- [Units and conversions](units)
- [Analysing results: histograms, MCPL files and error propagation](results-analysis)

### Advanced

- [Running at scale: MPI, seeds and parameter scans](mpi-scale)
- [Frequently asked questions](faq)
- [Adjacent research modules](adjacent-research-modules) — Tak, BzScope (formerly PiXiu), Experiment.Analyser

> **Planned pages.** The following pages are planned but do not exist yet; they are listed by name
> only: parameter-optimization (the `Optimiser`), ncrystal-plugins, legacy-gdml, dev-notes.

## Versioning and support

- This wiki documents **Cinema 2.0.0a5**, as reported by `Cinema.__version__`
  (`src/python/Cinema/__init__.py`). That dynamic version is what package builds use; the
  plain-text `Version` file at the repository root currently reads `v2.0.1` and may disagree with
  it — trust `Cinema.__version__`.
- Source repository: <https://code.ihep.ac.cn/cinema-developers/cinema>
  (`git clone https://code.ihep.ac.cn/cinema-developers/cinema.git`).
- Method paper: [Computer Physics Communications, doi:10.1016/j.cpc.2023.109004](https://doi.org/10.1016/j.cpc.2023.109004).
- Questions and support: **cinema-users@outlook.com**.
