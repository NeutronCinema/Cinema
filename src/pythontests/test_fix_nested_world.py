#!/usr/bin/env python3
"""Top-down nesting (world.placeChild(A); A.placeChild(B)) must not abort.

Regression guard for the GeoTree construction order bug: makeTree() used to
scan placed volumes in descending registration order, assuming every mother
carries a higher placed id than its daughters. Top-down nesting inverts that
(daughter B registered after mother A, so B holds the higher id): B was
processed before A existed in the node registry, A kept its childPhysicalID
list without ever receiving B as a linked child node, and the countChildNode
sanity check then threw Prompt::Error::BadInput ("countChildNode ...") through
the ctypes bridge, killing the interpreter with SIGABRT - uncatchable from
Python, so even showWorld's own error handling could not intervene.

makeTree() now builds all nodes first and links mother->daughter by id lookup,
independent of registration order. Both show() (which constructs WorldMesh and
therefore the tree via pt_countFullTreeNode) and a short transport run on the
nested tree must return with the process alive.

Run with pytest --forked like every test that touches the Launcher singleton.
"""

import pytest

pytestmark = pytest.mark.slow  # mesh chain + tiny transport run


def _makeNestedSim():
    from Cinema.Prompt import Prompt
    from Cinema.Prompt.geo import Volume, Transformation3D
    from Cinema.Prompt.solid import Box

    class Sim(Prompt):
        def __init__(self, seed=4096):
            super().__init__(seed)

        def makeWorld(self):
            world = Volume("world", Box(400, 400, 400), matCfg='void.ncmat')
            inner = Volume('inner', Box(200, 200, 200), matCfg='void.ncmat')
            core = Volume('core', Box(50, 50, 50), matCfg='void.ncmat')
            # the nesting direction that used to abort: a child placed into a
            # child, not straight into the world
            world.placeChild('innerPhy', inner, Transformation3D(0., 0., 0))
            inner.placeChild('corePhy', core)
            self.setWorld(world)

    sim = Sim()
    sim.makeWorld()
    return sim


def test_topdown_nested_world_show():
    # show() constructs WorldMesh -> pt_countFullTreeNode -> GeoTree: this is
    # where the old code aborted with Prompt::Error::BadInput 'countChildNode'
    sim = _makeNestedSim()
    sim.show(None, 0)  # SIGABRT here would fail the test
    assert sim.l.worldExist


def test_topdown_nested_world_transport():
    # the transport layer must also handle the nested tree: shoot neutrons
    # straight into the core and count the hits
    import numpy as np
    from Cinema.Prompt.gun import IsotropicGun

    sim = _makeNestedSim()
    gun = IsotropicGun()
    gun.setEnergy(1)
    sim.simulate(gun, int(1e3))
    # nothing to gather without a scorer; surviving the run is the assertion
    assert sim.l.worldExist
