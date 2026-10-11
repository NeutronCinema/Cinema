#!/usr/bin/env python3
# Coverage cluster "cov-py5-lifecycle": Launcher/simulation lifecycle and
# surrounding infrastructure.
#
# Sections:
#   1. clear()/setWorld/simulate round-trips (doc/wiki/simulation-lifecycle.md
#      section 8 pattern) - real simulations, medium tier.
#   2. Seed semantics (applied at setWorld, per-instance offsets under MPI).
#   3. clear() contract on python-side state (registry rebound, volume list kept).
#   4. Prompt/PromptMPI unit level WITHOUT mpirun (monkeypatched dummy MPI).
#   5. ConfigString serialisation round-trips incl. quoting behaviour.
#   6. Prompt/files.py MCPL particle struct layout (closed-form ctypes layout).
#   7. Path resolution helpers (Utils.findData, helper.findDataUnder).
#   8. Prompt/utils.py nccalNumDensity against crystallographic closed forms.
#   9. parameterOptimizer with the installed optuna (storage semantics,
#      deprecation/value errors, small quadratic mini-optimizations).
#
# The real-simulation tests follow the minimal world of
# test_prompt_clean_world.py (void world + detector with a WlSpectrum scorer)
# so its pinned hit array doubles as an independent reference here.

import ctypes
import pickle
import warnings

import numpy as np
import pytest

from Cinema.Prompt import promptCore as promptCore_mod
from Cinema.Prompt.configstr import ConfigString
from Cinema.Prompt.files import MCPLParticle
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.parameterOptimizer import Optimiser, Parameter
from Cinema.Prompt.promptCore import Prompt, PromptMPI
from Cinema.Prompt.scorer import WlSpectrum
from Cinema.Prompt.solid import Box
from Cinema.Interface import helper as interface_helper
from Cinema.Interface import Utils as interface_utils


# --------------------------------------------------------------- shared bits

_SENTINEL = object()  # volume_list ownership probe for the fast clear() test

GUN_CFG = ("gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;"
           "slit_w=2;slit_h=2;slit_z=1e99;temperature=293;")

# Independent reference: pinned by test_prompt_clean_world.py for the same
# seed (4096), geometry and 1e4 MaxwellianGun events.
EXPECTED_WL_HITS = [419., 447., 452., 477., 436., 444., 395., 386., 349., 316.,
                    302., 290., 294., 250., 235., 199., 220., 179., 162., 143.]

# The exact cfg string the C++ side receives for the WlSpectrum scorer below
# (insertion order of the ConfigString keys).
WAVELENGTH_SCORER_CFG = ('Scorer=WlSpectrum;name=WavelengthSp;'
                         'min=1;max=2;numbin=20;ptstate=ENTRY;')


class _WorldMixin:
    """The minimal documented world: void box + detector with a WL scorer."""

    def makeWorld(self):
        world = Volume('world', Box(50, 50, 200), 'void.ncmat')
        dtt = Volume('detector', Box(10, 10, 1))
        scorer = WlSpectrum()
        scorer.cfg_name = 'WavelengthSp'
        scorer.cfg_min = 1
        scorer.cfg_max = 2
        scorer.cfg_numbin = 20
        dtt.addScorer(scorer)
        world.placeChild('detectorPhy', dtt, Transformation3D(0, 0, 90))
        self.setWorld(world)


class ScanSim(_WorldMixin, Prompt):
    pass


class ScanSimMPI(_WorldMixin, PromptMPI):
    pass


def _build_run_gather(sim, num=10000):
    # doc section 8 scan-loop step: makeWorld (rebuilds + applies the seed via
    # setWorld), simulate, gather
    sim.makeWorld()
    sim.simulate(GUN_CFG, int(num))
    return sim.gatherHistData('WavelengthSp').getHit().copy()


# ===========================================================================
# 1. clear()/setWorld/simulate round-trips (doc section 8), real simulations
# ===========================================================================

