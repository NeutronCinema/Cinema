#!/usr/bin/env python3


import openmc
from openmc.data import K_BOLTZMANN, NEUTRON_MASS
import numpy as np
import matplotlib.pyplot as plt

# export PATH="/home/caixx/git/openmc/build/bin:$PATH"
# (cinemavirenv) caixx@x:~/git/cinema/rundir/del$ export OPENMC_CROSS_SECTIONS=~/git/openmc/build/data/endfb-viii.0-hdf5/cross_sections.xml


def run(cfg, energy, numbin_en, loweredge, upperedge, numPart, isGammaTransport):
    mat = openmc.Material.from_ncrystal(cfg)

    numbin_mu=10

    print(mat)
    materials = openmc.Materials()
    materials.append(mat)
    materials.export_to_xml()


    # Instantiate surfaces
    cyl = openmc.XCylinder(boundary_type='vacuum', r=1.e-6)
    px1 = openmc.XPlane(boundary_type='vacuum', x0=-1.)
    px2 = openmc.XPlane(boundary_type='transmission', x0=1.)
    px3 = openmc.XPlane(boundary_type='vacuum', x0=1.e9)

    # Instantiate cells
    inner_cyl_left = openmc.Cell()
    inner_cyl_right = openmc.Cell()
    outer_cyl = openmc.Cell()

    # Set cells regions and materials
    inner_cyl_left.region = -cyl & +px1 & -px2
    inner_cyl_right.region = -cyl & +px2 & -px3
    outer_cyl.region = ~(-cyl & +px1 & -px3)
    inner_cyl_right.fill = mat

    # Create root universe and export to XML
    geometry = openmc.Geometry([inner_cyl_left, inner_cyl_right, outer_cyl])
    geometry.export_to_xml('geometry.xml')

    # Define source
    source = openmc.IndependentSource()
    source.space = openmc.stats.Point((0,0,0))
    source.angle = openmc.stats.Monodirectional()
    
    if isinstance(energy, list):
        source.energy = openmc.stats.Uniform(energy[0], energy[1])
    else:
        source.energy = openmc.stats.Discrete([energy], [1.])
    
    source.particle = 'neutron'

    # Settings
    settings = openmc.Settings()
    # settings.temperature = 293.6
    settings.source = source
    settings.particles = numPart
    settings.run_mode = 'fixed source'
    settings.batches = 1
    settings.photon_transport = isGammaTransport
    cutoff=0.05
    settings.cutoff = {'energy_photon' : cutoff}
    settings.export_to_xml( 'settings.xml')
    settings.max_tracks = settings.particles
    


    # Define filters
    surface_filter = openmc.SurfaceFilter(cyl)
    particle_filter = openmc.ParticleFilter('neutron')
    energy_bins = np.logspace(np.log10(loweredge),
                                np.log10(upperedge), numbin_en+1)
    energy_filter = openmc.EnergyFilter(energy_bins)

    # Create tallies and export to XML
    tally = openmc.Tally(name='tally')
    tally.filters = [surface_filter, energy_filter, particle_filter]
    tally.scores = ['current']


    mufilter = openmc.MuFilter(numbin_mu)
    tally2 = openmc.Tally(name='tally2')
    tally2.filters = [ surface_filter, mufilter, particle_filter]
    tally2.scores = ['current']

    cellfilter = openmc.CellFilter(inner_cyl_right)
    tally3 = openmc.Tally(name='tally3')
    tally3.filters = [ energy_filter, cellfilter, particle_filter ]
    tally3.scores = ['flux']

    tallies = openmc.Tallies([tally, tally2, tally3])
    tallies.export_to_xml('tallies.xml')

    openmc.run(tracks=False)



def read_results(filename, tally, filter):
    with openmc.StatePoint(filename) as sp:        
        t = sp.get_tally(name=tally)
        x = 0.5*(t.find_filter(filter).bins[:,1]+t.find_filter(filter).bins[:,0])

        # t = sp.get_tally(name='tally')
        # x = 0.5*(t.find_filter(openmc.EnergyFilter).bins[:,1]+t.find_filter(openmc.EnergyFilter).bins[:,0])

        y = t.mean[:,0,0] 
        std_dev = t.std_dev[:,0,0]

    return x, y, std_dev


# def plot():
#     """Extract and plot the results

#     """
#     # Read results
#     path =  f'statepoint.1.h5'
#     x1, y1, sd = read_results(path)

#     # y1 /= np.diff(x1)*sum(y1)
#     print('y sum()', y1.sum())

#     # Set up the figure
#     # plt.figure(1, facecolor='w', figsize=(8,8))
#     plt.plot(x1, y1*partnum,'-o', label=f'openmc {y1.sum()*partnum}')
#     plt.legend(loc=0)
#     plt.show()

def openmcRun(cfg, energy, numbin_en=100, loweredge=1e-5, upperedge=30e6, partnum = 1e5, isGammaTransport=False):


    run(cfg, energy, numbin_en, loweredge, upperedge, int(partnum), isGammaTransport)


    #################################################################################################################################
    # import os
    # os.system(f'openmc' )
    # plot()

    sp = 'statepoint.1.h5' 
    # mu
    # sim.gatherHistData('SofAngle').plot(show=False, log=False)

    # x, y, std = read_results(sp, 2, openmc.MuFilter) 
    # plt.plot(x, y*partnum,'-o', label=f'openmc {y.sum()*partnum}')
    # plt.legend(loc=0)


    ##########################################################
    # energy
    x, y, std = read_results(sp, 'tally', openmc.EnergyFilter)
    plt.plot(x, y*partnum,'-o', label=f'openmc {y.sum()*partnum}')
    plt.legend(loc=0)