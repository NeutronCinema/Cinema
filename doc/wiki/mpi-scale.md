# Running at scale: MPI, seeds and parameter scans

This page takes a working simulation ([Your first simulation](first-simulation)) to production
statistics: launching under MPI, how events and random seeds are distributed over ranks,
collecting results safely, the parallel power iteration for `keff`, multi-seed production with
merged output, parameter scans in a single process, and the rules that keep batch jobs sane.
The underlying class mechanics (`Prompt` vs `PromptMPI`, the life cycle, the seed chain) are
documented in [The Simulation class](simulation-lifecycle); this page is the scale-oriented
companion.

It documents **Cinema 2.0.0a5**. Every number below was measured on the machine used to prepare
this wiki (October 2026) with the Ge-slab example `doc/example_basic.py`
from the repository unless stated otherwise; seed and event count are given with every result.

---

## 1. When to use `PromptMPI`, and the two launch routes

`PromptMPI` is a drop-in subclass of `Prompt`: the script you wrote for serial work needs no
changes. The class grabs `MPI.COMM_WORLD` itself and adds `.comm`, `.rank`, `.size`; from there
the event split, per-rank seeds and result gathering are all automatic.

There are two ways to launch the same script on N ranks:

```bash
# route 1: the script's own __main__ block drives the run
mpirun -n 4 python3 my_sim.py

# route 2: the prompt CLI drives the run (see the [cli](cli) page)
mpirun -n 4 prompt -g my_sim.py --gun BeamGun -n 1000000
```

Route 2 has script requirements of its own: the script must define a `Gun` subclass, must have
built the world by the time the CLI instantiates the class — in the constructor or the module
body (only code inside `if __name__ == "__main__":` is never executed) — and its constructor
parameters need type hints. The full contract is on the
[cli](cli) page. Both routes end up calling the same `PromptMPI.simulate`, so the
event split and seeds of section 2 apply identically — in CLI mode `-n` is the **total** number
of primaries, split over the ranks for you.

Measured, route 2 end to end: `mpirun -n 4 prompt -g my_sim.py --gun BeamGun -n 1000` runs four
ranks with seeds 4096–4099, prints one absorption line per rank
(`Scorer TOF rank 0: weight 6.0 ...`, ranks 1–3: 3, 10, 2 — 21 absorbed of the 1000 total), and
leaves a single `TOF.h5` written by rank 0.

**What MPI buys you.** Transport is the only part that scales. Every rank is a separate process
that imports the C++ core and rebuilds the NCrystal world — a 4-rank run prints
`set random seed:` 4096–4099, one per rank, and the `Configuring physics model` line twice per
rank (the serial run prints it twice in total) — so process start-up is paid once per rank and
does not shrink as ranks are added; only rank 0 runs the progress timer. Short jobs are
start-up dominated on every rank, so judge MPI performance by transport time on large event
counts. Measured on the Ge-slab example, 4,000,000 events, default seed 4096:

| Launch | Transport time (rank 0) | Merged absorbed weight |
|---|---|---|
| `python3` (1 rank) | 14.2 s | 62817 |
| `mpirun -n 4` | 4.0 s | 62749 |

A 3.5× speedup on four ranks. The two merged weights differ only by Monte-Carlo noise
(62817 vs 62749, well under the √62749 ≈ 250 counting error): the serial run
draws one random stream (seed 4096), the MPI run four (4096–4099). Do not read the total off
a rank line: the `Scorer TOF rank 0: weight 15700 ...` line is rank 0's *local* count for its
~1M-event share, not the sum. Histograms — not particles —
are what crosses MPI between ranks, so no interconnect bandwidth is required; ranks exchange a
few arrays per scorer at gather time.

---

## 2. Event distribution and random seeds

`PromptMPI.simulate(gun, num=0, timer=True, save2Disk=False)` is the whole distribution
machinery (source: `src/python/Cinema/Prompt/promptCore.py`):

```python
def simulate(self, gun, num: int = 0, timer=True, save2Disk=False):
    batchSize = int(num / self.size)
    if self.rank:
        # non-root ranks never print the timer nor save to disk: their
        # local histograms are reduced to the root rank afterwards
        super().simulate(gun, batchSize, timer=False, save2Disk=False)
    else:
        super().simulate(gun, num - batchSize * (self.size - 1), timer=timer, save2Disk=save2Disk)
```

