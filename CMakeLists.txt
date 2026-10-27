cmake_minimum_required(VERSION 3.15 FATAL_ERROR)
project(cinema)
set(FIND_LIBRARY_USE_LIB64_PATHS TRUE)
# specify the C++ standard
set(CMAKE_CXX_STANDARD 17)

#Concurrent
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# ---- Dependency discovery --------------------------------------------------
# One route for every channel (conda env, system install, wheel build via
# scikit-build-core, dev tree): CMAKE_PREFIX_PATH is authoritative and the
# dev external/ layout is only a fallback hint. The old CINEMA_LOCAL_BUILD
# env fork is gone (install.sh still exporting it is an inert no-op).
#
# CINEMA_FETCH_DEPS:
#   AUTO (default) - use pre-installed forks when found; otherwise download
#                    them and build inside the CMake build tree (FetchContent
#                    for VecGeom/kdsource, make install4prompt for gidiplus)
#   OFF            - never download; missing forks are a hard error (conda
#                    builds set this: they consume the packaged forks)
set(CINEMA_FETCH_DEPS "AUTO" CACHE STRING
  "AUTO: build missing private forks in-tree; OFF: require them pre-installed")
set(VECGEOM_GIT_REPOSITORY "https://code.ihep.ac.cn/caixx/VecGeom.git" CACHE STRING "cinema VecGeom fork")
set(VECGEOM_GIT_TAG "cinema" CACHE STRING "cinema VecGeom fork ref")
set(KDSOURCE_GIT_REPOSITORY "https://code.ihep.ac.cn/cinema-developers/kdsource.git" CACHE STRING "kdsource fork")
set(KDSOURCE_GIT_TAG "pt" CACHE STRING "kdsource fork ref")
set(GIDIPLUS_GIT_REPOSITORY "https://code.ihep.ac.cn/cinema-developers/gidiplus.git" CACHE STRING "gidiplus fork")
set(GIDIPLUS_GIT_TAG "pt" CACHE STRING "gidiplus fork ref")

# VecGeom (cinema fork; ships VecGeomConfig.cmake when installed).
# The dev-tree external/ layout is a hint for DEV builds only: a wheel
# build (SKBUILD) run from a configured dev checkout must not silently
# link the dev tree's forks — env prefixes and FetchContent are the only
# sources there. Stale find-cache entries from a dev configure are wiped
# for the same reason.
if(NOT SKBUILD)
  list(APPEND CMAKE_PREFIX_PATH
    "${CMAKE_SOURCE_DIR}/external/VecGeom/install"
    "${CMAKE_SOURCE_DIR}/external/xerces-c/install"
  )
else()
  unset(VecGeom_DIR CACHE)
  unset(mcpl CACHE)
  unset(KDS_LIB CACHE)
  unset(KDS_LIB_FILE CACHE)
  unset(GIDIPLUS_LIB CACHE)
  unset(GIDIPLUS_LIB_FILE CACHE)
  unset(GIDIPLUS_INCDIR CACHE)
