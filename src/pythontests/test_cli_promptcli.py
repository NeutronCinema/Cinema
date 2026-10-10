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

# Script exercising the list-kind dispatch: Optional[list], an un-annotated
# list default, and the bare `list` control (exact hint + explicit default).
_LIST_PARAM_SCRIPT = """\
from typing import Optional
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import Gun

class ListSim(Prompt):
    def __init__(self, bins=64):
        self.bins = bins

class ListGun(Gun):
    def __init__(self, x: Optional[list] = None, y=[1, 2], tags: list = ['a']):
        self.x = x
        self.y = y
        self.tags = tags
"""

# Script exercising the bool flag actions: annotated bools plus an un-annotated
# bool default (kind inferred from the default value).
_BOOL_PARAM_SCRIPT = """\
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import Gun

class BoolSim(Prompt):
    def __init__(self, on: bool = False, off: bool = True, loose=False):
        self.on = on
        self.off = off
        self.loose = loose

class BoolGun(Gun):
    def __init__(self, energy=1.0):
        self.energy = energy
"""

# The cli.md section-6 edge 1 repro: a real C++-backed gun subclassed with an
# `Optional[list]` source/slit annotation.
_EDGE_GUN_SCRIPT = """\
from typing import Optional
from Cinema.Prompt import Prompt
from Cinema.Prompt.gun import UniModeratorGun

class EdgeSim(Prompt):
    pass

class EdgeGun(UniModeratorGun):
    def __init__(self, src_whz: Optional[list] = None, slit_whz: Optional[list] = None,
                 wl_mean=1., wl_range=0.0001):
        super().__init__(src_whz, slit_whz, wl_mean, wl_range)
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


def test_parse_literal_roundtrip_and_rejects():
    from Cinema.Prompt.cli import promptcli
    assert promptcli.parse_literal('[1, 2]') == [1, 2]
    assert promptcli.parse_literal("{'k': 2}") == {'k': 2}
    with pytest.raises(ValueError, match='invalid literal'):
        promptcli.parse_literal('[1, 2')


def test_resolve_hint_kind_normalisation():
    import typing
    from Cinema.Prompt.cli import promptcli

    # Optional[X] degrades to X, for both union spellings
    assert promptcli.resolve_hint_kind(typing.Optional[list], None) is list
    assert promptcli.resolve_hint_kind(list | None, None) is list
    assert promptcli.resolve_hint_kind(typing.Optional[dict], None) is dict
    assert promptcli.resolve_hint_kind(typing.Optional[float], None) is float
    # generic containers degrade to the plain builtin
    assert promptcli.resolve_hint_kind(typing.List[float], None) is list
    assert promptcli.resolve_hint_kind(typing.Dict[str, int], None) is dict
    # Any/missing hint borrows the kind of the default value
    assert promptcli.resolve_hint_kind(typing.Any, [1, 2]) is list
    assert promptcli.resolve_hint_kind(typing.Any, 5) is int
    assert promptcli.resolve_hint_kind(typing.Any, 0.5) is float
    assert promptcli.resolve_hint_kind(typing.Any, False) is bool
    assert promptcli.resolve_hint_kind(typing.Any) is None
    assert promptcli.resolve_hint_kind(typing.Any, None) is None
    # ambiguous unions and custom classes resolve to no builtin kind
    assert promptcli.resolve_hint_kind(typing.Union[int, str], None) is None

    class _Custom:
        pass

    assert promptcli.resolve_hint_kind(_Custom, None) is None


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
    # '--scale 2.5' is typed at the parser now (scalar default 1.0 infers
    # type=float), so it arrives as a float without the str_or_float fallback
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


def test_pyscript_optional_and_untyped_list_coerce_to_real_lists(tmp_path, monkeypatch):
    """Optional[list] and un-annotated list parameters reach the gun as real
    lists (regression for the cli.md section-6 edge 1 SIGABRT: the raw string
    used to be forwarded into the C++ gun constructor)."""
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'list_params.py'
    script.write_text(_LIST_PARAM_SCRIPT)
    monkeypatch.setattr(
        sys, 'argv',
        ['prompt', '-g', str(script), '--gun', 'ListGun',
         '--x', '[1, 2]', '--y', '[3, 4]', '--tags', "['b', 'c']"])
    parser = promptcli.parser_factory()

    gun = parser.instantiate(parser.classes_defined['ListGun'])
    # Optional[list] override: '[1, 2]' parsed into a real list
    assert gun.x == [1, 2]
    assert isinstance(gun.x, list)
    # un-annotated list default [1, 2] gets the literal parser too
    assert gun.y == [3, 4]
    assert isinstance(gun.y, list)
    # control: hint exactly `list` with explicit default keeps working
    assert gun.tags == ['b', 'c']
    assert isinstance(gun.tags, list)

    # options absent from argv fall back to the declared defaults
    monkeypatch.setattr(
        sys, 'argv', ['prompt', '-g', str(script), '--gun', 'ListGun'])
    parser = promptcli.parser_factory()
    gun = parser.instantiate(parser.classes_defined['ListGun'])
    assert gun.x is None
    assert gun.y == [1, 2]
    assert gun.tags == ['a']


def test_pyscript_malformed_list_literal_fails_cleanly(tmp_path, monkeypatch, capsys):
    """A malformed literal must not reach the C++ gun: argparse rejects the
    value with a usage error, and the instantiate() guard raises ValueError
    naming the option."""
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'list_params.py'
    script.write_text(_LIST_PARAM_SCRIPT)
    monkeypatch.setattr(
        sys, 'argv',
        ['prompt', '-g', str(script), '--gun', 'ListGun', '--x', '[1, 2'])
    parser = promptcli.parser_factory()

    # CLI level: the literal type parser is rejected by argparse (exit 2)
    with pytest.raises(SystemExit) as exc:
        parser.instantiate(parser.classes_defined['ListGun'])
    assert exc.value.code == 2
    assert '--x' in capsys.readouterr().err

    # guard level: a raw string slipping past the parser (e.g. a hand-built
    # namespace) raises ValueError naming the option instead of aborting
    parser.parse_args = lambda: argparse.Namespace(x='[1, 2', y=[1, 2], tags=['a'])
    with pytest.raises(ValueError, match="--x expects a list, got"):
        parser.instantiate(parser.classes_defined['ListGun'])


def test_pyscript_bool_params_build_flag_actions(tmp_path, monkeypatch):
    """bool parameters build --param/--no-param switches without the `type`
    kwarg (regression for the cli.md section-6 edge 2 TypeError: argparse
    rejected the generated flag before parsing even started)."""
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'bool_params.py'
    script.write_text(_BOOL_PARAM_SCRIPT)
    monkeypatch.setattr(sys, 'argv', ['prompt', '-g', str(script)])
    # constructing the parser used to die with TypeError on the bool options
    parser = promptcli.parser_factory()

    actions = {a.dest: a for a in parser._actions}
    for dest in ('on', 'loose'):
        assert isinstance(actions[dest], argparse._StoreTrueAction)
        assert actions[dest].type is None
    assert isinstance(actions['off'], argparse._StoreFalseAction)
    assert actions['off'].type is None

    sim = parser.instantiate(parser.classes_defined['BoolSim'])
    assert sim.on is False
    assert sim.off is True
    assert sim.loose is False

    monkeypatch.setattr(
        sys, 'argv', ['prompt', '-g', str(script), '--on', '--no-off'])
    parser = promptcli.parser_factory()
    sim = parser.instantiate(parser.classes_defined['BoolSim'])
    assert sim.on is True
    assert sim.off is False
    assert sim.loose is False


def test_pyscript_lists_reach_cpp_surface_source_gun(tmp_path, monkeypatch):
    """Anchor on the cli.md section-6 edge 1 repro: a real C++-backed
    SurfaceSource gun subclassed with `src_whz: Optional[list] = None` must
    receive the parsed list. Pre-fix, SurfaceSource.setSource indexed the raw
    string, so cfg_src_w became the character '[' (later the C++ abort)."""
    from Cinema.Prompt.cli import promptcli

    script = tmp_path / 'edge_gun.py'
    script.write_text(_EDGE_GUN_SCRIPT)
    monkeypatch.setattr(
        sys, 'argv',
        ['prompt', '-g', str(script), '--gun', 'EdgeGun',
         '--src_whz', '[10, 10, -200]', '--slit_whz', '[5, 5, -20]'])
    parser = promptcli.parser_factory()
    gun = parser.instantiate(parser.classes_defined['EdgeGun'])
    assert gun.cfg_src_w == 10
    assert gun.cfg_src_h == 10
    assert gun.cfg_src_z == -200
    assert gun.cfg_slit_w == 5
    assert gun.cfg_slit_h == 5
    assert gun.cfg_slit_z == -20