- ranks 1..n-1 run `batchSize` events each, with the progress timer and the `save2Disk`
  dump off;
- **rank 0 runs the remainder** `num - batchSize*(size-1)` — up to `size-1` extra events, with
  the timer and progress printing on and, if requested, the `save2Disk=True` end-of-run dump;
- the sum over ranks equals the requested `num` exactly (it does not have to be divisible by
  the rank count; `num` may be a float such as `1e7`).

Measured, 100003 events on 4 ranks with a per-history counter scorer (a `PEA_PRE` scorer on a
void world fires exactly once per primary):

```text
Scorer cnt rank 0: weight 25003.0, hit 25003.0
Scorer cnt rank 1: weight 25000.0, hit 25000.0
Scorer cnt rank 2: weight 25000.0, hit 25000.0
Scorer cnt rank 3: weight 25000.0, hit 25000.0
```

25003 + 3 x 25000 = 100003 — the remainder lands on rank 0, and the total is exact.

**Seeds.** `PromptMPI.__init__(seed)` stores `seed + rank` and each rank's `setWorld` seeds its
own C++ random stream with it. A 4-rank job prints `set random seed: 4096` … `4099` for the
default constructor seed. The streams are independent by construction — statistically
independent runs that `gatherHistData` merges into one — and you must **not** re-seed per rank
yourself. The full seed chain (constructor → `setWorld` → `SingletonPTRand` → NCrystal) is in
[The Simulation class, section 5](simulation-lifecycle).

---

## 3. Collecting results: `gatherHistData` is collective

`PromptMPI.gatherHistData(cfg, raw=False, dst=0)` does three things:

1. fetches the rank-local histogram (this part is not collective);
2. prints one `Scorer <name> rank <r>: weight ..., hit ...` line per rank;
3. performs three `comm.Reduce` (sum) operations — weight, hit and Σw² — to root `dst`
   (default 0).

The rules that follow from this:

- **Every rank must call it**, in the same order — it is a collective call, like a barrier.
- **Only rank `dst` receives the merged histogram.** On the other ranks the returned object
  still holds that rank's *local, unmerged* data — fine for a quick look at one rank, wrong for
  totals.
- `dst` may be set to another rank if you want the merged result elsewhere.

Everything that consumes results — plotting, saving, analysis — must therefore be rank-gated:

```python
sim.simulate(gun, 1e7)
hist = sim.gatherHistData('TOF')
if sim.rank == 0:
    hist.savefig('tof.png')
```

`sim.save_all_scorers()` (one `<scorer>.h5` per scorer) may be called by all ranks: it gathers
each scorer internally (collective — keep it outside any rank gate) but guards its file writes
with `if self.rank == 0` itself. This is what the CLI route calls for you, which is why an
`mpirun -n 4 prompt -g ...` run leaves exactly one file set.

> **Warning — `gatherHistData` is not idempotent.** On rank `dst` it writes the merged arrays
> back into the live scorer histogram (the object behind `sim.scorer`), so after a manual
> `gatherHistData('TOF')` the scorer on rank 0 *holds the merged total* — and so does anything
> that re-fetches the live histogram afterwards, including `sim.l.getHist(...)`. Calling
> `save_all_scorers()` then gathers again — reducing the already-merged rank `dst` with
> the other ranks' local data — and the `.h5` comes out inflated. Measured on the 4-rank run of
> the section 1 table: gather followed by `save_all_scorers()` wrote `TOF.h5` with 109798 absorbed
> instead of 62749 — the already-merged rank-dst total (62749) was reduced again together with the
> other ranks' local data (47049), double-counting their contributions. Per scorer, do one or the
> other: either call
> `save_all_scorers()` alone, or gather manually and save/plot the returned object — do not
> gather the same scorer twice.