endif()
find_package(VecGeom ${VecGeom_VERSION} QUIET)
if(NOT VecGeom_FOUND)
  if(NOT CINEMA_FETCH_DEPS STREQUAL "AUTO")
    message(FATAL_ERROR
      "VecGeom not found and CINEMA_FETCH_DEPS=OFF: install the cinema fork "
      "packages (conda: vecgeom/kdsource/gidiplus from the "
      "cinema-prompt-feedstock channel) or point CMAKE_PREFIX_PATH at them")
  endif()
  message(STATUS "VecGeom not found -> fetching ${VECGEOM_GIT_REPOSITORY} (${VECGEOM_GIT_TAG})")
  include(FetchContent)
  # Option set identical to recipes/vecgeom/build.sh (cinema-prompt-feedstock)
  # and install_cdeps.py: builtin VecCore (tarball from CERN, not GitHub),
  # GDML on, shared libs (the fork's add_library() declares no type).
  set(VECGEOM_BUILTIN_VECCORE ON)
  set(VECGEOM_FAST_MATH OFF)
  set(BUILD_TESTING OFF)
  set(VECGEOM_GDML ON)
  set(VECGEOM_USE_NAVINDEX ON)
  set(__saved_BUILD_SHARED_LIBS "${BUILD_SHARED_LIBS}")
  set(BUILD_SHARED_LIBS ON)
  # EXCLUDE_FROM_ALL (CMake >= 3.28): the fork's install() rules stay out
  # of the wheel install step — kdsource's reference unbuilt kdtool
  # executables (only prompt_core is built under scikit-build-core), and
  # vecgeom's would pour lib/include strays into the prefix. The libs
  # cinema ships are bundled explicitly via $<TARGET_FILE:...> in the
  # SKBUILD install block below; inter-target dependencies still build.
  FetchContent_Declare(vecgeom
    GIT_REPOSITORY "${VECGEOM_GIT_REPOSITORY}"
    GIT_TAG "${VECGEOM_GIT_TAG}"
    GIT_SHALLOW TRUE GIT_PROGRESS TRUE
    EXCLUDE_FROM_ALL)
  FetchContent_MakeAvailable(vecgeom)
  set(BUILD_SHARED_LIBS "${__saved_BUILD_SHARED_LIBS}")
  # In-tree targets are unnamespaced; provide what src/cxx links against.
  if(NOT TARGET VecGeom::vecgeom)
    add_library(VecGeom::vecgeom ALIAS vecgeom)
  endif()
  if(NOT TARGET VecGeom::vgdml)
    add_library(VecGeom::vgdml ALIAS vgdml)
  endif()
  set(VecGeom_VERSION "${vecgeom_VERSION}")
  set(CINEMA_IN_TREE_VECGEOM ON)
  # cinema includes the GDML headers with their installed layout
  # (<VecGeom/gdml/*.h>); in the source tree they sit flat under
  # persistency/gdml/source/include. Mirror them under a prefixed
  # build-tree dir (symlink, deep copy where symlinks are unavailable).
  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/vecgeom-gdml/VecGeom")
  file(CREATE_LINK "${vecgeom_SOURCE_DIR}/persistency/gdml/source/include"
       "${CMAKE_BINARY_DIR}/vecgeom-gdml/VecGeom/gdml" SYMBOLIC COPY_ON_ERROR)
  include_directories(AFTER "${CMAKE_BINARY_DIR}/vecgeom-gdml")
endif()
message(STATUS "FOUND VecGeom: ${VecGeom_FOUND} ${VecGeom_DIR}")
message(STATUS "Using VecGeom version ${VecGeom_VERSION}")
# make sure we import VecGeom architecture flags - is this needed?
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${VECGEOM_CXX_FLAGS}")
# Make sure VecGeom::vgdml is enabled
if(NOT TARGET VecGeom::vgdml)
  message(FATAL_ERROR "Prompt requires VecGeom compiled with GDML support")
endif()

# NCrystal
#Find NCrystal:

if(NOT DEFINED NCrystal_DIR OR NCrystal_DIR MATCHES "-NOTFOUND")
  #Need to invoke "ncrystal-config --show cmakedir" if we want to be able to
  #work with ncrystal-core installed via python wheels:
  execute_process(
    COMMAND ncrystal-config --show cmakedir
    OUTPUT_VARIABLE "NCrystal_DIR" OUTPUT_STRIP_TRAILING_WHITESPACE
  )
endif()
find_package( NCrystal 4.0.0 REQUIRED )
message(STATUS "FOUND NCrystal_DIR: ${NCrystal_DIR}")
message(STATUS "Using NCrystal version ${NCrystal_VERSION}")
# Runtime libdir (pip wheels keep libNCrystal.so under site-packages; the
# wheel RPATH below derives its entry from this). Unset when the tool is
# not usable - the RPATH block then simply skips the NCrystal entry.
execute_process(COMMAND ncrystal-config --show libdir
  OUTPUT_VARIABLE NCRYSTAL_LIBDIR OUTPUT_STRIP_TRAILING_WHITESPACE
  RESULT_VARIABLE _ncrystal_libdir_rc)

