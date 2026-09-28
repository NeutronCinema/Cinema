"""ptplot --config: JSON plot specs are validated and rendered.

A spec is the persistable form of a ptplot invocation: exact input files
with their cfg-string parameters, one explicit output png per figure.  The
JSON layer must fail loudly on anything it cannot freeze (missing files,
globs, unknown keys, wrong types) and must resolve relative paths against
the spec file, not the cwd.
"""

import os
os.environ.setdefault('MPLBACKEND', 'Agg')   # before the CLI imports pyplot

import ctypes
import json
import numpy as np
import pytest


class _McplParticle(ctypes.Structure):
    """C ``mcpl_particle_t`` (mcpl.h, ``#pragma pack(1)``) - the minimal
    ctypes writer below keeps this test free of Cinema's mcplout helper."""
    _fields_ = [('ekin', ctypes.c_double),
                ('polarisation', ctypes.c_double * 3),
                ('position', ctypes.c_double * 3),
                ('direction', ctypes.c_double * 3),
                ('time', ctypes.c_double),
                ('weight', ctypes.c_double),
                ('pdgcode', ctypes.c_int32),
                ('userflags', ctypes.c_uint32)]


def _write_mcpl(path, seed=3, n=500):
    """A small thermal-ish record file (MCPL storage units: cm / MeV / ms)."""
    rng = np.random.default_rng(seed)
    lib = ctypes.CDLL('libmcpl.so')
    lib.mcpl_create_outfile.restype = ctypes.c_void_p
    lib.mcpl_create_outfile.argtypes = [ctypes.c_char_p]
    lib.mcpl_add_particle.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.mcpl_close_outfile.argtypes = [ctypes.c_void_p]
    f = lib.mcpl_create_outfile(os.fspath(path).encode())
    assert f, f'mcpl_create_outfile failed for {path}'
    arr = (_McplParticle * n)()
    for i, e_mev in enumerate(rng.uniform(0.01, 0.2, n) * 1e-6):  # eV -> MeV
        arr[i].ekin = e_mev
        arr[i].position[2] = 1.0
        arr[i].direction[2] = 1.0
        arr[i].weight = 1.0
        arr[i].pdgcode = 2112                        # neutron
    for i in range(n):
        lib.mcpl_add_particle(f, ctypes.byref(arr[i]))
    lib.mcpl_close_outfile(f)


def _spec(path, plots):
    with open(path, 'w') as f:
        json.dump({'plots': plots}, f)
    return str(path)


def test_config_renders_each_plot(tmp_path):
    from Cinema.Prompt.cli.ptplotcli import main
    mcpl_a = _write_mcpl(tmp_path / 'a.mcpl')
    mcpl_b = _write_mcpl(tmp_path / 'b.mcpl', seed=4)
    cfg = _spec(tmp_path / 'spec.json', [
        # combined overlay with cfg parameters + nested output directory
        {'files': [{'path': 'a.mcpl', 'para': 'wavelength', 'unit': 'AA',
                    'binmin': 0.2, 'binmax': 2.8, 'binnum': 26},
                   {'path': 'b.mcpl', 'para': 'wavelength', 'unit': 'AA',
                    'binmin': 0.2, 'binmax': 2.8, 'binnum': 26}],
         'output': 'figs/compare.png'},
        # individual h5-style single file, per-plot ylin
        {'files': [{'path': 'a.mcpl', 'para': 'ekin', 'unit': 'eV',
                    'binmin': 0.0, 'binmax': 0.25, 'binnum': 25}],
         'output': 'figs/single.png', 'ylin': True},
    ])
    main(['--config', cfg, '--no-show'])
    assert (tmp_path / 'figs' / 'compare.png').exists()
    assert (tmp_path / 'figs' / 'single.png').exists()


def test_config_overlays_files_of_one_plot(tmp_path, capsys):
    """All files of one plot must land in ONE combined figure, not one
    figure per file all overwriting the same output path."""
    from Cinema.Prompt.cli.ptplotcli import main
    _write_mcpl(tmp_path / 'a.mcpl')
    _write_mcpl(tmp_path / 'b.mcpl', seed=4)
    cfg = _spec(tmp_path / 'spec.json',
                [{'files': [{'path': 'a.mcpl'}, {'path': 'b.mcpl'}],
                  'output': 'overlay.png'}])
    main(['--config', cfg, '--no-show'])
    out = capsys.readouterr().out
    assert out.count('Combined plot saved to') == 1
    assert 'Plot saved to' not in out
    assert (tmp_path / 'overlay.png').exists()