**Reading the merged total.** The Reduce merges the per-bin arrays only. On rank `dst`,
`hist.getWeight().sum()`, `hist.getHit().sum()` and `hist.getAccWeight()` (it re-sums the
live array on each call) are merged totals, but the cached scalar `hist.getTotalWeight()`
still holds the destination rank's pre-reduce value — `setWeight` replaces only the per-bin
array. Measured on the section 2 run: after the 4-rank gather, `getWeight().sum()` = 100003
while `getTotalWeight()` = 25003 (only `getTotalWeight` was read in that run). A 2-rank,
40000-event run with seed 4096 shows the same pattern: `getWeight().sum()` =
`getAccWeight()` = 607, `getTotalWeight()` = 339. Read totals off the arrays, not off the
cached scalar.

**What happens if you forget the gate** (both measured on 2 ranks):

- *Ungated plotting/saving:* every rank executes it. All ranks write the **same file name**,
  the last writer wins, and the survivor can be a single rank's local data rather than the
  merged total — an ungated `h.save('tof.h5')` on a 10000-event, 2-rank run left a file
  holding rank 1's local 65 absorbed counts, not the sum over ranks.
- *A collective call inside a rank gate:* deadlock. Running `if sim.rank == 0:
  sim.gatherHistData('cnt')` leaves rank 0 waiting forever inside `comm.Reduce` while the other
  ranks carry on and exit; the job hung until an external `timeout` killed it. Never gate the
  call itself — gate only what uses its result.

**Per-rank files inside one job.** If you want each rank's local histogram on disk (e.g. to
inspect rank-to-rank fluctuations), bypass the collective with the launcher's non-collective
getter and tag the file name with the rank:

```python
local = sim.l.getHist(sim.scorer['TOF'])
local.save(f'tof_rank{sim.rank}.h5')     # every rank writes its own file
```

Fetch it **before** any `gatherHistData` call — after a gather, rank `dst`'s live histogram
already holds the merged data (measured: a fetch-after-gather wrote 10003 hits to rank 0's
"local" file instead of its 2503). With 10003 events on 4 ranks, fetched before gathering:
four files, holding 2503 / 2500 / 2500 / 2500 hits.

---

## 4. The parallel power iteration: `keff` with exchanged fission banks

Everything above parallelises *independent* histories. The power iteration for the multiplication
factor `keff` cannot work that way: cycle N's source is cycle N−1's fission sites, so the ranks
must advance **one shared chain**, not p independent ones. `PromptMPI.simulateSecondStack(num)`
does exactly that and returns the pooled fission-birth count of the cycle:

```python
sim.simulate(gun, batchsize)                 # the initial source cycle, split like any run
births = []
for cycle in range(n_cycles):
    births.append(sim.simulateSecondStack(batchsize))   # every rank, every cycle
k_active = [b / batchsize for b in births[skip:]]
keff, err = np.mean(k_active), np.std(k_active) / np.sqrt(len(k_active))
```

The rules that keep this correct:

- **The split is automatic.** The first `num % size` ranks transport one extra particle so the
  pooled source is exactly `num`; a rank whose share is zero sits out the cycle but still joins
  every collective.
- **Never gate the collective.** `simulateSecondStack` contains MPI collectives: call it on every
  rank the same number of times, exactly like `gatherHistData` (section 3).
- **One return value, one meaning.** The return value is the *total* fission births of the pooled
  chain in this cycle — divide by the total source size per cycle, exactly as in the serial loop.
- The `GidiSetting` power iteration must be enabled as in the serial case
  ([Materials & physics](materials-physics)).

### The two bank exchanges

Between cycles the ranks exchange fission sites; `PromptMPI(bank_exchange=...)` selects the
scheme (default `'nearest'`):

| | `'nearest'` (default) | `'pooled'` |
|---|---|---|
| Idea | every rank draws the same `num` source sites against the conceptual pooled bank from one shared seed (the OpenMC "nearest neighbours" scheme); only sites that change owner travel | every rank allgathers the raw banks, then resamples its share from the pooled bank with the exact serial sampling |
| Data per rank per cycle | expected O(√num) sites at the worst boundary, independent of the rank count | the whole bank: O(num) sites per rank |
| Sampling | with replacement, like OpenMC | shuffle/truncate or with-replacement fill — exactly the serial path |
| Use when | many ranks or large source banks | you want bit-level serial sampling semantics per bank state |