# MCPL + KDSource: kdsource has no cmake package config; mcpl-config says
# where the mcpl headers (and, in conda prefixes, the kdsource headers too)
# live.
# Dev tree WINS over any ambient environment: external/KDSource/install
# carries mcpl and kdsource headers+libs together (src/cxx expects them in
# ONE include dir). If the shell happens to have a conda/pip mcpl-config on
# PATH (e.g. env 'test' with the pip mcpl-core), honoring it first would mix
# pip mcpl headers - which have no kdsource.h - with the dev kdsource lib
# and break the build on PTMCPLGun.cc.
set(_dev_kds_root "${CMAKE_SOURCE_DIR}/external/KDSource/install")
if(NOT SKBUILD AND EXISTS "${_dev_kds_root}/include/kdsource.h"
    AND EXISTS "${_dev_kds_root}/lib")
  set(MCPL_INCDIR "${_dev_kds_root}/include")
  set(MCPL_LIB "${_dev_kds_root}/lib")
else()
  execute_process(COMMAND mcpl-config --show libdir
    OUTPUT_VARIABLE "MCPL_LIB" OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _mcpl_config_rc)
  execute_process(COMMAND mcpl-config --show includedir
    OUTPUT_VARIABLE "MCPL_INCDIR" OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _mcpl_config_rc2)
  if(NOT _mcpl_config_rc EQUAL 0 OR NOT _mcpl_config_rc2 EQUAL 0 OR NOT EXISTS "${MCPL_INCDIR}")
    if(SKBUILD)
      message(FATAL_ERROR
        "mcpl-config unusable in a wheel build (rc=${_mcpl_config_rc}/${_mcpl_config_rc2}, "
        "includedir='${MCPL_INCDIR}') - the dev-tree external/ fallback does not apply here")
    endif()
    set(MCPL_INCDIR "${_dev_kds_root}/include")
    set(MCPL_LIB "${_dev_kds_root}/lib")
  endif()
endif()
message(STATUS "MCPL headers: ${MCPL_INCDIR}")

# Resolve libmcpl here so src/cxx's FIND_LIBRARY(mcpl ...) is a no-op even
# when the kdsource lib dir below is an in-tree build directory.
find_library(mcpl NAMES mcpl HINTS "${MCPL_LIB}")
if(NOT mcpl)
  message(FATAL_ERROR "libmcpl not found via mcpl-config (libdir: ${MCPL_LIB})")
endif()

# KDSource: KDS_LIB is consumed by src/cxx as the search dir for libkdsource
# (and, historically, libmcpl); its headers sit next to mcpl's (MCPL_INCDIR).
if(NOT KDS_LIB)
  if(SKBUILD)
    # wheel builds: CMAKE_PREFIX_PATH only (conda route), never the dev tree
    find_library(KDS_LIB_FILE NAMES kdsource)
  else()
    find_library(KDS_LIB_FILE NAMES kdsource
      HINTS "${CMAKE_SOURCE_DIR}/external/KDSource/install/lib")
  endif()
endif()
if(KDS_LIB_FILE)
  get_filename_component(KDS_LIB "${KDS_LIB_FILE}" DIRECTORY)
elseif(CINEMA_FETCH_DEPS STREQUAL "AUTO")
  message(STATUS "kdsource not found -> fetching ${KDSOURCE_GIT_REPOSITORY} (${KDSOURCE_GIT_TAG})")
  include(FetchContent)
  # same flag as recipes/kdsource/build.sh (its cmake_minimum_required is 3.24)
  set(CMAKE_POLICY_VERSION_MINIMUM 3.24)
  FetchContent_Declare(kdsource
    GIT_REPOSITORY "${KDSOURCE_GIT_REPOSITORY}"
    GIT_TAG "${KDSOURCE_GIT_TAG}"
    GIT_SHALLOW TRUE GIT_PROGRESS TRUE
    EXCLUDE_FROM_ALL)  # keep install() rules out of the wheel (see vecgeom)
  FetchContent_MakeAvailable(kdsource)
  # The in-tree lib does not exist yet at configure time, so src/cxx's
  # FIND_LIBRARY(kdsource ...) cannot find it — pre-seed its cache variable
  # with the target file instead (a set cache var makes find_library skip).
  set(kdsource "$<TARGET_FILE:kdsource>" CACHE FILEPATH "kdsource library" FORCE)
  # kdsource.h lives in the fetched source tree, not next to mcpl's headers;
  # KDSourceConfig.h is configure_file()-generated in the fork's build dir
  # (installed layouts ship it next to kdsource.h instead).
  include_directories(AFTER "${kdsource_SOURCE_DIR}/src/kdsource"
                              "${kdsource_BINARY_DIR}")
  set(CINEMA_IN_TREE_KDSOURCE ON)
