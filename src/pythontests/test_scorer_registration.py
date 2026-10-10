#!/usr/bin/env python3
"""
Volume.addScorer duplicate-name contract.

Scorer names are the histogram lookup keys, so a second registration under an
already-used name used to silently alias to the first histogram. All three
registration branches of Volume.addScorer (helper object with C++ pointer,
legacy config string, helper .cfg object) now raise ValueError on a name that
is already registered, on this or any other volume of the world.
"""
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.scorer import ESpectrumHelper, MultiScatCounter
import pytest


def _makeVolume(name):
    # dilute pure-physics material: no NCrystal data parsing, keeps these
    # registration checks in the fast tier
    return Volume(name, Box(10, 10, 10),
                  'physics=idealElaScat;xs_barn=1;density_per_aa3=0.01;'
                  'energy_transfer_eV=0.01')


def test_unique_names_still_accepted():
    """Existing behaviour: unique names register fine on one and across volumes."""
    vol1 = _makeVolume('unique_vol1')
    vol2 = _makeVolume('unique_vol2')

    ESpectrumHelper('uniq_entry_a', 1e-6, 1, 10, 2112, 'ENTRY', False).make(vol1)
    ESpectrumHelper('uniq_entry_b', 1e-6, 1, 10, 2112, 'EXIT', False).make(vol1)
    ESpectrumHelper('uniq_entry_c', 1e-6, 1, 10, 2112, 'ENTRY', False).make(vol2)

    assert 'uniq_entry_a' in Volume.scorer_dict
    assert 'uniq_entry_b' in Volume.scorer_dict
    assert 'uniq_entry_c' in Volume.scorer_dict


def test_same_name_on_different_volumes_raises():
    """The registry is shared by all volumes: a name clash across volumes raises."""
    vol1 = _makeVolume('clash_vol1')
    vol2 = _makeVolume('clash_vol2')

    ESpectrumHelper('clashing_name', 1e-6, 1, 10, 2112, 'ENTRY', False).make(vol1)
    with pytest.raises(ValueError, match="clashing_name"):
        ESpectrumHelper('clashing_name', 1e-6, 1, 10, 2112, 'ENTRY', False).make(vol2)


def test_same_volume_double_registration_raises():
    """Re-registering on the same volume is the same silent-aliasing bug."""
    vol = _makeVolume('double_vol')

    ESpectrumHelper('double_name', 1e-6, 1, 10, 2112, 'ENTRY', False).make(vol)
    with pytest.raises(ValueError, match="double_name"):
        ESpectrumHelper('double_name', 1e-6, 1, 10, 2112, 'EXIT', False).make(vol)


def test_legacy_config_string_duplicate_raises():
    """The legacy string branch extracts the name= field and must check it too."""
    vol = _makeVolume('legacy_vol')

    ESpectrumHelper('legacy_name', 1e-6, 1, 10, 2112, 'ENTRY', False).make(vol)
    # same scorer name handed over as a raw legacy cfg string
    legacyCfg = ("Scorer=ESpectrum;name=legacy_name;min=1e-6;max=1;numbin=10;"
                 "particle=2112;ptstate=ENTRY;scoreTransfer=0;")
    with pytest.raises(ValueError, match="legacy_name"):
        vol.addScorer(legacyCfg)


def test_multiscat_counter_duplicate_raises():
    """MultiScatCounter goes through the C++-pointer branch: checked as well."""
    vol = _makeVolume('counter_vol')

    MultiScatCounter().make(vol)
    with pytest.raises(ValueError, match="ScatterCounter"):
        MultiScatCounter().make(vol)
