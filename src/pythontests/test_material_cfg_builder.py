#!/usr/bin/env python3
# Contracts of the Material / Mirror / ConfigString cfg-string builders.
#
# The builders are deliberately exercised WITHOUT a real NCrystal material:
# a Material('<file>.ncmat') triggers the NCrystal pre-validation, whose
# scatter-model build costs 0.34-0.5 s per forked test and can never be
# cached across forks. Every case here either leaves nccfg unset or assigns
# the cfg_nccfg attribute directly; the cfg property is pure python and
# never hands the value to NCrystal, so all bodies are microsecond-level.

import pytest

from Cinema.Prompt.configstr import ConfigString
from Cinema.Prompt.physics import Material, Mirror, _validateMatCfg


def _materialWithNccfg(text='X'):
    """A Material whose nccfg is set without paying NCrystal validation."""
    mat = Material()
    mat.cfg_nccfg = text
    return mat


def test_unset_nccfg_cfg_raises():
    # the cfg property refuses to build a string before a material is set
    mat = Material()
    with pytest.raises(ValueError, match='not set'):
        mat.cfg


def test_nccfg_only_cfg_string():
    mat = _materialWithNccfg('X')
    assert mat.cfg == "physics=ncrystal;nccfg='X'"


def test_setbiasscat_appends_scatter_bias():
    mat = _materialWithNccfg()
    mat.setBiasScat(0.5)
    assert mat.cfg == "physics=ncrystal;nccfg='X';scatter_bias=0.5"


def test_setbiasabsp_appends_abs_bias():
    mat = _materialWithNccfg()
    mat.setBiasAbsp(2.0)
    assert mat.cfg == "physics=ncrystal;nccfg='X';abs_bias=2.0"


def test_full_cfg_canonical_key_order():
    # all three options together: keys must appear in the canonical order
    # (physics, nccfg, scatter_bias, abs_bias, absorp_in_weight)
    mat = _materialWithNccfg()
    mat.setBiasScat(0.5)
    mat.setBiasAbsp(2.0)
    mat.setAbsorpInWeight(True)
    assert mat.cfg == ("physics=ncrystal;nccfg='X'"
                       ";scatter_bias=0.5;abs_bias=2.0"
                       ";absorp_in_weight=true")


def test_unit_biases_and_no_absorp_emit_no_suffix():
    # the defaults (factor 1.0, flag off) must not add any option: the
    # suffixes are appended only for non-default values
    mat = _materialWithNccfg()
    mat.setBiasScat(1.0)
    mat.setBiasAbsp(1.0)
    mat.setAbsorpInWeight(False)
    assert mat.cfg == "physics=ncrystal;nccfg='X'"


def test_mirror_cfg_exact():
    # Mirror keeps the trailing semicolon of the generic dict-based builder
    assert Mirror(0.7).cfg == 'physics=Mirror;m=0.7;'


def test_mirror_default_reflectivity():
    mir = Mirror()
    assert mir.cfg_m == 1.
    assert mir.cfg == 'physics=Mirror;m=1.0;'


def test_configstring_makecfg_docstring_example():
    # the documented example of the base class: cfg_<key> items are joined
    # as 'key=value;' in insertion order
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    cs.cfg_value = 100
    assert cs.cfg == 'name=quantity;value=100;'
    assert cs.cfg_name == 'quantity'
    assert cs.makeCfg() == 'name=quantity;value=100;'


def test_configstring_makecfg_rejects_none_value():
    # a None-valued cfg_ item must fail loudly instead of emitting 'k=None;'
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    cs.cfg_missing = None
    with pytest.raises(RuntimeError, match='is None'):
        cs.makeCfg()


# --- physics namespace pre-check against the plugin registry ----------------
#
# These cases stay microsecond-level: none of the cfg strings references a
# .ncmat file, so no NCrystal content validation runs - only the namespace
# existence check against the C++ registry, whose builtin bootstrap is a
# pair of factory registrations.

def test_plugin_namespace_known_passes():
    # the builtin idealElaScat resolves through the generic registry route
    _validateMatCfg("physics=idealElaScat;xs_barn=20.5"
                    ";density_per_aa3=0.07;energy_transfer_eV=1.0")


def test_plugin_namespace_unknown_raises_valueerror():
    # the python-side check mirrors the C++ 'unknown physics' rejection,
    # surfaced at material-construction time instead of at launch time
    with pytest.raises(ValueError, match='unknown physics nope'):
        _validateMatCfg("physics=nope;xs=1")


def test_plugin_namespaces_listing_contains_builtins():
    from Cinema.Interface import pluginNamespaces
    known = pluginNamespaces()
    assert known is not None
    assert {'ncrystal', 'idealElaScat'} <= known
