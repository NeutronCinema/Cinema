#!/usr/bin/env python3
"""Units, half-sizes and materials, checked against analytic values.

Demonstrates the two conventions that bite every newcomer, by building solids
and comparing ``Volume.getCapacity()`` (which reports mm^3) with the analytic
value:

1. **Lengths are mm** — the internal transport unit for shape dimensions,
   translations, positions and capacities alike.
2. **Box takes HALF-lengths** (and the axial parameter of Tube, Cone, ... is a
   HALF-height): ``Box(10, 10, 10)`` is a 20 x 20 x 20 mm cube of
   8000 mm^3, not a 10 mm cube.

It also shows the two ways a material enters a volume: an NCrystal config
string naming a data file (``'void.ncmat'`` is true vacuum, ``'Cd.ncmat'`` is
cadmium), and what happens with ``matCfg=None`` — a dilute hydrogen gas
default is applied, announced with a RuntimeWarning (it is NOT vacuum).

This script needs no display and does no rendering: no pyvista involved.

Expected runtime: about 3 s, essentially Python/C++ start-up. Output:
printed checks only, no files.
"""

import math
import warnings

from Cinema.Prompt.solid import Box, Tube
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.physics import Material


def main():
    # --- half-lengths, verified through the capacity -----------------------
    cube = Volume("cube", Box(10, 10, 10), matCfg='void.ncmat')
    assert abs(cube.getCapacity() - 20.0**3) < 1e-9  # (2*10) mm sides
    print(f"Box(10, 10, 10)      capacity = {cube.getCapacity():10.3f} mm^3 "
          "(= 20 x 20 x 20: HALF-lengths)")

    # the axial size of a Tube is a HALF-height as well
    tube = Volume("tube", Tube(0, 10, 20), matCfg='void.ncmat')
    expected = math.pi * 10.0**2 * 40.0  # r = 10 mm, full height = 40 mm
    assert abs(tube.getCapacity() - expected) < 1e-6
    print(f"Tube(0, 10, 20)      capacity = {tube.getCapacity():10.3f} mm^3 "
          "(= pi*r^2*40: HALF-height)")

    # --- materials by name -------------------------------------------------
    # a material is an NCrystal config string; a bare file name is wrapped
    # into a full config by the Material helper
    mat = Material('Cd.ncmat')
    print(f"Material('Cd.ncmat').cfg -> {mat.cfg}")

    # 'void.ncmat' is true vacuum (zero-density NCrystal data)
    vacuum = Volume("vacuum", Box(5, 5, 5), matCfg='void.ncmat')
    print(f"'void.ncmat' volume, matCfg reported as: {vacuum.matCfg}")

    # --- the matCfg=None trap ----------------------------------------------
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        lazy = Volume("lazy", Box(5, 5, 5))  # no matCfg!
    # the applied default is a dilute hydrogen GAS, not vacuum
    assert "freegas::H1" in lazy.matCfg
    for w in caught:
        print(f"{w.category.__name__}: {w.message}")
    print("matCfg=None applied:", lazy.matCfg)

    print("all unit/material checks passed")


if __name__ == "__main__":
    main()