Both schemes advance the same shared chain and differ only in where the resampling happens.
Measured on the U7H993 keff sphere (r = 87.407 mm, seed 1010, batchsize 2000, 12 cycles with
the first 3 skipped as the source transient, gidi power iteration on):

| Run | Exchange | keff | deviation from serial |
|---|---|---|---|
| serial `Prompt`, 1 rank | — | 0.9638 ± 0.0162 | reference (± is the active-cycle spread) |
| `PromptMPI`, 1 rank | (bypassed) | = serial, **bit-identical** | the size-1 path *is* the serial path, pinned by `test_parallel_keff.py` |
| 3 ranks | `nearest` | 0.9728 | 0.6σ |
| 3 ranks | `pooled` | 0.9851 | 1.3σ |

Beware short runs: the first cycles are a transient (the source-cycle bank still carries the
fixed-source spectrum), and two correct realizations of the same chain differ by far more at
3 cycles than the naive σ/√n suggests — serial and 3-rank pooled, both correct, read 0.96 vs
1.05 keff over their first 3 cycles. Skip at least a few cycles and judge nothing by fewer
than ~10. The first-cycle birth counts above (2236 serial, 2213 for both MPI variants) already
differ from the serial run, and that is expected: each rank carries its own seed (seed + rank)
and normalises the parked bank to its own share, so a parallel chain is a different realization
from cycle 1 on — the two MPI variants coincide in cycle 1 only because the first exchange
engages after the first transport leg.

Mechanically, `'nearest'` costs one allgather of the per-rank bank sizes plus one alltoall of
the site blobs; every rank derives the same assignment from the shared sample (seeded by the
`seed` argument of `PromptMPI`, which must therefore be identical on every rank), so no request
phase is needed. A bank blob is 84 bytes per particle, so even the pooled exchange moves well
under a megabyte per rank at batchsize 2000 — the schemes only part ways at many ranks and
large source banks, where the pooled allgather costs O(num) sites per rank while the
nearest-neighbour exchange stays at the O(√num) boundary fluctuation regardless of rank count.
If no rank fissions at all, `simulateSecondStack` raises the same
`RuntimeError: secondary stack is empty` the serial path raises — collectively, in lockstep on
every rank.

### An MPI-specific gotcha: OpenBLAS worker threads

Under `mpirun`, unpinned OpenBLAS worker threads spin on the core the rank is bound to and
roughly **double** the cycle time (1.57 → 0.78 s/cycle on the toy above, birth counts
identical). Export `OPENBLAS_NUM_THREADS=1` before `mpirun` for transport runs — the parallel-keff
tests do — but do not set it globally: serial numpy-heavy post-processing still wants its threads.

---

## 5. Multi-seed production

One `mpirun -n 4` job already gives you four statistically independent random streams and one
merged answer — that is the simplest way to production statistics, and section 1–3 are all it
needs. Run **separate seeds that you keep separate** when you want one of the following:

- an **empirical error estimate**: the spread of N independent results is a direct measure of
  the statistical uncertainty, no error-propagation assumptions needed;
- **job-level independence**: N small jobs queue, restart and fail independently on a cluster,
  where one large allocation is monolithic;
- to add results later (run more seeds next week and merge).

> **Legacy notice.** The repository's `runExample/` directory shows the historical version of
> this pattern: a shell loop firing `prompt -n 1e7 -s $i -g PSD.gdml` GDML jobs in parallel,
> merged afterwards by `anaMcpl.py` with `McplAnalysor.getHistMany`. GDML input is legacy —
> use the Python API below. The merge tooling itself is unchanged and remains the recommended
> way to combine independent runs.

### 5.1 Producing one run per seed

Run one seed per process, each in **its own directory** (why becomes clear in section 5.3): keep the
[first-simulation](first-simulation) script, take the seed from `sys.argv`, and let the shell
drive the loop.

`one_seed.py` — the first-simulation script with the seed taken from the command line. The
module shape it expects: `my_sim.py` must expose a module-level `Simulation` class whose
constructor does **not** call `makeWorld` (move that call here), plus a module-level `gun`
instance:

