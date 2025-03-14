#!/bin/bash
# --set options
PREFIX="https://code.ihep.ac.cn/cinema-developers/"
while getopts ":f" option
  do
    case "${option}"
     in
      f) echo "Running: "${PREFIX};;
      *) PREFIX="https://code.ihep.ac.cn/cinema-developers/";;
    esac
done
if (( $OPTIND == 1 )); then
  PREFIX="https://code.ihep.ac.cn/cinema-developers/"
fi 
NUMCPU=$(grep ^cpu\\scores /proc/cpuinfo | uniq |  awk '{print $4}')

#remove previously sourced env
function cinema_prunepath() {
    P=$(IFS=:;for p in ${!1}; do [[ $p != ${2}* ]] && echo -n ":$p" || :; done)
    export $1=${P:1:99999}
}

if [ ! -z ${CINEMAPATH:-} ]; then
    cinema_prunepath PATH "$CINEMAPATH/cinemabin"
    cinema_prunepath LD_LIBRARY_PATH "$CINEMAPATH/cinemabin:$CINEMAPATH/src/python/bin"
    cinema_prunepath DYLD_LIBRARY_PATH "$CINEMAPATH/cinemabin"
    cinema_prunepath PYTHONPATH "$CINEMAPATH/src/python;$CINEMAPATH/src/python/ptgeo/python"
    cinema_prunepath NCRYSTAL_PLUGIN_LIST
    cinema_prunepath NCRYSTAL_DATA_PATH
    echo "Cleaned up previously defined Cinema enviorment"
fi

unset cinema_prunepath

function findSetEnv(){
  if [ -f $CINEMAPATH/cinemabin/envCache.txt ]; then
    while IFS=" " read -r name value; do
      export "${name}=${value}"
    done < $CINEMAPATH/cinemabin/envCache.txt 
    for i in "$@"; do
      if [ ! -v "$i" ];then
        echo "Not set ..."
        return 2
        break
      fi
    done
    return 0
  else
    return 2
  fi
}

export CINEMA_LOCAL_BUILD=1
export CINEMAPATH="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#install ncrystal
export response='y'
if [ ! -f $CINEMAPATH/external/ncrystal/install/lib/libNCrystal.so ]; then
  # read -r -p "Do you want to install NCrystal into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
      if [ ! -d $CINEMAPATH/external ]; then
        mkdir $CINEMAPATH/external
      fi
      cd $CINEMAPATH/external
      if [ -d ncrystal ]; then
        rm -rf ncrystal
      fi
      git clone ${PREFIX}/ncrystal.git ncrystal
      cd -
      mkdir $CINEMAPATH/external/ncrystal/build && cd $CINEMAPATH/external/ncrystal/build
      cmake  -DCMAKE_INSTALL_PREFIX=$CINEMAPATH/external/ncrystal/install ..
      make -j ${NUMCPU} && make install
      cd -
      echo "installed  ncrystal"
    else
      echo "Found ncrystal"
    fi
    eval $( $CINEMAPATH/external/ncrystal/install/bin/ncrystal-config --setup)  
    export NCRYSTAL_DATA_PATH="$CINEMAPATH/ncmat:$CINEMAPATH/external/ncystal/install/share/Ncrystal/data"
  else
    eval $( $CINEMAPATH/external/ncrystal/install/bin/ncrystal-config --setup)  
    export NCRYSTAL_DATA_PATH="$CINEMAPATH/ncmat:$CINEMAPATH/external/ncystal/install/share/Ncrystal/data"
    echo "NCrystal config done"
fi

