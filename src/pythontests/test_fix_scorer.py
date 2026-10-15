# Regression tests for the scorer usability/correctness fixes
# (usability report findings #3, #10, #11, #24, #25, #28, #33, #38).
#
# All tests are pure Python on purpose: the point of the fixes is that
# validation now happens in Python before any ctypes call, so no test
# needs a live C++ geometry/physics setup (which could abort the process
# on old code).
import os
import warnings

import pytest

from Cinema.Prompt import scorer as scorer_mod
from Cinema.Prompt.scorer import (
    ParticleTracingState,
    ESpectrumHelper,
    WlSpectrumHelper,
    VolFluenceHelper,
    DepositionHelper,
    TOFHelper,
    DirectSqHelper,
    DirectSqwHelper,
    PSDHelper,
    MCPLOutHelper,
    MultiScatMixin1D,
    MultiScatMixin2D,
    PSD,
    WlSpectrum,
    ESpectrum,
    TOF,
    VolFluence,
    ESpectrumHelperV1,
    WlSpectrumHelperV1,
    TOFHelperV1,
    VolFluenceHelperV1,
    makePSD,
)


class _RejectingVol:
    """Volume stub that fails make() if the scorer binding is ever reached."""

    def addScorer(self, *args, **kwargs):
        raise AssertionError("vol.addScorer reached although it must be prevented by the Python-side validation")


class _RecordingVol:
    """Volume stub that records the addScorer call."""

    def __init__(self):
        self.calledWith = None

    def addScorer(self, *args, **kwargs):
        self.calledWith = args


def warnedDeprecations(w):
    return [x for x in w if issubclass(x.category, DeprecationWarning)]


# ---------------------------------------------------------------------------
# #3: TOFHelper (1D scorer) must be wired to MultiScatMixin1D, not 2D
# ---------------------------------------------------------------------------

def test_tof_helper_uses_1d_multiscat_mixin():
    assert MultiScatMixin1D in TOFHelper.__mro__
    assert MultiScatMixin2D not in TOFHelper.__mro__
    assert TOFHelper.addScatterCounter.__qualname__ == 'MultiScatMixin1D.addScatterCounter'


# ---------------------------------------------------------------------------
# #10: range mistakes must raise ValueError in Python, before any ctypes call
# ---------------------------------------------------------------------------

def test_espectrum_rejects_nonpositive_min_for_log_binning():
    with pytest.raises(ValueError, match="Scorer espec"):
        ESpectrumHelper("espec", min=0, max=1, numbin=10, linear=False)


def test_espectrum_rejects_inverted_range():
    with pytest.raises(ValueError, match="Scorer espec"):
        ESpectrumHelper("espec", min=1, max=1e-5, numbin=10)


def test_espectrum_allows_zero_min_with_linear_binning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # the deprecated linear= alias itself is allowed to warn
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        h = ESpectrumHelper("espec", min=0, max=1, numbin=10, linear=True)
    assert h.linear is True


def test_wlspectrum_range_validation():
    with pytest.raises(ValueError):
        WlSpectrumHelper("wl", min=0.0, max=10, numbin=10, linear=False)
    with pytest.raises(ValueError):
        WlSpectrumHelper("wl", min=10, max=0.1, numbin=10)


def test_volfluence_and_deposition_range_validation():
    with pytest.raises(ValueError):
        VolFluenceHelper("vf", min=0, max=10, numbin=10, linear=False)
    with pytest.raises(ValueError):
        DepositionHelper("dep", min=5, max=-5, numbin=10, pdg=2112, ptstate='ENTRY')


def test_tof_range_validation():
    with pytest.raises(ValueError):
        TOFHelper("tof", min=1e-3, max=1e-4, numbin=10)


def test_psdhelper_yrange_validation():
    with pytest.raises(ValueError):
        PSDHelper("psd", xmin=-10, xmax=10, xnumbin=10, ymin=10, ymax=-10, ynumbin=10)


