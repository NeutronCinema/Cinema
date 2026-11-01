import collections
import re
import subprocess

text = open('/tmp/heu11/nc_pcs3.txt').read()
# PCs: standalone 16-digit hex tokens (skip maps-range lines which contain ' r-xp ' style perms)
pcs = []
maps_lines = []
for line in text.splitlines():
    if re.search(r' [r][-][wxp]p? ', line):
        maps_lines.append(line)
        continue
    for tok in re.findall(r'0x[0-9a-f]{12,16}\b', line):
        pcs.append(int(tok, 16))

segs = []
for line in maps_lines:
    parts = line.split()
    if len(parts) < 6:
        continue
    try:
        lo, hi = int(parts[0].split('-')[0], 16), int(parts[0].split('-')[1], 16)
        foff = int(parts[2], 16)
    except ValueError:
        continue
    segs.append((lo, hi, foff, parts[-1]))

buckets = collections.Counter()
per_lib_offs = collections.defaultdict(list)
miss = 0
for a in pcs:
    for lo, hi, foff, path in segs:
        if lo <= a < hi:
            fo = a - lo + foff
            base = path.split('/')[-1]
            buckets[base] += 1
            per_lib_offs[base].append(fo)
            break
    else:
        miss += 1

total = sum(buckets.values())
print(f'TOTAL {total} unmatched {miss}')
for k, v in buckets.most_common(10):
    print(f'{v:5d} ({100*v/total:4.1f}%)  {k}')

LIBS = {
    'libprompt_core.so': '/data/caixx/cinema/cinemabin/src/cxx/libprompt_core.so',
    'libNCrystal.so': '/data/caixx/miniconda3/envs/pt/lib/libNCrystal.so',
    'libvecgeom.so': '/data/caixx/miniconda3/envs/pt/lib/libvecgeom.so',
}
allf = collections.Counter()
for base, offs in per_lib_offs.items():
    exe = LIBS.get(base)
    if not exe:
        continue
    r = subprocess.run(['addr2line', '-f', '-C', '-e', exe],
                       input='\n'.join(hex(o) for o in offs),
                       capture_output=True, text=True)
    lines = r.stdout.splitlines()
    for i in range(0, len(lines) - 1, 2):
        f = lines[i].strip()
        if f and f != '??':
            allf[f'{base}: {f.split("(")[0][:58]}'] += 1

atotal = sum(allf.values())
print(f'\nsymbolized: {atotal}')
for k, v in allf.most_common(20):
    print(f'{v:4d} ({100*v/atotal:4.1f}%)  {k}')
