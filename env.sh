#!/bin/bash
# --- deprecated -----------------------------------------------------------
# The legacy source-install flow (env.sh + install.sh + cimbuild) is being
# retired. To USE prompt:  conda install -c csns cinema-prompt
# To DEVELOP on the source tree: pixi (README, "Developers guidelines").
# Source this file only if you deliberately need the legacy flow.
# Non-interactive stdin (CI) defaults to abort.
echo "WARNING: env.sh (legacy source-install environment) is deprecated."
echo "         Use 'conda install -c csns cinema-prompt' to run prompt, or the"
echo "         pixi workflow in README.md (Developers guidelines) to develop."
read -r -p "Continue with the deprecated env.sh flow anyway? [y/N] " _envsh_ack || true
case "${_envsh_ack:-}" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."
       return 1 2>/dev/null || exit 1
       ;;
esac
unset _envsh_ack
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
