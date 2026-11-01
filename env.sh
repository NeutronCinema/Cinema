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

# Repo-root paths the test suite relies on (geonav/gidi ctest cases read data
# relative to these): CINEMAPATH locates libprompt_core.so, NCRYSTAL_DATA_PATH
# exposes the bundled ncmat files. Explicit exports win over the implicit
# fallbacks; unset them to override with your own locations.
_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export CINEMAPATH="${CINEMAPATH:-$_root}"
export NCRYSTAL_DATA_PATH="${NCRYSTAL_DATA_PATH:-$_root/ncmat}"
unset _root

echo -e "Enjoy!"
