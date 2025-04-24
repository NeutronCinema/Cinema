# Prompt

Prompt: Probability-Conserved Cross Section Biasing Monte Carlo Particle Transport System. 

Introduction of system can be found at [arXiv](https://arxiv.org/abs/2304.06226).

## Installing on Linux(Ubuntu) from source

### With native linux envrionment

To build Prompt, several prerequisites are needed.
```
sudo apt install g++ cmake python3-dev python3-pip python3-venv libxml2-dev libhdf5-dev libfftw3-dev libopenmpi-dev libgl1
```

Clone the source and compile it as

```
git clone https://gitlab.com/cinema-developers/prompt.git
cd prompt
. env.sh
cimbuild
```

### With conda envrionment

Use `conda` cml to manage prerequisites:
```
conda create -n tmp python=3.10 cxx-compiler cmake make=4.3 fftw unzip openmp
```

Then source `env.sh`
```
. env.sh
```

## Installing on Linux with pip

```
pip install neutron-cinema
```


## Runing Prompt simulations

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
