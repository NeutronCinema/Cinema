"""Unit tests for Cinema.Prompt.cli.promptcli helpers and CLI parsing.

promptcli pulls the Visualiser/VTK import chain, so it is deliberately
imported INSIDE each test and never at module scope (collecting this file
must stay cheap). Under pytest --forked each child then pays the ~200 ms
import once per body, which is why every test here carries the `medium`
marker (bodies stay far below the 0.7 s slow-tier threshold).

The `.py`-script cases follow the classes-only-script pattern of
test_fix_misc.py::test_prompt_py_help_warns_before_executing_script: a
minimal script defining one Prompt-derived sim class and one Gun-derived
gun class is written to tmp_path and parsed through parser_factory with a
monkeypatched sys.argv.
"""
import argparse
import sys

import pytest

# In-body import of promptcli costs ~200 ms per forked child (the module is
# intentionally not imported at module scope), which places every body in the
# 50 ms - 0.7 s medium tier.
pytestmark = pytest.mark.medium

# Classes-only script used for the discovery/instantiate flows.
_SIM_GUN_SCRIPT = """\
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import Gun

class CoerceSim(Prompt):
    def __init__(self, scale=1.0, label='none'):
        self.scale = scale
        self.label = label

class CoerceGun(Gun):
    def __init__(self, energy=1.0):
        self.energy = energy
"""

# Script whose sim class has a REQUIRED ctor parameter.
_REQUIRED_PARAM_SCRIPT = """\
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import Gun

class NeedSim(Prompt):
    def __init__(self, needparam):
        self.needparam = needparam

class NeedGun(Gun):
    def __init__(self, energy=1.0):
        self.energy = energy
"""

_NO_SIM_SCRIPT = """\
from Cinema.Prompt.gun import Gun

class OnlyGun(Gun):
    pass
"""

_DUPLICATE_SIM_SCRIPT = """\
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import Gun

class DupA(Prompt):
    pass

class DupB(Prompt):
    pass

class DupGun(Gun):
    pass
"""


# ---------------------------------------------------------------- pure helpers
def test_str_or_float_quoted_strips_quotes():
    from Cinema.Prompt.cli import promptcli
    # quoted strings are returned verbatim minus the quotes, no float attempt
    assert promptcli.str_or_float('"abc"') == 'abc'
    assert promptcli.str_or_float("'ab_c'") == 'ab_c'


def test_str_or_float_numeric_converts():
    from Cinema.Prompt.cli import promptcli
    value = promptcli.str_or_float('2.5')
    assert value == pytest.approx(2.5)
    assert isinstance(value, float)
    assert promptcli.str_or_float('10') == pytest.approx(10.0)


def test_str_or_float_bare_word_stays_str():
    from Cinema.Prompt.cli import promptcli
    assert promptcli.str_or_float('bare_word') == 'bare_word'


def test_get_classes_from_base_class_finds_derived():
    from Cinema.Prompt.cli import promptcli

    class _Base:
        pass

    class _Derived(_Base):
        pass

    class _Unrelated:
        pass

    found = promptcli.get_classes_from_base_class(
        _Base, {'_Derived': _Derived, '_Unrelated': _Unrelated})
    assert found is _Derived


def test_get_classes_from_base_class_unknown_raises():
    from Cinema.Prompt.cli import promptcli

    class _Derived:
        pass

    # the error lists the available (defined) class names
    with pytest.raises(ValueError, match='Availables.*_Derived'):
        promptcli.get_classes_from_base_class(int, {'_Derived': _Derived})


def test_analyze_class_constructor_flags_and_hints():
    from Cinema.Prompt.cli import promptcli

    class _Dummy:
        def __init__(self, a: float, b: int = 3, c='x'):
            pass

    info = promptcli.analyze_class_constructor(_Dummy)
    assert set(info) == {'a', 'b', 'c'}
    assert info['a']['required'] is True
    assert info['a']['type'] is float
    assert info['b']['required'] is False
    assert info['b']['default'] == 3
    assert info['b']['type'] is int
    # unannotated parameters fall back to typing.Any
    assert info['c']['required'] is False
    assert info['c']['default'] == 'x'
    assert info['c']['type'] is not float  # Any, not a concrete type


def test_build_argument_help_quotes_string_default():
    from Cinema.Prompt.cli import promptcli

    class _Dummy:
        def __init__(self, a: float, c='x'):
            pass

    info = promptcli.analyze_class_constructor(_Dummy)
    assert promptcli.build_argument_help(info['c']) == "Default: 'x'"
    assert promptcli.build_argument_help(info['a']) == ''