else()
  message(FATAL_ERROR
    "libkdsource not found and CINEMA_FETCH_DEPS=OFF: install the cinema "
    "fork packages or point CMAKE_PREFIX_PATH at a prefix with "
    "lib/libkdsource.so")
endif()

# GIDIPlus (static lib; headers e.g. GIDI.hpp land in <prefix>/include)
if(NOT GIDIPLUS_LIB)
  if(SKBUILD)
    find_library(GIDIPLUS_LIB_FILE NAMES gidiplus)
  else()
    find_library(GIDIPLUS_LIB_FILE NAMES gidiplus
      HINTS "${CMAKE_SOURCE_DIR}/external/gidiplus/lib")
  endif()
  if(GIDIPLUS_LIB_FILE)
    get_filename_component(GIDIPLUS_LIB "${GIDIPLUS_LIB_FILE}" DIRECTORY)
  endif()
endif()
if(NOT GIDIPLUS_LIB AND CINEMA_FETCH_DEPS STREQUAL "AUTO")
  message(STATUS "gidiplus not found -> fetching ${GIDIPLUS_GIT_REPOSITORY} (${GIDIPLUS_GIT_TAG})")
  include(FetchContent)
  # Makefile project (no top-level CMakeLists): MakeAvailable sees the
  # missing CMakeLists.txt and populates only. The install4prompt target
  # runs at build time — flags identical to recipes/gidiplus/build.sh.
  # make >= 4.4 drops the fork's MAKEFLAGS-based SMR_PATH propagation when
  # MAKEFLAGS is in the environment, hence the --unset.
  FetchContent_Declare(gidiplus
    GIT_REPOSITORY "${GIDIPLUS_GIT_REPOSITORY}"
    GIT_TAG "${GIDIPLUS_GIT_TAG}"
    GIT_SHALLOW TRUE GIT_PROGRESS TRUE)
  FetchContent_MakeAvailable(gidiplus)
  include(ProcessorCount)
  ProcessorCount(_gidi_jobs)
  if(_gidi_jobs EQUAL 0)
    set(_gidi_jobs 1)
  endif()
  set(GIDIPLUS_INSTALL_DIR "${CMAKE_BINARY_DIR}/gidiplus-install")
  set(GIDIPLUS_LIB "${GIDIPLUS_INSTALL_DIR}/lib")
  set(GIDIPLUS_INCDIR "${GIDIPLUS_INSTALL_DIR}/include")
  add_custom_command(
    OUTPUT "${GIDIPLUS_LIB}/libgidiplus.a"
    COMMAND ${CMAKE_COMMAND} -E env --unset=MAKEFLAGS
            make -s install4prompt -j${_gidi_jobs} SHELL=bash
            "CXXFLAGS=-std=c++11 -fPIC" "CFLAGS=-fPIC"
            "INSTALL_PREFIX=${GIDIPLUS_INSTALL_DIR}"
    WORKING_DIRECTORY "${gidiplus_SOURCE_DIR}"
    VERBATIM)
  add_custom_target(gidiplus-build DEPENDS "${GIDIPLUS_LIB}/libgidiplus.a")
  set(CINEMA_GIDIPLUS_TARGET gidiplus-build)
elseif(NOT GIDIPLUS_LIB)
  message(FATAL_ERROR
    "libgidiplus not found and CINEMA_FETCH_DEPS=OFF: install the gidiplus "
    "package or point CMAKE_PREFIX_PATH at a prefix with lib/libgidiplus.a")
