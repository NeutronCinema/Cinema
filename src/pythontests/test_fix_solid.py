"""Regression tests for usability findings #17 and #26 (Prompt/solid.py).

#17: the Tube docstring example pre-converted 90 with np.deg2rad although the
     parameter is degree-based, so the "quarter tube" example built a 0.44 %
     sliver.
#26: the same degree-based angular parameters were spelled four ways across
     the module (startphi/deltaphi, phiStart_deg/phiDelta_deg, startPhi/
     deltaPhi, sphi/dphi), the hyperbolic tube class was misspelled
     HypebolicTube, and its stereo-angle error demanded radians for a
     degree-based input.
"""

import re
import warnings

import pytest

from Cinema.Prompt.solid import (Tube, Sphere, Cone, PolyCone, GenTrapezoid,
                                 HyperbolicTube, HypebolicTube)
from Cinema.Prompt.geo import Volume


def _capacity(solid):
    """Capacity in mm^3, via a Volume wrapper of the solid."""
    return Volume('cap_probe', solid).getCapacity()


def test_tube_docstring_example_is_quarter_tube():
    # finding #17: execute the docstring example and check it really is a
    # quarter of the full tube (old example gave a ratio of 0.00436)
    m = re.search(r">>> tube_segment = (Tube\(.*\))\s*(?:#.*)?$", Tube.__doc__, re.M)
    assert m, "Tube docstring quarter-tube example is gone"
    expr = m.group(1)
    # the parameter is degree-based: the example must not pre-convert
    assert "deg2rad" not in expr, f"docstring example converts degrees twice: {expr}"
    tube = eval(expr)  # content is fixed by the docstring above
    full = _capacity(Tube(1.0, 2.0, 5.0))
    assert _capacity(tube) / full == pytest.approx(90 / 360)


def test_canonical_spellings_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        Tube(1, 2, 5, phiStart_deg=30, phiDelta_deg=90)
        Sphere(1, 2, phiStart_deg=0, phiDelta_deg=90, thetaStart_deg=0, thetaDelta_deg=45)
        Cone(3, 1, 10, 1, 0.5, phiStart_deg=30, phiDelta_deg=90)
        PolyCone([0, 2, 4, 6], [1, 1.5, 2, 1.5], [3, 3.5, 4, 3.5], phiStart_deg=0, phiDelta_deg=90)
        GenTrapezoid(13, 45, 0, 6, 4, 4, alpha1=0, dy2=6, dx3=4, dx4=4, alpha2=0)


def test_deprecated_spellings_warn():
    with pytest.warns(DeprecationWarning, match="startphi"):
        Tube(1, 2, 5, startphi=0, deltaphi=90)
    with pytest.warns(DeprecationWarning, match="starttheta"):
        Sphere(1, 2, starttheta=0, deltatheta=45)
    with pytest.warns(DeprecationWarning, match="startPhi"):
        Cone(3, 1, 10, 1, 0.5, startPhi=30, deltaPhi=90)
    with pytest.warns(DeprecationWarning, match="sphi"):
        PolyCone([0, 2, 4, 6], [1, 1.5, 2, 1.5], [3, 3.5, 4, 3.5], sphi=0, dphi=90)
    with pytest.warns(DeprecationWarning, match="Alpha1"):
        GenTrapezoid(13, 45, 0, 6, 4, 4, Alpha1=0, dy2=6, dx3=4, dx4=4, Alpha2=0)


