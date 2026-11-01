# Transport profiling toolchain (附3 method, rebuilt 2026-10-31)

SIGPROF self-sampler + offline symbolization for profiling the prompt
transport without a perf binary.

## Usage

    gcc -shared -fPIC -O2 -o sampler.so sampler.c
    LD_PRELOAD=$PWD/sampler.so SAMPLER_OUT=/tmp/pcs.txt <the workload>
    python3 sym2.py   # reads /tmp/heu11/nc_pcs*.txt + the maps tail; edit
                      # the paths and the lib table at the top first

- The sampler writes raw PCs at 200 Hz (ITIMER_PROF, async-signal-safe
  write(2)) and dumps /proc/self/maps at exit.
- sym2.py: PCs = the standalone 0x-prefixed 16-digit tokens; the maps
  lines (with the .so paths) give the segment table; the file offsets =
  (pc - seg_lo) + seg_file_offset; addr2line -f -C per library.

Caveats learned the hard way:
- gdb-based sampling (bt/continue loops) does NOT work: continue blocks
  until the next stop, so only the first sample lands. Use this sampler.
- The LD_PRELOAD propagates to child processes: multiple writers truncate
  each other's output. Preload only the process you measure (env on the
  command, not exported).
- ITIMER_PROF ticks on CPU time: a sleeping process produces no samples
  (correct, but don't use sleep as the test workload).