```python
import sys
from my_sim import Simulation, gun         # your simulation module

sim = Simulation(seed=int(sys.argv[1]))    # seed from the command line
sim.makeWorld()
sim.simulate(gun, 100000)
sim.gatherHistData('TOF').save('tof.h5')
```

```bash
for seed in 1 2 3 4; do
  mkdir -p seed$seed && (cd seed$seed && python3 ../one_seed.py $seed)
done
```

Keep it one process per seed: do **not** collapse the loop into Python — the Launcher (and its
seed flag) is process-wide, so a second `Simulation(seed=...)` in the same process fails at
`makeWorld()` with `RuntimeError: World exist already: only one world can be set per process`,
stopping every run after the first (the error is catchable, but a scan loop has no reason to
trip it). Cycling seeds inside
one process is possible but requires `sim.clear()` before each new build — see section 5.4.

Measured on the Ge-slab example, 1e5 events per seed, serial:

| Seed | Absorbed neutrons |
|---|---|
| 1 | 1634 |
| 2 | 1562 |
| 3 | 1528 |
| 4 | 1583 |

Mean 1577, spread (standard deviation of the four values) 44 — consistent with the counting-
statistics expectation of √1577 ≈ 40 per run. The seed spread *is* your error bar: quoting
"1577 ± 44" here uses four independent runs and no error model at all. A single 4e5-event run
would deliver the same central value with only the internal √N estimate.

### 5.2 Merging independent runs

Three routes, all measured with the seed-1 and seed-2 runs above (1634 and 1562 absorbed):

**HDF5 route** — load the `<scorer>.h5` files and add them; the gvar-backed arrays combine
errors in quadrature automatically:

```python
from Cinema import CinemaXY
a = CinemaXY.from_hdf5('seed1/tof.h5')
b = CinemaXY.from_hdf5('seed2/tof.h5')
merged = a + b
print(merged.sum())        # 3196(57)  -- 1634(40) + 1562(40), sqrt(40^2+40^2) = 57
```

**MCPL route** — `sim.simulate(gun, n, save2Disk=True)` writes each scorer as an MCPL
container (`ScorerTOF_TOF_seed5489.mcpl.gz` for the example; see section 5.3 for the name).
The kwarg is accepted by `PromptMPI.simulate` as well and takes effect on rank 0 — in a
serial (one-rank) `PromptMPI` process that is the only rank, so the same script works for
both bases and no class swap is needed any more. (Serial `Prompt` and serial `PromptMPI`
runs with the same seed are equivalent — the section 5.1 table is reproduced exactly.)
Merge every
file matching a glob; files are ordered by the last integer in their names:

```python
from Cinema.Prompt.PromptFileReader import McplAnalysor
merged = McplAnalysor('seed*/ScorerTOF_TOF_seed*.mcpl.gz').getHistMany()
print(merged.weight.sum())   # 3196.0
```

`getHistMany(offset=0, num=None)` returns an `ErrorPropagator` (weights summed, errors in
quadrature) that you can plot or analyse further; this is the modernised `runExample`
machinery. Measured for the two section 5.1 seeds re-run with the `Prompt` base: the two
`ScorerTOF_TOF_seed5489.mcpl.gz` files carry 1634 and 1562 absorbed, and the merge prints
`3196.0`. Per-rank *particle-record* MCPL files are merged differently — see section 8.

**In-memory route** — `hist1.merge(hist2)` on two `Hist1D`/`Hist2D` objects sums weight and
hit and combines Σw² in quadrature. It refuses histograms whose free-text `note` differs
(`addNote` the same label on both first). Use it when you already hold both histograms in one
session.

### 5.3 Why one directory per seed

The MCPL file name embeds the **C++ RNG seed current when the scorer was created** — which, on
the first build in a process, is the library default `5489`, *not* your constructor seed. The
two runs of §4.1 with seeds 1 and 2 both wrote `ScorerTOF_TOF_seed5489.mcpl.gz`; in one
directory the second run silently overwrites the first (the `.h5` names have no seed component
at all). Separate directories are the only safe naming. The full story is in
[The Simulation class, section 7](simulation-lifecycle).

