#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box, Sphere
from Cinema.Prompt.scorer import VolFluenceHelper, ESpectrumHelper
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting 
import matplotlib.pyplot as plt
from Cinema.Interface import plotStyle

plotStyle()
import os
# openmc reads its cross-section XML (e.g. endfb-viii.0-hdf5/cross_sections.xml)
# from OPENMC_CROSS_SECTIONS; take it from the environment, no default here.
os.environ['OPENMC_CROSS_SECTIONS'] = os.environ.get('OPENMC_CROSS_SECTIONS', '')

cdata=GidiSetting()
cdata.setGidiThreshold(-5)
cdata.setEnableGidi(True)

partnum = int(1e6)
energy = 1e4

loweredge=1e-5
upperedge=30e6

numbin_en=300
# cfg='freegas::H2O/1gcm3/H_is_1_H1/O_is_1_O16'
# cfg='freegas::H/1gcm3/H_is_1_H1'
cfg='freegas::O/1gcm3/O_is_O16'
# cfg='freegas::U/1gcm3/U_is_U235'
# cfg='freegas::U/1gcm3/U_is_U238'
# cfg='freegas::C/1gcm3/C_is_1_C13;temp=293.6'
# cfg='freegas::Ag/1gcm3'
# cfg='freegas::H/.1gcm3/H_is_H1'

class MySim(PromptMPI):
    def __init__(self, seed=4096) -> None:
        super().__init__(seed)   

    def makeWorld(self):

        # world = Volume("world", Box(400, 400, 400))
        lw = Material(cfg) 
        world = Volume("sphere", Sphere(0, 300), matCfg=lw)

        # sphere = Volume("sphere", Sphere(0, 300), matCfg=lw)
        # world.placeChild('sphere', sphere)

        VolFluenceHelper('spct', min=loweredge, max=upperedge, numbin=numbin_en, ptstate='PEA').make(world)
        # ESpectrumHelper('escap', min=1e-5, max=20e6, ptstate='EXIT').make(sphere)

        self.setWorld(world)

sim = MySim(seed=1010)
sim.makeWorld()

gun = IsotropicGun()
gun.setEnergy(energy)

# vis or production
sim.simulate(gun, partnum)


destination = 0
spct = sim.gatherHistData('spct', dst=destination)
# escap= sim.gatherHistData('escap', dst=destination)
if sim.rank==destination:
    # escap.plot(log=True)
    # plt.legend(loc=0)
    # plt.show()
    spct.plot(show=False, log=True)

################################################################################
import matplotlib.pyplot as plt
import numpy as np
import openmc
import openmc.model


def build_model(numPart):
    water = openmc.Material.from_ncrystal(cfg)

    # water = openmc.Material(name='water')
    # water.set_density('g/cm3', 1.)
    # water.add_nuclide('H1', 2.)
    # water.add_nuclide('O16', 1.)

    materials = openmc.Materials([water])
    materials.export_to_xml()

#################################
    moderator_radius = openmc.Sphere(x0=0., y0=0., r=30, boundary_type='vacuum')

    moderator_cell = openmc.Cell()
    moderator_cell.fill = water
    moderator_cell.region = -moderator_radius

##########################################
    # Create root universe and export to XML
    universe = openmc.Universe()
    universe.add_cell(moderator_cell)
    geometry = openmc.Geometry(universe)
    geometry.export_to_xml('geometry.xml')

    # Define source
    source = openmc.IndependentSource()
    source.space = openmc.stats.Point((0,0,0))
    source.angle = openmc.stats.Monodirectional()
    source.energy = openmc.stats.Discrete([energy], [1.])
    source.particle = 'neutron'

    # Settings
    settings = openmc.Settings()
    # settings.temperature = 293.6
    settings.source = source
    settings.particles = numPart
    settings.run_mode = 'fixed source'
    settings.batches = 1
    settings.photon_transport = False
    cutoff=0.05
    settings.cutoff = {'energy_photon' : cutoff}
    settings.export_to_xml( 'settings.xml')

    # Define filters
    particle_filter = openmc.ParticleFilter('neutron')
    energy_bins = np.logspace(np.log10(loweredge),
                                np.log10(upperedge), numbin_en+1)
    energy_filter = openmc.EnergyFilter(energy_bins)

    # Create tallies and export to XML
    tally = openmc.Tally(name='tally')
    tally.filters = [energy_filter, particle_filter]
    tally.scores = ['flux']

    tallies = openmc.Tallies([tally])
    tallies.export_to_xml('tallies.xml')



def read_results(filename, tally, filter):
    with openmc.StatePoint(filename) as sp:        
        t = sp.get_tally(name=tally)
        x = 0.5*(t.find_filter(filter).bins[:,1]+t.find_filter(filter).bins[:,0])

        # t = sp.get_tally(name='tally')
        # x = 0.5*(t.find_filter(openmc.EnergyFilter).bins[:,1]+t.find_filter(openmc.EnergyFilter).bins[:,0])

        y = t.mean[:,0,0]
        std_dev = t.std_dev[:,0,0]

    return x, y, std_dev


build_model(partnum)
openmc.run()

vol=4./3*np.pi*30**3 /partnum*100

sp = 'statepoint.1.h5' 
# mu
x, y, std = read_results(sp, 'tally', openmc.EnergyFilter) 
plt.loglog(x, y/vol,'-o', label=f'openmc {y.sum()/vol}')
plt.legend(loc=0)
plt.show()
