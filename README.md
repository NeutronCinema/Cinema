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
### Install pre-built conda package on linux

```
conda install csns::cinema-prompt
```

### Install from source on Linux(Ubuntu)

#### Use native linux envrionment manager `apt`

Use `apt` cml to manage prerequisites:
```
sudo apt install g++ cmake python3-dev python3-pip python3-venv libxml2-dev libhdf5-dev libfftw3-dev libopenmpi-dev libgl1
```

Clone the source and compile it as

```
git clone https://code.ihep.ac.cn/cinema-developers/cinema.git
cd cinema
. env.sh
cimbuild -r
```

#### Use conda envrionment manager `conda`

Use `conda` cml to manage prerequisites:
```
conda create -n pt python=3.10 
conda activate pt
conda install cxx-compiler=1.10 cmake make=4.3 fftw unzip openmpi libxml2 xerces-c=3.2.4 mpi4py hdf5=1.12 matplotlib pyvista vtkbool vtk=*=qt*
```

Then source `env.sh`
```
. env.sh
```

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