### 5.4 Several seeds in one process

Seeds can also be cycled inside a single process: `clear()` the simulation, then build a
**fresh** `Simulation(seed=s)` object (the `.seed` property is read-only). This works because
`clear()` resets the C++ seed flag, so the new object's `setWorld` may seed again. Measured in
one process, 1e5 events each: seed 1 → 1634, same object after `clear()` → 1634 again
(bit-identical), fresh `Simulation(seed=2)` after `clear()` → 1562 — the same value the
standalone seed-2 run of section 5.1 produced. Sequential seeds in one process are exactly
equivalent to separate runs.

---

## 6. Parameter scans in one process

A scan over geometry or physics parameters does not need one process per point. `sim.clear()`
tears the world down in place — C++ resource manager, `worldExist` flag, scorer registry — so
the next `makeWorld()` can build the next point:

```python
sim = Simulation(seed=4096)
for thickness in (1.0, 2.0, 5.0):
    sim.clear()
    sim.makeWorld(thickness)          # your makeWorld takes the parameter
    sim.simulate(gun, 100000)
    h = sim.gatherHistData('TOF')
    if sim.rank == 0:
        h.savefig(f'tof_t{thickness}.png')
```

Semantics that matter at scale:

- `clear()` is **mandatory** between builds — a second `setWorld` without it raises
  `RuntimeError: World exist already: only one world can be set per process`. The precise
  failure mode is described in
  [The Simulation class, section 8](simulation-lifecycle).
- Each scan point restarts the random stream from the same seed (because `setWorld` re-applies
  it), so points are comparable with minimal noise between them — and a re-run of one point
  reproduces it bit for bit (measured: 1634 → 1634, section 5.4).
- To also vary the *seed* per point, construct a fresh `Simulation(seed=...)` after `clear()`
  (section 5.4).
- Long scans accumulate Python-side bookkeeping (`Volume.volume_list` is deliberately not
  cleared — it owns memory); for hundreds of points, batch your scans into separate processes.

---

## 7. Tuning free parameters: the Optuna-based `Optimiser`

When a scan becomes a search — fitting simulation free parameters against measured data — the
module `Cinema.Prompt.parameterOptimizer` provides an Optuna-based `Optimiser`: subclass it,
implement `objective(trial)` (inside it: `self.sim.clear()`, `makeWorld(params)` from
`self.getParameters(trial)`, `simulate`, return a score), register search ranges with
`addParameter(name, lower, upper)`, and call `optimize(name, n_trials, storage="sqlite:///optuna_study.db")` —
`optimize_botorch` swaps in a Bayesian sampler. Two things to know: the class is **not**
exported from `Cinema.Prompt` — import it as
`from Cinema.Prompt.parameterOptimizer import Optimiser` (several in-repo scripts still use the
broken shorter import) — and `optimize` requires an explicit `storage=` URL for anything worth keeping (the former
hardcoded remote study-storage default with embedded credentials was removed for security;
calls without one raise a `ValueError` pointing at `sqlite:///optuna_study.db`). The deprecated
`localhost=True` still selects an Optuna *in-memory* study that dies with the process — fine for
a quick scan, not for results you want to keep. A fuller treatment is planned as its own page (see the planned-pages list
on [home](home)); everything needed to use the class safely is in this section.

---

## 8. Batch etiquette

1. **Never call `show()` in a batch job.** It opens an interactive pyvista window; under MPI
   rank 0 renders while every other rank waits at a barrier behind it. Use it for interactive
   checks only ([visualization](visualization)).
2. **Assume every output file name collides.** `<scorer>.h5` and `<scorer>.pdf` are plain
   scorer names — every run overwrites them; the histogram MCPL names embed the library-default
   seed, not yours (section 5.3). Structure production runs as one directory per seed or per
   point, and have the job move results out before exiting.
3. **The `save2Disk=True` dump is root-rank-only under MPI.** `PromptMPI.simulate` accepts
   the flag and rank 0 writes the `<...>_seed<seed>.mcpl.gz` histogram containers; non-root
   ranks never dump. For array-style output prefer `save_all_scorers()` (rank 0, `.h5`),
   which reduces the merged histograms before writing.
