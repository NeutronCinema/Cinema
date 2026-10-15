#!/usr/bin/env python3
"""
Test prompt ptstate

ENTRY
EXIT
    PROPAGATE_PRE
    PROPAGATE_POST
    PEA_PRE
    PEA_POST
    SURFACE
    ABSORB
"""
import pytest
from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Sphere, Tube
from Cinema.Prompt.gun import SimpleThermalGun
from Cinema.Prompt.scorer import ESpectrumHelper
from Cinema.Prompt.geo import Transformation3D
import numpy as np

@pytest.mark.slow  # >0.7 s body: excluded from the pre-push hook, runs in cimbuild -t
def test_ENTRY_EXIT():
    """
    A Sphere@Box model with void material
    Neutrons are expect to entry and exit twice the box
    """
    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            sample_mat = "void.ncmat"
            box = Volume('sample', Box(2,2,2), sample_mat)
            sphere = Volume('sphere', Sphere(0,1), sample_mat)

            scorerTest1 = ESpectrumHelper('testObj_ENTRY', 1e-6, 10, 20, 2112, 'ENTRY', False, )
            scorerTest1.make(box)
            scorerTest2 = ESpectrumHelper('testObj2_EXIT', 1e-6, 10, 20, 2112, 'EXIT', False, )
            scorerTest2.make(box)

            box.placeChild('phy_sphere', sphere)

            world.placeChild('physicalSample', box)

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()

    gun = "gun=MaxwellianGun;src_w=1;src_h=1;src_z=-100;slit_w=1;slit_h=1;slit_z=1e99;temperature=293;"
    # sim.show(gun, 100)
    pnum = 1e4
    sim.simulate(gun, pnum)
    wlhist = sim.gatherHistData('testObj_ENTRY')
    wlhist2 = sim.gatherHistData('testObj2_EXIT')
    print(np.array(wlhist.getTotalHit()))
    print(np.array(wlhist2.getTotalHit()))
    np.testing.assert_allclose(wlhist.getTotalHit(), pnum * 2, rtol=0.1)
    np.testing.assert_allclose(wlhist2.getTotalHit(), pnum * 2, rtol=0.1)
    sim.clear()


def test_PROPAGATE_PRE_POST():
    """
    A pensil model with ideal elastic material
    Neutrons are expect to propagate pre and post the box
    """
    class MySim(PromptMPI):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            length = 1e6
            world = Volume('world', Box(50, 50, length * 2 + 100))

            sample_mat = 'physics=idealElaScat;xs_barn=1;density_per_aa3=0.01;energy_transfer_eV=0.01'

            pensil = Volume('pensil', Tube(0,1e-9,length,), sample_mat)

            scorerTest1 = ESpectrumHelper('testObj_PRE', 0.00, 0.11, 10, 2112, 'PROPAGATE_PRE', False, linear=True)
            scorerTest1.make(pensil)
            scorerTest2 = ESpectrumHelper('testObj2_POST', 0.00, 0.11, 10, 2112, 'PROPAGATE_POST', False, linear=True)
            scorerTest2.make(pensil)

            world.placeChild('physicalSample', pensil, Transformation3D(z=length))

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()

    gun = SimpleThermalGun()
    gun.setEnergy(0.05)
    gun.setPosition([0,0,-100])

    # sim.show(gun, 100, zscale=1.)
    pnum = 1e4
    sim.simulate(gun, pnum)
    wlhist = sim.gatherHistData('testObj_PRE')
    wlhist2 = sim.gatherHistData('testObj2_POST')
    exp1 = [0.0, 0.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    exp2 = [0.0, 0.0, 0.0, 10000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    # print(list(wlhist.getHit()),sep=',')
    # print(list(wlhist2.getHit()),sep=',')
    # print(wlhist.getEdges())
    np.testing.assert_allclose(wlhist.getHit(), exp1, rtol=0.1)
    np.testing.assert_allclose(wlhist2.getHit(), exp2, rtol=0.1)
    sim.clear()


@pytest.mark.medium
def test_PEA_PRE_absorber():
    """
    A thick Cd slab: thermal neutrons entering it are almost all absorbed.

    PEA_PRE (propagate-exit-absorb) must fire exactly once per track segment:
    propagate_pre before each in-volume interaction - including the absorbing
    one - plus once at exit. An absorbed segment is therefore counted once,
    so per history PEA_PRE == ENTRY + EXIT. When the absorbing segment was
    additionally registered as an absorb trigger, PEA_PRE recorded about
    twice the number of entries.
    """
    class MySim(Prompt):
        def __init__(self, seed) -> None:
            super().__init__(seed)

        def makeWorld(self):
            world = Volume('world', Box(50, 50, 200))

            sample_mat = "Cd.ncmat"
            slab = Volume('sample', Box(2,2,20), sample_mat)

            scorerTest1 = ESpectrumHelper('testObj_ENTRY', 1e-6, 10, 20, 2112, 'ENTRY', False, )
            scorerTest1.make(slab)
            scorerTest2 = ESpectrumHelper('testObj2_EXIT', 1e-6, 10, 20, 2112, 'EXIT', False, )
            scorerTest2.make(slab)
            scorerTest3 = ESpectrumHelper('testObj3_PEA_PRE', 1e-6, 10, 20, 2112, 'PEA_PRE', False, )
            scorerTest3.make(slab)

            world.placeChild('phy_sample', slab)

            self.setWorld(world)

    sim = MySim(seed=4096)
    sim.makeWorld()

    gun = "gun=MaxwellianGun;src_w=1;src_h=1;src_z=-100;slit_w=1;slit_h=1;slit_z=1e99;temperature=293;"
    pnum = 1e4
    sim.simulate(gun, pnum)
    nentry = sim.gatherHistData('testObj_ENTRY').getTotalHit()
    nexit = sim.gatherHistData('testObj2_EXIT').getTotalHit()
    npea = sim.gatherHistData('testObj3_PEA_PRE').getTotalHit()
    print(nentry, nexit, npea)
    # one fire per segment: an absorbed history scores once (the pre-hit of
    # the absorbing interaction), a transmitted history scores once at exit
    np.testing.assert_allclose(npea, nentry + nexit, rtol=0.05)
    # guard against the old double counting: absorption must not score again
    np.testing.assert_allclose(npea, nentry, rtol=0.1)
    assert npea < 1.5 * nentry
    sim.clear()


def test_prompt_ptstate():
    if __name__ == '__main__':
        test_ENTRY_EXIT()
        test_PROPAGATE_PRE_POST()

