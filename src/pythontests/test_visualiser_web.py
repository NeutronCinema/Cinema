#!/usr/bin/env python3
"""Web (trame) mode of the Visualiser.

Covers the module-level launch_web_service (serving any pyvista plotter to a
browser), the Visualiser/Prompt web dispatch, and the `prompt -v --web` CLI.
"""

import os
import subprocess
import sys
import time
import urllib.request

import pytest

pyvista = pytest.importorskip('pyvista')
pytest.importorskip('trame')

from Cinema.Prompt import Prompt
from Cinema.Prompt.Visualiser import Visualiser, launch_web_service, stop_web_service
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.solid import Box

GUN_CFG = "gun=MaxwellianGun;src_w=2;src_h=2;src_z=-100;slit_w=2;slit_h=2;slit_z=1e99;temperature=293;"

# standalone twin of _TinySim for the CLI subprocess test
TINY_SIM = '''
from Cinema.Prompt import Prompt
from Cinema.Prompt.geo import Volume, Transformation3D
from Cinema.Prompt.gun import PythonGun
from Cinema.Prompt.solid import Box


class MySim(Prompt):
    def __init__(self, seed=4096):
        super().__init__(seed)
        self.makeWorld()

    def makeWorld(self):
        world = Volume('world', Box(50, 50, 200), 'void.ncmat')
        det = Volume('detector', Box(10, 10, 1))
        world.placeChild('detectorPhy', det, Transformation3D(0, 0, 90))
        self.setWorld(world)


class MyGun(PythonGun):
    def sampleEnergy(self, dummy):
        self.pdata['ekin'] = 0.0253

    def sampleDirection(self, dummy):
        self.pdata['dir'] = [0., 0., 1.]

    def samplePosition(self, dummy):
        self.pdata['pos'] = [0., 0., -100.]
'''


class _TinySim(Prompt):
    def makeWorld(self):
        world = Volume('world', Box(50, 50, 200), 'void.ncmat')
        det = Volume('detector', Box(10, 10, 1))
        world.placeChild('detectorPhy', det, Transformation3D(0, 0, 90))
        self.setWorld(world)


@pytest.mark.forked
def test_launch_web_service_serves_http():
    """A plain plotter is served over HTTP and stops gracefully (block=False)."""
    pl = pyvista.Plotter(off_screen=True)
    pl.add_mesh(pyvista.Sphere())
    server = launch_web_service(pl, mode='client', port=0, open_browser=False, block=False)
    try:
        assert server.port > 0
        with urllib.request.urlopen(f'http://127.0.0.1:{server.port}/index.html', timeout=10) as resp:
            assert resp.status == 200
            assert resp.read()
    finally:
        stop_web_service(server)


@pytest.mark.forked
def test_launch_web_service_idle_timeout():
    """timeout>0: with no browser client ever connecting, the server stops itself."""
    pl = pyvista.Plotter(off_screen=True)
    pl.add_mesh(pyvista.Sphere())
    server = launch_web_service(pl, mode='client', port=0, open_browser=False,
                                block=False, timeout=2)
    port = server.port
    assert port > 0
    # HTTP responses alone do not count as a client; the wslink reaper fires
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/index.html', timeout=10) as resp:
        assert resp.status == 200
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/index.html', timeout=2)
        except OSError:
            return  # port refused: the idle reaper stopped the server
        time.sleep(0.2)
    raise AssertionError('idle timeout did not stop the server')


@pytest.mark.forked
def test_visualiser_web_dispatch(monkeypatch):
    """Prompt.show(web=True) routes to show_web on an off-screen plotter."""
    shown = {}

    def fake_show_web(self, **kwargs):
        shown.update(kwargs)
        assert self.plotter.off_screen  # web mode must not open a desktop window

    monkeypatch.setattr(Visualiser, 'show_web', fake_show_web)

    sim = _TinySim(seed=4096)
    sim.makeWorld()
    sim.show(GUN_CFG, 2, web=True, web_mode='client', web_port=1234,
             web_host='127.0.0.1', web_open_browser=False)

    assert shown['mode'] == 'client'
    assert shown['port'] == 1234
    assert shown['open_browser'] is False


@pytest.mark.forked
def test_prompt_cli_web(tmp_path):
    """`prompt -v --web` serves the visualisation; the printed URL answers 200."""
    sim = tmp_path / 'tiny_sim.py'
    sim.write_text(TINY_SIM)
    import Cinema
    cinema_src = os.path.dirname(os.path.dirname(Cinema.__file__))  # .../src/python
    env = dict(os.environ)
    # the subprocess must import the same Cinema tree as this test, which may
    # not be the first entry of an inherited PYTHONPATH
    env['PYTHONPATH'] = cinema_src + os.pathsep + env.get('PYTHONPATH', '')
    env['PYVISTA_OFF_SCREEN'] = '1'
    env.pop('DISPLAY', None)  # web client mode must not need X
    proc = subprocess.Popen(
        [sys.executable, '-m', 'Cinema.Prompt.cli.promptcli',
         '-g', str(sim), '--gun', 'MyGun', '-n', '3', '-v',
         '--web', '--web-no-browser'],
        cwd=str(tmp_path), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = None
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if 'served at: ' in line:
                url = line.split('served at: ')[1].strip()
                break
        assert url, 'no served URL found in the CLI output'
        with urllib.request.urlopen(url, timeout=10) as resp:
            assert resp.status == 200
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