def test_directsqw_ekin_yrange_validation():
    with pytest.raises(ValueError):
        DirectSqwHelper("sqw", 10., 0.025, ekinmin=0.5, ekinmax=-0.5)


def test_directsq_inverted_qrange_validation():
    with pytest.raises(ValueError, match="Scorer sq"):
        DirectSqHelper("sq", qmin=10., qmax=1., numbin=10, mod_smp_dist=10.)


# ---------------------------------------------------------------------------
# #11: MCPLOutHelper must pre-check the output directory in Python
# ---------------------------------------------------------------------------

def test_mcplout_rejects_missing_directory():
    out = MCPLOutHelper('/no_such_cinema_test_dir/out.mcpl')
    with pytest.raises(ValueError, match="no_such_cinema_test_dir"):
        out.make(_RejectingVol())


def test_mcplout_rejects_unwritable_directory(tmp_path):
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    ro = tmp_path / "readonly"
    ro.mkdir()
    ro.chmod(0o500)
    out = MCPLOutHelper(str(ro / "out.mcpl"))
    try:
        with pytest.raises(ValueError, match="not writable"):
            out.make(_RejectingVol())
    finally:
        ro.chmod(0o700)


def test_mcplout_valid_directory_reaches_the_binding(tmp_path, monkeypatch):
    calls = {}

    def fake_new(name, pdg, groupid, kill, compress):
        calls['name'] = name.decode('utf-8') if isinstance(name, bytes) else name
        return 4242

    monkeypatch.setattr(scorer_mod, '_pt_KillerMCPL_new', fake_new)
    out = MCPLOutHelper(str(tmp_path / "out.mcpl"))
    vol = _RecordingVol()
    out.make(vol)
    assert vol.calledWith[1] == 4242
    assert "out.mcpl" in calls['name']


# ---------------------------------------------------------------------------
# #24: legacy scorer APIs must emit DeprecationWarning
# ---------------------------------------------------------------------------

def test_legacy_configstring_scorers_warn():
    for cls in (PSD, WlSpectrum, ESpectrum, TOF, VolFluence):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cls()
        assert warnedDeprecations(w), f"{cls.__name__} construction emitted no DeprecationWarning"


def test_legacy_v1_helpers_warn():
    for make in (lambda: ESpectrumHelperV1("en"),
                 lambda: WlSpectrumHelperV1("wl"),
                 lambda: TOFHelperV1("tof"),
                 lambda: VolFluenceHelperV1("vf")):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            make()
        assert warnedDeprecations(w), "V1 helper construction emitted no DeprecationWarning"


def test_modern_helpers_do_not_warn_on_default_use():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ESpectrumHelper("en", min=1e-5, max=1, numbin=10)
        TOFHelper("tof")
    assert not warnedDeprecations(w)


def test_legacy_defaults_deliberately_differ_from_helpers():
    # documented drift: the string-config classes keep their historical
    # defaults for backward compatibility (unification would silently change
    # existing scripts, see usability report #24)
    assert ESpectrum().cfg_max == 0.25
    assert (WlSpectrum().cfg_min, WlSpectrum().cfg_max) == (0.0, 5)
    assert (TOF().cfg_min, TOF().cfg_max) == (0.0025, 0.008)
    assert VolFluence().cfg_ptstate == 'ENTRY'
    assert VolFluence().cfg_linear == 'yes'


# ---------------------------------------------------------------------------
# #25: binning flag names (log canonical; linear/logx deprecated aliases)
# ---------------------------------------------------------------------------

def test_linear_kwarg_still_works_but_warns():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        h = ESpectrumHelper("en", min=1e-5, max=1, numbin=10, linear=False)
    assert warnedDeprecations(w), "linear= did not warn"
    assert h.log is True and h.linear is False


def test_log_kwarg_is_canonical_and_silent():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        h = ESpectrumHelper("en", min=1e-5, max=1, numbin=10, log=True)
        h2 = WlSpectrumHelper("wl", min=0.1, max=10, numbin=10, log=False)
    assert not warnedDeprecations(w)
    assert h.log is True and h.linear is False
    assert h2.log is False and h2.linear is True