def test_aliases_produce_identical_geometry_to_canonical():
    cases = [
        (lambda: Tube(1.0, 2.0, 5.0, phiStart_deg=0, phiDelta_deg=90),
         lambda: Tube(1.0, 2.0, 5.0, startphi=0, deltaphi=90)),
        (lambda: Sphere(1.0, 2.0, 0, 90, 0, 45),
         lambda: Sphere(1.0, 2.0, startphi=0, deltaphi=90, starttheta=0, deltatheta=45)),
        (lambda: Cone(3.0, 1.0, 10.0, 1.0, 0.5, phiStart_deg=0, phiDelta_deg=90),
         lambda: Cone(3.0, 1.0, 10.0, 1.0, 0.5, startPhi=0, deltaPhi=90)),
        (lambda: PolyCone([0, 2, 4, 6], [1, 1.5, 2, 1.5], [3, 3.5, 4, 3.5], phiStart_deg=0, phiDelta_deg=90),
         lambda: PolyCone([0, 2, 4, 6], [1, 1.5, 2, 1.5], [3, 3.5, 4, 3.5], sphi=0, dphi=90)),
        (lambda: GenTrapezoid(13, 45, 0, 6, 4, 4, alpha1=0, dy2=6, dx3=4, dx4=4, alpha2=0),
         lambda: GenTrapezoid(13, 45, 0, 6, 4, 4, Alpha1=0, dy2=6, dx3=4, dx4=4, Alpha2=0)),
    ]
    for canonical, legacy in cases:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert _capacity(legacy()) == pytest.approx(_capacity(canonical()))


def test_positional_call_sites_unchanged():
    # renaming parameters must not affect positional arguments
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        full = _capacity(Tube(1.0, 2.0, 5.0))
        assert _capacity(Tube(1.0, 2.0, 5.0, 0, 90)) == pytest.approx(full / 4)
        Sphere(1.0, 2.0, 0, 90, 0, 45)
        Cone(3.0, 1.0, 10.0, 1.0, 0.5, 30, 90)
        PolyCone([0, 2, 4, 6], [1, 1.5, 2, 1.5], [3, 3.5, 4, 3.5], 0, 90)
        GenTrapezoid(13, 45, 0, 6, 4, 4, 0, 6, 4, 4, 0)


def test_passing_both_spellings_raises():
    with pytest.raises(ValueError, match="not both"):
        Tube(1, 2, 5, phiStart_deg=30, startphi=45)


def test_unknown_keyword_still_typeerror():
    # **kwargs must not swallow typos
    with pytest.raises(TypeError):
        Tube(1, 2, 5, not_an_angle=1)


def test_alias_path_still_validates():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match="360"):
            Tube(1, 2, 5, startphi=0, deltaphi=400)
    assert any(issubclass(x.category, DeprecationWarning) for x in w)


def test_hyperbolictube_rename():
    h = HyperbolicTube(5.0, 40, 45, 10.0)
    assert isinstance(h, HyperbolicTube)


def test_hypebolictube_misspelled_alias_deprecated():
    with pytest.warns(DeprecationWarning):
        h = HypebolicTube(5.0, 40, 45, 10.0)
    assert isinstance(h, HyperbolicTube)
    assert _capacity(h) == pytest.approx(_capacity(HyperbolicTube(5.0, 40, 45, 10.0)))


def test_stereo_angle_error_matches_degree_input():
    # the ctor takes deg; the old message demanded radians and quoted the
    # rad-converted value, steering users into a silent unit error
    with pytest.raises(ValueError) as e:
        HyperbolicTube(5.0, 100, 100, 10.0)
    msg = str(e.value)
    assert "unit deg" in msg
    assert "unit rad" not in msg
    assert "100" in msg  # quotes the degree value the user actually passed
    # obeying the corrected message: degrees below 90 construct fine
    HyperbolicTube(5.0, 89, 89, 10.0)
    # a genuinely too-strong degree angle is still rejected
    with pytest.raises(ValueError):
        HyperbolicTube(5.0, 91, 45, 10.0)


def test_gentrapezoid_missing_arguments_named():
    # alpha1/alpha2 stay required despite the sentinel defaults needed by the
    # deprecated Alpha1/Alpha2 keywords
    with pytest.raises(TypeError, match="alpha2"):
        GenTrapezoid(13, 45, 0, 6, 4, 4, alpha1=0, dy2=6, dx3=4, dx4=4)


def test_docstrings_use_canonical_spellings():
    assert "phiStart_deg" in Tube.__doc__
    assert "phiStart_deg" in Sphere.__doc__
    assert "thetaStart_deg" in Sphere.__doc__
    assert "phiStart_deg" in Cone.__doc__
    assert "phiStart_deg" in PolyCone.__doc__
    assert "alpha1" in GenTrapezoid.__doc__
