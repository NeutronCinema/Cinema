#!/usr/bin/env python3

from Cinema.Prompt import PromptMPI
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.solid import Box, Tube, Sphere
from Cinema.Prompt.scorer import ESpectrumHelper, MultiScatCounter
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import SimpleThermalGun,UniModeratorGun
from Cinema.Prompt.GidiSetting import GidiSetting 
import numpy as np

cdata=GidiSetting()
cdata.setEnableGidi(False)
cdata.setGammaTransport(False)



def test_scatter():
    """
    Use a sample with disabled absorption to test scatter number -2, 0, 1, etc.
    -2 must equal incoming particle numbers
    0+1+others must equal incoming particle numbers
    """
    g_scatNum = 1

    class MySim(PromptMPI):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):
            length = 200
            world = Volume('world', Box(100, 100, length * 2 + 100))

            sample_mat = "physics=ncrystal;nccfg='Al_sg225.ncmat';abs_bias=0."

            sample = Volume('sample', Box(10,10,10,), sample_mat)
            scatterCounter = MultiScatCounter()
            scatterCounter.make(sample)

            detector = Volume('det', Sphere(80,80+1e-3,0.,360.,0,179.9))
            for isca in np.arange(-2,8):
                scorer = ESpectrumHelper(f'ekin{isca}')
                scorer.make(detector)
                scorer.addScatterCounter(scatterCounter, isca)
            
            world.placeChild('physicalSample', sample, Transformation3D(z=0))
            world.placeChild('phydet', detector,)
            self.setWorld(world)

    sim = MySim(seed=1010)
    sim.makeWorld()

    windowsize=0.001
    gun = UniModeratorGun()
    gun.setSource([windowsize,windowsize,-150])
    gun.setSlit([windowsize,windowsize,0])

    partnum_ = 1e5
    if 0:
        partnum = 100
        sim.show(gun, partnum)
    else:
        partnum = int(partnum_)
        sim.simulate(gun, partnum)

    ms_sample = sim.gatherHistData("ScatterCounter")
    msw = ms_sample.getWeight()
    print(msw)

    countnumlist = []
    for isca in np.arange(-2,8):
        print(f"====scatter {isca}====")
        dtt0 = sim.gatherHistData(f"ekin{isca}")
        score = dtt0.getWeight()
        print(score)
        print(dtt0.getAccWeight())
        countnumlist.append(dtt0.getAccWeight())
    print("====Result====")
    print("Sum of various counts required: ", np.array(countnumlist[2:]).sum())
    print("Incoming particle numbers: ", partnum_)
    np.testing.assert_allclose(np.array(countnumlist[2:]).sum(), partnum_)
    np.testing.assert_allclose(countnumlist[0], partnum_)
    sim.clear()

def test_gun_missing_sample():
    """
    Use a sample with disabled absorption to test scatter number -2, 0, 1, etc.
    -2 must equal incoming particle numbers
    -1 must equal incoming particle numbers
    """
    g_scatNum = 1

    class MySim(PromptMPI):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):
            length = 200
            world = Volume('world', Box(100, 100, length * 2 + 100))

            sample_mat = "physics=ncrystal;nccfg='Al_sg225.ncmat';abs_bias=0."

            sample = Volume('sample', Box(10,10,1,), sample_mat)
            scatterCounter = MultiScatCounter()
            scatterCounter.make(sample)

            detector = Volume('det', Sphere(80,80+1e-3,0.,360.,0,175))
            isca = -1
            scorer = ESpectrumHelper(f'ekin{isca}')
            scorer.make(detector)
            scorer.addScatterCounter(scatterCounter, isca)
            
            world.placeChild('physicalSample', sample, Transformation3D(x=20))
            world.placeChild('phydet', detector,)
            self.setWorld(world)

    sim = MySim(seed=1010)
    sim.makeWorld()

    windowsize=10
    gun = UniModeratorGun()
    gun.setSource([windowsize,windowsize,-150])
    gun.setSlit([windowsize,windowsize,0])

    partnum_ = 1e4
    if 0:
        partnum = 100
        sim.show(gun, partnum)
    else:
        partnum = int(partnum_)
        sim.simulate(gun, partnum)

    ms_sample = sim.gatherHistData("ScatterCounter")
    msw = ms_sample.getWeight()
    print(msw)

    isca=-1
    print(f"====scatter {isca}====")
    dtt0 = sim.gatherHistData(f"ekin{isca}")
    score = dtt0.getWeight()
    print(score)
    counts = dtt0.getAccWeight()
    np.testing.assert_allclose(counts, partnum_)
    sim.clear()

def test_gun_patial_missing_sample():
    g_scatNum = 1

    class MySim(PromptMPI):
        def __init__(self, seed=4096) -> None:
            super().__init__(seed)   

        def makeWorld(self):
            length = 200
            world = Volume('world', Box(100, 100, length * 2 + 100))

            sample_mat = "physics=ncrystal;nccfg='Al_sg225.ncmat';abs_bias=0."

            sample = Volume('sample', Box(10,10,1,), sample_mat)
            scatterCounter = MultiScatCounter()
            scatterCounter.make(sample)

            detector = Volume('det', Sphere(80,80+1e-3,0.,360.,0,179))
            for isca in np.arange(-2,8):
                scorer = ESpectrumHelper(f'ekin{isca}')
                scorer.make(detector)
                scorer.addScatterCounter(scatterCounter, isca)
            
            world.placeChild('physicalSample', sample, Transformation3D(x=9.8)) # some particles are missing target(sample)
            world.placeChild('phydet', detector,)
            self.setWorld(world)

    sim = MySim(seed=1010)
    sim.makeWorld()

    windowsize=1
    gun = UniModeratorGun()
    gun.setSource([windowsize,windowsize,-150])
    gun.setSlit([windowsize,windowsize,0])

    partnum_ = 1e5
    if 0:
        partnum = 100
        sim.show(gun, partnum)
    else:
        partnum = int(partnum_)
        sim.simulate(gun, partnum)

    ms_sample = sim.gatherHistData("ScatterCounter")
    msw = ms_sample.getWeight()
    print(msw)

    countnumlist = []
    for isca in np.arange(-2,8):
        print(f"====scatter {isca}====")
        dtt0 = sim.gatherHistData(f"ekin{isca}")
        score = dtt0.getWeight()
        print(score)
        print(dtt0.getAccWeight())
        countnumlist.append(dtt0.getAccWeight())
    print("====Result====")
    print("Sum of various counts required: ", np.array(countnumlist[2:]).sum())
    print("Bypass particles: ", countnumlist[1])
    print("Incoming particle numbers: ", partnum_)
    np.testing.assert_allclose(np.array(countnumlist[1:]).sum(), partnum_)
    np.testing.assert_allclose(countnumlist[0], partnum_)
    sim.clear()

if __name__ == '__main__':
    test_scatter()
    test_gun_missing_sample()
    test_gun_patial_missing_sample()
