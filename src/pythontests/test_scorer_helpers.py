# Unit tests for the scorer.py helpers: range/binning validation, the
# ParticleTracingState table, ptstate plumbing, and the ctypes argument
# order of every *Helper.make() forwarding call.
#
# All ctypes entry points are monkeypatched with recording fakes: the
# Python->C argument order of make() cannot be checked against a live
# binding without building a world (and a wrong order would only show up
# as garbage scorers or a C++ abort in a real simulation), so these tests
# pin the exact tuples here. Everything is pure Python and sub-millisecond.

import warnings

import pytest

from Cinema.Prompt import scorer as scorer_mod
from Cinema.Prompt.scorer import (
    _checkScorerRange,
    _resolveLogBinning,
    ParticleTracingState,
    ScorerHelper,
    ESpectrumHelper,
    WlSpectrumHelper,
    TOFHelper,
    VolFluenceHelper,
    DepositionHelper,
    DirectSqHelper,
    DirectSqwHelper,
    PSDHelper,
    MCPLOutHelper,
)

_COBJ = 4242  # sentinel handle returned by every fake *_new


class _RecordingVol:
    """Volume stub recording addScorer; optional getCapacity like geo.Volume."""

    def __init__(self, capacity=123.456):
        self.calledWith = None
        self._capacity = capacity

    def getCapacity(self):
        return self._capacity

    def addScorer(self, *args):
        self.calledWith = args


# ---------------------------------------------------------------------------
# _checkScorerRange units
# ---------------------------------------------------------------------------

def test_check_scorer_range_valid_passthrough():
    # a sane range and log-binning-compatible min must not raise
    assert _checkScorerRange('s', 1.0, 10.0) is None
    assert _checkScorerRange('s', 1.0, 10.0, logBinning=True) is None
    assert _checkScorerRange('s', 0.0, 10.0, logBinning=False, axis='x') is None


def test_check_scorer_range_min_equal_max_raises():
    # half-open interval logic: an empty range is a user mistake
    with pytest.raises(ValueError, match=r"range min \(1\.0\) must be smaller than max \(1\.0\)"):
        _checkScorerRange('s', 1.0, 1.0)


def test_check_scorer_range_inverted_message():
    with pytest.raises(ValueError, match=r"range min \(5\.0\) must be smaller than max \(2\.0\)"):
        _checkScorerRange('s', 5.0, 2.0)


def test_check_scorer_range_log_binning_nonpositive_min_message():
    with pytest.raises(ValueError, match=r"min \(0\) must be positive for logarithmic binning"):
        _checkScorerRange('s', 0, 10, logBinning=True)
    with pytest.raises(ValueError, match=r"min \(-1\.5\) must be positive for logarithmic binning"):
        _checkScorerRange('s', -1.5, 10, logBinning=True)


def test_check_scorer_range_y_axis_label():
    # the 2D helpers pass axis='y'; the message must say which axis is wrong
    with pytest.raises(ValueError) as excinfo:
        _checkScorerRange('s', 4.0, 1.0, axis='y')
    assert 'y-axis range min (4.0)' in str(excinfo.value)
    # ... and the label is absent for the x/default case
    with pytest.raises(ValueError) as excinfo_x:
        _checkScorerRange('s', 4.0, 1.0)
    assert 'y-axis' not in str(excinfo_x.value)


# ---------------------------------------------------------------------------
# _resolveLogBinning units
# ---------------------------------------------------------------------------

def test_resolve_log_binning_linear_alias_inverts_and_warns():
    with pytest.warns(DeprecationWarning, match="'linear' keyword is deprecated"):
        log = _resolveLogBinning('ESpectrumHelper', None, False, defaultLinear=False)
    assert log is True  # linear=False means logarithmic binning
    with pytest.warns(DeprecationWarning, match="'linear' keyword is deprecated"):
        log2 = _resolveLogBinning('WlSpectrumHelper', None, True, defaultLinear=False)
    assert log2 is False


