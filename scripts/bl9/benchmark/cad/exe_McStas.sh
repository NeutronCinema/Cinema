#!/bin/bash

##### Input #####
INPUT='kds_bl9'    # McStas istrument name, without .instr
OutDir='mcstas' # Directory where execute simulation and store output files
N=1E8          # Number of particles to 
# KDSource install prefix (holds lib/ and mcstas/contrib/KDSource.comp);
# point KDSOURCE_PREFIX at your installation.
KDSourceLibPath="${KDSOURCE_PREFIX:?KDSOURCE_PREFIX must point at your KDSource install prefix}"
### End Input ###

# Execute McStas
rm -rf $OutDir
export LD_LIBRARY_PATH=$KDSourceLibPath/lib
cp $KDSourceLibPath/mcstas/contrib/KDSource.comp .
mcrun -c $INPUT --dir=$OutDir -n $N --format=NeXus
rm KDSource.comp $INPUT.c $INPUT.out
echo Simulation ended successfully