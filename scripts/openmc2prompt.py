#!/usr/bin/env python3
"""openmc2prompt: convert an OpenMC benchmark case into a Cinema/Prompt driver.

Reads the classic OpenMC XML inputs (materials.xml, geometry.xml, settings.xml)
from an OpenMC case directory and emits, into <casedir>/prompt:

  <prefix>.py                    standalone Cinema/PromptMPI keff driver
  mat<N>_<name>_main.ncmat       per-sab-material NCMAT, TSL nuclides REMOVED
                                 (fractions renormalised, density reduced by
                                 the removed mass - absolute densities of the
                                 remaining nuclides are preserved exactly)
  mat<N>_<name>.ncmat            plain free-gas NCMAT for non-sab materials
  run.sh                         runner (cd to the conversion root; cinema env)

Thermal-scattering route (round 2): materials carrying <sab .../> are emitted
as OpenMC-style COMPOSITE configs (Material.fuse): the main NCMAT above plus a
shared H-phase NCMAT derived from the mapped water file (carrier atoms sterile,
H kernel kept) through which NCrystal's native S(alpha,beta) sampler runs.
Component weights are absorption-ratio bookkeeping
(w = absH_material / absH_Hphase), so no big kernel data is ever duplicated.

Mapping: pass --tsl-map <sab_name>=<water.ncmat> (repeatable).  A material
whose sab name has no mapping is a hard error listing the missing names.
The H-phase file is derived automatically next to the mapped water file on
first use and shared by all cases (never per-case copies).  Wire paths are
relative to the conversion root (= cwd at conversion time); run.sh cds there.

Supported geometry (round 1): concentric spheres centred on the origin - the
solution-benchmark family (HEU-SOL-*/LEU-SOL-*/PU-SOL-*).  Cells must be
simple +-surface intersections; nesting is derived from the sphere radii.
Lattices, non-concentric and non-sphere arrangements are rejected with a
clear message for now.

Example (from the benchmarks repo root):
  python3 /data/caixx/cinema/scripts/openmc2prompt.py \
      icsbep/heu-sol-therm-032/openmc/case-1 \
      --tsl-map c_H_in_H2O=indc-usa-107/prompt/data/water_cab_T293.6K.ncmat
  bash icsbep/heu-sol-therm-032/openmc/prompt/run.sh
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

AVOGADRO = 0.602214  # 1e24 atoms per mol (at/cm3 per g/cm3 per g/mol)
M_H = 1.008          # H molar mass, g/mol


def die(msg):
    sys.exit("openmc2prompt: " + msg)


_ELEMENT_MASSES = {
    "H": 1.008, "D": 2.014, "C": 12.011, "N": 14.007, "O": 15.999,
    "Al": 26.982, "Si": 28.085, "Mn": 54.938, "Fe": 55.845, "Cu": 63.546,
    "V": 50.942, "Zr": 91.224, "Pb": 207.2, "U": 238.029,
}


def _mass_number(nuclide):
    """Approximate molar mass from the mass number (H1->1.008 kept special);
    good to <0.15%, only used to convert OpenMC 'sum' atom densities."""
    base = nuclide.split("_")[0]
    for k in ("H1", "H2", "H3"):
        if base == k:
            return float(k[1:]) + 0.008
    digits = "".join(ch for ch in base if ch.isdigit())
    if digits:
        return float(digits)
    if base in _ELEMENT_MASSES:
        return _ELEMENT_MASSES[base]
    die(f"cannot infer molar mass for nuclide/element {nuclide!r}")


def _frac_value(frac_str):
    num, _, den = frac_str.partition("/")
    return float(num) / float(den) if den else float(num)


def parse_materials(path):
    tree = ET.parse(path)
    out = []
    for m in tree.getroot().findall("material"):
        mid = int(m.get("id"))
        name = (m.get("name") or f"mat{mid}").replace(" ", "_")
        dens = m.find("density")
        if dens is None:
            die(f"material {mid} has no <density>")
        units = dens.get("units")
        if units == "sum":
            # atom-sum density: the ao values ARE the nuclide atom densities
            # in 1e24/at/cm3 (absolute). This is what all ICSBEP cases use.
            rho = None
        else:
            rho = float(dens.get("value"))
            if units != "g/cm3" and units != "g/cc":
                die(f"material {mid}: unsupported density unit {units}")
        nucs, sab = [], None
        for n in m.findall("nuclide"):
            nucs.append((n.get("name"), float(n.get("ao") if n.get("ao") else n.get("wo"))))
            if n.get("wo") and not n.get("ao"):
                die(f"material {mid}: weight-percent nuclides unsupported yet")
        s = m.find("sab")
        if s is not None:
            sab = s.get("name")
        out.append(dict(id=mid, name=name, rho=rho, nucs=nucs, sab=sab))
    return out


def parse_geometry(path):
    tree = ET.parse(path)
    root = tree.getroot()
    surfaces = {}
    for s in root.findall("surface"):
        sid = int(s.get("id"))
        stype = s.get("type")
        coeffs = [float(x) for x in s.get("coeffs").split()]
        boundary = s.get("boundary", "")
        surfaces[sid] = dict(type=stype, coeffs=coeffs, boundary=boundary)
    cells = []
    for c in root.findall("cell"):
        fill = c.get("material")
        uni = c.get("universe")
        cells.append(dict(id=int(c.get("id")), material=int(fill) if fill else None,
                          region=c.get("region", ""), universe=uni))
    return surfaces, cells


def nested_onion(surfaces, cells):
    """Validate the concentric-sphere pattern and return cells sorted
    outside-in."""
    radius_of_cell = {}
    for c in cells:
        terms = c["region"].split()
        if not terms:
            die("cell %d: empty region" % c["id"])
        for t in terms:
            if t[0] in "+-":
                sense, sids = t[0], t[1:]
            else:
                sense, sids = "+", t
            sid = int(sids)
            s = surfaces.get(sid)
            if s is None:
                die("cell %d references unknown surface %d" % (c["id"], sid))
            if s["type"] != "sphere" or tuple(s["coeffs"][:3]) != (0.0, 0.0, 0.0):
                die("unsupported surface %d (type %s): round-1 converter only "
                    "handles origin-centred spheres" % (sid, s["type"]))
        def term_sid(t):
            return int(t[1:]) if t[0] in "+-" else int(t)
        rout = max(surfaces[term_sid(t)]["coeffs"][3] for t in terms)
        radius_of_cell[c["id"]] = rout
    order = sorted(cells, key=lambda c: -radius_of_cell[c["id"]])
    for a, b in zip(order, order[1:]):
        if radius_of_cell[a["id"]] <= radius_of_cell[b["id"]]:
            die("cells %d and %d are not strictly nested; round-1 converter "
                "only handles onion geometries" % (a["id"], b["id"]))
    for c in order:
        outer = surfaces[int(c["region"].split()[-1][1:])]
        c["boundary"] = outer.get("boundary", "")
    return order


def split_ncmat_blocks(text):
    """Split NCMAT text into (header_lines, blocks); a block starts at a line
    whose first character is '@'."""
    header, blocks, cur = [], [], None
    for ln in text.splitlines() + ["@END"]:
        stripped = ln.strip()
        if stripped.startswith("@"):
            if cur is not None:
                blocks.append(cur)
            if stripped == "@END":
                cur = None
                break
            cur = [ln]
        elif cur is None:
            header.append(ln)
        else:
            cur.append(ln)
    return header, blocks


def hphase_from_water(water_path):
    """Derive the shared H-phase NCMAT from a mapped water NCMAT: carrier
    atoms (everything except H) become sterile, so the phase contributes only
    the H kernel (with its own absorption).  The file keeps the water file's
    own density - the composite weight absorbs it.  Returns (path, absH)."""
    text = open(water_path).read()
    header, blocks = split_ncmat_blocks(text)
    rho, h_frac, msum_nonh = None, None, 0.0
    out_blocks = []
    for b in blocks:
        kind = b[0].strip()
        if kind == "@DENSITY":
            for ln in b:
                t = ln.split("#")[0].strip()
                if t.endswith("g_per_cm3"):
                    rho = float(t.split()[0])
            out_blocks.append(b)
        elif kind == "@DYNINFO":
            el, frac = None, "1"  # missing fraction: relative weight 1
            for ln in b:
                t = ln.strip()
                if t.startswith("element "):
                    el = t.split()[1]
                elif t.startswith("fraction"):
                    frac = "%.17g" % _frac_value(t.split()[1])
            is_h = el is not None and el.split("_")[0] in ("H", "H1", "H2")
            if is_h:
                h_frac = _frac_value(frac)
            else:
                msum_nonh += _frac_value(frac) * _mass_number(el)
            nb = []
            for ln in b:
                t = ln.strip()
                if t.startswith("element "):
                    nb.append("  element " + el)
                elif t.startswith("fraction"):
                    nb.append("  fraction " + frac)
                elif t.startswith("type"):
                    nb.append("  type sterile" if not is_h else ln)
                else:
                    nb.append(ln)
            out_blocks.append(nb)
        else:
            out_blocks.append(b)
    if rho is None or h_frac is None:
        die(f"{water_path}: cannot derive an H-phase (need @DENSITY and an H "
            "dyninfo with a fraction)")
    # absolute H atom density of the phase population (1e24/at/cm3):
    m_avg_all = h_frac * M_H + msum_nonh
    n_tot = rho / m_avg_all * AVOGADRO
    abs_h = h_frac * n_tot
    out = []
    for ln in header:
        out.append(ln)
    for b in out_blocks:
        out.extend(b)
        out.append("")
    hp = os.path.splitext(water_path)[0] + "_Hphase.ncmat"
    with open(hp, "w") as f:
        f.write("\n".join(out) + "\n")
    return hp, abs_h


def absH_of_hphase(hphase_path):
    """Absolute H atom density (1e24/at/cm3) of an H-phase file."""
    text = open(hphase_path).read()
    _, blocks = split_ncmat_blocks(text)
    rho, h_frac, msum_nonh = None, None, 0.0
    for b in blocks:
        kind = b[0].strip()
        if kind == "@DENSITY":
            for ln in b:
                t = ln.split("#")[0].strip()
                if t.endswith("g_per_cm3"):
                    rho = float(t.split()[0])
        elif kind == "@DYNINFO":
            el, frac = None, "1"  # missing fraction: relative weight 1
            for ln in b:
                t = ln.strip()
                if t.startswith("element "):
                    el = t.split()[1]
                elif t.startswith("fraction"):
                    frac = t.split()[1]
                    f = _frac_value(frac)
                    if el.split("_")[0] in ("H", "H1", "H2"):
                        h_frac = f
                    else:
                        msum_nonh += f * _mass_number(el)
    if rho is None or h_frac is None:
        die(f"{hphase_path}: not a usable H-phase file")
    m_avg_all = h_frac * M_H + msum_nonh
    n_tot = rho / m_avg_all * AVOGADRO
    return h_frac * n_tot


def write_main_ncmat(mat, path, keep, keep_frac_sum, rho_main):
    """Emit the main NCMAT: TSL-carried nuclides removed, remaining fractions
    renormalised, density = rho_total - rho_H so every remaining nuclide keeps
    its ABSOLUTE atom density (gidi's validated mat1_main_v3 form)."""
    lines = ["NCMAT v3",
             "# Autogenerated by cinema scripts/openmc2prompt.py",
             f"# from OpenMC material {mat['id']} ({mat['name']}) - composite",
             "# main: TSL-carried H nuclides removed, fractions renormalised,",
             "# density reduced by the removed H mass (absolute densities of",
             "# the remaining nuclides are preserved exactly).",
             "@DENSITY",
             f"  {rho_main:.17g} g_per_cm3"]
    for n, f in keep:
        lines.append("@DYNINFO")
        lines.append(f"  element {n}")
        lines.append(f"  fraction {f / keep_frac_sum:.17g}")
        lines.append("  type freegas")
    atomdb = {
        "U234": "234.04095u 0.942fm 0.0b 102.5b",
        "U236": "236.04568u 0.868fm 0.0b 5.15b",
    }
    missing = [n for n, _ in keep if n in atomdb]
    if missing:
        lines.append("@ATOMDB")
        for n in missing:
            lines.append(f"  {n}  {atomdb[n]}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_plain_ncmat(mat, outdir):
    """Non-sab material: free-gas NCMAT with all nuclides (round-1 form)."""
    nucs = mat["nucs"]
    total_ao = sum(f for _, f in nucs)
    lines = ["NCMAT v3",
             "# Autogenerated by cinema scripts/openmc2prompt.py",
             f"# from OpenMC material {mat['id']} ({mat['name']})",
             "@DENSITY"]
    if mat["rho"] is not None:
        lines.append(f"  {mat['rho']} g_per_cm3")
    else:
        rho = sum(f * _mass_number(n) for n, f in nucs) * AVOGADRO
        lines.append("# total atom density %.6e 1e24/at/cm3; mass density"
                     " from nuclide masses" % total_ao)
        lines.append(f"  {rho:.6g} g_per_cm3")
    for n, f in nucs:
        lines.append("@DYNINFO")
        lines.append(f"  element {n}")
        lines.append(f"  fraction {f / total_ao:.17g}")
        lines.append("  type freegas")
    atomdb = {
        "U234": "234.04095u 0.942fm 0.0b 102.5b",
        "U236": "236.04568u 0.868fm 0.0b 5.15b",
    }
    missing = [n for n, _ in nucs if n in atomdb]
    if missing:
        lines.append("@ATOMDB")
        for n in missing:
            lines.append(f"  {n}  {atomdb[n]}")
    path = os.path.join(outdir, "mat%d_%s.ncmat" % (mat["id"], mat["name"]))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


EMITTED = """#!/usr/bin/env python3
# Autogenerated by cinema scripts/openmc2prompt.py from {src}
# Case: {case}
# Geometry: concentric spheres (outside-in): {onion}
# Composite TSL route: sab materials are Material.fuse() of a main NCMAT
# (TSL nuclides removed, absolute densities preserved) and shared H-phase
# NCMATs (absorption-ratio weights); NCrystal's native S(alpha,beta) sampler
# runs inside each component. Cinema units: mm, eV.
import os, sys, time
sys.path.insert(0, os.environ.get("CINEMA_SRC", "/data/caixx/cinema/src/python"))
import numpy as np
from Cinema.Prompt import PromptMPI
from Cinema.Prompt.geo import Volume
from Cinema.Prompt.solid import Sphere
from Cinema.Prompt.physics import Material
from Cinema.Prompt.gun import IsotropicGun
from Cinema.Prompt.GidiSetting import GidiSetting


class Sim(PromptMPI):
    def __init__(self, seed={seed}):
        super().__init__(seed)

    def makeWorld(self):
        c = GidiSetting()
        c.setEnableGidi(True)
        c.setEnableGidiPowerIteration(True)
{matcfgs}
        world = None
        parent = None
{volumes}
        self.setWorld(world)


def main():
    sim = Sim()
    sim.makeWorld()
    gun = IsotropicGun()
    gun.setEnergy({gunekin:g})
    gun.setPosition([0, 0, 0])
    sim.simulate(gun, {particles})

    births, cycles = 0, 0
    t0 = time.time()
    for i in range({cycles}):
        n = sim.simulateSecondStack({particles})
        if i >= {inactive}:
            births += n
            cycles += 1
        if i % 25 == 0:
            print("cycle", i, "births", n, flush=True)
    keff = births / cycles / {particles}
    sigma = keff / np.sqrt(births) if births else float("inf")
    print("RESULT keff = %.6f +/- %.6f (%d cycles x %d) in %.0fs"
          % (keff, sigma, cycles, {particles}, time.time() - t0))
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "{prefix}_keff.txt"), "w").write(
        "%.6f %.6f\\n" % (keff, sigma))


if __name__ == "__main__":
    main()
"""


RUNSH = """#!/usr/bin/env bash
# Autogenerated by cinema scripts/openmc2prompt.py - reproducible runner.
# Conversion root (all ncmat paths in the driver are relative to this dir):
ROOT={root!r}
cd "$ROOT"
export CINEMAPATH=${{CINEMAPATH:-/data/caixx/cinema}}
export NCRYSTAL_LIB=${{NCRYSTAL_LIB:-/data/caixx/miniconda3/envs/cinema/lib/libNCrystal.so}}
export PYTHONPATH=/data/caixx/cinema/src/python${{PYTHONPATH:+:$PYTHONPATH}}
export OMP_NUM_THREADS=${{OMP_NUM_THREADS:-8}}
exec /data/caixx/miniconda3/envs/cinema/bin/python {relpy!r} "$@"
"""


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("casedir", help="OpenMC case dir (materials/geometry/settings.xml)")
    p.add_argument("--outdir", default=None, help="output dir (default: <casedir>/prompt)")
    p.add_argument("--prefix", default="prompt")
    p.add_argument("--temp", type=float, default=293.6, help="material temperature, K")
    p.add_argument("--tsl-map", action="append", default=[], metavar="SAB=FILE",
                   help="map an OpenMC sab name to a water NCMAT file whose H "
                        "kernel serves that component (repeatable). A sab "
                        "without a mapping is a hard error.")
    p.add_argument("--cycles", type=int, default=None)
    p.add_argument("--inactive", type=int, default=None)
    p.add_argument("--particles", type=int, default=None)
    p.add_argument("--seed", type=int, default=1010)
    p.add_argument("--gidi-threshold", type=float, default=5.0)
    a = p.parse_args()

    casedir = a.casedir.rstrip("/")
    outdir = a.outdir or os.path.join(casedir, "prompt")
    os.makedirs(outdir, exist_ok=True)
    root = os.getcwd()  # conversion root: wire paths are relative to this

    tsl_map = {}
    for item in a.tsl_map:
        sab, _, path = item.partition("=")
        if not sab or not path:
            die(f"bad --tsl-map entry {item!r} (expected SAB=FILE)")
        tsl_map[sab] = path

    def find(name):
        path = os.path.join(casedir, name)
        return path if os.path.isfile(path) else None

    mf, gf, sf = find("materials.xml"), find("geometry.xml"), find("settings.xml")
    if not (mf and gf and sf):
        die(f"{casedir} lacks materials/geometry/settings.xml")

    materials = parse_materials(mf)
    mat_by_id = {m["id"]: m for m in materials}
    surfaces, cells = parse_geometry(gf)
    onion = nested_onion(surfaces, cells)

    st = ET.parse(sf).getroot()
    def integer(tag, default):
        e = st.find(tag)
        return int(float(e.text)) if e is not None and e.text else default
    cycles = a.cycles or integer("batches", 200)
    inactive = a.inactive or min(integer("inactive", 50), cycles // 2)
    particles = a.particles or integer("particles", 10000)
    srce = st.find("source")
    gunekin = 1e6
    if srce is not None:
        ee = srce.find(".//energy")
        if ee is not None and ee.get("type") == "discrete":
            vals = [float(x) for x in ee.find("parameters").text.split()]
            gunekin = vals[-1] * 1e6  # OpenMC source energies are eV already

    seen_sabs = {m["sab"] for m in materials if m["sab"]}
    unmapped = sorted(seen_sabs - set(tsl_map))
    if unmapped:
        die("unmapped sab names (pass --tsl-map for each): "
            + ", ".join(unmapped))

    def relpath(path):
        return os.path.relpath(os.path.abspath(path), root)

    hphase_cache = {}   # mapped water file -> (hphase relpath, absH_phase)
    matcfgs, written = [], []
    for m in materials:
        tag = "mat%d" % m["id"]
        if m["sab"]:
            tsl = tsl_map[m["sab"]]
            if tsl not in hphase_cache:
                if not os.path.isfile(tsl):
                    die(f"--tsl-map target does not exist: {tsl}")
                hp_abs, abs_h_phase = hphase_from_water(tsl)
                hphase_cache[tsl] = (relpath(hp_abs), abs_h_phase)
            hp_rel, abs_h_phase = hphase_cache[tsl]

            # split the material: main (non-H) + TSL component
            total_ao = sum(f for _, f in m["nucs"])
            h_ao = sum(f for n, f in m["nucs"] if n.split("_")[0].startswith("H"))
            keep = [(n, f) for n, f in m["nucs"]
                    if not n.split("_")[0].startswith("H")]
            if not keep:
                die(f"material {m['id']}: every nuclide is TSL-carried (H) - "
                    "cannot build a main file")
            keep_sum = sum(f for _, f in keep)
            m_avg = sum(f * _mass_number(n) for n, f in m["nucs"]) / total_ao
            if m["rho"] is None:
                rho_total = sum(f * _mass_number(n) for n, f in m["nucs"]) * 1.66054
            else:
                rho_total = m["rho"]
            abs_h = h_ao      # absolute H atom density of the material (1e24/cm3)
            rho_main = rho_total - abs_h * M_H * 1.66054

            main_path = os.path.join(outdir, "mat%d_%s_main.ncmat" % (m["id"], m["name"]))
            write_main_ncmat(m, main_path, keep, keep_sum, rho_main)
            written.append(main_path)
            weight = abs_h / abs_h_phase

            matcfgs.append(f"        c.setGidiThreshold({a.gidi_threshold:g})  # {tag} composite")
            matcfgs.append(f"        {tag} = Material.fuse([")
            matcfgs.append(f"            {relpath(main_path)!r},")
            matcfgs.append(f"            ({hp_rel!r}, {weight!r}),")
            matcfgs.append(f"        ], temp={a.temp:g})")
        else:
            nc = write_plain_ncmat(m, outdir)
            written.append(nc)
            cfg = f"{relpath(nc)};temp={a.temp:g}K"
            matcfgs.append(f"        c.setGidiThreshold(-1)  # {tag}")
            matcfgs.append(f'        {tag} = Material("{cfg}")')

    volumes = []
    for depth, c in enumerate(onion):
        sid = int(c["region"].split()[-1][1:])
        r = surfaces[sid]["coeffs"][3] * 10.0  # cm -> mm
        ident = " " * 8
        if depth == 0:
            volumes.append(f"{ident}world = Volume(\"cell{c['id']}\", "
                           f"Sphere(0, {r!r}), matCfg=mat{c['material']})")
            volumes.append(f"{ident}parent = world")
        else:
            volumes.append(f"{ident}child = Volume(\"cell{c['id']}\", "
                           f"Sphere(0, {r!r}), matCfg=mat{c['material']})")
            volumes.append(f"{ident}parent.placeChild(\"cell{c['id']}\", child)")
            volumes.append(f"{ident}parent = child")

    src = os.path.basename(casedir)
    case = os.path.basename(os.path.dirname(casedir)) + "/" + src
    onion_desc = " -> ".join("cell%d(r=%.4fcm,%s)" % (
        c["id"], surfaces[int(c["region"].split()[-1][1:])]["coeffs"][3],
        mat_by_id[c["material"]]["name"] if c["material"] in mat_by_id else "?")
        for c in onion)

    text = EMITTED.format(src=casedir, case=case, onion=onion_desc,
                          seed=a.seed, matcfgs="\n".join(matcfgs),
                          volumes="\n".join(volumes), gunekin=gunekin,
                          particles=particles, cycles=cycles,
                          inactive=inactive, prefix=a.prefix)
    outpy = os.path.join(outdir, a.prefix + ".py")
    with open(outpy, "w") as f:
        f.write(text)
    compile(text, outpy, "exec")

    runsh_path = os.path.join(outdir, "run.sh")
    with open(runsh_path, "w") as f:
        f.write(RUNSH.format(root=os.path.abspath(root),
                             relpy=relpath(outpy)))
    os.chmod(runsh_path, 0o755)

    print("wrote", outpy)
    for f in sorted(set(written)):
        print("wrote", f)
    print("wrote", runsh_path)
    print("geometry:", onion_desc)
    if seen_sabs:
        print("composite TSL route: w = absH(material)/absH(H-phase); "
              "main files keep absolute non-H densities.")


if __name__ == "__main__":
    main()
