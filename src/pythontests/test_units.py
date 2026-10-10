"""Regression test for the Cinema.Interface.units constants.

2026-10-10: `fs` was defined as s*1e15 (30 orders of magnitude off); the
time-unit ladder must express durations in seconds, matching ps.
"""
import pytest

from Cinema.Interface import units as u


def test_time_unit_ladder():
    assert u.s == pytest.approx(1.0)
    assert u.ps == pytest.approx(1e-12)
    assert u.fs == pytest.approx(1e-15)  # regression: was 1e15
    assert u.THz == pytest.approx(1e12)


def test_energy_unit_ladder():
    assert u.MeV == pytest.approx(1e6)
    assert u.meV == pytest.approx(1e-3)


def test_rad_per_fs_conversion():
    # 1 rad/fs = 1e15 rad/s, independent of the `fs` duration constant
    assert u.radpfs2meV == pytest.approx(u.radpsec2meV * 1e15)
