#!/usr/bin/env python3
# Roundtrip tests: Solid -> pyvista mesh -> Tessellated -> back to transport.
# See doc/plan/06-mesh-transport.md for the design contract.

import numpy as np
import pytest

pyvista = pytest.importorskip('pyvista')

from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.physics import Material
from Cinema.Prompt.scorer import ESpectrum
from Cinema.Prompt.solid import Box, Sphere, Tube, SolidSubtraction, Tessellated
from Cinema.Prompt.Mesh import BoolSolidMeshHandlerMixin

# the mesh API lives on the Solid classes now (mixed in); bind the statics
# locally so the mesh-conditioning tests read like the calls they make
clean_for_tessellated = BoolSolidMeshHandlerMixin.clean_for_tessellated
structured_cylinder = BoolSolidMeshHandlerMixin.structured_cylinder
boolean = BoolSolidMeshHandlerMixin.boolean


def _volume_centroid(mesh):
    """Signed volume and volume-weighted centroid of a closed triangle mesh
    (divergence theorem over the facets)."""
    points = mesh.points
    tris = mesh.triangulate().faces.reshape(-1, 4)[:, 1:]
    a, b, c = points[tris[:, 0]], points[tris[:, 1]], points[tris[:, 2]]
    tet = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6.0
    vol = tet.sum()
    centroid = ((a + b + c) / 4.0 * tet[:, None]).sum(axis=0) / vol
    return vol, centroid


def test_box_exact():
    box = Box(10, 20, 30)
    mesh = box.to_polydata()
    assert mesh.n_points == 8
    assert mesh.n_faces_strict == 6
    rep = box.roundtrip_report()
    assert rep['ratio'] == pytest.approx(1.0, rel=1e-12)  # planar solid: exact


def test_sphere_tube_fidelity_monotone():
    sphere = Sphere(0, 50)
    rep30 = sphere.roundtrip_report(30)
    rep100 = sphere.roundtrip_report(100)
    assert rep30['ratio'] > 0.98
    assert rep100['ratio'] > 0.999
    assert rep100['ratio'] >= rep30['ratio']

    tube = Tube(0, 50, 100)
    rt30 = tube.roundtrip_report(30)
    rt100 = tube.roundtrip_report(100)
    assert rt30['ratio'] > 0.98
    assert rt100['ratio'] > 0.999


def test_capacity_cross_check_pyvista():
    # VecGeom surface integral vs pyvista volume: independent implementations
    rep = Sphere(0, 50).roundtrip_report(64)
    assert rep['capacity_mesh'] == pytest.approx(rep['capacity_polydata'],
                                                 rel=1e-12)


def test_boolean_solid_fallback():
    """Boolean Solids mesh through the operand-unpacking fallback (identity
    placement): Solid in, Tessellated out, capacity vs the analytic annulus."""
    pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    holed = SolidSubtraction(Tube(0, 50, 100), Tube(0, 10, 120))
    solid = holed.to_tessellated(64)
    analytic = np.pi * (50.**2 - 10.**2) * 200
    assert solid.capacity() / analytic > 0.99  # 64-gon deficit ~1.6e-3


def test_boolean_transform_offset():
    """The right operand's Transformation3D must reach the mesh.

    The hole sits at x=+15: fully inside laterally (10+15 < 50) and piercing
    both caps (halfz 150 > 100), so the removed volume is exact.  The volume
    alone cannot tell an offset hole from a coaxial one (same removed
    volume) - the centroid can: it shifts by -15 * 10^2 / (50^2 - 10^2) =
    -0.625 mm (the inscribed-polygon deficits of hole and outer tube share
    the same factor and cancel in the ratio).
    """
    pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    holed = SolidSubtraction(Tube(0, 50, 100), Tube(0, 10, 150),
                             Transformation3D(x=15))
    mesh = clean_for_tessellated(holed.to_polydata(64))
    vol, centroid = _volume_centroid(mesh)
    analytic = np.pi * (50.**2 - 10.**2) * 200
    assert vol / analytic == pytest.approx(1.0, rel=0.005)  # 64-gon deficit
    assert centroid[0] == pytest.approx(-0.625, abs=0.01)
    assert centroid[1] == pytest.approx(0., abs=1e-9)
    assert centroid[2] == pytest.approx(0., abs=1e-9)