if [ -f $CINEMAPATH/external/ncrystal/install/lib/libNCrystal.so ]; then
  if [ ! -f $CINEMAPATH/external/ncplugin-BzScope/testcode/utils/cache/bld/libNCPlugin_PiXiu.so ]; then
    echo "Installing ncplugin-BzScope"
    cd $CINEMAPATH/external
    git clone ${PREFIX}/ncplugin-BzScope.git
    cd -
    cd $CINEMAPATH/external/ncplugin-BzScope
    . testcode/utils/bootstrap.sh 
    ncpluginbuild
    cd -
  fi
  echo "Found ncplugin-BzScope"
  . $CINEMAPATH/external/ncplugin-BzScope/testcode/utils/bootstrap.sh 
  export NCRYSTAL_PLUGIN_LIST="$CINEMAPATH/external/ncplugin-BzScope/testcode/utils/cache/bld/libNCPlugin_BzScope.so:$NCRYSTAL_PLUGIN_LIST"
fi

#MCPL
if [ ! -f $CINEMAPATH/external/mcpl/install/lib/libmcpl.so ]; then
  # read -r -p "Do you want to install MCPL into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
      if [ ! -d $CINEMAPATH/external ]; then
        mkdir $CINEMAPATH/external
      fi
      cd $CINEMAPATH/external
      if [ -d mcpl ]; then
        rm -rf mcpl
      fi
      git clone ${PREFIX}/mcpl.git
      cd -
      # MCPL is not built as it will be built in the KDSource
      mkdir $CINEMAPATH/external/mcpl/build && cd $CINEMAPATH/external/mcpl/build
      cmake  -DCMAKE_INSTALL_PREFIX=$CINEMAPATH/external/mcpl/install ..
      make -j ${NUMCPU} && make install
      cd -
      # echo "Cloned MCPL, not built"
  fi
  else
    echo "Found MCPL"
fi

#install libxerces
if [ ! -f $CINEMAPATH/external/xerces-c/install/lib/libxerces-c.so ]; then
  # read -r -p "Do you want to install libxerces into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
      if [ ! -d $CINEMAPATH/external ]; then
        mkdir $CINEMAPATH/external
      fi
      cd $CINEMAPATH/external
      if [ -d xerces-c ]; then
        rm -rf xerces-c
      fi
      git clone -b v3.2.3 --single-branch ${PREFIX}/xerces-c.git
      cd -
      mkdir $CINEMAPATH/external/xerces-c/build && cd $CINEMAPATH/external/xerces-c/build
      cmake  -DCMAKE_INSTALL_PREFIX=$CINEMAPATH/external/ncrystal/install ..
      cmake -DBUILD_SHARED_LIBS=ON -Dnetwork=OFF -Dextra-warnings=OFF  -DCMAKE_INSTALL_PREFIX=$CINEMAPATH/external/xerces-c/install ..
      make -j ${NUMCPU} && make install
      cd -
      echo "installed  libxerces"
  fi
  else
    echo "Found libxerces"
fi

# KDSource 
# 1st check if libxml2 is installed, if not install version 2.9.3, as required by KDSource
# 2nd install KDSource
findSetEnv PROMPT_LIBXML2_LIB
if [ $? -eq 0 ]; then
  echo "LIBXML2 path read from environment variable cache"
elif find /lib -name *libxml2.so | grep -q . ; then
  export PROMPT_LIBXML2_LIB="$(dirname $(find /lib -name *libxml2.so -print -quit))"
elif find $CINEMAPATH/external/libxml2-2.9.3/local -name *libxml2.so | grep -q .; then
  export PROMPT_LIBXML2_LIB=$CINEMAPATH/external/libxml2-2.9.3/local
else
  echo "libxml2 missing! Installing to "${CINEMAPATH}"/external"
  cd $CINEMAPATH/external
  wget https://download.gnome.org/sources/libxml2/2.9/libxml2-2.9.3.tar.xz
  tar xf libxml2-2.9.3.tar.xz
  cd -
  cd $CINEMAPATH/external/libxml2-2.9.3/
  if [ ! -d $CINEMAPATH/external/libxml2-2.9.3/local ]; then
    mkdir $CINEMAPATH/external/libxml2-2.9.3/local
  fi
  ./configure --prefix=$CINEMAPATH/external/libxml2-2.9.3/local --with-python=off
  make -j ${NUMCPU} && make install
  export PROMPT_LIBXML2_LIB=$CINEMAPATH/external/libxml2-2.9.3/local
  cd -