# ------------------------------------------------------------ parser_factory
def test_parser_factory_no_args_prints_help_and_exits(capsys, monkeypatch):
    from Cinema.Prompt.cli import promptcli
    monkeypatch.setattr(sys, 'argv', ['prompt'])
    with pytest.raises(SystemExit) as exc:
        promptcli.parser_factory()
    assert exc.value.code == 1
    assert 'usage:' in capsys.readouterr().out


def test_parser_factory_missing_geo_raises(monkeypatch):
    from Cinema.Prompt.cli import promptcli
    # some other flag present but no -g
    monkeypatch.setattr(sys, 'argv', ['prompt', '-n', '5'])
    with pytest.raises(ValueError, match='without a geometry file'):
        promptcli.parser_factory()


def test_parser_factory_gdml_builds_parser_only(monkeypatch):
    from Cinema.Prompt.cli import promptcli
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', 'x.gdml'])
    # constructed only: simulate() is NOT called, so no geometry is loaded
    parser = promptcli.parser_factory()
    assert isinstance(parser, promptcli.PromptGdmlParser)


def test_parser_factory_bad_extension_raises(monkeypatch):
    from Cinema.Prompt.cli import promptcli
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', 'x.txt'])
    with pytest.raises(ValueError, match='NOT correct'):
        promptcli.parser_factory()


# ------------------------------------------------- .py script via tmp_path
def test_pyscript_discovers_classes_and_gun_help(tmp_path, monkeypatch):
    from Cinema.Prompt import Prompt
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'classes_only.py'
    script.write_text(_SIM_GUN_SCRIPT)
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', str(script)])
    parser = promptcli.parser_factory()

    # exactly one sim and one gun discovered from the script
    assert parser.sim == ['CoerceSim']
    assert parser.guns == ['CoerceGun']
    # --gun option exists and lists the available gun class
    help_text = parser.format_help()
    assert '--gun' in help_text
    assert 'CoerceGun' in help_text

    # _check_args: missing --gun raises and names the available guns
    with pytest.raises(ValueError, match='NOT specified.*CoerceGun'):
        parser._check_args(argparse.Namespace(gun=None))
    parser._check_args(argparse.Namespace(gun='CoerceGun'))  # must not raise
    assert Prompt is not None  # silence unused-import lint; used via mro in script


def test_pyscript_missing_sim_class_raises(tmp_path, monkeypatch):
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'no_sim.py'
    script.write_text(_NO_SIM_SCRIPT)
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', str(script)])
    # the Prompt check runs before the Gun check, so this script fails on it
    with pytest.raises(ValueError, match="No class 'Prompt' is defined"):
        promptcli.parser_factory()


def test_pyscript_duplicate_sim_class_raises(tmp_path, monkeypatch):
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'dup_sim.py'
    script.write_text(_DUPLICATE_SIM_SCRIPT)
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', str(script)])
    with pytest.raises(ValueError, match="duplicated in 2 classes"):
        promptcli.parser_factory()


def test_pyscript_instantiate_coerces_argv_values(tmp_path, monkeypatch):
    from Cinema.Prompt import Prompt
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'coerce.py'
    script.write_text(_SIM_GUN_SCRIPT)
    monkeypatch.setattr(
        sys, 'argv',
        ['prompt', '-g', str(script), '--scale', '2.5', '--gun', 'CoerceGun'])
    parser = promptcli.parser_factory()

    sim = parser.instantiate(Prompt)
    assert type(sim).__name__ == 'CoerceSim'
    # '--scale 2.5' arrives untyped (no annotation -> no argparse type), so
    # instantiate() coerces it through str_or_float into a float
    assert sim.scale == pytest.approx(2.5)
    assert isinstance(sim.scale, float)
    # absent from argv -> ctor default survives
    assert sim.label == 'none'


def test_pyscript_missing_required_param(tmp_path, monkeypatch):
    from Cinema.Prompt import Prompt
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'need_param.py'
    script.write_text(_REQUIRED_PARAM_SCRIPT)
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', str(script)])
    parser = promptcli.parser_factory()  # construction is fine, parse is not

    # observable CLI behaviour: argparse enforces the required option first
    with pytest.raises(SystemExit) as exc:
        parser.instantiate(Prompt)
    assert exc.value.code == 2

    # the instantiate() guard itself: with the argv namespace lacking the
    # parameter (simulated via a stub parse_args) it names the missing param
    parser.parse_args = lambda: argparse.Namespace()
    with pytest.raises(ValueError, match='Missing parameters: needparam'):
        parser.instantiate(Prompt)