def test_boolean_transform_rotation():
    """A tilted, offset box milled out of another box (rot_new_z=30 + x=10)
    vs a reference whose operand was rotated/translated with pyvista itself -
    independent of the C++ placement plumbing.

    The operand has a non-square cross-section (40x120), so +30 deg and
    -30 deg (what an inverted transform would apply) remove different
    volumes - unlike a 90-deg rotation of symmetric operands, this pins the
    rotation DIRECTION as well.  The CSG capacity (MC estimate) anchors
    which of the two the VecGeom navigation actually implements.
    """
    pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    box, tower = Box(40, 40, 60), Box(20, 60, 80)
    sub = SolidSubtraction(box, tower,
                           Transformation3D(x=10).applyRotZ(30))
    ours = sub.to_polydata(64)
    ref_l = box.to_polydata(64)
    ref_r = tower.to_polydata(64).rotate_z(30).translate((10, 0, 0))
    ref = boolean(ref_l, ref_r, 'difference')
    assert ours.volume == pytest.approx(ref.volume, rel=1e-6)
    coaxial = boolean(ref_l, tower.to_polydata(64), 'difference')
    assert ours.volume != pytest.approx(coaxial.volume, rel=1e-2)
    # VecGeom's own MC capacity of the same CSG boolean agrees with the mesh
    assert ours.volume == pytest.approx(sub.capacity(), rel=1e-2)


def test_boolean_mesh_fallback_trimesh():
    pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    outer = pyvista.Cylinder(radius=50, height=200, resolution=64).triangulate()
    inner = pyvista.Cylinder(radius=10, height=200, resolution=64).triangulate()
    result = boolean(outer, inner, 'difference')
    solid = Tessellated(clean_for_tessellated(result))
    analytic = np.pi * (50.**2 - 10.**2) * 200
    assert solid.capacity() / analytic > 0.99  # 64-gon deficit ~1.6e-3


def test_structured_cylinder():
    mesh = structured_cylinder(50, 200, 64, 10)
    assert mesh.n_open_edges == 0
    solid = Tessellated(clean_for_tessellated(mesh))
    cap = solid.capacity()
    assert cap == pytest.approx(mesh.volume, rel=1e-12)
    analytic = np.pi * 50.**2 * 200
    assert cap / analytic == pytest.approx((64 / (2 * np.pi)) * np.sin(2 * np.pi / 64),
                                           rel=1e-6)  # inscribed polygon deficit


def test_clean_removes_degenerate_facets():
    mesh = structured_cylinder(50, 200, 16, 4)
    bad = np.hstack([mesh.faces, np.asarray([3, 0, 0, 1])])  # zero-area facet
    dirty = pyvista.PolyData(mesh.points, bad)
    cleaned = clean_for_tessellated(dirty)
    expected = mesh.triangulate().n_faces_strict  # side quads split in two
    assert cleaned.n_faces_strict == expected
    assert cleaned.n_open_edges == 0


def test_clean_rejects_open_mesh():
    mesh = structured_cylinder(50, 200, 16, 4)
    faces = np.asarray(mesh.faces).copy()
    faces = faces[5:]  # drop the first face -> hole
    opened = pyvista.PolyData(mesh.points, faces)
    with pytest.raises(ValueError, match='watertight'):
        clean_for_tessellated(opened)


def test_tessellated_rejects_big_faces():
    theta = np.linspace(0, 2 * np.pi, 6, endpoint=False)
    points = np.column_stack([np.cos(theta), np.sin(theta), np.zeros(6)])
    pentagon = pyvista.PolyData(points, np.asarray([6, 0, 1, 2, 3, 4, 5]))
    with pytest.raises(ValueError, match='vertices'):
        Tessellated(pentagon)


@pytest.mark.forked
def test_transport_csg_vs_mesh_smoke():
    """Symmetric world: analytic sphere (left) vs its Tessellated mesh
    (right), isotropic gun at the centre.  By symmetry the ENTRY spectra
    must agree within Poisson statistics (3 sigma).

    Forked: setWorld closes the VecGeom geometry for the whole process
    (GeoManager is a singleton and fIsClosed never resets), so any later
    world-building test would segfault in ResourceManager::addScorer -
    a pre-existing engine limitation, one closed geometry per process.
    """
    r, dist = 60., 150.
    water = Material('freegas::H2O/1gcm3/H_is_H1/O_is_O16')

    from Cinema.Prompt import Prompt

    class Sim(Prompt):
        def makeWorld(self):
            world = Volume('world', Box(400, 400, 400))
            csg = Volume('csg', Sphere(0, r), matCfg=water)
            mesh = Volume('mesh', Sphere(0, r).to_tessellated(64),
                          matCfg=water)
            left = ESpectrum(); left.cfg_name = 'esL'
            right = ESpectrum(); right.cfg_name = 'esR'
            csg.addScorer(left)
            mesh.addScorer(right)
            world.placeChild('csgP', csg, Transformation3D(-dist, 0, 0))
            world.placeChild('meshP', mesh, Transformation3D(dist, 0, 0))
            self.setWorld(world)

    sim = Sim(seed=4096)
    sim.makeWorld()
    gun = IsotropicGun()
    gun.setEnergy(0.0253)  # eV, thermal
    sim.simulate(gun, 1e4)

    hit_l = sim.gatherHistData('esL').getHit().sum()
    hit_r = sim.gatherHistData('esR').getHit().sum()
    assert hit_l > 100  # enough statistics for the comparison
    assert abs(hit_l - hit_r) < 3 * np.sqrt(hit_l + hit_r)
