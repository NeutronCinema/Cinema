#!/usr/bin/env python3
import openmc
from openmc.data import K_BOLTZMANN, NEUTRON_MASS
import numpy as np
import matplotlib.pyplot as plt

# export PATH="<openmc-build-dir>/bin:$PATH"
# $ export OPENMC_CROSS_SECTIONS=<openmc-build-dir>/data/endfb-viii.0-hdf5/cross_sections.xml


def run(energy, numPart):
    # mat = openmc.Material(1, "uo2")
    # # Add nuclides to uo2
    # mat.add_nuclide('U235', 0.03)
    # mat.add_nuclide('U238', 0.97)
    # mat.add_nuclide('O16', 2.0)
    # mat.set_density('g/cm3', 10.0)

    mat = openmc.Material(1, "h")
    # Add nuclides to uo2
    mat.add_nuclide('H1', 1.0)
    mat.set_density('g/cm3', 1.0)

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
    energy=energy
    source.energy = openmc.stats.Discrete([energy], [1.])
    source.particle = 'neutron'

    # Settings
    settings = openmc.Settings()
    # settings.temperature = 293.6
    settings.source = source
    settings.particles = numPart
    settings.run_mode = 'fixed source'
    settings.batches = 1
    settings.photon_transport = True
    cutoff=0.05
    settings.cutoff = {'energy_photon' : cutoff}
    settings.max_tracks = settings.particles
    settings.export_to_xml( 'settings.xml')


    # Define filters
    surface_filter = openmc.SurfaceFilter(cyl)
    particle_filter = openmc.ParticleFilter('neutron')
    energy_bins = np.logspace(np.log10(1e-6),
                                np.log10(20e6), 300)
    energy_filter = openmc.EnergyFilter(energy_bins)

    # Create tallies and export to XML
    tally = openmc.Tally(name='tally')
    tally.filters = [surface_filter, energy_filter, particle_filter]
    tally.scores = ['current']


    mufilter = openmc.MuFilter(300)
    tally2 = openmc.Tally(name='tally2')
    tally2.filters = [ mufilter, particle_filter]
    tally2.scores = ['events']



    tallies = openmc.Tallies([tally, tally2])
    tallies.export_to_xml('tallies.xml')


def read_results(filename):
    """Read the energy, mean, and standard deviation from the output

    Parameters
    ----------
    code : {'openmc', 'mcnp', 'serpent'}
        Code which produced the output file
    filename : str
        Path to the output file

    Returns
    -------
    energy : numpy.ndarray
        Energy bin values [MeV]
    mean : numpy.ndarray
        Sample mean of the tally
    std_dev : numpy.ndarray
        Sample standard deviation of the tally

    """
    with openmc.StatePoint(filename) as sp:
        t = sp.get_tally(name='tally')
        # print(t.__dict__)
        x = t.find_filter(openmc.EnergyFilter).bins[:,1]
        y = t.mean[:,0,0]
        std_dev = t.std_dev[:,0,0]

    return x, y, std_dev
 
def plot():
    """Extract and plot the results

    """
    # Read results
    path =  f'statepoint.1.h5'
    x1, y1, sd = read_results(path)

    # y1 /= np.diff(x1)*sum(y1)
    print('y sum()', y1.sum())

    # Set up the figure
    plt.figure(1, facecolor='w', figsize=(8,8))
    plt.loglog(x1, y1)
    plt.show()

run(1e6, int(1e4))
openmc.run(tracks=False)

# import os
# os.system(f'openmc' )
plot()