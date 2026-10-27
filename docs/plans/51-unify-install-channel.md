# Unify the install/packaging channels: pip as build root, conda for deps

Status: Phase 1 implemented (this branch). Phases 2–6 planned.

## Background

Cinema/Prompt currently ships three install/packaging channels that overlap and
even destroy each other:

| Channel | Mechanism | Audience | Core problems |
|---|---|---|---|
| `env.sh`/`install.sh` | source-compiles everything into `external/`, cmake in `cinemabin/`, env vars | developers | 438-line parallel dependency build duplicating the pip channel |
| `pip install .` | hatch hook runs `tools/scripts/build_tool/install_cdeps.py`: `rm -rf build external` (destroying the dev channel's products), compiles deps, cmake, hand-copies the `.so` into the package | feedstock / power users | destructive, no cache, pollutes the source tree |
| conda feedstock | `recipe/build.sh` is a one-line `pip install .` wrapper + conda-forge binary deps; rolling builds from the dev branch, `--no-test`, `post-link.sh` pip-installs plugins on user machines | end users | version split across three sources (`__init__.py` 2.1.0 / `Version` file v2.0.1 / meta.yaml fallback 2.0.0a1), no tests, plugin hack |

## Decisions

- **pip/pyproject is the build root** — one build truth (the same CMakeLists
  and the same dependency orchestrator) for every audience.
- **conda provides dependencies and distribution.** Everything conda-forge /
  csns can supply (hdf5, libxml2, xerces, fftw, mcpl, ncrystal-lib, gvar, MPI
  variants, …) is resolved by conda — in CI *and* in developer environments.
  The three private forks (VecGeom `caixx/cinema`, KDSource `pt`, gidiplus `pt`
  tarball) stay source-built by the orchestrator until they get recipes on the
  csns channel.
- **Progressive phases**, each an independent revertable MR.
- **Tag-driven conda releases** (tag → main label; dev-branch nightlies →
  `label/dev`).

## Phase 1 — remove destructiveness + single version source (this branch)

1. `tools/scripts/build_tool/install_cdeps.py`
   - the `rm -rf build external` is gone; nothing outside the deps root is deleted
   - all paths derive from `_deps_root()`: `PROMPT_DEPS_ROOT` env var (conda
     feedstock staging) > legacy `external/` under `CONDA_BUILD` > per-pin
     cache directory `~/.cache/prompt-deps/<pin-hash>` for a plain
     `pip install .` in a dev checkout
   - the main cinema build moved out of the source tree
     (`<deps-root>/cinema-build`); the only write into the checkout is the
     wheel payload `.so` copied to `src/python/Cinema/`
   - stamp-based idempotency: `stamps/<dep>.stamp` records pin + checked-out
     commit; matching stamps skip the rebuild (delete the stamp or the deps
     root to force); a failed build aborts without stamping
   - private-fork pins centralised in the `PINS` dict
2. conda feedstock (separate repository `cinema-prompt-feedstock`)
   - `recipe/build.sh` exports `HATCH_VERSION` extracted from
     `src/python/Cinema/__init__.py`; a `GIT_DESCRIBE_TAG` that disagrees with
     `__version__` fails the build instead of silently falling back
   - `recipe/meta.yaml` renders the version straight from
     `src/python/Cinema/__init__.py` via conda-build's `load_file_regex`
     (meta.yaml is rendered *before* build.sh runs, so a variable exported
     there would not be visible at render time)
3. the root `Version` file is deprecated (nothing reads it); the single source
   of the version is `__version__` in `src/python/Cinema/__init__.py`.

### Acceptance criteria

- `pip install .` in a real dev checkout leaves `external/` and `cinemabin/`
  intact.
- A scratch-dir build still produces a working wheel; `conda build --no-test`
  passes with the version taken from `__init__.py`.
- Tag vs `__version__` mismatch fails the conda build.

## Later phases (planned, not in this MR)

2. **CMake contract**: drop the `CINEMA_LOCAL_BUILD` branches, add `install()`
   rules + install RPATH (`$ORIGIN`), build the in-package `.so` via
   `PROMPT_INSTALL_LIBDIR=.`, `_getPromptLib()` prefers the in-package library.
3. **Feedstock hardening**: tag-driven Release/Nightly Jenkins jobs, enable
   L0 (`prompt --help`, import) and L1 (seconds-scale Ge+TOF smoke) tests,
   gvar from conda-forge.
4. **Dev-side conda-ification**: `install.sh` shrinks to a conda-env bootstrap
   + orchestrator call; the NCrystal bridge is consolidated (fixing the
   trailing-`;` `NCRYSTAL_PLUGIN_LIST` bug).
5. **Plugin conda-ification**: three small recipes on the csns channel retire
   `post-link.sh`; docker becomes a pure conda consumer.
6. *(optional)* migrate the build backend from the hatch build-scripts hook to
   scikit-build-core (managed build dir, native editable installs).

## Invariants (must hold after every phase)

- `conda install csns::cinema-prompt` and its entry points keep working.
- `. env.sh && cimbuild -t` workflow, `cinemabin/`, `-t/-tt/-ttt` semantics
  unchanged.
- `CINEMAPATH` / `NCRYSTAL_*` variable names unchanged.
