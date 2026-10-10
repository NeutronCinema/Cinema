#!/usr/bin/env python3
# Regression tests for the Prompt/geo.py + Prompt/component.py +
# Prompt/physics.py fixes (usability audit findings #2, #5, #8, #12, #21,
# #22, #27, #31, #37).
#
# Geometry assembly runs against the real C++ library (volumes and the
# boolean-capacity overlap probe are cheap); no transport is started. Tests
# that need the NCrystal C API skip cleanly when the library is unavailable.

import warnings
from copy import deepcopy

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as scipyRot

import Cinema.Prompt.geo as geo
from Cinema.Prompt.component import Anchor, DiskChopper, EntityArray
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.physics import DiskChopper as CanonicalDiskChopper
from Cinema.Prompt.physics import Material, _getNcrystalCApi, wrapRawNccfg
from Cinema.Prompt.solid import Box

FILLER = 'freegas::H1/1e-26kgm3/H_is_1_H1'


def _getNCCApiUnavailable():
    try:
        return _getNcrystalCApi() is None
    except Exception:
        return True


needsNCCApi = pytest.mark.skipif(_getNCCApiUnavailable(),
                                 reason='NCrystal C API unavailable')


def makeVol(name, hx=10.):
    return Volume(name, Box(hx, hx, hx), matCfg=FILLER)


# ----------------------------------------------------------------- finding #2

@pytest.mark.slow  # >0.7 s body: excluded from the pre-push hook, runs in cimbuild -t
def test_from_alignment_aligns_vectors():
    # the documented align-two-vectors constructor used to fail on every
    # input ("if rotated or original is None" parsed as
    # "(rotated) or (original is None)")
    rotated = np.array([[0., 0., 1.], [1., 0., 0.]])
    original = np.array([[0., 0., 1.], [0., 1., 0.]])
    tf = Transformation3D.from_alignment(1., 2., 3., rotated=rotated,
                                         original=original)
    ref, _ = scipyRot.align_vectors(original, rotated)
    assert np.allclose(tf.getRotMatrix(), ref.as_matrix())
    assert np.allclose(tf.getTranslation(), [1., 2., 3.])


def test_from_alignment_accepts_plain_lists():
    # plain python lists hit the same broken guard on the old code
    tf = Transformation3D.from_alignment(
        rotated=[[0., 0., 1.], [1., 0., 0.]],
        original=[[0., 0., 1.], [0., 1., 0.]])
    assert np.allclose(tf.getTranslation(), [0., 0., 0.])


def test_from_alignement_deprecated_spelling_works():
    rotated = np.array([[0., 0., 1.], [1., 0., 0.]])
    original = np.array([[0., 0., 1.], [0., 1., 0.]])
    with pytest.warns(DeprecationWarning):
        tf = Transformation3D.from_alignement(0., 0., 0., rotated=rotated,
                                              original=original)
    ref, _ = scipyRot.align_vectors(original, rotated)
    assert np.allclose(tf.getRotMatrix(), ref.as_matrix())


def test_setrotbyalignement_deprecated_alias():
    tf = Transformation3D()
    with pytest.warns(DeprecationWarning):
        ret = tf.setRotByAlignement([[0., 0., 1.], [1., 0., 0.]],
                                    [[0., 0., 1.], [0., 1., 0.]])
    assert ret is tf


# ----------------------------------------------------------------- finding #5

def test_deepcopy_keeps_translation_and_rotation():
    src = Transformation3D(10., 20., 30.).applyRotZ(45.)
    cp = deepcopy(src)
    # the copy used to report getTranslation() == [0, 0, 0] (the values went
    # into the non-mangled "_translation" attribute)
    assert np.allclose(cp.getTranslation(), [10., 20., 30.])
    assert np.allclose(cp.getRotMatrix(), src.getRotMatrix())
    assert not hasattr(cp, '_translation')
    assert not hasattr(cp, 'sciRotMatrix')
    # the copy must not alias the source translation array
    assert not np.shares_memory(cp.getTranslation(), src.getTranslation())
    assert src.getTranslation()[0] == 10.
    # python and C++ side of the copy agree
    pts = np.array([[1., 0., 0.]])
    assert np.allclose(cp.transform_py(pts), cp.transform(pts))


