# Plan: Migrate Python Tests to pytest Framework

## Motivation

The current Python test files in `src/pythontests/` are bare scripts that run C++ simulation code at module import time. This causes two problems:

1. **pytest collection crashes** — C++ extension code (`Prompt.setSeed`, `Prompt.setWorld`) runs during import, causing `Fatal Python error: Aborted`
2. **No test isolation** — all tests are module-level code, no fixtures, no selective execution

The test infrastructure (CMake + CTest integration) was already updated to use `pytest` instead of `python test_*.py`, but the test files themselves haven't been updated to match.

## Approach

### Phase 1: Fix the test infrastructure (already done)

- `pyproject.toml`: added `[tool.pytest.ini_options]` and `pytest` to `[project.optional-dependencies] dev`
- `CMakeLists.txt`: replaced per-file `add_test` loop with single `pytest` invocation
- `src/pythontests/__init__.py`: added to all subdirectories
- `pytest` package: installed

### Phase 2: Rewrite test files to pytest style

For each test file, the conversion pattern is:

1. Move module-level simulation setup into pytest fixtures or test functions
2. Replace `print(...)` with `assert`
3. Move class-based test helpers (like `MySim(Prompt)`) into fixtures or test classes
4. Ensure no C++ extension code runs at import time

### Phase 3: Verification

- `ctest -R python-tests` passes
- `ctest` passes (all C++ tests still green)
- Individual test files runnable with `pytest src/pythontests/test_xxx.py -v`

## Test files to convert

### Root level (currently no test functions, module-level code)
- `test_prompt.py` — integration test, runs `prompt` CLI
- `test_prompt_gun.py` — gun simulation
- `test_prompt_filter.py` — filter simulation
- `test_prompt_hist.py`, `test_prompt_hist2.py` — histogram tests
- `test_prompt_scorer.py`, `test_prompt_scorer_class.py`, `test_prompt_scorerCfg.py` — scorer tests
- `test_prompt_chopper.py`, `test_prompt_mirror.py` — component tests
- `test_prompt_clean_world.py`, `test_prompt_setaxis.py` — geometry tests
- `test_prompt_pythongun.py` — Python gun test
- `test_pompt_sphereflux.py` — sphere flux test
- `test_array.py`, `test_cinema_array_ops.py`, `test_cinemaarray.py` — array tests
- `test_integrated_cases.py` — integrated cases
- `test_mcplgun.py` — MCPL gun test
- `test_tak_functionXY.py`, `test_tak_parfft.py`, `test_tak_trj.py` — Tak analysis tests
- `test_transf3d.py` — transformation test

### Subdirectory tests (need to be checked)
- `prompt_scorers/` — all module-level code
- `prompt_solids/` — all module-level code
- `prompt_physics/` — subdirectories with module-level code
- `app/test_prompt_plotter.py` — needs checking
- `post_analysis/test_ParticleParameter.py` — needs checking

## Files to exclude from pytest collection

Use `__init__.py` with `pytest_collect_file` or `conftest.py` with `collect_ignore` to skip files that cannot be converted.

## Risk

- Some tests depend on external data files (GDML, MCPL) — these may not work in all environments
- Tests that call `os.system('prompt ...')` require the `prompt` CLI to be installed
- C++ extension crashes at import time are the main blocker — once test code is wrapped in functions, this is resolved
