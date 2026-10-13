#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################

import functools

import numpy as np
from .launcher import Launcher, _WORLD_EXIST_MSG
from .geo import Volume
from ..Interface import importFunc
import warnings
try:
    from mpi4py import MPI
except ImportError:
    # mpi4py is optional: only the PromptMPI subclass needs it. Serial Prompt
    # runs (including promptcli) must work without it.
    MPI = None

_pt_ResourceManager_clear = importFunc('pt_ResourceManager_clear', None, [])
__all__ = ["Prompt", "PromptMPI"]


def _guard_second_make_world(func):
    """Wrap a makeWorld override with the one-world-per-process fail-fast.

    A second makeWorld in the same process used to build a whole throwaway
    geometry into the already-closed world (VecGeom logs "Logical Volume
    created after geometry is closed") before hitting the worldExist guard in
    setWorld - or an unrelated mid-build error instead of the documented
    exception. The wrapper raises the same RuntimeError as setWorld (the
    promise of doc/wiki/simulation-lifecycle.md) immediately, before any
    Volume is constructed. clear() resets the flag, so the documented
    clear() -> makeWorld() rebuild loop keeps working.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.l.worldExist:
            raise RuntimeError(_WORLD_EXIST_MSG)
        return func(self, *args, **kwargs)
    wrapper._second_world_guard = True
    return wrapper


def _nn_windows(num, size):
    """Contiguous per-rank slices of a ``num``-sized shared sample.

    Used by the parallel power iteration both for the transport split and
    for the nearest-neighbour bank exchange: the first ``num % size`` ranks
    take one extra site, the windows tile [0, num) exactly. Returns a list
    of (lo, hi) tuples, one per rank.
    """
    base, extra = divmod(int(num), int(size))
    out = []
    lo = 0
    for rank in range(int(size)):
        width = base + (1 if rank < extra else 0)
        out.append((lo, lo + width))
        lo += width
    return out


def _nn_send_indices(sample, counts, num, size, rank):
    """Pure assignment half of the nearest-neighbour bank exchange.

    Given the shared sorted sample of source sites, the per-rank bank sizes
    and the caller's rank, returns (cum, sends): cum is the exclusive scan
    of counts (the rank bank ranges), sends[j] the LOCAL record indices
    (already offset by this rank's own start) this rank must hand to rank
    j, including its locally-owned slice at j == rank. Identical inputs
    give identical outputs on every rank, which is what lets each rank
    derive the whole assignment without a request phase.
    """
    cum = np.zeros(size + 1, dtype=np.int64)
    cum[1:] = np.cumsum(counts)
    windows = _nn_windows(num, size)
    need = sample[windows[rank][0]:windows[rank][1]]
    owner = np.searchsorted(cum, need, side='right') - 1
    # rank j receives every site in its slice that lives in my range; for
    # j == myself that is the locally-owned part of my own slice
    sends = []
    for j in range(size):
        jneed = sample[windows[j][0]:windows[j][1]]
        if j == rank:
            sel = need[owner == rank]
        else:
            sel = jneed[(jneed >= cum[rank]) & (jneed < cum[rank + 1])]
        sends.append((sel - cum[rank]).astype(np.uint64))
    return cum, sends


def _no_ghost_registry_entries():
    """Keep Volume.scorer_dict free of entries for rejected registrations.

    Volume.addScorer (geo.py) writes the scorer into the python-side registry
    before the bridged C++ call, so a rejected cfg used to leave a ghost
    entry: an honest retry with the same name then failed with a false
    "already registered" ValueError, and the poisoned registry later sent
    gatherHistData/save_all_scorers into the unbridged getHist lookup, whose
    C++ exception cannot be caught from python (process abort). Restoring the
    pre-call registry when addScorer raises removes the ghost again. This is
    a safety net at the Prompt layer and a no-op once geo.addScorer inserts
    only after the C++ call succeeded.
    """
    original = Volume.addScorer

    @functools.wraps(original)
    def addScorer(*args, **kwargs):
        registry = args[0].__class__.scorer_dict
        snapshot = dict(registry)
        try:
            return original(*args, **kwargs)
        except Exception:
            registry.clear()
            registry.update(snapshot)
            raise

    Volume.addScorer = addScorer


_no_ghost_registry_entries()


class Prompt:
    """
    Core class for particle transport and ray-tracing simulation with Monte Carlo method.
    
    This class encapsulates the methods to visualize the simulation, simulate in production mode, 
    and collect data. 

    Derived from Prompt class to run simulations. 
    Or to inherit its child class PromptMPI to run in parallel.
    
    Attributes:
        _l (Launcher): Simulator launcher instance, responsible for calling the underlying physics engine
        _seed (int): Random seed for reproducible simulations
        world: Geometry world object (only used when isSubmodel is True)
    
    Examples:
        >>> prompt = Prompt(seed=1234)
        >>> prompt.makeWorld()  # Must be implemented in subclass
        >>> prompt.simulate(gun_config, num_events=1000)
    """
    
    def __init__(self, seed: int = 4096) -> None:
        """
        Initialize a Prompt instance.
        
        Args:
            seed: Random seed, defaults to 4096
        """
        self._l = Launcher()
        self._seed = seed

    @property
    def seed(self):
        """Random seed of the simulation (read-only property)."""
        return self._seed

    @property
    def l(self):
        """Launcher instance (read-only property)."""
        return self._l
    
    @property
    def scorer(self):
        """Get the dictionary of all current scorers (read-only property)."""
        return Volume.scorer_dict

    def makeWorld(self):
        """
        Build the geometry world (abstract method, must be implemented in subclass).

        Raises:
            NotImplementedError: Must be implemented in subclass
            RuntimeError: On the second makeWorld in one process without an
                intervening clear() (see setWorld; one world per process)

        Note:
            Subclass overrides are wrapped by __init_subclass__ with the same
            fail-fast guard that setWorld applies, so the second attempt
            raises before any geometry is built.
        """
        raise NotImplementedError('')

    def __init_subclass__(cls, **kwargs):
        """Install the second-world guard on every makeWorld override.

        The most-derived makeWorld found on the new class (its own or
        inherited from a mixin) is wrapped with _guard_second_make_world,
        except Prompt's own abstract placeholder above. Already wrapped
        functions (subclasses that do not override) are left alone.
        """
        super().__init_subclass__(**kwargs)
        for klass in cls.__mro__:
            if klass is Prompt:  # the abstract placeholder stays unwrapped
                break
            makeWorld = klass.__dict__.get('makeWorld')
            if makeWorld is not None:
                if not getattr(makeWorld, '_second_world_guard', False):
                    cls.makeWorld = _guard_second_make_world(makeWorld)
                break
    
    def scorerNameConfig(self, name):
        """
        Configure scorer name, handling duplicate names.
        
        Args:
            name: Original scorer name
            
        Returns:
            str: Processed scorer name (adds '`' suffix if duplicate)
        """
        if name in self.scorer.keys():
            newName = name + '`'
            warnings.warn(f"Duplicated scorer name {name}. Changed to {newName}")
            return newName

    def clear(self):
        """
        Clean up resources and reset simulation environment.
        
        Clears resource manager, resets world existence flag, and scorer dictionary.
        """
        _pt_ResourceManager_clear()
        self.l.worldExist = False
        Volume.scorer_dict = {}
    
    def setWorld(self, world):
        """
        Set the geometry world.

        Args:
            world: Geometry world object

        Raises:
            RuntimeError: If a world already exists in this process

        Note:
            sets world through Launcher and applies random seed. Only one
            world can be set per process (the Launcher is a process-wide
            singleton shared by every Prompt instance), so run each world,
            e.g. each parameter-scan point, in its own process or mpirun rank.
        """
        # check before setSeed: the underlying C++ aborts the whole process
        # (uncatchable SIGABRT) when the seed is set a second time
        if self.l.worldExist:
            raise RuntimeError(_WORLD_EXIST_MSG)
        self.l.setSeed(self.seed)
        self.l.setWorld(world)

    def show(self, gun, num: int = 0, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False):
        """
        Display geometries and particle trajectories.

        Args:
            gun: Particle gun configuration or object
            num: Number of particles to display, defaults to 0 (no trajectory, only show geometries)
            mergeMesh: Whether to merge meshes
            xscale, yscale, zscale: Coordinate scaling factors
            byMat: Color the geometry by material
            addLegend: Add legend
            geoClip: Geometry clipping
        """
        self.l.showWorld(gun, num, mergeMesh, xscale, yscale, zscale, byMat, addLegend=addLegend, geoClip=geoClip)

    def simulateSecondStack(self, num):
        """
        Simulate using second stack.

        Args:
            num: Number of simulation events

        Returns:
            Simulation result
        """
        num = int(num)
        if num < 0:
            raise ValueError(f'num must be non-negative, got {num}')
        return self.l.goWithSecondStack(num)

    def simulate(self, gun, num: int = 0, timer=True, save2Disk=False):
        """
        Execute particle transport/ray-tracing simulation.
        
        Args:
            gun: Particle gun, an instance of class Gun
            num: Number of simulation events, defaults to 0
            timer: Whether to enable timer, defaults to True
            save2Disk: Whether to save to disk, defaults to False
        """
        if hasattr(gun, 'items'):
            self.l.setGun(gun.cfg)
            self.l.go(int(num), timer=timer, save2Disk=save2Disk)
        elif isinstance(gun, str):
            self.l.setGun(gun)
            self.l.go(int(num), timer=timer, save2Disk=save2Disk)
        else:
            # it is a python gun
            from tqdm import tqdm
            show_progress = not hasattr(self, 'rank') or self.rank == 0
            
            # Calculate actual number of iterations based on vectorized size
            vectorized_size = getattr(gun, 'vectorized', 1)
            actual_iterations = int(num) // vectorized_size
            remaining_particles = int(num) % vectorized_size
            
            # Create progress bar with batch size information
            desc = f'Progress (batch_size={vectorized_size}):'
            event_range = tqdm(range(actual_iterations), desc=desc, unit=" batches") if show_progress else range(actual_iterations)
        
            for _ in event_range:
                gun.generate()
                self.l.simOneEvent(False)
            
            # Handle remaining particles if any
            if remaining_particles > 0:
                # Temporarily set vectorized to remaining particles
                original_vectorized = gun.vectorized
                gun.vectorized = remaining_particles
                gun.generate()
                self.l.simOneEvent(False)
                # Restore original vectorized size
                gun.vectorized = original_vectorized

    def gatherHistData(self, cfg, raw=False):
        """
        Collect histogram data from scorer.

        Args:
            cfg: Scorer configuration or name
            raw: Whether to return raw data, defaults to False (uses scorer dictionary)

        Returns:
            Hist: Histogram data object

        Raises:
            KeyError: If no scorer with the given name is registered
        """
        if raw:
            return self.l.getHist(cfg)
        else:
            try:
                return self.l.getHist(self.scorer[cfg])
            except KeyError:
                raise KeyError(f"no scorer named '{cfg}'; registered scorers: {list(self.scorer)}") from None

    def save_all_scorers(self, savepdf=False):
        """
        Save data for all scorers.

        Args:
            savepdf: Whether to also save PDF format images, defaults to False

        Note:
            gatherHistData is called by every rank (it is collective under
            MPI, so gating it would deadlock); only the file writes are
            done on rank 0. Works on plain Prompt (serial) too.
            A scorer whose histogram lookup fails (e.g. a stale registry
            entry left behind by a rejected registration) is skipped with a
            RuntimeWarning instead of aborting the whole save. The registry
            is identical on every rank, so all ranks skip the same names and
            stay collective.
        """
        rank = getattr(self, 'rank', 0)
        for scname in self.scorer:
            try:
                sc_value = self.gatherHistData(scname)
            except Exception as exc:  # keep going: one bad scorer must not
                # discard the results of every other scorer
                warnings.warn(f"skipping scorer '{scname}': could not gather "
                              f"its histogram ({exc})", RuntimeWarning,
                              stacklevel=2)
                continue
            if rank == 0:
                if savepdf:
                    sc_value.savefig(f"{scname}.pdf", log=False)
                sc_value.save(f"{scname}.h5")
                
class PromptMPI(Prompt):
    """
    MPI parallel augmented Prompt.

    Auto-ranking of processes and auto-reduce of histogram data.
    simulateSecondStack runs the power iteration (keff) in parallel: the
    ranks collectively advance one fission chain instead of independent
    ones, exchanging fission banks between cycles. Two exchange schemes
    (bank_exchange=...):

      'nearest' (default): the OpenMC "nearest neighbours" scheme. Every
        rank draws the same sample of source sites against the conceptual
        pooled bank, and only the sites that change owner cross ranks —
        expected O(sqrt(num)) particles per rank, independent of the rank
        count. Derives the exchange sample from the seed argument, which
        must be identical on every rank (the per-rank transport streams
        still differ: each rank is seeded with seed + rank).
      'pooled': an allgather of the raw banks, then each rank resamples its
        share from the pooled bank with the exact serial sampling. Bit-level
        serial statistics per bank state; every rank receives the whole
        bank, O(num) particles per rank.

    Attributes:
        comm: MPI communicator
        rank (int): Current process MPI rank
        size (int): Total number of MPI processes
    """

    def __init__(self, seed=4096, bank_exchange='nearest') -> None:
        """
        Initialize MPI version of Prompt instance.

        Args:
            seed: Initial random seed, each process gets different seed
                (seed + rank). Must be the same on every rank; the parallel
                bank exchange additionally derives its shared sampling from
                this value.
            bank_exchange: 'nearest' (default) or 'pooled', see the class
                docstring

        Raises:
            ImportError: If mpi4py is not available in this environment
            ValueError: On an unknown bank_exchange value
        """
        if bank_exchange not in ('nearest', 'pooled'):
            raise ValueError(f"unknown bank_exchange {bank_exchange!r}; "
                             "expected 'nearest' or 'pooled'")
        self._bank_exchange = bank_exchange
        self._base_seed = int(seed)
        self._keff_cycle = 0
        if MPI is None:
            raise ImportError(
                'PromptMPI requires the mpi4py package, which is not installed '
                'in this python environment; install mpi4py (it needs MPI headers, '
                'e.g. the libopenmpi-dev apt package or conda openmpi/mpi4py) or '
                'use the serial Prompt class instead')
        self._comm = MPI.COMM_WORLD
        self._rank = self._comm.Get_rank()
        self._size = self._comm.Get_size()
        super().__init__(seed + self._rank)

    @property
    def comm(self):
        return self._comm
    
    @property
    def rank(self):
        return self._rank

    @property
    def size(self):
        return self._size

    def simulate(self, gun, num: int = 0, timer=True, save2Disk=False):
        """
        MPI version of simulation method, automatically distributes events to processes.

        Args:
            gun: Particle gun, an instance of class Gun
            num: Total number of events
            timer: Whether to enable timer, defaults to True (timing prints on rank 0 only)
            save2Disk: Whether to save scorers to disk, defaults to False
                (saved on rank 0 only; non-root ranks never save since their
                histograms are reduced to the root rank afterwards)
        """
        batchSize = int(num / self.size)
        if self.rank:
            # non-root ranks never print the timer nor save to disk: their
            # local histograms are reduced to the root rank afterwards
            super().simulate(gun, batchSize, timer=False, save2Disk=False)
        else:
            super().simulate(gun, num - batchSize * (self.size - 1), timer=timer, save2Disk=save2Disk)

    def simulateSecondStack(self, num):
        """MPI version of the power-iteration cycle (parallel keff).

        Every rank transports its share of the source bank (the first
        ``num % size`` ranks take one extra particle, so the pooled source
        is exactly ``num``), then the fission banks are exchanged according
        to bank_exchange and each rank enters the next cycle with its share
        of source sites. This is the same single-chain power iteration the
        serial code runs, with the transport stratified over ranks — the
        bank exchange mirrors what OpenMC calls "synchronizing fission
        bank", in either the nearest-neighbour or the pooled form.

        ``num`` must be at least ``size``: a pooled source smaller than the
        rank count would leave some ranks with an empty share and no
        well-defined place in the chain. ``num`` may change between calls
        (every rank is active on every cycle, so each bank simply
        resamples to the new share of the current chain). ``num`` must be
        identical on every rank, like the call pattern itself.

        Returns:
            The pooled fission-birth count of this cycle. Divide it by the
            total source size per cycle exactly as in the serial loop; the
            per-cycle statistics of all ranks are summed into this number.

        Raises:
            ValueError: if ``num < size`` (or negative).
            RuntimeError: collectively, with the serial
                "secondary stack is empty" wording, if no fission happened
                on any rank this cycle — the same clean stop the serial
                path offers. Also raised collectively when a rank enters
                the iteration with an empty fission bank (run more events
                in simulate() first so every rank banks fissions).
        """
        if self._size == 1:
            # identity path: bit-identical to the serial Prompt, no
            # collective calls, no extra RNG consumption
            return super().simulateSecondStack(num)
        num = int(num)
        if num < self._size:
            raise ValueError(f'parallel power iteration needs num >= size '
                             f'(got num={num}, size={self._size}); a pooled source '
                             'smaller than the rank count has no well-defined '
                             'chain semantics')
        # collective entry guard, before transport: a rank whose fission
        # bank is still empty (its share of the initial simulate() produced
        # no fissions) would throw a rank-local CalcError inside the C++
        # entry and hang the other ranks in the first collective
        empty = 1 if self.l.secondStackSize() <= 12 else 0 # 12 bytes: header-only blob
        if self.comm.allreduce(empty, op=MPI.SUM):
            raise RuntimeError('a rank enters the power iteration with an empty '
                               'fission bank; run more events in simulate() first '
                               'so every rank banks fissions')
        lo, hi = _nn_windows(num, self._size)[self._rank]
        local = hi - lo
        births = self.l.goWithSecondStack(local)
        total = self.comm.allreduce(births, op=MPI.SUM)
        if total == 0:
            # the serial clean stop, raised in lockstep on every rank: the
            # bank is empty everywhere, there is no next cycle
            raise RuntimeError('secondary stack is empty')
        if self._bank_exchange == 'nearest':
            self._exchangeBankNearestNeighbour(num, local)
        else:
            self._exchangeBankPooled(local)
        # drives the shared sampling of the nearest-neighbour exchange;
        # identical across ranks because every rank calls in lockstep
        self._keff_cycle += 1
        return total

    def _exchangeBankPooled(self, local):
        """Allgather the raw banks; resample the local share from the pool.

        Ranks with a zero share sit out: they contribute no blob and touch
        no RNG (a stale bank is harmless, they never transport it)."""
        pool = b''.join(self.comm.allgather(
            self.l.exportSecondStack() if local else b''))
        if local:
            # resample this rank's share from the pooled bank; the next
            # cycle's goWithSecondStack normalise then sees an already
            # correct-sized bank and consumes no further random numbers
            if len(pool) < 12: # all-dead safety net: simulateSecondStack
                # already stops the loop collectively before we get here
                raise RuntimeError('secondary stack is empty')
            self.l.importSecondStack(pool, local)

    def _exchangeBankNearestNeighbour(self, num, local):
        """OpenMC 12.1.2 "Nearest Neighbors Algorithm" bank exchange.

        Instead of gathering the whole pooled bank on every rank, all ranks
        draw the same num indices into the conceptual pooled bank from one
        shared seed and view them sorted — the next cycle's source, in bank
        order. Rank r owns the [lo, hi) slice of that order; most of its
        slice lands inside its own [a, b) bank range (it exported that bank
        above), and only the boundary deviation changes owner. Expected
        exchange volume is O(sqrt(num)) sites at the worst boundary and
        independent of the rank count, versus O(num) per rank for the
        pooled allgather. Every rank derives the same assignment from the
        shared sample, so no request phase is needed; the exchange is one
        allgather of the bank sizes plus one alltoall of the site blobs.
        """
        blob = self.l.exportSecondStack() if local else b''
        # (len - 12) // 84 unpacks the record count of a PKB1 blob; the
        # layout is fixed by BankRecord in PTStackManager.cc
        counts = self.comm.allgather(max(len(blob) - 12, 0) // 84)
        total_bank = sum(counts)
        if total_bank == 0:
            # all-dead safety net: simulateSecondStack already stops the
            # loop collectively before we get here. Keep the bank empty;
            # the literal is the 12-byte empty PKB1 blob (magic + count 0).
            if local:
                self.l.importSecondStack(b'PKB1' + b'\x00' * 8, 0)
            return
        # the shared sample: identical on every rank; sorted, it is the next
        # source in bank order. Sampling with replacement, like OpenMC.
        rng = np.random.default_rng([self._base_seed, self._keff_cycle])
        sample = np.sort(rng.integers(0, total_bank, size=num, dtype=np.int64))
        cum, sends_idx = _nn_send_indices(sample, counts, num, self._size, self._rank)
        sends = [self.l.extractSecondStack(blob, idx) if idx.size else b''
                 for idx in sends_idx]
        recv = self.comm.alltoall(sends)
        # normaliseTo == 0: the slices partition the shared sample, so the
        # bank is already exactly the local share — no resampling, no RNG.
        # Zero-share ranks receive only empty slices and keep their (never
        # transported) bank untouched.
        if local:
            self.l.importSecondStack(b''.join(recv), 0)

    def show(self, gun, num: int = 0, mergeMesh=False, xscale=1.0, yscale=1.0, zscale=1.0, byMat=False, addLegend=False, geoClip=False):
        """
        MPI version of display method, only shows on rank 0 process.
        
        Args:
            gun: Particle gun configuration
            num: Number of particles to display
            mergeMesh: Whether to merge meshes
            xscale, yscale, zscale: Coordinate scaling factors
            byMat: color by material
            addLegend: Add legend
            geoClip: Geometry clipping
        """
        if self.rank == 0:
            self.l.showWorld(gun, num, mergeMesh, xscale, yscale, zscale, byMat, addLegend=addLegend, geoClip=geoClip)
            self.comm.Barrier()
        else:
            self.comm.Barrier()

    def gatherHistData(self, cfg, raw=False, dst=0):
        """
        MPI version of data collection method, aggregates data from all processes to target process.
        
        Args:
            cfg: Scorer configuration
            raw: Whether to use raw configuration
            dst: Target process rank, defaults to 0 (master process)
            
        Returns:
            Hist: Aggregated histogram data
        """
        hist = super().gatherHistData(cfg, raw)
        weight = hist.getWeight()
        hit = hist.getHit()
        ww = hist.getWW()
        print(f'Scorer {cfg} rank {self.rank}: weight {hist.getWeight().sum()}, hit {hist.getHit().sum()}')

        recvw = None
        recvh = None
        recww = None

        if self.rank == dst:  # only create the buffer for rank0
            recvw = np.empty(weight.size, dtype='float')
            recvh = np.empty(hit.size, dtype='float')
            recww = np.empty(ww.size, dtype='float')
        self.comm.Reduce(weight, recvw, op=MPI.SUM, root=dst)
        self.comm.Reduce(hit, recvh, op=MPI.SUM, root=dst)
        self.comm.Reduce(ww, recww, op=MPI.SUM, root=dst)

        if self.rank == dst:
            # The reduced content goes into an independent clone: writing it
            # into the live scorer histogram would corrupt the scorer, so this
            # and every later gather (save_all_scorers re-gathers) would
            # cumulatively inflate the data. The scorer keeps its rank-local
            # content, keeping gathers idempotent.
            if not callable(getattr(hist, 'clone', None)):
                raise RuntimeError(
                    f"the histogram of scorer {cfg!r} provides no clone(): "
                    "the loaded Cinema core library is stale (built before "
                    "pt_HistBase_clone) or the object is not a fresh Hist; "
                    "rebuild the library and rerun the simulation")
            hist2 = hist.clone()
            hist2.setHit(recvh)
            hist2.setWeight(recvw)
            hist2.setWW(recww)
            return hist2
        return hist