def test_relative_paths_resolve_against_spec_dir(tmp_path):
    from Cinema.Prompt.cli.ptplotcli import main
    (tmp_path / 'data').mkdir()
    _write_mcpl(tmp_path / 'data' / 'deep.mcpl')
    cfg_dir = tmp_path / 'cfgs'
    cfg_dir.mkdir()
    cfg = _spec(cfg_dir / 'spec.json',
                [{'files': [{'path': '../data/deep.mcpl', 'para': 'ekin',
                             'unit': 'eV', 'binmin': 0.0, 'binmax': 0.25,
                             'binnum': 10}],
                  'output': '../out/deep.png'}])
    (tmp_path / 'out').mkdir()
    main(['--config', cfg, '--no-show'])       # cwd-independent by construction
    assert (tmp_path / 'out' / 'deep.png').exists()


def test_missing_file_rejected(tmp_path):
    from Cinema.Prompt.cli.ptplotcli import load_json_config
    cfg = _spec(tmp_path / 'spec.json',
                [{'files': [{'path': 'nope.mcpl'}], 'output': 'x.png'}])
    with pytest.raises(FileNotFoundError):
        load_json_config(cfg)
    # globs are not frozen specs either: they hit the same existence check
    _write_mcpl(tmp_path / 'a.mcpl')
    cfg = _spec(tmp_path / 'spec2.json',
                [{'files': [{'path': '*.mcpl'}], 'output': 'x.png'}])
    with pytest.raises(FileNotFoundError):
        load_json_config(cfg)


def test_bad_specs_rejected(tmp_path):
    from Cinema.Prompt.cli.ptplotcli import load_json_config
    _write_mcpl(tmp_path / 'a.mcpl')
    base = {'files': [{'path': 'a.mcpl'}], 'output': 'x.png'}
    bad = [dict(base, junk=1),                       # unknown plot key
           {'files': [], 'output': 'x.png'},          # empty file list
           {'files': 'a.mcpl', 'output': 'x.png'},    # files not a list
           {'files': [{'path': 'a.mcpl'}]},           # missing output
           dict(base, ylin='yes'),                    # ylin not bool
           dict(base, downbinning=-1),                # negative downbinning
           {'files': [{'no_path': 1}], 'output': 'x.png'},   # no path
           {'files': [{'path': 'a;mcpl'}], 'output': 'x.png'},  # ';' in path
           {'files': [{'path': 'a.mcpl', 'binmin': None}], 'output': 'x.png'},
           ]
    for i, plot in enumerate(bad):
        with pytest.raises(ValueError):
            load_json_config(_spec(tmp_path / f'bad{i}.json', [plot]))
    with pytest.raises(ValueError):                   # no plots list
        load_json_config(_spec(tmp_path / 'empty.json', []))
    (tmp_path / 'broken.json').write_text('{oops')     # invalid JSON
    with pytest.raises(ValueError):
        load_json_config(str(tmp_path / 'broken.json'))


def test_individual_mcpl_to_output_dir(tmp_path):
    """-o <dir> + single .mcpl.gz input: derived name must be .png, not .gz
    (pre-existing bug the JSON route inherits through create_plot)."""
    from Cinema.Prompt.cli.ptplotcli import main
    _write_mcpl(tmp_path / 'a.mcpl')
    out = tmp_path / 'figs'
    out.mkdir()
    main([str(tmp_path / 'a.mcpl') + ';para=ekin;unit=eV;binmin=0;binmax=0.25;'
          'binnum=10', '-o', str(out), '--no-show'])
    assert (out / 'a.png').exists()


def test_cli_mutual_exclusion(tmp_path, capsys):
    from Cinema.Prompt.cli.ptplotcli import main
    _write_mcpl(tmp_path / 'a.mcpl')
    cfg = _spec(tmp_path / 'spec.json',
                [{'files': [{'path': 'a.mcpl'}], 'output': 'x.png'}])
    with pytest.raises(SystemExit):                   # config + input files
        main(['--config', cfg, str(tmp_path / 'a.mcpl'), '--no-show'])
    with pytest.raises(SystemExit):                   # neither given
        main(['--no-show'])