fi
if [ ! -f $CINEMAPATH/external/KDSource/install/lib/libkdsource.so ]; then
  # read -r -p "Do you want to install KDSource into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
      if [ ! -d $CINEMAPATH/external ]; then
        mkdir $CINEMAPATH/external
      fi
      cd $CINEMAPATH/external
      if [ -d KDSource ]; then
        rm -rf KDSource
      fi
      git clone ${PREFIX}/KDSource.git
      cd -

      # should in fact use git clone --recurse-submodules ${PREFIX}/KDSource.git
      # but we don't have access to github 90% of the time
      cp -rf $CINEMAPATH/external/mcpl $CINEMAPATH/external/KDSource

      # # git clone --recurse-submodules ${PREFIX}/KDSource.git
      # cd $CINEMAPATH/external/KDSource
      # git clone ${PREFIX}/mcpl.git
      # cd -
      
      mkdir  $CINEMAPATH/external/KDSource/build $CINEMAPATH/external/KDSource/install && cd $CINEMAPATH/external/KDSource/build
      # rm -rf $CINEMAPATH/external/KDSource/mcpl
      # ln -s $CINEMAPATH/external/mcpl $CINEMAPATH/external/KDSource/
      cmake  -DCMAKE_INSTALL_PREFIX=$CINEMAPATH/external/KDSource/install -DCMAKE_PREFIX_PATH=$PROMPT_LIBXML2_LIB -DCMAKE_BUILD_TYPE=RELEASE ..
      make -j ${NUMCPU} && make install
      cd -
      cd $CINEMAPATH/external/KDSource/python
      pip install .
      cd -
      echo "installed  KDSource"
  fi
  else
    echo "Found KDSource"
fi


#install VecGeom
if [ ! -f $CINEMAPATH/external/VecGeom/install/lib/libvecgeom.a ]; then
  # read -r -p "Do you want to install VecGeom into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    if [ ! -d $CINEMAPATH/external ]; then
      mkdir $CINEMAPATH/external
    fi
    cd $CINEMAPATH/external
    if [ -d VecGeom ]; then
      rm -rf VecGeom
    fi
    # git clone  -b  v2.0.0-rc2 --single-branch https://code.ihep.ac.cn/caixx/VecGeom.git
    git clone --branch cinema https://code.ihep.ac.cn/caixx/VecGeom.git
    cd -

    mkdir $CINEMAPATH/external/VecGeom/build && cd $CINEMAPATH/external/VecGeom/build
    # patch $CINEMAPATH/external/VecGeom/persistency/gdml/source/src/Middleware.cpp < $CINEMAPATH/external/vecgoem1.2.0_Middleware_cpp.patch
    # patch $CINEMAPATH/external/VecGeom/persistency/gdml/source/include/Middleware.h < $CINEMAPATH/external/vecgeom1.2.0_Middleware_h.patch
    cmake -DXercesC_INCLUDE_DIR=$CINEMAPATH/external/xerces-c/install/include   -DVECGEOM_BUILTIN_VECCORE=ON -DVECGEOM_FAST_MATH=OFF -DBUILD_TESTING=OFF -DXercesC_LIBRARY_RELEASE=$CINEMAPATH/external/xerces-c/install/lib/libxerces-c.so -DCMAKE_INSTALL_PREFIX=$CINEMAPATH/external/VecGeom/install -DVECGEOM_GDML=ON -DVECGEOM_USE_NAVINDEX=ON  ..
    make -j${NUMCPU} && make install
    cd -
    echo "installed  VecGeom"
  fi
  else
    echo "Found VecGeom"
fi

# gidiplus
# first check&install hdf5 
findSetEnv PROMPT_HDF5_LIB PROMPT_HDF5_HEADER PROMPT_HDF5_PATH
if [ $? -eq 0 ]; then
  echo "HDF5 path read from environment variable cache"