4. **Per-rank particle MCPL files merge by iteration.** An `MCPLOutHelper` scorer writes one
   file per rank with the rank appended (`det_pro0.mcpl`, `det_pro1.mcpl`, ...); the suffix
   appears whenever `mpi4py` is importable, so even a serial process writes `det_pro0.mcpl`.
   Merge by iterating the files with `PTMCPL` (see [Results analysis](results-analysis)) or
   the `mcpl` package tools — `McplAnalysor` is for histogram containers, not particle records.
5. **The test suite is fork-isolated.** `cimbuild -t` (the build+test wrapper) runs the Python
   tests through pytest with `--forked` (the same flag the CTest wiring uses): each test runs
   in a forked child, so a hard C++ abort (which Cinema can still produce on misuse, e.g. a
   broken plugin environment during NCrystal model configuration) kills only that child, not
   the whole run. Write long multi-case batch scripts
   the same way if they exercise rough edges.
6. **Set `OPENBLAS_NUM_THREADS=1` under `mpirun`.** Unpinned OpenBLAS worker threads spin on
   the rank's core and roughly double the transport time (section 4).

---

## 9. Gotchas

| Symptom | Cause and remedy |
|---|---|
| Job hangs at the end, one rank missing from the output | A collective call (`gatherHistData`, `save_all_scorers`) sits inside an `if rank == 0:` gate. Every rank must call it; gate only the use of the result (section 3). |
| Result file contains one rank's data, not the total | Plotting/saving was not rank-gated: all ranks wrote the same file name and the last writer won. Gate with `if sim.rank == 0:` (section 3). |
| `.h5` total is implausibly large, roughly double the expected count | `gatherHistData` was called manually and `save_all_scorers()` afterwards: the first call already merged the data into rank `dst`'s live scorer, so the second gather counts it again. Per scorer use one or the other (section 3). |
| `getTotalWeight()` after a gather returns one rank's count, not the total | The MPI reduction updates the per-bin arrays only; the cached totals keep the destination rank's pre-reduce values. Use `hist.getWeight().sum()` / `getHit().sum()` (section 3). |
| `save2Disk=True` produced no files on most ranks | The dump is root-rank-only under MPI: rank 0 writes, non-root ranks never do. For per-scorer `.h5` files use `save_all_scorers()` (section 2, section 8). |
| Second seed's output overwrote the first | Histogram MCPL names embed the library-default seed (5489), `.h5` names have none. One directory per seed (section 5.3). |
| `RuntimeError: World exist already: only one world can be set per process` during a scan | `setWorld` ran twice without `clear()`. Call `sim.clear()` before every rebuild (section 5). |
| Want a different seed for the next scan point | `.seed` is read-only; construct a fresh `Simulation(seed=s)` after `clear()` — legal, because `clear()` resets the C++ seed flag (section 5.4). |
| All ranks abort right after `Configuring physics model` | Not an MPI problem: a known environment defect taints `NCRYSTAL_PLUGIN_LIST`; the remedy is on [Install](install). |
| MPI run transports at half the expected speed | Unpinned OpenBLAS worker threads spin-wait on the rank's core. `export OPENBLAS_NUM_THREADS=1` before `mpirun` (section 4); leave it unset for serial work. |
| `from Cinema.Prompt import Optimiser` fails | It is not exported there; use `from Cinema.Prompt.parameterOptimizer import Optimiser`, and configure local storage for `optimize` (section 6). |

---

## Where to go next

- [Your first simulation](first-simulation) — the single-process pattern this page scales out
- [The Simulation class](simulation-lifecycle) — seed machinery, life cycle, output files
- [The command line](cli) — the `prompt -g` route and `ptplot` for the result files
- [Scoring](scorers) — scorer catalogue
- [Results analysis](results-analysis) — what to do with merged histograms; `PTMCPL` for
  reading per-rank particle files

---

*Source files: `src/python/Cinema/Prompt/promptCore.py`,
`src/python/Cinema/Prompt/PromptFileReader.py` (project repository).
Questions: cinema-users@outlook.com.*
