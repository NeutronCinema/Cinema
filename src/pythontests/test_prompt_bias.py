#!/usr/bin/env python3
"""Cross-section bias physics tests (variance-reduction biasing).

The biasing contract: a material configured with abs_bias/scatter_bias != 1
transports particles with the BIASED cross sections (sigma_true x bias), and
the per-step weight correction exp((bias-1)*length*rho*sigma_true) restores
unbiasedness - so any observable must agree with the bias=1 run within
statistics. These tests pin that contract because the planned per-material
total-cross-section cache must keep the cached values TRUE (bias applied at
use time); a cache that bakes the bias in would silently break the weight
correction exactly here.

Each transmission runs in a fresh subprocess: the Launcher is a
process-wide singleton (one world per process).
"""

import math
import os
import subprocess
import sys

import pytest

VENV_PY = sys.executable
INNER_CFG = "freegas::H2O/1gcm3/H_is_H1/O_is_O16;temp=293.6K"

_RUNNER = r'''
import sys
sys.path.insert(0, "/data/caixx/cinema/src/python")
from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Box
from Cinema.Prompt.scorer import ESpectrumHelper
from Cinema.Prompt.physics import Material

inner_cfg, abs_bias, nprim = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])

class SlabSim(Prompt):
    """Pencil thermal beam through a 5 mm water slab, transmission on EXIT."""
    def makeWorld(self):
        water = Material(inner_cfg)
        if abs_bias != 1.0:
            water.setBiasAbsp(abs_bias)
        world = Volume("world", Box(10, 10, 12), matCfg=water)
        slab = Volume("slab", Box(10, 10, 2.5), matCfg=water)
        world.placeChild("slab", slab)
        ESpectrumHelper("esc", min=1e-3, max=1e8, numbin=50,
                        pdg=2112, ptstate="EXIT").make(world)
        self.setWorld(world)

sim = SlabSim()
sim.makeWorld()
gun = "gun=SimpleThermalGun;position=0,0,-100;direction=0,0,1;energy=0.0253"
sim.simulate(gun, nprim)
h = sim.gatherHistData("esc")
print("T %.6f" % (float(h.getTotalWeight()) / nprim))
'''


def _run_transmission(abs_bias, nprim=200000):
    path = os.path.join("/tmp", "bias_runner_%d.py" % os.getpid())
    with open(path, "w") as f:
        f.write(_RUNNER)
    env = dict(os.environ)
    env.setdefault("CINEMAPATH", "/data/caixx/cinema")
    out = subprocess.run([VENV_PY, path, INNER_CFG, str(abs_bias), str(nprim)],
                         capture_output=True, text=True, env=env,
                         timeout=600)
    for line in out.stdout.splitlines():
        if line.startswith("T "):
            return float(line.split()[1])
    raise RuntimeError("runner produced no T:\n"
                       + out.stdout[-1500:] + out.stderr[-1500:])


def test_abs_bias_transport_stays_unbiased():
    """A biased absorption cross section must not shift the observable.

    5 mm water slab, thermal neutrons, 200k particles per arm: the
    abs_bias=3 run transports with sigma_abs x 3 and corrects weights per
    step; its transmission must match the abs_bias=1 run within 3 combined
    sigma (a cache that baked the bias into the stored xs would break the
    weight correction and land many sigma away)."""
    nprim = 200000
    t_ref = _run_transmission(1.0, nprim)
    t_bia = _run_transmission(3.0, nprim)
    sigma = math.sqrt(max(t_ref * (1 - t_ref), 1e-12) / nprim)
    combined = 3.0 * sigma * math.sqrt(2)
    print(f"T(bias=1) = {t_ref:.5f}, T(abs_bias=3) = {t_bia:.5f}, "
          f"3 combined sigma = {combined:.5f}")
    assert abs(t_bia - t_ref) < combined, (
        f"biased transmission {t_bia:.5f} deviates from unbiased "
        f"{t_ref:.5f} by more than 3 combined sigma - the weight "
        "correction no longer matches the transported xs")


def test_scatter_bias_scales_transport_xs():
    """The transport-visible total xs is true x bias (the product semantics).

    The offline xs() reports the bias-scaled total: doubling scatter_bias
    doubles the total. This pins the multiplication order the cache design
    relies on (cache stores true; bias multiplies at use time)."""
    sys.path.insert(0, "/data/caixx/cinema/src/python")
    from Cinema.Prompt.physics import Material
    from Cinema.Prompt.compoundModel import ModelCollection
    c1 = Material(INNER_CFG)
    c2 = Material(INNER_CFG)
    c2.setBiasScat(2.0)
    e = 0.0253
    xs1 = ModelCollection(c1.cfg).xs(e, pdg=2112)
    xs2 = ModelCollection(c2.cfg).xs(e, pdg=2112)
    print(f"xs(bias=1) = {xs1:.6g}, xs(scatter_bias=2) = {xs2:.6g}, "
          f"ratio = {xs2/xs1:.6f}")
    # scatter_bias scales ONLY the scatter channel: sigma_abs stays at its
    # true value, so the total scales sub-linearly. Water at thermal:
    # sigma_abs/sigma_total ~ 0.7 percent -> expected ratio ~ 1.993.
    ratio = xs2 / xs1
    assert 1.0 < ratio < 2.0, "bias must raise the total sub-linearly"
    assert ratio == pytest.approx(2.0, abs=0.02), (
        f"scatter-only bias ratio {ratio} outside the expected "
        "[1.98, 2.0] window: the per-channel product semantics broke")
