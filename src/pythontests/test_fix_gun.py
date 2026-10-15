"""Regression tests for usability findings #11/#14/#19 (gun.py, configstr.py).

Pure Python on purpose: the ctypes push into the C++ gun stack is stubbed out,
so these tests never touch C++ state and are safe to run against old code
(where they must fail).
"""

import copy

import numpy as np
import pytest

from Cinema.Prompt.configstr import ConfigString
from Cinema.Prompt.gun import Gun, MCPLGun, PythonGun


def _canonical_particle_dtype():
    # The layout the C++ backend reads at fixed offsets: 9 packed float64.
    return np.dtype([
        ('ekin', np.float64),
        ('w', np.float64),
        ('t', np.float64),
        ('pos', np.float64, 3),
        ('dir', np.float64, 3),
    ])


@pytest.fixture
def push_recorder(monkeypatch):
    """Stub the ctypes push so C++ never receives (possibly garbage) particles."""
    import Cinema.Prompt.gun as gunmod
    calls = []
    def _rec(cobj, buf, num):
        calls.append((cobj, np.asarray(buf).copy(), int(num)))
    monkeypatch.setattr(gunmod, '_pt_PythonGun_pushToStackMany', _rec)
    return calls


# ---- #14: ConfigString missing attributes must raise AttributeError ----

def test_configstr_missing_attr_raises_attributeerror():
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    assert cs.cfg_name == 'quantity'
    with pytest.raises(AttributeError):
        cs.no_such_key
    assert hasattr(cs, 'cfg_name')
    assert not hasattr(cs, 'no_such_key')
    assert getattr(cs, 'no_such_key', 'dflt') == 'dflt'


def test_configstr_deepcopy():
    # deepcopy looks up __deepcopy__ with 3-arg getattr; a KeyError would abort it
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    cs2 = copy.deepcopy(cs)
    assert cs2.cfg_name == 'quantity'


# ---- #14: MCPLGun must be a Gun subclass ----

def test_mcplgun_is_gun_subclass():
    assert issubclass(MCPLGun, Gun)
    g = MCPLGun()
    assert g.pdg == 2112
    # the duck-typing idiom used on guns in promptCore.simulate
    assert getattr(g, 'vectorized', 1) == 1


# ---- #11: MCPL input file must be validated in Python ----

def test_mcplgun_missing_file_raises_filenotfound(tmp_path):
    missing = str(tmp_path / 'no_such_file.mcpl.gz')
    with pytest.raises(FileNotFoundError) as ei:
        MCPLGun(missing)
    assert missing in str(ei.value)
    g = MCPLGun()
    with pytest.raises(FileNotFoundError) as ei:
        g.setMCPLFile(missing)
    assert missing in str(ei.value)


def test_mcplgun_existing_file_accepted(tmp_path):
    f = tmp_path / 'exists.mcpl.gz'
    f.write_bytes(b'')
    g = MCPLGun(str(f))
    assert g.cfg_mcplfile == str(f)
    assert 'mcplfile' in g.cfg


# ---- #19: pdata dtype/shape validated before the ctypes push ----

def test_pythongun_valid_generate(push_recorder):
    g = PythonGun(vectorized=4)
    assert g.pdata.dtype == _canonical_particle_dtype()
    g.generate()
    assert len(push_recorder) == 1
    _, buf, num = push_recorder[0]
    assert num == 4
    assert buf.dtype == np.float64
    assert buf.size == 4 * 9


def test_pythongun_generate_with_num(push_recorder):
    g = PythonGun(vectorized=4)
    g.generate(6)
    assert push_recorder[0][2] == 6
    assert g.pdata.size == 4  # pdata restored afterwards


def test_pythongun_partial_generate(push_recorder):
    # the idiom promptCore.simulate uses for the remaining particles
    g = PythonGun(vectorized=4)
    original = g.vectorized
    g.vectorized = 3
    g.generate()
    g.vectorized = original
    assert push_recorder[0][2] == 3


def test_pythongun_sample_override_still_works(push_recorder):
    # overriding the sample* methods (the documented customization) stays valid
    class MyGun(PythonGun):
        def sampleEnergy(self, num):
            self.pdata['ekin'] = 1.0
    g = MyGun(vectorized=2)
    g.generate()
    assert len(push_recorder) == 1
    assert np.all(push_recorder[0][1][0::9] == 1.0)


def _broken_gun(dtype):
    class BrokenGun(PythonGun):
        def __init__(self, vectorized=1):
            super().__init__(vectorized=vectorized)
            self.particle_dtype = dtype
            self.pdata = np.zeros(self.vectorized, dtype=dtype)
    return BrokenGun


def test_pythongun_rejects_dropped_field(push_recorder):
    dtype = np.dtype([('ekin', np.float64), ('t', np.float64),
                      ('pos', np.float64, 3), ('dir', np.float64, 3)])
    with pytest.raises(ValueError) as ei:
        _broken_gun(dtype)(vectorized=2).generate()
    assert 'particle_dtype' in str(ei.value)
    assert push_recorder == []


def test_pythongun_rejects_reordered_fields(push_recorder):
    # same itemsize, C++ would read every value from the wrong slot
    dtype = np.dtype([('w', np.float64), ('ekin', np.float64), ('t', np.float64),
                      ('pos', np.float64, 3), ('dir', np.float64, 3)])
    with pytest.raises(ValueError) as ei:
        _broken_gun(dtype)(vectorized=2).generate()
    assert 'particle_dtype' in str(ei.value)
    assert push_recorder == []


def test_pythongun_rejects_float32_fields(push_recorder):
    # 6 doubles per particle: old code handed C++ a short buffer (overread)
    dtype = np.dtype([('ekin', np.float32), ('w', np.float32), ('t', np.float32),
                      ('pos', np.float32, 3), ('dir', np.float32, 3)])
    with pytest.raises(ValueError) as ei:
        _broken_gun(dtype)(vectorized=2).generate()
    assert 'particle_dtype' in str(ei.value)
    assert push_recorder == []


def test_pythongun_rejects_extra_field(push_recorder):
    dtype = np.dtype([('ekin', np.float64), ('w', np.float64), ('t', np.float64),
                      ('pos', np.float64, 3), ('dir', np.float64, 3),
                      ('extra', np.int32)])
    with pytest.raises(ValueError) as ei:
        _broken_gun(dtype)(vectorized=2).generate()
    assert 'particle_dtype' in str(ei.value)
    assert push_recorder == []


def test_pythongun_rejects_short_pdata(push_recorder):
    g = PythonGun(vectorized=4)
    g.pdata = g.pdata[:1]
    with pytest.raises(ValueError) as ei:
        g.generate()
    assert 'pdata' in str(ei.value)
    assert push_recorder == []


def test_pythongun_rejects_non_1d_pdata(push_recorder):
    g = PythonGun(vectorized=4)
    g.pdata = np.zeros((2, 2), dtype=g.particle_dtype)
    with pytest.raises(ValueError):
        g.generate()
    assert push_recorder == []
