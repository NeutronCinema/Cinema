#!/usr/bin/env python3
# Unit-convention regression test for MCPL output: MCPLOutHelper (C++
# KillerMCPL) must store particle records in MCPL-standard units
# (cm / MeV / ms) so external tools and MCPLGun read back the same
# numbers Cinema holds internally (mm / eV / s). A pre-fix writer stored
# the internal units unconverted (energies x1e6, positions x10, times
# x1e-3 off when read by any standard-unit reader).
#
# The scorer only closes (and gzips) its file when it is destroyed,
# which happens at interpreter exit - so the simulation runs in a
# subprocess and this process reads the finished file.

import subprocess
import sys
import textwrap

import numpy as np
import pytest

mcpl = pytest.importorskip("mcpl")

# geometry the assertions below are derived from: the gun sits at the
# origin firing along +z, and the detector box (half length 5 mm) is
# centred at z = 100 mm, so its ENTRY plane is at z = 95 mm
GUN_ENERGY_EV = 1e-3
ENTRY_PLANE_MM = 95.0

# speed of a neutron from the same constants the C++ core uses
# (PTUnitSystem.hh): v = c * sqrt(2E/mc2), here in m/s
_NEUTRON_MASS_EV = 1.00866491588 * 931494095.17
_SPEED_M_PER_S = 299792458.0 * np.sqrt(2.0 * GUN_ENERGY_EV / _NEUTRON_MASS_EV)


def _run_tiny_sim(outdir):
    script = textwrap.dedent('''
        import sys
        from Cinema.Prompt import Prompt
        from Cinema.Prompt.geo import Transformation3D, Volume
        from Cinema.Prompt.scorer import MCPLOutHelper
        from Cinema.Prompt.solid import Box
        from Cinema.Prompt.gun import SimpleThermalGun

        outdir = sys.argv[1]

        class MySim(Prompt):
            def makeWorld(self):
                world = Volume('world', Box(50, 50, 200), 'void.ncmat')
                det = Volume('detector', Box(10, 10, 5))
                out = MCPLOutHelper(outdir + '/out', kill=True)
                out.make(det)
                world.placeChild('detectorPhy', det, Transformation3D(z=100))
                self.setWorld(world)

        sim = MySim(seed=1010)
        sim.makeWorld()
        gun = SimpleThermalGun()
        gun.setEnergy({energy})
        gun.setPosition([0, 0, 0])
        sim.simulate(gun, 3)
        # no sim.clear(): it releases the raw scorer pointers without
        # deleting them, which would leave the MCPL file unclosed
    ''').format(energy=GUN_ENERGY_EV)
    proc = subprocess.run([sys.executable, '-c', script, str(outdir)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, \
        f'stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}'


@pytest.mark.slow  # subprocess interpreter start + tiny simulation, ~3 s body
def test_mcplout_helper_file_in_standard_units(tmp_path):
    _run_tiny_sim(tmp_path)

    files = list(tmp_path.glob('*.mcpl.gz'))
    assert len(files) == 1
    f = mcpl.MCPLFile(str(files[0]))
    particles = list(f.particles)
    assert len(particles) == 3

    # analytic time of flight over the 95 mm gap, converted s -> ms as
    # the writer must do
    tof_ms = (ENTRY_PLANE_MM / (_SPEED_M_PER_S * 1e3)) * 1e3

    for p in particles:
        # file holds MeV: 1e-3 eV must read back as 1e-9 MeV
        assert p.ekin == pytest.approx(GUN_ENERGY_EV * 1e-6, rel=1e-6)
        # file holds cm: the 95 mm entry plane must read back as 9.5 cm
        assert p.position[2] == pytest.approx(ENTRY_PLANE_MM * 0.1, rel=1e-6)
        assert p.position[0] == pytest.approx(0.0, abs=1e-6)
        assert p.position[1] == pytest.approx(0.0, abs=1e-6)
        # file holds ms: analytic TOF, so this only passes when the
        # stored milliseconds equal the real seconds x1e3
        assert p.time == pytest.approx(tof_ms, rel=1e-6)
        # direction and weight pass through without conversion
        assert tuple(p.direction) == (0., 0., 1.)
        assert p.weight == pytest.approx(1.0)
        assert p.pdgcode == 2112

    # the polarisation triple carries [surviveP, scatter number, dE in MeV];
    # particles killed on first entry have no scatter counter (-3) and no loss
    assert f.opt_polarisation
    for p in particles:
        assert p.polarisation[0] == pytest.approx(1.0, abs=1e-6)
        assert p.polarisation[1] == pytest.approx(-3.0, abs=1e-6)
        assert p.polarisation[2] == pytest.approx(0.0, abs=1e-12)