elif find /usr -name *hdf5.so | grep -q . ; then
  export PROMPT_HDF5_LIB="$(dirname $(find /usr -name *hdf5.so -print -quit))"
  # there are cases where lib and header not in the same well-setup directory tree like .../bin .../include .../lib, so another find cml
  export PROMPT_HDF5_HEADER="$(dirname $(find /usr -name *hdf5.h -print -quit))"
  export PROMPT_HDF5_PATH="$(dirname $(dirname $(find /usr -name *hdf5.so -print -quit)))"
elif find $CINEMAPATH/external/hdf5-1.12.2/local -name *hdf5.so | grep -q .; then
  export PROMPT_HDF5_LIB=$CINEMAPATH/external/hdf5-1.12.2/local/lib
  export PROMPT_HDF5_HEADER=$CINEMAPATH/external/hdf5-1.12.2/local/include
  export PROMPT_HDF5_PATH=$CINEMAPATH/external/hdf5-1.12.2/local/
else
  echo "HDF5 missing! Installing to "$CINEMAPATH"/external"
  cd $CINEMAPATH/external
  wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.12/hdf5-1.12.2/src/hdf5-1.12.2.tar.gz
  tar xvf hdf5-1.12.2.tar.gz
  cd -
  cd $CINEMAPATH/external/hdf5-1.12.2
  if [ ! -d $CINEMAPATH/external/hdf5-1.12.2/local ]; then
    mkdir $CINEMAPATH/external/hdf5-1.12.2/local
  fi
  ./configure --prefix=$CINEMAPATH/external/hdf5-1.12.2/local
  make -j${NUMCPU} && make install
  cd -
  export PROMPT_HDF5_LIB=$CINEMAPATH/external/hdf5-1.12.2/local/lib
  export PROMPT_HDF5_HEADER=$CINEMAPATH/external/hdf5-1.12.2/local/include
  export PROMPT_HDF5_PATH=$CINEMAPATH/external/hdf5-1.12.2/local/
fi
export PROMPT_HDF5_DIR="$PROMPT_HDF5_PATH;$PROMPT_HDF5_LIB;$PROMPT_HDF5_HEADER"

if [ ! -f $CINEMAPATH/external/gidiplus/lib/libgidiplus.a ]; then
  # read -r -p "Do you want to install gidiplus into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    if [ ! -d $CINEMAPATH/external ]; then
      mkdir $CINEMAPATH/external
    fi
    cd $CINEMAPATH/external
    if [ -d gidiplus ]; then
      rm -rf gidiplus
    fi
    git clone -b master --single-branch ${PREFIX}/gidiplus.git
    cd -
    cd $CINEMAPATH/external/gidiplus
    # wget https://github.com/zeux/pugixml/releases/download/v1.13/pugixml-1.13.zip 
    # mv pugixml-1.13.zip Misc
    make -s -j${NUMCPU} SHELL=bash CXXFLAGS="-std=c++11 -fPIC"  CFLAGS="-fPIC" HDF5_PATH=${PROMPT_HDF5_PATH} HDF5_LIB=${PROMPT_HDF5_LIB} HDF5_INCLUDE=${PROMPT_HDF5_HEADER}
    cd -
    echo "installed gidiplus"
  fi
  else
    echo "Found gidiplus"
fi

if [ -f $CINEMAPATH/src/python/Cinema/__init__.py ]; then
  export PYTHONPATH="$CINEMAPATH/src/python:$CINEMAPATH/src/python/ptgeo/python:$PYTHONPATH"
  echo "Added Cinema python module into path"
else
  echo "Can not find Cinema python module"
fi


if [ ! -d $CINEMAPATH/cinemabin ]; then
  mkdir $CINEMAPATH/cinemabin
  cd $CINEMAPATH/cinemabin
  cmake -DHDF5_ROOT=$PROMPT_HDF5_DIR .. 
  make -j${NUMCPU} 
  cd -
fi