endif()
# Unified link handle for src/cxx in both modes (installed archive or the
# in-tree build above). A plain ${GIDIPLUS_LIB}/libgidiplus.a path on the
# link line breaks Ninja when the archive comes from a custom step ("no
# known rule to make it"); an imported target's location is exempt.
add_library(gidiplus STATIC IMPORTED GLOBAL)
# no INTERFACE_INCLUDE_DIRECTORIES: the gidiplus headers appear only at
# build time in fetch mode, and imported targets are generate-time-checked
# against non-existent dirs — src/cxx passes ${GIDIPLUS_INCDIR} itself.
set_target_properties(gidiplus PROPERTIES
  IMPORTED_LOCATION "${GIDIPLUS_LIB}/libgidiplus.a")
if(NOT GIDIPLUS_INCDIR)
  if(SKBUILD)
    find_path(GIDIPLUS_INCDIR NAMES GIDI.hpp PATH_SUFFIXES include)
  else()
    find_path(GIDIPLUS_INCDIR NAMES GIDI.hpp
      HINTS "${CMAKE_SOURCE_DIR}/external/gidiplus/include" PATH_SUFFIXES include)
  endif()
  if(NOT GIDIPLUS_INCDIR)
    message(FATAL_ERROR
      "GIDI.hpp not found: install the gidiplus package or point "
      "CMAKE_PREFIX_PATH at a prefix with include/GIDI.hpp")
  endif()
endif()

# set(Python_ROOT_DIR ${CMAKE_SOURCE_DIR}/cinemavirenv/bin/python)
set(Python_FIND_STRATEGY LOCATION)

#Test
enable_testing()

add_subdirectory(src/cxx)
# cxxtests link against the full dev context and are never shipped: under
# scikit-build-core (SKBUILD) the wheel builds only the prompt_core target
# (see pyproject [tool.scikit-build.build] targets), and cxxtests fails to
# link against the csns mcpl build anyway — keep it out of wheel builds.
if(NOT SKBUILD)
  add_subdirectory(src/cxxtests) #DO NOT REMOVE TESTS!!!
endif()
add_subdirectory(bin)

# gidiplus's Makefile build must finish before prompt_core links the archive
if(CINEMA_GIDIPLUS_TARGET)
  add_dependencies(prompt_core ${CINEMA_GIDIPLUS_TARGET})
endif()

set(Python_FIND_STRATEGY LOCATION)
set(Python_ROOT_DIR ${PROJECT_SOURCE_DIR}/cinemavirenv/bin/python)
find_package(Python REQUIRED COMPONENTS Interpreter)

# Python tests via pytest (auto-discovers test_*.py in src/pythontests/)
add_test(NAME python-tests
  COMMAND ${Python_EXECUTABLE} -m pytest ${PROJECT_SOURCE_DIR}/src/pythontests/ -v --forked
  WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/cinemabin
)