# ---------------------------------------------------------------- finding #12

def test_applyrotbymatrix_updates_python_side_and_returns_self():
    rz90 = scipyRot.from_euler('z', 90, degrees=True)
    tf = Transformation3D()
    ret = tf.applyRotbyMatrix(rz90.as_matrix())
    assert ret is tf
    assert np.allclose(tf.getRotMatrix(), rz90.as_matrix())
    # the python-side rotation used to stay identity: C++ and python
    # transforms of the same frame diverged
    pts = np.array([[1., 0., 0.]])
    assert np.allclose(tf.transform_py(pts), tf.transform(pts))
    # chaining works (old code returned None)
    chained = Transformation3D().applyRotbyMatrix(rz90.as_matrix()).applyRotZ(30)
    assert isinstance(chained, Transformation3D)


def test_deepcopy_after_applyrotbymatrix_keeps_rotation():
    rz90 = scipyRot.from_euler('z', 90, degrees=True)
    tf = Transformation3D()
    tf.applyRotbyMatrix(rz90.as_matrix())
    cp = deepcopy(tf)
    # deepcopy rebuilds from the python-side rotation, which used to be stale
    assert np.allclose(cp.getRotMatrix(), rz90.as_matrix())


# ---------------------------------------------------------------- finding #31

def test_transformation3d_rejects_nonnumeric_arguments():
    with pytest.raises(TypeError, match='Transformation3D'):
        Transformation3D(None)
    with pytest.raises(TypeError, match=r'Transformation3D\(\*pos\)'):
        Transformation3D([0, 0, 100])
    with pytest.raises(TypeError):
        Transformation3D(0., 0., np.array([1., 2., 3.]))
    # plain ints and numpy scalars remain fine
    Transformation3D(np.float64(1.), 2, 0)


def test_failed_construction_leaves_no_unraisable_del():
    # on the old code the __del__ of the never-initialized object printed
    # "AttributeError: ... no attribute 'cobj'" via the unraisable hook
    import gc
    import sys
    unraisables = []
    oldHook = sys.unraisablehook
    sys.unraisablehook = unraisables.append
    try:
        tf = Transformation3D(1., 2., 3.)
        del tf
        try:
            Transformation3D(None)
        except TypeError:
            pass
        gc.collect()
        assert unraisables == []
    finally:
        sys.unraisablehook = oldHook


# ---------------------------------------------------------------- finding #21

def test_overlapping_daughters_warn():
    world = makeVol('oworld', 30.)
    world.placeChild('od1', makeVol('od1'), Transformation3D(0., 0., 0.))
    # 20 mm cubes shifted by (5,5,5): 15x15x15 mm of doubly defined region
    with pytest.warns(RuntimeWarning, match=r"Daughter volumes .* overlap"):
        world.placeChild('od2', makeVol('od2'), Transformation3D(5., 5., 5.))


def test_disjoint_daughters_do_not_warn():
    world = makeVol('dworld', 60.)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter('always')
        world.placeChild('dd1', makeVol('dd1'), Transformation3D(0., 0., 0.))
        world.placeChild('dd2', makeVol('dd2'), Transformation3D(25., 0., 0.))
    assert not [w for w in rec if 'overlap' in str(w.message)]


def test_overlap_check_can_be_disabled():
    world = makeVol('nworld', 30.)
    world.placeChild('nd1', makeVol('nd1'), Transformation3D(0., 0., 0.))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter('always')
        world.placeChild('nd2', makeVol('nd2'), Transformation3D(5., 5., 5.),
                         checkOverlap=False)
    assert not [w for w in rec if 'overlap' in str(w.message)]


# ---------------------------------------------------------------- finding #22

@pytest.mark.slow  # >0.7 s body: excluded from the pre-push hook, runs in cimbuild -t
def test_anchor_getreltransf_known_transform():
    a1 = Anchor(Transformation3D(0., 0., 0.), 'origin')
    a2 = Anchor(Transformation3D(100., 0., 0.).applyRotZ(90.), 'shifted')
    rel = a1.getRelTransf(a2)
    # p_self = R_rel p_other + t_rel with R_rel = R1^-1 R2, t_rel = R1^-1 (t2-t1)
    assert np.allclose(rel.refFrame.getRotMatrix(),
                       scipyRot.from_euler('z', 90, degrees=True).as_matrix())
    assert np.allclose(rel.refFrame.getTranslation(), [100., 0., 0.])
    # a point 10 mm along other's local x maps to (100, 10, 0) in self frame
    p = np.array([[10., 0., 0.]])
    mapped = rel.refFrame.getRotMatrix().dot(p[0]) + rel.refFrame.getTranslation()
    assert np.allclose(mapped, [100., 10., 0.])


