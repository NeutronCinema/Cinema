"""Unit tests for ptplotcli config-string parsing and integral helpers.

Only pure parsing/formatting logic is exercised here: MCPLDataCfgStr /
IncidentParametersCfgStr config strings, parse_file_groups against files
created in tmp_path, format_integral_value and calculate_integral. No MCPL
or HDF5 file is ever read. ptplotcli is imported at module scope; it is
cheap once Cinema.Prompt is loaded (the heavy Cinema import is shared with
the other test modules at collection time).
"""
import numpy as np
import pytest

from Cinema import CinemaXY
from Cinema.Prompt.cli import ptplotcli


# ------------------------------------------------------------ MCPLDataCfgStr
def test_mcplcfg_happy_path_parses_all_fields():
    cfg = ptplotcli.MCPLDataCfgStr.from_filestring(
        'file.mcpl;para=time;unit=us;binmin=0;binmax=10;binnum=50')
    assert cfg.filename == 'file.mcpl'
    assert cfg.para == 'time'
    assert cfg.unit == 'us'
    assert cfg.binmax == pytest.approx(10.0)
    assert cfg.to_dict()['binnum'] == 50


def test_mcplcfg_incident_params_extracted_and_stripped():
    cfg = ptplotcli.MCPLDataCfgStr.from_filestring(
        'det.mcpl;para=scattering_angle;'
        'incident_params=[incident_wavelength_A=4;'
        'incident_direction=(0,0,1);sample_position=(0,0,0)]')
    # the bracketed block is kept verbatim (incl. the nested tuples) ...
    assert cfg.incident_params == \
        'incident_wavelength_A=4;incident_direction=(0,0,1);sample_position=(0,0,0)'
    # ... and stripped from the main string, so the rest parses normally
    assert cfg.filename == 'det.mcpl'
    assert cfg.para == 'scattering_angle'


def test_mcplcfg_unmatched_bracket_raises():
    with pytest.raises(ValueError, match='unmatched square brackets'):
        ptplotcli.MCPLDataCfgStr.from_filestring('f.mcpl;incident_params=[foo=1')


def test_mcplcfg_invalid_para_raises():
    # para must be one of AVAILABLE_PARTICLE_PARAMETERS (exception_only)
    with pytest.raises(ValueError, match="invalid value: 'bogus'"):
        ptplotcli.MCPLDataCfgStr.from_filestring('f.mcpl;para=bogus')


def test_mcplcfg_unknown_field_raises():
    with pytest.raises(ValueError, match="unknown parameter: 'bogus'"):
        ptplotcli.MCPLDataCfgStr.from_filestring('f.mcpl;bogus=1')


def test_mcplcfg_h5_with_semicolon_raises():
    with pytest.raises(ValueError, match=r'\.h5 files with ; mechanism'):
        ptplotcli.MCPLDataCfgStr.from_filestring('a.h5;para=time')


def test_mcplcfg_non_string_raises():
    with pytest.raises(TypeError, match='Must be a string'):
        ptplotcli.MCPLDataCfgStr.from_filestring(123)


def test_mcplcfg_bin_value_coercion():
    cfg_auto = ptplotcli.MCPLDataCfgStr.from_filestring(
        'f.mcpl;binmin=auto;binmax=auto;binnum=50')
    assert cfg_auto.binmin == 'auto'   # literal survives
    assert cfg_auto.binmax == 'auto'
    cfg_num = ptplotcli.MCPLDataCfgStr.from_filestring('f.mcpl;binmin=1.5')
    assert cfg_num.binmin == pytest.approx(1.5)
    assert isinstance(cfg_num.binmin, float)
    # 'binnum=50' on the auto string coerced to a real int
    assert cfg_auto.to_dict()['binnum'] == 50
    assert isinstance(cfg_auto.to_dict()['binnum'], int)


def test_incident_cfg_unknown_field_raises():
    with pytest.raises(ValueError, match="unknown parameter: 'bogus'"):
        ptplotcli.IncidentParametersCfgStr.from_string('bogus=1')


# --------------------------------------------------------- parse_file_groups
def test_parse_file_groups_plain_file(tmp_path):
    f1 = tmp_path / 'a.h5'
    f1.write_text('x')
    groups = ptplotcli.parse_file_groups([str(f1)])
    assert len(groups) == 1
    assert groups[0] == [{'filename': str(f1)}]


def test_parse_file_groups_plus_combination(tmp_path):
    f1 = tmp_path / 'a.h5'
    f2 = tmp_path / 'b.h5'
    f1.write_text('x')
    f2.write_text('x')
    groups = ptplotcli.parse_file_groups([f'{f1}+{f2}'])
    # both files land in ONE group (plotted together)
    assert len(groups) == 1
    assert [d['filename'] for d in groups[0]] == [str(f1), str(f2)]


def test_parse_file_groups_glob(tmp_path):
    for name in ('a.h5', 'b.h5', 'c.h5'):
        (tmp_path / name).write_text('x')
    groups = ptplotcli.parse_file_groups([str(tmp_path / '*.h5')])
    assert len(groups) == 1
    assert sorted(d['filename'] for d in groups[0]) == \
        sorted(str(tmp_path / n) for n in ('a.h5', 'b.h5', 'c.h5'))


def test_parse_file_groups_nonexistent_skipped_with_warning(tmp_path, capsys):
    groups = ptplotcli.parse_file_groups([str(tmp_path / 'nope.h5')])
    assert groups == [[]]
    assert "does not exist" in capsys.readouterr().out


# ------------------------------------------------------- integral formatting
def test_format_integral_value_large_magnitudes():
    assert ptplotcli.format_integral_value(2.5e6) == '2.50e+06'   # >= 1e6: scientific
    assert ptplotcli.format_integral_value(1500.0) == '1500'      # >= 1000: integer


def test_format_integral_value_small_magnitudes():
    assert ptplotcli.format_integral_value(42.5) == '42.50'       # 1..1000: 2 decimals
    assert ptplotcli.format_integral_value(0.25) == '0.2500'      # < 1: 4 decimals


def test_calculate_integral_equals_sum_of_mean():
    data = CinemaXY.from_sdev(
        mean=np.arange(5.0) * 2.0,
        sdev=np.full(5, 0.1),
        x=np.arange(5.0) + 0.5,
    )
    assert ptplotcli.calculate_integral(data) == pytest.approx(np.sum(data.mean))
    assert ptplotcli.calculate_integral(data) == pytest.approx(20.0)