@pytest.mark.medium  # first world build in the process (~0.3 s) dominates
def test_clear_rebuild_same_seed_identical_histogram():
    # doc section 8 canonical scan loop: clear -> makeWorld -> simulate ->
    # gather, twice in one process. The scorer histogram must be bit-identical
    # for the same seed, and equal to the independent reference array.
    sim = ScanSim(seed=4096)
    h1 = _build_run_gather(sim)
    np.testing.assert_array_equal(h1, EXPECTED_WL_HITS)
    assert h1.sum() == 6395  # every reference entry is an integer hit count

    # doc gotcha: the python-side ownership list is never cleared, neither by
    # builds nor by clear()
    n_before = len(Volume.volume_list)
    assert n_before >= 2  # world + detector from the first build

    sim.clear()
    h2 = _build_run_gather(sim)
    np.testing.assert_array_equal(h1, h2)
    assert len(Volume.volume_list) == n_before + 2  # second build appended

    sim.clear()  # documented hygiene: no world left for the next test


@pytest.mark.medium
def test_seed_is_applied_at_setworld(capfd):
    # The seed is applied by setWorld (not at construction): each build prints
    # exactly one "set random seed: <seed>" line, twice after a clear() cycle.
    # The line comes from C++ printf, so fd-level capture (capfd) is needed.
    sim = ScanSim(seed=4096)
    _build_run_gather(sim)
    sim.clear()
    _build_run_gather(sim)
    out = capfd.readouterr().out
    assert out.count('set random seed:') == 2
    assert out.count('set random seed: 4096') == 2
    sim.clear()  # documented hygiene: no world left for the next test


@pytest.mark.medium
def test_same_seed_new_instance_identical_histogram():
    # A brand-new Prompt instance (shared Launcher singleton) with the same
    # seed reproduces the histogram exactly after a clear() handover.
    sim1 = ScanSim(seed=4096)
    h1 = _build_run_gather(sim1)
    sim1.clear()

    sim2 = ScanSim(seed=4096)
    h2 = _build_run_gather(sim2)
    np.testing.assert_array_equal(h1, h2)
    np.testing.assert_array_equal(h2, EXPECTED_WL_HITS)
    sim2.clear()  # documented hygiene: no world left for the next test


@pytest.mark.medium
def test_different_seed_different_histogram():
    # Seeds are applied at setWorld: a different seed must move every statistical
    # quantity (here: the hit array and its total), otherwise the seed plumbing
    # is dead. The total is a deterministic integer for this build.
    sim = ScanSim(seed=4096)
    h1 = _build_run_gather(sim)
    sim.clear()

    sim_b = ScanSim(seed=4097)
    h2 = _build_run_gather(sim_b)
    assert not np.array_equal(h1, h2)
    assert h1.sum() == 6395
    assert h2.sum() == 6501
    sim_b.clear()  # documented hygiene: no world left for the next test


@pytest.mark.medium
def test_promptmpi_real_single_rank_end_to_end():
    # PromptMPI outside mpirun is rank 0 of a 1-rank COMM_WORLD; the reduce in
    # gatherHistData must be the identity and the physics must match the serial
    # reference (same seed -> same histogram).
    pytest.importorskip('mpi4py')
    sim = ScanSimMPI(seed=4096)
    assert sim.rank == 0
    assert sim.size == 1
    h = _build_run_gather(sim)
    np.testing.assert_array_equal(h, EXPECTED_WL_HITS)
    sim.clear()  # documented hygiene: no world left for the next test


# ===========================================================================
# 2. clear() contract on python-side state (fast, no world needed)
# ===========================================================================

def test_clear_resets_documented_python_state():
    # doc section 8: clear() empties the scorer registry (rebinds a fresh
    # dict), re-allows setWorld, and deliberately keeps Volume.volume_list.
    # (Pure-python state only: the real-geometry variant of the volume_list
    # check runs in test_clear_rebuild_same_seed_identical_histogram.)
    sim = Prompt(seed=1)
    Volume.volume_list.append(_SENTINEL)
    old_registry = Volume.scorer_dict
    old_registry['stale'] = 'cfg'
    try:
        sim.clear()

        assert sim.l.worldExist is False
        assert Volume.scorer_dict == {}          # emptied...
        assert Volume.scorer_dict is not old_registry  # ...by rebinding
        assert _SENTINEL in Volume.volume_list   # ownership list kept
    finally:
        if _SENTINEL in Volume.volume_list:
            Volume.volume_list.remove(_SENTINEL)