def test_frame_composition_mul():
    parent = Transformation3D(0., 0., 100.).applyRotZ(90.)
    child = Transformation3D(10., 0., 0.)
    comp = parent * child
    # t = t_parent + R_parent . t_child
    assert np.allclose(comp.getTranslation(), [0., 10., 100.])
    assert np.allclose(comp.getRotMatrix(), parent.getRotMatrix())


def test_entityarray_make_rotate_z_places_rotated_copies():
    ea = EntityArray(makeVol('rzel', 2.))
    ea.create(Transformation3D(10., 0., 0.))
    ea.make_rotate_z(90., 1)
    assert len(ea.members) == 2
    world = ea.refFrame * ea.members[1].refFrame
    assert np.allclose(world.getTranslation(), [0., 10., 0.])
    assert np.allclose(world.getRotMatrix(),
                       scipyRot.from_euler('z', 90, degrees=True).as_matrix())


def test_entityarray_reflect_mirrors_positions():
    ea = EntityArray(makeVol('refl', 2.))
    ea.create(Transformation3D(10., 0., 0.))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter('always')
        ea.reflect('YZ', 0.)
    assert len(ea.members) == 2
    world = ea.refFrame * ea.members[1].refFrame
    assert np.allclose(world.getTranslation(), [-10., 0., 0.])
    # untilted members mirror without an orientation caveat
    assert not [w for w in rec if issubclass(w.category, RuntimeWarning)]


def test_entityarray_reflect_warns_on_rotated_members():
    ea = EntityArray(makeVol('refl2', 2.))
    ea.create(Transformation3D(10., 0., 0.).applyRotZ(30.))
    with pytest.warns(RuntimeWarning, match='orientation'):
        ea.reflect('YZ', 0.)


# ---------------------------------------------------------------- finding #27

def test_default_matcfg_recorded_and_warns_once():
    # make the once-flag deterministic even without per-test forking
    geo._defaultMatcfgWarned = False
    with pytest.warns(RuntimeWarning, match='matCfg'):
        v = Volume('defaultfill', Box(1., 1., 1.))
    # .matCfg used to stay None although the dilute filler was configured
    assert v.matCfg == 'freegas::H1/1e-26kgm3/H_is_1_H1'
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter('always')
        v2 = Volume('defaultfill2', Box(1., 1., 1.))
    assert not [w for w in rec if issubclass(w.category, RuntimeWarning)]
    assert v2.matCfg == v.matCfg


# ------------------------------------------------------------------ finding #8

def test_raw_parameterised_nccfg_warned_and_wrapped():
    with pytest.warns(RuntimeWarning, match='raw NCrystal'):
        wrapped = wrapRawNccfg('Al_sg225.ncmat;temp=300K')
    assert wrapped == "physics=ncrystal;nccfg='Al_sg225.ncmat;temp=300K'"
    # bare raw strings and compound materials carry no parameters and are
    # accepted unchanged
    assert wrapRawNccfg('Al_sg225.ncmat') == 'Al_sg225.ncmat'
    assert wrapRawNccfg('solid::Cd/8.65gcm3') == 'solid::Cd/8.65gcm3'
    assert wrapRawNccfg('freegas::H1/1e-26kgm3/H_is_1_H1') == \
        'freegas::H1/1e-26kgm3/H_is_1_H1'
    # Material-style strings are untouched
    canon = "physics=ncrystal;nccfg='Al_sg225.ncmat'"
    assert wrapRawNccfg(canon) == canon