def test_resolve_log_binning_explicit_log_wins():
    # when both are given, the canonical `log` flag is kept unchanged
    with pytest.warns(DeprecationWarning):
        log = _resolveLogBinning('ESpectrumHelper', False, True, defaultLinear=False)
    assert log is False
    with pytest.warns(DeprecationWarning):
        log2 = _resolveLogBinning('ESpectrumHelper', True, False, defaultLinear=False)
    assert log2 is True
    # no keyword at all: falls back to the class default (not linear -> log)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        assert _resolveLogBinning('X', None, None, defaultLinear=False) is True


# ---------------------------------------------------------------------------
# ParticleTracingState table
# ---------------------------------------------------------------------------

def test_pts_state_value_num_table():
    expected = {
        'SURFACE': 0,
        'ENTRY': 1,
        'PROPAGATE_PRE': 2,
        'PROPAGATE_POST': 3,
        'EXIT': 4,
        'PEA_PRE': 5,
        'PEA_POST': 6,
        'ABSORB': 7,
    }
    assert len(ParticleTracingState) == 8
    for name, num in expected.items():
        assert ParticleTracingState[name].value_num == num


def test_pts_state_string_roundtrip():
    for member in ParticleTracingState:
        assert member.to_string() == member.name
        assert ParticleTracingState.from_string(member.name) is member
        # from_string is case-insensitive
        assert ParticleTracingState.from_string(member.name.lower()) is member


def test_pts_state_from_string_error_lists_valid_names():
    with pytest.raises(ValueError) as excinfo:
        ParticleTracingState.from_string('BOGUS')
    msg = str(excinfo.value)
    assert 'BOGUS' in msg
    for member in ParticleTracingState:
        assert member.name in msg


# ---------------------------------------------------------------------------
# ptstate plumbing through ScorerHelper
# ---------------------------------------------------------------------------

def test_scorerhelper_without_ptstate_raises_typeerror():
    # derived classes must pass ptstate explicitly; None is a programming error
    with pytest.raises(TypeError, match='ptstate must be a string or ParticleTracingState enum'):
        ScorerHelper('bad', 0.0, 1.0, 10)
    with pytest.raises(TypeError, match='ptstate'):
        ScorerHelper('bad', 0.0, 1.0, 10, pdg=2112, ptstate=None)


def test_scorerhelper_garbage_ptstate_defers_error_to_ptsnum():
    # __init__ accepts any str; the undefined name only fails when ptsNum
    # is read (at make() time)
    h = TOFHelper('tof', ptstate='NOT_A_STATE')
    assert h.ptstate == 'NOT_A_STATE'
    with pytest.raises(RuntimeError, match='undefined'):
        h.ptsNum


def test_scorerhelper_enum_ptstate_stored_as_string():
    h = TOFHelper('tof', ptstate=ParticleTracingState.EXIT)
    assert h.ptstate == 'EXIT'
    assert h.ptsNum == ParticleTracingState.EXIT.value_num == 4
    h2 = TOFHelper('tof2', ptstate=ParticleTracingState.ABSORB)
    assert h2.ptstate == 'ABSORB' and h2.ptsNum == 7


# ---------------------------------------------------------------------------
# make() ctypes forwarding (recording fakes, exact argument order)
# ---------------------------------------------------------------------------

def test_espectrum_make_argument_order(monkeypatch):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerESpectrum_new', fake_new)
    vol = _RecordingVol()
    h = ESpectrumHelper('en', min=0.5, max=2.0, numbin=8, pdg=2112, ptstate='EXIT',
                        energyTransfer=True, groupID=3, log=False)
    h.make(vol)
    name, energyTransfer, mn, mx, numbin, pdg, ptsNum, groupID, linear = seen['args']
    assert name == b'en'
    assert energyTransfer is True
    assert (mn, mx, numbin, pdg) == (0.5, 2.0, 8, 2112)
    assert ptsNum == ParticleTracingState.EXIT.value_num == 4
    assert groupID == 3
    assert linear is True and linear == h.linear
    assert vol.calledWith == (h, _COBJ) and h.cobj == _COBJ