if [ -d $CINEMAPATH/cinemabin ]; then
  export LD_LIBRARY_PATH="$CINEMAPATH/cinemabin:$LD_LIBRARY_PATH"
  export DYLD_LIBRARY_PATH="$CINEMAPATH/cinemabin:$DYLD_LIBRARY_PATH"
  export PATH="$CINEMAPATH/src/python/ptgeo/examples:$CINEMAPATH/cinemabin/bin:$CINEMAPATH/scripts:$PATH"
  echo "Added the cinemabin directory into environment"
fi

# Refresh cache file
> $CINEMAPATH/cinemabin/envCache.txt 

function writeEnv(){
  for i in "$@"; do
    eval echo "$i"" "'$'"$i" >> $CINEMAPATH/cinemabin/envCache.txt 
  done
}

writeEnv PROMPT_LIBXML2_LIB PROMPT_HDF5_LIB PROMPT_HDF5_PATH PROMPT_HDF5_DIR PROMPT_HDF5_HEADER


if [ -f $CINEMAPATH/cinemavirenv/bin/activate ]; then
  . $CINEMAPATH/cinemavirenv/bin/activate
else
  # read -r -p "Do you want install Cinema python virtual environment in $CINEMAPATH/cinemavirenv? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    python3 -m venv $CINEMAPATH/cinemavirenv
    . $CINEMAPATH/cinemavirenv/bin/activate
    if [[ $DOCKER == false ]]; then
      pip install -r $CINEMAPATH/requirement
    else
      echo "Python with Docker enviorment"
      pip install -r $CINEMAPATH/requirement
    fi
  fi
fi

if [ $OPENMCIN -eq 1 ]; then
  if [ ! -f $CINEMAPATH/external/openmc/local/lib/libopenmc.so ]; then
    if [ ! -d $CINEMAPATH/external ]; then
      mkdir $CINEMAPATH/external
    fi
    cd $CINEMAPATH/external
    if [ -d openmc ]; then
      # rm -rf openmc
      echo "Not doing anything"
    fi
    cd -
    . $CINEMAPATH/tools/scripts/linux/prompt_openmcInstall
    pip install NCrystal
    echo "OPENMC INSTALLED"
    export PATH=$CINEMAPATH/external/openmc/local/bin/:$PATH
  else
    echo "Found OPENMC"
    export PATH=$CINEMAPATH/external/openmc/local/bin/:$PATH
    echo "OPENMC executable added to PATH."
  fi
fi

#SSSP
if [ -f $CINEMAPATH/external/pixiusssp/SSSP_precision_pseudos/Cu.pbe-dn-kjpaw_psl.1.0.0.UPF ]; then
  export PIXIUSSSP=$CINEMAPATH/external/pixiusssp
else
  # read -r -p "Do you want (re)install the SSSP DFT pseudopotential into $CINEMAPATH/external? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    cd  $CINEMAPATH/external/
    git clone ${PREFIX}/pixiusssp.git
    cd -
    cd $CINEMAPATH/external/pixiusssp
    mkdir SSSP_precision_pseudos
    tar -xzvf SSSP_1.1.2_PBE_precision.tar.gz --directory SSSP_precision_pseudos
    cp Cu.pbe-dn-kjpaw_psl.1.0.0.UPF SSSP_precision_pseudos/
    rm SSSP_precision_pseudos/Cu_ONCV_PBE-1.0.oncvpsp.upf
    cd -
    export PIXIUSSSP=$CINEMAPATH/external/pixiusssp
  fi
fi

# add submodule and define the master branch as the one you want to track
if [ ! -f $CINEMAPATH/src/python/ptgeo/__init__.py ]; then
  echo "Clone ptgeo submodule"
  cd $CINEMAPATH/src/python
  # git submodule add https://gitlab.com/cinema-developers/ptgeo.git
  # git submodule init
  git submodule update --init --recursive
  cd -
fi


export PATH="$CINEMAPATH/src/python/ptgeo/examples:$PATH"
echo "Added the ptgeo example directory into environment"