def test_base_scorer_flags_consistent():
    h = TOFHelper("tof")
    assert h.linear is True and h.log is False


def test_directsqw_logx_deprecated_alias():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        h = DirectSqwHelper("sqw", 10., 0.025, logx=True)
    assert warnedDeprecations(w), "logx= did not warn"
    assert h.logx is True and h.log is True


def test_directsqw_log_flag_warns_about_missing_cxx_support():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        h = DirectSqwHelper("sqw", 10., 0.025, log=True)
    assert any(issubclass(x.category, UserWarning) and 'linearly binned' in str(x.message)
               for x in w), "log=True did not warn that the C++ scorer stays linear"


# ---------------------------------------------------------------------------
# #28: makePSD deprecation and clear failure on non-Box solids
# ---------------------------------------------------------------------------

def test_makepsd_warns_deprecation_for_box():
    class _BoxLike:
        hx = 2.0
        hy = 2.0
        hz = 0.0001

    class _Vol:
        solid = _BoxLike()

        def addScorer(self, cfg):
            self.cfg = cfg

    vol = _Vol()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        makePSD('psd', vol)
    assert warnedDeprecations(w), "makePSD emitted no DeprecationWarning"
    assert 'Scorer=PSD' in vol.cfg


def test_makepsd_rejects_non_box_solid():
    class _TubeLike:
        # non-Box solids have no hx/hy/hz half-length attributes
        pass

    class _Vol:
        solid = _TubeLike()

    with pytest.raises(TypeError, match="PSDHelper"):
        makePSD('psd', _Vol())


# ---------------------------------------------------------------------------
# #33: ParticleTracingState.from_string must reject garbage; ptsNum deduplicated
# ---------------------------------------------------------------------------

def test_from_string_rejects_garbage():
    with pytest.raises(ValueError, match="Valid"):
        ParticleTracingState.from_string('BOGUS')


def test_from_string_valid_names_case_insensitive():
    assert ParticleTracingState.from_string('entry') is ParticleTracingState.ENTRY
    assert ParticleTracingState.from_string('Pea_Pre') is ParticleTracingState.PEA_PRE


def test_ptsnum_delegates_to_the_enum_table():
    h = TOFHelper("tof")
    assert h.ptsNum == ParticleTracingState['ENTRY'].value_num == 1
    h2 = ESpectrumHelper("en", min=1e-5, max=1, numbin=10, ptstate='ABSORB')
    assert h2.ptsNum == ParticleTracingState['ABSORB'].value_num == 7


def test_scorerhelper_has_real_docstring():
    assert ScorerHelper_docstring_present()


def ScorerHelper_docstring_present():
    from Cinema.Prompt.scorer import ScorerHelper
    doc = ScorerHelper.__doc__
    return doc is not None and 'ScorerHelper' in doc and 'ptstate' in doc


# ---------------------------------------------------------------------------
# #38: DirectSqHelper docstring names the real parameter; immutable defaults
# ---------------------------------------------------------------------------

def test_directsq_docstring_documents_the_real_parameter():
    doc = DirectSqHelper.__init__.__doc__
    assert 'mod_smp_dist : float' in doc
    assert 'distanceMS : float' not in doc


def test_directsq_defaults_are_immutable():
    a = DirectSqHelper("a", qmin=1., qmax=10., numbin=10, mod_smp_dist=10.)
    b = DirectSqHelper("b", qmin=1., qmax=10., numbin=10, mod_smp_dist=10.)
    assert isinstance(a.refDir, tuple) and isinstance(a.samplePos, tuple)
    with pytest.raises(TypeError):
        a.refDir[0] = 99.0
    assert b.refDir[0] == 0
    assert b.samplePos[0] == 0


def test_directsqw_defaults_are_immutable():
    h = DirectSqwHelper("sqw", 10., 0.025)
    assert h.mean_incident_dir == (0, 0, 1)
    assert h.sample_position == (0, 0, 0)