def test_tof_and_wlspectrum_make_argument_order(monkeypatch):
    seen = {}

    def fake_tof(*args):
        seen['tof'] = args
        return _COBJ

    def fake_wl(*args):
        seen['wl'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerTOF_new', fake_tof)
    monkeypatch.setattr(scorer_mod, '_pt_ScorerWlSpectrum_new', fake_wl)

    t = TOFHelper('tof', min=1e-3, max=4e-2, numbin=9, pdg=2112, ptstate='ENTRY', groupID=2)
    t.make(_RecordingVol())
    name, mn, mx, numbin, pdg, ptsNum, groupID = seen['tof']
    assert name == b'tof'
    assert (mn, mx, numbin, pdg) == (1e-3, 4e-2, 9, 2112)
    assert ptsNum == ParticleTracingState.ENTRY.value_num == 1
    assert groupID == 2

    w = WlSpectrumHelper('wl', min=0.2, max=8.0, numbin=11, pdg=2112,
                         ptstate='ABSORB', groupID=5, log=False)
    w.make(_RecordingVol())
    name, mn, mx, numbin, pdg, ptsNum, groupID, linear = seen['wl']
    assert name == b'wl'
    assert (mn, mx, numbin, pdg) == (0.2, 8.0, 11, 2112)
    assert ptsNum == ParticleTracingState.ABSORB.value_num == 7
    assert groupID == 5
    assert linear is True and linear == w.linear


def test_volfluence_make_forwards_volume_capacity(monkeypatch):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerVolFluence_new', fake_new)
    vol = _RecordingVol(capacity=987.65)
    h = VolFluenceHelper('vf', min=0.1, max=5.0, numbin=12, pdg=2112, groupID=1, log=False)
    h.make(vol)
    name, mn, mx, numbin, capacity, pdg, ptsNum, linear, groupID = seen['args']
    assert name == b'vf'
    assert (mn, mx, numbin) == (0.1, 5.0, 12)
    assert capacity == pytest.approx(987.65)  # forwarded from vol.getCapacity()
    assert pdg == 2112
    assert ptsNum == ParticleTracingState.PEA_PRE.value_num == 5
    assert linear is True and linear == h.linear
    assert groupID == 1
    assert vol.calledWith == (h, _COBJ)


def test_deposition_make_argument_order(monkeypatch):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerDeposition_new', fake_new)
    vol = _RecordingVol()
    h = DepositionHelper('dep', min=0.5, max=2.0, numbin=7, pdg=2112, ptstate='ENTRY',
                         log=False, groupID=6)
    h.make(vol)
    name, mn, mx, numbin, pdg, ptsNum, linear, groupID = seen['args']
    assert name == b'dep'
    assert (mn, mx, numbin, pdg) == (0.5, 2.0, 7, 2112)
    assert ptsNum == ParticleTracingState.ENTRY.value_num == 1
    assert linear is True and linear == h.linear
    assert groupID == 6
    assert vol.calledWith == (h, _COBJ)


def test_psd_type_num_table():
    assert PSDHelper('p1', psdtype='XY').psdTypeNum == 0
    assert PSDHelper('p2', psdtype='XZ').psdTypeNum == 1
    assert PSDHelper('p3', psdtype='YZ').psdTypeNum == 2
    with pytest.raises(RuntimeError, match='undefined'):
        PSDHelper('p4', psdtype='ZZ').psdTypeNum


def test_psd_make_forwards_type_num_and_is_global(monkeypatch):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerPSD_new', fake_new)
    vol = _RecordingVol()
    h = PSDHelper('psd', xmin=-5., xmax=5., xnumbin=20, ymin=-2., ymax=2., ynumbin=10,
                  pdg=2112, ptstate='EXIT', psdtype='YZ', groupID=4, isGlobal=True)
    h.make(vol)
    (name, mn, mx, numbin, ymin, ymax, ynumbin, pdg, ptsNum,
     psdTypeNum, groupID, isGlobal) = seen['args']
    assert name == b'psd'
    assert (mn, mx, numbin) == (-5., 5., 20)
    assert (ymin, ymax, ynumbin) == (-2., 2., 10)
    assert pdg == 2112
    assert ptsNum == ParticleTracingState.EXIT.value_num == 4
    assert psdTypeNum == 2  # 'YZ'
    assert groupID == 4
    assert isGlobal is True
    assert vol.calledWith == (h, _COBJ)


def test_directsq_make_forwards_geometry_and_method(monkeypatch):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerDeltaMomentum_new', fake_new)
    vol = _RecordingVol()
    h = DirectSqHelper('sq', qmin=0.05, qmax=4.0, numbin=15, mod_smp_dist=20.0,
                       pdg=2112, refDir=(0., 1., 0.), samplePos=(1., 2., 3.),
                       ptstate='ENTRY', method=1, log=False, groupID=8)
    h.make(vol)
    (name, distMS, qmin, qmax, numbin, pdg,
     rx, ry, rz, sx, sy, sz, ptsNum, method, linear) = seen['args']
    assert name == b'sq'
    assert distMS == 20.0  # distanceMS attribute
    assert (qmin, qmax, numbin, pdg) == (0.05, 4.0, 15, 2112)
    assert (rx, ry, rz) == h.refDir == (0., 1., 0.)
    assert (sx, sy, sz) == h.samplePos == (1., 2., 3.)
    assert ptsNum == ParticleTracingState.ENTRY.value_num == 1
    assert method == 1
    assert linear is True and linear == h.linear
    assert vol.calledWith == (h, _COBJ)


def test_directsqw_make_forwards_geometry_and_logx(monkeypatch):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_ScorerDirectSqw_new', fake_new)
    vol = _RecordingVol()
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        h = DirectSqwHelper('sqw', mod_smp_dist=33.0, mean_ekin=0.025,
                            mean_incident_dir=(0., 1., 0.), sample_position=(1., 2., 3.),
                            qmin=0.5, qmax=5.0, num_qbin=7,
                            ekinmin=-0.2, ekinmax=0.3, num_ebin=9,
                            pdg=2112, groupID=4, ptstate='PEA_POST')
    h.make(vol)
    (name, qmin, qmax, nqbin, emin, emax, nebin, pdg, groupID,
     modSmpDist, meanEkin, dx, dy, dz, sx, sy, sz, ptsNum, logx) = seen['args']
    assert name == b'sqw'
    assert (qmin, qmax, nqbin) == (0.5, 5.0, 7)
    assert (emin, emax, nebin) == (-0.2, 0.3, 9)
    assert pdg == 2112 and groupID == 4
    assert modSmpDist == 33.0 and meanEkin == pytest.approx(0.025)
    assert (dx, dy, dz) == h.mean_incident_dir == (0., 1., 0.)
    assert (sx, sy, sz) == h.sample_position == (1., 2., 3.)
    assert ptsNum == ParticleTracingState.PEA_POST.value_num == 6
    assert logx is False and logx == h.logx == h.log
    assert vol.calledWith == (h, _COBJ)


# ---------------------------------------------------------------------------
# MCPLOutHelper forwarding and mpi naming
# ---------------------------------------------------------------------------

def test_mcplout_make_forwards_kill_and_compress(monkeypatch, tmp_path):
    seen = {}

    def fake_new(*args):
        seen['args'] = args
        return _COBJ

    monkeypatch.setattr(scorer_mod, '_pt_KillerMCPL_new', fake_new)
    vol = _RecordingVol()
    out = MCPLOutHelper(str(tmp_path / 'out.mcpl'), pdg=2112, groupID=2,
                        kill=True, compress=False)
    out.make(vol)
    fname, pdg, groupID, kill, compress = seen['args']
    assert fname == (str(tmp_path / 'out.mcpl') + '_pro0').encode('utf-8')
    assert pdg == 2112
    assert groupID == 2
    assert kill is True
    assert compress is False
    assert vol.calledWith == (out, _COBJ) and out.cobj == _COBJ


def test_mcplout_mpi_naming_characterization():
    # mpi4py is importable outside mpirun (singleton COMM_WORLD, rank 0),
    # so use_mpi is True and the per-rank name carries the '_pro0' suffix.
    # Note: make() appends the suffix AFTER the full file name, i.e. after
    # the .mcpl extension - pinned here as characterization.
    out = MCPLOutHelper('out')
    assert out.use_mpi is True
    assert out.name == 'out'
    assert out.name_mpi == 'out_pro0'
