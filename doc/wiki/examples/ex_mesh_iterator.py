#!/usr/bin/env python3
"""Programmatic meshing: walk the closed world with the Mesh iterator.

Demonstrates how to get the same meshes the viewer shows, in a plain script
with no window and no plotting: iterate ``Cinema.Prompt.Mesh.Mesh`` after the
world is closed, and read out one pyvista PolyData per geometry-tree node.

Useful for sanity checks (sizes, positions), custom figures and off-screen
export pipelines. Prints the physical-volume name (the name given to
``placeChild``), the material config and the mesh point count per node.

The world contains one boolean-solid volume (a box with a slot cut out).
Boolean solids cannot be tessellated by VecGeom directly; the iterator meshes
the two children and combines them with vtkbool, printing its "highly
experimental" warning and falling back to a point-cloud reconstruction when
that fails — so expect a warning line and an approximate surface for that
one node.

Expected runtime: about 4 s. Output: printed table only, no files.
"""

from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Transformation3D, Volume
from Cinema.Prompt.solid import Box, SolidSubtraction


class Sim(Prompt):
    def __init__(self, seed=4096):
        super().__init__(seed)

    def makeWorld(self):
        world = Volume("world", Box(300, 300, 300), matCfg='void.ncmat')

        # a boolean solid: a 60 mm cube with a 20 mm wide slot cut through it
        # (all half-lengths, mm)
        slot = SolidSubtraction(Box(30, 30, 30), Box(25, 10, 5),
                                Transformation3D(0, 0, 0))
        boolvol = Volume("slabWithSlot", slot, matCfg='Cd.ncmat')

        sample = Volume("sample", Box(20, 20, 20), matCfg='Al_sg225.ncmat')

        world.placeChild("boolPhy", boolvol, Transformation3D(0, 0, -80))
        world.placeChild("samplePhy", sample, Transformation3D(0, 0, 80))
        self.setWorld(world)


if __name__ == "__main__":
    sim = Sim()
    sim.makeWorld()

    # the iterator walks the C++ geometry manager, so the world must be
    # closed already (it is, after makeWorld above)
    from Cinema.Prompt.Mesh import Mesh

    print(f"{'physical volume':<18} {'points':>7}  material")
    for node in Mesh():
        name, mesh = node.getMesh(30)  # 30 = tessellation fineness
        print(f"{name:<18} {mesh.n_points:>7}  {node.getMaterialName()}")
