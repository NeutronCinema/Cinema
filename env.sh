#!/bin/bash
OPENMCIN=0
DOCKER=false
while getopts hi:x:do option
do
case "${option}"
in
    h) echo "$USAGE"
    exit 0;;
    x) INPUT=${OPTARG};;
    i) ARGS=${OPTARG};;
    d) DOCKER=true;;
    o) OPENMCIN=1;;
    *) echo "$USAGE"
      exit 0;;
esac
done


if ! hash cmake 2>/dev/null
then
    echo "cmake is required to continue the installation of Cinema"
    return
fi

if ! hash git 2>/dev/null
then
    echo "git is required to continue the installation of Cinema"
    return
fi

#if ! hash pw.x 2>/dev/null
#then
#    echo "pw.x is required to continue the installation of Cinema"
#    return
#fi
shift $(( $OPTIND-1 ))
. "$( dirname "${BASH_SOURCE[0]}" )"/install.sh

# NCrystal's python package locates libNCrystal.so via NCRYSTAL_LIB or an
# ncrystal-config found on PATH (NCrystal/_locatelib.py). This env leaves the
# conda env bin off PATH, so set NCRYSTAL_LIB explicitly, deriving the conda
# prefix from the ncrystal-pluginmanager path resolved in install.sh:
if [ -z "${NCRYSTAL_LIB:-}" ] && [ -n "${NCRYSTAL_PLUGINMANAGER:-}" ]; then
  _ncpm_bin="$( command -v "${NCRYSTAL_PLUGINMANAGER}" 2>/dev/null || true )"
  if [ -n "$_ncpm_bin" ]; then
    _ncpm_lib="$( dirname "$( dirname "$_ncpm_bin" )" )/lib/libNCrystal.so"
    [ -f "$_ncpm_lib" ] && export NCRYSTAL_LIB="$_ncpm_lib"
    unset _ncpm_lib
  fi
  unset _ncpm_bin
fi

alias pull='git pull --recurse-submodules'
# ln -s
echo -e "Enjoy!"