def test_scorer_property_tracks_the_registry():
    sim = Prompt(seed=1)
    assert sim.scorer is Volume.scorer_dict
    Volume.scorer_dict['X'] = 'cfg'
    assert sim.scorer['X'] == 'cfg'
    del Volume.scorer_dict['X']


# ===========================================================================
# 3. Prompt units (fast)
# ===========================================================================

def test_prompt_construction_contracts():
    sim = Prompt()
    assert sim.seed == 4096  # documented default
    assert Prompt(seed=7).seed == 7
    with pytest.raises(NotImplementedError):
        sim.makeWorld()
    with pytest.raises(AttributeError):
        sim.seed = 1234  # read-only property
    with pytest.raises(AttributeError):
        sim.l = None      # read-only property


def test_second_prompt_shares_launcher_singleton():
    first = Prompt(seed=1)
    second = Prompt(seed=2)
    assert second.l is first.l


def test_scorer_name_config_duplicate_handling():
    sim = Prompt(seed=1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        assert sim.scorerNameConfig('brand_new') is None
        assert caught == []
    sim.scorer['taken'] = 'cfg'
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        assert sim.scorerNameConfig('taken') == 'taken`'
        assert len(caught) == 1
        assert 'Duplicated scorer name taken' in str(caught[0].message)
    del sim.scorer['taken']


# ===========================================================================
# 4. PromptMPI unit level WITHOUT mpirun (dummy MPI / real 1-rank comm)
# ===========================================================================

class _FakeMPI:
    """Stand-in for the mpi4py module; SUM is a sentinel identity token."""
    SUM = 'SUM'

    def __init__(self, comm):
        self.COMM_WORLD = comm


class _ReduceBus:
    """Lets two fake ranks 'meet' inside single-threaded Reduce calls.

    Non-root contributions are queued; each root call consumes exactly one
    queued buffer (FIFO) and sums it with its own - the exact semantics of a
    2-rank MPI.Sum reduce.
    """

    def __init__(self):
        self.pending = []

    def reduce(self, comm, sendbuf, recvbuf, op, root):
        if recvbuf is None:
            self.pending.append(np.asarray(sendbuf, dtype=float).copy())
        else:
            total = np.asarray(sendbuf, dtype=float).copy()
            if self.pending:
                total = total + self.pending.pop(0)
            np.asarray(recvbuf)[...] = total


class _FakeComm:
    def __init__(self, rank, size, bus=None):
        self._rank = rank
        self._size = size
        self.bus = bus
        self.barriers = 0
        self.reduce_calls = []

    def Get_rank(self):
        return self._rank

    def Get_size(self):
        return self._size

    def Barrier(self):
        self.barriers += 1

    def Reduce(self, sendbuf, recvbuf, op=None, root=0):
        self.reduce_calls.append({'has_recvbuf': recvbuf is not None,
                                  'op': op, 'root': root})
        if self.bus is not None:
            self.bus.reduce(self, sendbuf, recvbuf, op, root)


class _FakeHist:
    def __init__(self, weight, hit, ww):
        self.weight = np.asarray(weight, dtype=float)
        self.hit = np.asarray(hit, dtype=float)
        self.ww = np.asarray(ww, dtype=float)
        self.set_calls = []

    def getWeight(self):
        return self.weight

    def getHit(self):
        return self.hit

    def getWW(self):
        return self.ww

    def setWeight(self, w):
        self.weight = np.asarray(w, dtype=float)
        self.set_calls.append('weight')

    def setHit(self, h):
        self.hit = np.asarray(h, dtype=float)
        self.set_calls.append('hit')

    def setWW(self, w):
        self.ww = np.asarray(w, dtype=float)
        self.set_calls.append('ww')

    def clone(self):
        # PromptMPI.gatherHistData writes the reduced content into an
        # independent clone (fix wave 2), so the fake must clone like the
        # real Hist: fresh object, copied arrays, empty setter log.
        # type(self) keeps subclass behaviour (e.g. _SavingHist.save).
        return type(self)(self.weight.copy(), self.hit.copy(), self.ww.copy())


def _fake_mpi_promptmpi(monkeypatch, rank, size, bus=None):
    comm = _FakeComm(rank, size, bus)
    monkeypatch.setattr(promptCore_mod, 'MPI', _FakeMPI(comm))
    return promptCore_mod.PromptMPI(seed=100), comm


def test_promptmpi_real_comm_properties_outside_mpirun():
    pytest.importorskip('mpi4py')
    from mpi4py import MPI
    sim = PromptMPI(seed=7)
    assert sim.rank == 0
    assert sim.size == 1
    assert sim.comm is MPI.COMM_WORLD
    assert sim.seed == 7  # no offset on rank 0


def test_promptmpi_seed_offset_and_properties_with_fake_ranks(monkeypatch):
    sim, comm = _fake_mpi_promptmpi(monkeypatch, rank=3, size=8)
    assert sim.rank == 3
    assert sim.size == 8
    assert sim.comm is comm
    assert sim.seed == 103  # documented seed + rank offset


@pytest.mark.parametrize('num,size', [(103, 4), (100, 3), (7, 8), (9, 9)])
def test_promptmpi_simulate_event_split_by_rank(monkeypatch, num, size):
    # closed form of the documented split: batch = int(num/size) on non-root
    # ranks (timer/save2Disk forced off), remainder on the root rank.
    batch = int(num / size)
    expected_root = num - batch * (size - 1)
    recorded = {}

    def fake_simulate(self, gun, num=0, timer=True, save2Disk=False):
        recorded.update(num=num, timer=timer, save2Disk=save2Disk)

    monkeypatch.setattr(Prompt, 'simulate', fake_simulate)

    _sim, _ = _fake_mpi_promptmpi(monkeypatch, rank=1, size=size)
    PromptMPI.simulate(_sim, 'gun', num)
    assert recorded == {'num': batch, 'timer': False, 'save2Disk': False}

    recorded.clear()
    _sim0, _ = _fake_mpi_promptmpi(monkeypatch, rank=0, size=size)
    PromptMPI.simulate(_sim0, 'gun', num, timer=False, save2Disk=True)
    assert recorded == {'num': expected_root, 'timer': False,
                        'save2Disk': True}


def test_promptmpi_show_only_on_root_rank(monkeypatch):
    shown = []

    def fake_showworld(self, gun, particles=None, mergeMesh=False, xscale=1.0,
                       yscale=1.0, zscale=1.0, byMat=False, addLegend=False,
                       geoClip=False):
        shown.append((gun, particles))

    monkeypatch.setattr(type(Prompt(seed=1).l), 'showWorld', fake_showworld)

    sim0, comm0 = _fake_mpi_promptmpi(monkeypatch, rank=0, size=2)
    sim0.show('gun;', 5)
    assert shown == [('gun;', 5)]
    assert comm0.barriers == 1  # root barriers *after* showing

    shown.clear()
    sim1, comm1 = _fake_mpi_promptmpi(monkeypatch, rank=1, size=2)
    sim1.show('gun;', 5)
    assert shown == []
    assert comm1.barriers == 1  # non-root only joins the barrier


def test_promptmpi_gather_one_real_rank_is_identity(monkeypatch):
    # with the real mpi4py COMM_WORLD (1 rank) the three SUM reduces must be
    # the identity: buffers come back exactly as they were sent.
    pytest.importorskip('mpi4py')
    hist = _FakeHist([1., 2., 3.], [4., 5., 6.], [0., 0.25, 0.5])
    monkeypatch.setattr(Prompt, 'gatherHistData', lambda self, cfg, raw=False: hist)
    sim = PromptMPI(seed=1)
    out = sim.gatherHistData('S')
    np.testing.assert_array_equal(out.getWeight(), [1., 2., 3.])
    np.testing.assert_array_equal(out.getHit(), [4., 5., 6.])
    np.testing.assert_array_equal(out.getWW(), [0., 0.25, 0.5])
    # root returns an independent clone: the setters write the reduced content
    # into the clone (documented setter order), the original stays untouched —
    # that untouched original is what keeps repeated gathers idempotent.
    assert out.set_calls == ['hit', 'weight', 'ww']
    assert hist.set_calls == []


def test_promptmpi_gather_two_fake_ranks_sum_into_root(monkeypatch):
    bus = _ReduceBus()
    hist0 = _FakeHist([1., 2.], [3., 4.], [0.5, 0.5])
    hist1 = _FakeHist([10., 20.], [30., 40.], [1.5, 2.5])
    monkeypatch.setattr(Prompt, 'gatherHistData',
                        lambda self, cfg, raw=False: hist0 if self.rank == 0 else hist1)

    sim1, comm1 = _fake_mpi_promptmpi(monkeypatch, rank=1, size=2, bus=bus)
    out1 = sim1.gatherHistData('S')

    sim0, comm0 = _fake_mpi_promptmpi(monkeypatch, rank=0, size=2, bus=bus)
    out0 = sim0.gatherHistData('S')

    # root owns the reduced (summed) histograms
    np.testing.assert_array_equal(out0.getWeight(), [11., 22.])
    np.testing.assert_array_equal(out0.getHit(), [33., 44.])
    np.testing.assert_array_equal(out0.getWW(), [2.0, 3.0])
    assert out0.set_calls == ['hit', 'weight', 'ww']

    # non-root rank gets its local histogram back untouched
    np.testing.assert_array_equal(out1.getWeight(), [10., 20.])
    assert out1.set_calls == []

    # exactly three SUM reduces towards root 0 on each side
    assert len(comm0.reduce_calls) == 3
    assert len(comm1.reduce_calls) == 3
    for call in comm0.reduce_calls:
        assert call['has_recvbuf'] is True
        assert call['op'] == promptCore_mod.MPI.SUM
        assert call['root'] == 0
    for call in comm1.reduce_calls:
        assert call['has_recvbuf'] is False


def test_promptmpi_save_all_scorers_writes_only_on_root(monkeypatch):
    saved = []

    class _SavingHist(_FakeHist):
        def save(self, fname):
            saved.append(fname)

        def savefig(self, fname, log=False):
            saved.append(fname)

    monkeypatch.setattr(Volume, 'scorer_dict', {'S1': 'cfg1'})
    monkeypatch.setattr(type(Prompt(seed=1).l), 'getHist',
                        lambda self, cfg: _SavingHist([1.], [1.], [1.]))

    sim1, _ = _fake_mpi_promptmpi(monkeypatch, rank=1, size=2)
    sim1.save_all_scorers()
    assert saved == []  # non-root never writes

    sim0, _ = _fake_mpi_promptmpi(monkeypatch, rank=0, size=2)
    sim0.save_all_scorers(savepdf=True)
    assert saved == ['S1.pdf', 'S1.h5']  # gather per scorer, files on root only


# ===========================================================================
# 5. ConfigString serialisation round-trips
# ===========================================================================

def _reference_parse(cfg):
    """Independent cfg-string reader: split on ';', then on the first '='."""
    items = {}
    for chunk in cfg.split(';'):
        if not chunk:
            continue
        key, _, value = chunk.partition('=')
        items[key] = value
    return items


def test_configstring_serialisation_types_and_order():
    # values are str()'d verbatim, keys keep insertion order
    cs = ConfigString()
    cs.cfg_f = 1.5
    cs.cfg_i = -3
    cs.cfg_b = True
    cs.cfg_s = 'txt'
    assert cs.makeCfg() == 'f=1.5;i=-3;b=True;s=txt;'
    assert cs.cfg == cs.makeCfg()
    assert ConfigString().makeCfg() == ''


def test_configstring_values_pass_through_unescaped():
    # there is NO quoting/escaping: '=', ';' and spaces inside a value reach
    # the serialised string verbatim (callers must avoid such characters).
    cs = ConfigString()
    cs.cfg_k = 'x=1;foo'
    cs.cfg_p = 'a b'
    cs.cfg_e = ''
    assert cs.makeCfg() == 'k=x=1;foo;p=a b;e=;'
    # the ambiguity is real: a reference parser reads five items, not two
    assert _reference_parse(cs.makeCfg()) == {
        'k': 'x=1', 'foo': '', 'p': 'a b', 'e': ''}


def test_configstring_reference_parser_roundtrip():
    # serialise -> independent parse -> same key/value pairs
    cs = ConfigString()
    cs.cfg_name = 'WavelengthSp'
    cs.cfg_min = 1
    cs.cfg_numbin = 20
    parsed = _reference_parse(cs.makeCfg())
    assert parsed == {'name': 'WavelengthSp', 'min': '1', 'numbin': '20'}
    # the cfg actually handed to C++ for the scorer built in this file
    assert _reference_parse(WAVELENGTH_SCORER_CFG) == {
        'Scorer': 'WlSpectrum', 'name': 'WavelengthSp', 'min': '1',
        'max': '2', 'numbin': '20', 'ptstate': 'ENTRY'}


def test_configstring_any_key_containing_cfg_prefix_is_serialised():
    # the filter is a substring test, and str.replace strips EVERY 'cfg_'
    cs = ConfigString()
    cs.xcfg_mode = 1        # contains 'cfg_' inside the key
    cs.cfg_cfg_a = 2        # both occurrences stripped
    assert cs.makeCfg() == 'xmode=1;a=2;'


def test_configstring_pickle_roundtrip():
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    cs.cfg_value = 100
    cs2 = pickle.loads(pickle.dumps(cs))
    assert cs2 == cs
    assert cs2.makeCfg() == 'name=quantity;value=100;'


def test_configstring_delattr_removes_item():
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    cs.cfg_value = 100
    del cs.cfg_value
    assert 'cfg_value' not in cs
    assert not hasattr(cs, 'cfg_value')
    assert cs.makeCfg() == 'name=quantity;'


def test_configstring_cfg_assignment_is_shadowed_by_property():
    # footgun pin: 'cs.cfg = x' stores a dict item that the cfg property
    # (computed string) keeps shadowing on read
    cs = ConfigString()
    cs.cfg_name = 'quantity'
    cs.cfg = 'raw'
    assert cs['cfg'] == 'raw'
    assert cs.cfg == 'name=quantity;'  # still the property, not 'raw'


# ===========================================================================
# 6. Prompt/files.py: MCPL particle struct layout (closed form)
# ===========================================================================

def test_mcpl_particle_struct_layout():
    # pins the MCPLParticle layout in files.py, which must mirror the packed
    # mcpl.h mcpl_particle_t exactly (#pragma pack(1)): 12 float64 (96 B),
    # int32 pdgcode at 96, uint32 userflags at 100, sizeof 104. The C++
    # writer memcpy's sizeof(mcpl_particle_t) == 104 bytes from this struct
    # into the file, so any drift here corrupts or truncates the written
    # particle (the former c_uint64 userflags at 104 sat OUTSIDE the 104-B
    # window and userflags never reached the file).
    expected = [
        ('ekin', 0), ('polarisation_x', 8), ('polarisation_y', 16),
        ('polarisation_z', 24), ('position_x', 32), ('position_y', 40),
        ('position_z', 48), ('direction_x', 56), ('direction_y', 64),
        ('direction_z', 72), ('time', 80), ('weight', 88),
        ('pdgcode', 96), ('userflags', 100)]
    names = [name for name, _ in MCPLParticle._fields_]
    assert names == [name for name, _ in expected]
    for name, offset in expected:
        assert getattr(MCPLParticle, name).offset == offset
    assert ctypes.sizeof(MCPLParticle) == 104
    field_types = dict(MCPLParticle._fields_)
    assert field_types['ekin'] is ctypes.c_double
    assert field_types['pdgcode'] is ctypes.c_int32
    assert field_types['userflags'] is ctypes.c_uint32


# ===========================================================================
# 7. Path resolution helpers
# ===========================================================================

def test_find_data_resolves_under_cinemapath(tmp_path, monkeypatch):
    monkeypatch.setenv('CINEMAPATH', str(tmp_path))
    (tmp_path / 'data' / 'Al').mkdir(parents=True)
    target = tmp_path / 'data' / 'Al' / 'cell.json'
    target.write_text('{}')

    assert interface_utils.findData('Al/cell.json') == str(target)

    # a second copy in a nested subdir of the material dir is ambiguous (the
    # lookup walks recursively, but only under data/<material>/)
    (tmp_path / 'data' / 'Al' / 'nested').mkdir()
    (tmp_path / 'data' / 'Al' / 'nested' / 'cell.json').write_text('{}')
    with pytest.raises(RuntimeError, match='2 Al/cell.json files found'):
        interface_utils.findData('Al/cell.json')

    (tmp_path / 'data' / 'Al' / 'nested' / 'cell.json').unlink()
    (tmp_path / 'data' / 'Al' / 'cell.json').unlink()
    with pytest.raises(RuntimeError, match='0 Al/cell.json files found'):
        interface_utils.findData('Al/cell.json')


def test_find_data_custom_directory_argument(tmp_path, monkeypatch):
    monkeypatch.setenv('CINEMAPATH', str(tmp_path))
    (tmp_path / 'other' / 'Fe').mkdir(parents=True)
    target = tmp_path / 'other' / 'Fe' / 'x.json'
    target.write_text('{}')
    assert interface_utils.findData('Fe/x.json', dir='other') == str(target)


def test_find_data_under_takpath_prefix(tmp_path, monkeypatch):
    # the non-absPath branch resolves against $TAKPATH + <path>
    monkeypatch.setenv('TAKPATH', str(tmp_path))
    (tmp_path / 'sub' / 'deeper').mkdir(parents=True)
    target = tmp_path / 'sub' / 'deeper' / 'needle.dat'
    target.write_text('x')
    assert interface_helper.findDataUnder('needle.dat', '/sub/deeper') \
        == str(target)
    with pytest.raises(FileNotFoundError):
        interface_helper.findDataUnder('missing.dat', '/sub')


# ===========================================================================
# 8. Prompt/utils.py: nccalNumDensity
# ===========================================================================

AVOGADRO = 6.02214076e23


def test_nccal_num_density_al_from_cell_geometry():
    from Cinema.Prompt.utils import nccalNumDensity
    nd = nccalNumDensity('Al_sg225.ncmat')
    # regression anchor for the installed physics stack
    assert nd == pytest.approx(6.023238256131623e19)
    # closed form: Al_sg225.ncmat declares an FCC cell a=4.04958 A with 4
    # atoms/cell (8 corners*1/8 + 6 faces*1/2) -> n = 4/a^3, reported per mm^3
    closed_form = 4.0 / 4.04958**3 * 1e21
    assert nd == pytest.approx(closed_form, rel=1e-4)


def test_nccal_num_density_water_counts_atoms_not_molecules():
    from Cinema.Prompt.utils import nccalNumDensity
    nd = nccalNumDensity('LiquidWaterH2O_T293.6K.ncmat')
    # regression anchor for the installed physics stack
    assert nd == pytest.approx(1.0010350313492967e20)
    # closed form: @DENSITY 0.99820 g/cm^3, H2O 18.01528 g/mol, 3 atoms each
    closed_form = 0.99820 / 18.01528 * AVOGADRO * 3 * 1e-3  # /cm^3 -> /mm^3
    assert nd == pytest.approx(closed_form, rel=1e-3)


# ===========================================================================
# 9. parameterOptimizer with the installed optuna
# ===========================================================================

class _FakeTrial:
    def __init__(self):
        self.calls = []
        self.next = 0.25

    def suggest_float(self, name, low, high):
        self.calls.append((name, low, high))
        return self.next


def test_parameter_range_validation():
    p = Parameter('x', -1.0, 1.0, 0.5)
    assert (p.name, p.lower_lim, p.upper_lim, p.promptval) == \
        ('x', -1.0, 1.0, 0.5)
    with pytest.raises(RuntimeError, match='not in the range'):
        Parameter('x', -1.0, 1.0, 2.0)
    with pytest.raises(RuntimeError, match='not in the range'):
        Parameter('x', -1.0, 1.0, -2.0)
    with pytest.raises(RuntimeError, match='wrong parameter range'):
        Parameter('x', 1.0, 1.0, 1.0)  # lower == upper
    # error precedence: with lower > upper the range check fires first for
    # every possible prompt value
    with pytest.raises(RuntimeError, match='not in the range'):
        Parameter('x', 2.0, 1.0, 1.5)  # lower > upper


def test_parameter_get_with_and_without_trial():
    p = Parameter('x', -1.0, 1.0, 0.5)
    assert p.get() == 0.5
    assert p.get(None) == 0.5  # falsy trail falls back to the prompt value
    trial = _FakeTrial()
    assert p.get(trial) == 0.25
    assert trial.calls == [('x', -1.0, 1.0)]


def test_optimiser_addparameter_midpoint_and_getparameters():
    opt = Optimiser(sim=None)
    opt.addParameter('x', -2.0, 4.0)          # default prompt value: midpoint
    opt.addParameter('y', 0.0, 1.0, val=0.75)
    assert opt.parameters[0].promptval == 1.0
    assert opt.getParameters() == {'x': 1.0, 'y': 0.75}

    trial = _FakeTrial()
    got = opt.getParameters(trial)
    assert got == {'x': 0.25, 'y': 0.25}
    assert trial.calls == [('x', -2.0, 4.0), ('y', 0.0, 1.0)]


@pytest.mark.medium  # optuna import in the forked process
def test_optimize_without_storage_names_removed_mysql_default():
    opt = Optimiser(sim=None)
    with pytest.raises(ValueError, match='no optuna storage given') as ei:
        opt.optimize(name='cov_study', n_trials=1)
    # the error must explain both the security removal and the escape hatches
    assert 'remote-MySQL' in str(ei.value)
    assert 'sqlite:///optuna_study.db' in str(ei.value)
    assert 'localhost=True' in str(ei.value)


class _Quadratic(Optimiser):
    """f(x) = x^2 with a deliberately non-optimal prompt value: if the
    optuna plumbing stopped feeding suggestions into the objective, the best
    value would stick at 0.25 and the convergence assertions below would
    fail."""

    def __init__(self):
        super().__init__(sim=None, directions=['minimize'])
        self.addParameter('x', -0.5, 0.5, val=0.5)

    def objective(self, trial):
        params = self.getParameters(trial)
        return params['x'] ** 2


@pytest.mark.medium  # optuna import + 5 in-memory trials
def test_optimize_inmemory_quadratic_converges():
    opt = _Quadratic()
    with pytest.warns(FutureWarning, match='localhost is deprecated'):
        study = opt.optimize(name='cov_quad_inmem', n_trials=5, localhost=True)
    assert study is opt.study
    assert study.study_name == 'cov_quad_inmem'
    assert len(study.trials) == 5
    assert str(study.direction) == 'StudyDirection.MINIMIZE'
    # loose convergence threshold: broken suggestion plumbing would stick at
    # the prompt value (f = 0.25); genuine 5-point search stays far below
    assert study.best_value < 0.15
    assert abs(study.best_params['x']) < 0.39


@pytest.mark.slow  # sqlite journal fsync dominates: ~0.75 s body even with
# only 4 trials, above the 0.7 s medium ceiling
def test_optimize_sqlite_persists_and_reload_accumulates(tmp_path):
    import optuna
    dbfile = tmp_path / 'study.db'
    url = f'sqlite:///{dbfile}'

    opt = _Quadratic()
    study = opt.optimize(name='cov_quad_sqlite', n_trials=4, storage=url)
    assert dbfile.exists() and dbfile.stat().st_size > 0
    assert len(study.trials) == 4
    assert study.best_value < 0.2  # broken plumbing would stay at 0.25

    # load_if_exists=True: reopening the same study on the same storage must
    # not raise (n_trials=0 keeps this cheap - the 5-trial convergence pin
    # lives in the in-memory test above)
    opt2 = _Quadratic()
    study2 = opt2.optimize(name='cov_quad_sqlite', n_trials=0, storage=url)
    assert len(study2.trials) == 4
    assert study2.best_value == pytest.approx(study.best_value)

    # the storage is readable without any Cinema object (analysisdb path)
    reloaded = optuna.load_study(study_name='cov_quad_sqlite', storage=url)
    assert len(reloaded.trials) == 4


@pytest.mark.medium  # sqlite study creation + 3 trials, ~0.6 s body
def test_optimize_storage_wins_over_deprecated_localhost_flag(tmp_path):
    dbfile = tmp_path / 'combo.db'
    opt = _Quadratic()
    with pytest.warns(FutureWarning, match='localhost is deprecated'):
        study = opt.optimize(name='cov_quad_combo', n_trials=3,
                             localhost=True, storage=f'sqlite:///{dbfile}')
    # the explicit storage URL is honoured even with the deprecated flag set
    # (no convergence pin here: covered by the in-memory and sqlite tests)
    assert dbfile.exists()
    assert len(study.trials) == 3
