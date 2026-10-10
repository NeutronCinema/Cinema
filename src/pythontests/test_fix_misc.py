"""Regression tests for the misc CLI/Interface fix batch (2026-10-10).

Covers usability-report findings #29 (module-level-execution warning in
promptcli.parser_factory), #34 (helper.findData -> findDataUnder) and #44
(strict energy units in Cinema.convertor). The C++ halves of #32 and the
install.sh trailing-semicolon fix are runtime-verified by the release gate
after the rebuild.
"""
import os
import sys

import pytest

from Cinema import convertor
from Cinema.Interface import helper
from Cinema.Interface import Utils as interface_utils


# ---------------------------------------------------------------- #34
def test_find_data_under_abs_path(tmp_path):
    (tmp_path / 'sub').mkdir()
    target = tmp_path / 'sub' / 'needle.txt'
    target.write_text('x')
    # regression: absPath=True used to raise UnboundLocalError (pxpath never
    # assigned), and a miss returned None instead of raising
    assert helper.findDataUnder('needle.txt', str(tmp_path), absPath=True) == str(target)
    with pytest.raises(FileNotFoundError):
        helper.findDataUnder('no_such_file.txt', str(tmp_path), absPath=True)


def test_find_data_under_requires_takpath(monkeypatch):
    monkeypatch.delenv('TAKPATH', raising=False)
    # regression: TAKPATH unset used to raise TypeError (None + str)
    with pytest.raises(RuntimeError, match='TAKPATH'):
        helper.findDataUnder('whatever.txt')


def test_utils_find_data_is_untouched():
    # the canonical repository-data locator keeps its contract
    with pytest.raises(RuntimeError, match='Al/cell.json'):
        interface_utils.findData('a/b/c.txt')


# ---------------------------------------------------------------- #44
def test_convertor_rejects_unknown_unit():
    # regression: unknown units were silently treated as eV (1000x error for meV)
    with pytest.raises(ValueError, match='eV, meV, keV, MeV'):
        convertor.angleCosine2Q_units(0.5, 25.3, enin_unit='mevv')
    with pytest.raises(ValueError, match='eV, meV, keV, MeV'):
        convertor.angleCosine2Q_units(0.5, 25.3, enin_unit='eV', enout=1.0, enout_unit='mevv')
    with pytest.raises(ValueError, match='eV, meV, keV, MeV'):
        convertor.wl2ekin_units(1.0, ekin_unit='banana')
    with pytest.raises(ValueError, match='eV, meV, keV, MeV'):
        convertor.ekin2wl_units(25.3, ekin_unit='banana')


def test_convertor_units_values_unchanged():
    # valid spellings convert exactly as before
    assert convertor.angleCosine2Q_units(0.5, 25.3, enin_unit='meV') == \
        pytest.approx(convertor.angleCosine2Q(0.5, 25.3e-3))
    assert convertor.wl2ekin_units(1.0) == pytest.approx(convertor.wl2ekin(1.0))
    assert convertor.ekin2wl_units(25.3, ekin_unit='meV') == \
        pytest.approx(convertor.ekin2wl(25.3e-3))


def test_convertor_mev_factors_physics():
    # regression: _meV2eV/_eV2meV used to be inverted (1e3/1e-3), turning
    # 25.3 meV into 25300 eV; anchor on the thermal-neutron pair 1.798 A <-> 25.3 meV
    assert convertor.meV2eV(25.3) == pytest.approx(25.3e-3)
    assert convertor.eV2meV(1.0) == pytest.approx(1e3)
    assert convertor.wl2ekin(1.798) == pytest.approx(25.3e-3, rel=1e-3)


def test_convertor_mev_mev_case_distinct():
    # meV (milli) and MeV (mega) differ only by case and must not be folded
    assert convertor.angleCosine2Q_units(0.5, 1.0, enin_unit='MeV') == \
        pytest.approx(convertor.angleCosine2Q(0.5, 1e6))


# ---------------------------------------------------------------- #29
def test_prompt_py_help_warns_before_executing_script(capsys, tmp_path):
    """`prompt -g script.py -h` must print the module-level-execution NOTE
    before the script loads, then reach the argparse help (SystemExit 0)."""
    script = tmp_path / 'classes_only.py'
    script.write_text(
        "from Cinema.Prompt import Prompt\n"
        "from Cinema.Prompt.gun import Gun\n"
        "class ClassesOnlySim(Prompt):\n"
        "    pass\n"
        "class ClassesOnlyGun(Gun):\n"
        "    def __init__(self, energy=1.0):\n"
        "        super().__init__()\n"
    )
    argv = sys.argv
    sys.argv = ['prompt', '-g', str(script), '-h']
    try:
        from Cinema.Prompt.cli import promptcli
        parser = promptcli.parser_factory()
        out_before = capsys.readouterr().out
        with pytest.raises(SystemExit) as exc:
            parser.parse_args()
        assert exc.value.code == 0
        out_help = capsys.readouterr().out
    finally:
        sys.argv = argv

    assert 'module level' in out_before          # the NOTE precedes the load
    assert 'usage:' in out_help                  # help still prints