@pytest.mark.medium  # ~0.46 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
@needsNCCApi
def test_bad_nccfg_content_raises_python_error():
    # NCrystal::Error::BadInput used to terminate the process without any
    # python exception; the check delegates to the real NCrystal parser
    with pytest.raises(ValueError, match='NCrystal'):
        Material('void.ncmat;nosuchkey=3')
    with pytest.raises(ValueError, match='NCrystal'):
        Material('void.ncmat;temp=notanumber')
    # the report's original SIGABRT repro: mos without dir1/dir2 is rejected
    # by the NCrystal model factory even though info-level parsing accepts
    # it, so the pre-check must build the scatter model to see this error
    with pytest.raises(ValueError, match='mos'):
        Material('Ge_sg227.ncmat;mos=0.0267deg')
    # whatever the linked NCrystal accepts must pass the pre-validation
    # untouched
    Material('freegas::H1/1e-26kgm3/H_is_1_H1')
    Material('Ge_sg227.ncmat')
    Material('solid::Cd/8.65gcm3')


@pytest.mark.medium  # ~0.31 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
@needsNCCApi
def test_setmaterial_mos_repro_raises_not_aborts():
    # the usability report's verbatim #8 repro: this exact call used to
    # terminate the whole process (SIGABRT, "Must set all or none of mos,
    # dir1 and dir2 parameters")
    with pytest.raises(ValueError, match='mos'):
        Volume('mosrepro', Box(10, 10, 1), matCfg='Ge_sg227.ncmat;mos=0.0267deg')


@pytest.mark.medium  # ~0.32 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
@needsNCCApi
def test_setmaterial_validates_content_before_ctypes():
    with pytest.raises(ValueError, match='NCrystal'):
        Volume('cmatv', Box(2., 2., 2.),
               matCfg="physics=ncrystal;nccfg='void.ncmat;nosuchkey=3'")


@pytest.mark.medium  # ~0.32 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
def test_setmaterial_accepts_valid_cfgs_end_to_end():
    v = Volume('matok', Box(2., 2., 2.), matCfg=FILLER)
    v.setMaterial('solid::Cd/8.65gcm3')
    with pytest.warns(RuntimeWarning, match='raw NCrystal'):
        v.setMaterial('void.ncmat;temp=100K')


@pytest.mark.medium  # ~0.32 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
def test_material_cfg_roundtrip_unchanged():
    m = Material('void.ncmat')
    assert m.cfg == "physics=ncrystal;nccfg='void.ncmat'"


# ---------------------------------------------------------------- finding #37

@pytest.mark.medium  # ~0.31 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
def test_setabsorpinweight_rejects_garbage():
    m = Material('void.ncmat')
    with pytest.raises(TypeError, match='flag'):
        m.setAbsorpInWeight('factor')
    # any nonzero "factor" used to be truthiness-coerced to true
    with pytest.raises(TypeError):
        m.setAbsorpInWeight(5.0)
    with pytest.raises(TypeError):
        m.setAbsorpInWeight(0.5)
    with pytest.raises(TypeError):
        m.setAbsorpInWeight(None)


@pytest.mark.medium  # ~0.31 s body: medium tier (cimbuild -tt/-ttt), skipped by the pre-push hook
def test_setabsorpinweight_accepts_bools_and_01():
    m = Material('void.ncmat')
    m.setAbsorpInWeight(True)
    assert 'absorp_in_weight=true' in m.cfg
    m.setAbsorpInWeight(False)
    assert 'absorp_in_weight' not in m.cfg
    m.setAbsorpInWeight(1)
    assert 'absorp_in_weight=true' in m.cfg
    m.setAbsorpInWeight(0)
    assert 'absorp_in_weight' not in m.cfg


def test_diskchopper_canonical_physics_definition():
    chp = CanonicalDiskChopper()
    assert chp.cfg == 'physics=DiskChopper;rotFreq=25;r=100;theta0=20;n=1;phase=0;'
    kw = CanonicalDiskChopper(rotFreq=10., r=50., theta0=5., n=2, phase=30.)
    assert 'rotFreq=10.0' in kw.cfg
    assert 'n=2' in kw.cfg and 'phase=30.0' in kw.cfg


def test_component_diskchopper_is_deprecated_working_alias():
    with pytest.warns(DeprecationWarning):
        legacy = DiskChopper()
    assert legacy.cfg == CanonicalDiskChopper().cfg
    assert isinstance(legacy, CanonicalDiskChopper)
