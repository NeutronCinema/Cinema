#!/usr/bin/env python3
"""P2.3/P2.3a/P2.4 contract tests for the GidiSetting front-end API.

Each test runs in its own forked process (pytest --forked), which also gives
it a fresh GidiSetting singleton, so the tests do not have to clean up after
each other.
"""

import warnings

import pytest

from Cinema.Prompt.GidiSetting import GidiSetting


def test_default_path_stays_off_and_available_is_explicit():
    gidi = GidiSetting()
    # P2.3a: constructing the setting probes nothing; gidi stays off until an
    # explicit enable() (or the raw setEnableGidi alias) is called.
    assert gidi.getEnableGidi() is False
    # This build ships the gidi data, so explicit introspection must agree.
    assert gidi.available() is (gidi.isCompiled and
                                __import__('os').path.isfile(gidi.getGidiPops()))


def test_enable_disable_roundtrip():
    gidi = GidiSetting()
    if not gidi.available():
        pytest.skip("gidi data not installed")
    gidi.enable()
    assert gidi.getEnableGidi() is True
    gidi.disable()
    assert gidi.getEnableGidi() is False


def test_enable_with_missing_data_raises_actionable_error():
    gidi = GidiSetting()
    if not gidi.isCompiled:
        pytest.skip("gidi not compiled")
    good_pops, good_map = gidi.getGidiPops(), gidi.getGidiMap()
    gidi.setGidiPops('/nonexistent/pops.xml')
    try:
        with pytest.raises(ValueError) as exc:
            gidi.enable()
        # P2.4: the message must be actionable — name the missing file and
        # the way out (setGidiPops/setGidiMap or available()).
        msg = str(exc.value)
        assert '/nonexistent/pops.xml' in msg
        assert 'setGidiPops' in msg
        # P2.3a: never silently degraded — the enable did NOT go through.
        assert gidi.getEnableGidi() is False
    finally:
        gidi.setGidiPops(good_pops)


def test_enable_warns_when_not_compiled():
    gidi = GidiSetting()
    if gidi.isCompiled:
        pytest.skip("gidi is compiled in this build")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gidi.enable()
    assert any(issubclass(w.category, RuntimeWarning) and 'NOT compiled' in str(w.message)
               for w in caught)


def test_defaults_introspection():
    gidi = GidiSetting()
    d = gidi.defaults()
    assert d['enable'] is False
    assert d['threshold'] == 5.0
    assert d['gammaTransport'] is False
    assert d['powerIteration'] is False
    # defaults() must not modify the live setting
    assert gidi.getGidiThreshold() == 5.0