# ---- Wheel install contract (scikit-build-core) ----------------------------
# pip/wheel builds install the extension INTO the Cinema python package
# (site-packages/Cinema/libprompt_core.so, next to the sources that
# wheel.packages copies there). $ORIGIN keeps co-located libs resolvable;
# $ORIGIN/../../.. resolves to the active env's lib/ (conda env and venv
# layouts alike) for the shared deps (mcpl, NCrystal, hdf5, fftw, and the
# pre-installed forks). Forks built in-tree by CINEMA_FETCH_DEPS=AUTO are
# bundled next to the extension and resolved by $ORIGIN alone.
# Plain dev/conda-build routes (SKBUILD unset) keep their existing
# behavior: no install rules, build.sh copies the .so itself.
if(SKBUILD)
  # The shared deps (NCrystal, mcpl) stay OUTSIDE the wheel - where exactly
  # is decided by the installing environment, not the build one: pip puts
  # them in per-package data dirs under site-packages, conda in <prefix>/lib.
  # So the RPATH is DERIVED at build time from what the config tools report
  # alone: in a pip build the two libdirs are sibling package dirs under the
  # same site-packages, so their longest common directory prefix IS that
  # site-packages, and each entry is the libdir re-expressed relative to it
  # ($ORIGIN = <site-packages>/Cinema at runtime; the isolation env and the
  # runtime env share everything below site-packages, so the entry survives
  # pip deleting the build env). The build interpreter is deliberately NOT
  # consulted: inside pip's overlay build envs a conda python's sysconfig
  # reports the OUTER env's site-packages, which bakes cross-root .. chains
  # into the wheel. Conda libdirs (<prefix>/lib, both identical) have no
  # suffix below their common prefix and add nothing - the ../../.. entry
  # already covers them.
  set(_cinema_rpath "$ORIGIN;$ORIGIN/../../..")
  set(_cinema_libdirs "")
  foreach(_libdir "${MCPL_LIB}" "${NCRYSTAL_LIBDIR}")
    if(_libdir AND IS_ABSOLUTE "${_libdir}" AND EXISTS "${_libdir}")
      string(REGEX REPLACE "//$" "/" _libdir "${_libdir}")
      string(REGEX REPLACE "/+$" "" _libdir "${_libdir}")
      list(APPEND _cinema_libdirs "${_libdir}")
    endif()
  endforeach()
  if(_cinema_libdirs)
    list(REMOVE_DUPLICATES _cinema_libdirs)
    list(GET _cinema_libdirs 0 _cinema_sp_base)
    # reduce against every further libdir -> longest common dir prefix
    foreach(_libdir IN LISTS _cinema_libdirs)
      if(NOT "${_libdir}" STREQUAL "${_cinema_sp_base}")
        string(REPLACE "/" ";" _p_cur "${_cinema_sp_base}")
        string(REPLACE "/" ";" _p_new "${_libdir}")
        # component 0 is the empty root marker; keep it out so joining
        # does not double the leading slash
        list(REMOVE_AT _p_cur 0)
        list(REMOVE_AT _p_new 0)
        list(LENGTH _p_cur _n_cur)
        list(LENGTH _p_new _n_new)
        if(_n_new LESS _n_cur)
          set(_n_cur _n_new)
        endif()
        set(_i 0)
        set(_reduced "")
        while(_i LESS _n_cur)
          list(GET _p_cur ${_i} _c1)
          list(GET _p_new ${_i} _c2)
          if(NOT "${_c1}" STREQUAL "${_c2}")
            break()
          endif()
          if(_reduced STREQUAL "")
            set(_reduced "${_c1}")
          else()
            string(APPEND _reduced "/${_c1}")
          endif()
          math(EXPR _i "${_i} + 1")
        endwhile()
        if(_reduced STREQUAL "")
          set(_cinema_sp_base "/")
        else()
          set(_cinema_sp_base "/${_reduced}")
        endif()
      endif()
    endforeach()
    if(NOT _cinema_sp_base STREQUAL "" AND NOT _cinema_sp_base STREQUAL "/")
      foreach(_libdir IN LISTS _cinema_libdirs)
        file(RELATIVE_PATH _cinema_suffix "${_cinema_sp_base}" "${_libdir}")
        if(_cinema_suffix AND NOT _cinema_suffix STREQUAL "."
            AND NOT _cinema_suffix MATCHES "^\\.\\./")
          list(APPEND _cinema_rpath "$ORIGIN/../${_cinema_suffix}")
        endif()
      endforeach()
      list(REMOVE_DUPLICATES _cinema_rpath)
    endif()
  endif()
  message(STATUS "Wheel RPATH for prompt_core: ${_cinema_rpath}")
  set_target_properties(prompt_core PROPERTIES
    INSTALL_RPATH "${_cinema_rpath}")
  install(TARGETS prompt_core DESTINATION Cinema)
  if(CINEMA_IN_TREE_VECGEOM AND CINEMA_IN_TREE_KDSOURCE)
    install(FILES $<TARGET_FILE:vecgeom> $<TARGET_FILE:vgdml>
                  $<TARGET_FILE:kdsource>
            DESTINATION Cinema)
  endif()
endif()
