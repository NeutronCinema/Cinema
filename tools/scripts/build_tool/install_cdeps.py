#!/usr/bin/env python3
"""
A python-based 3rd-party dependencies management for Prompt, intended to be cross-platform.

Every private-fork dependency is downloaded, built and installed below one
root (see _deps_root()) and nothing outside that root is ever deleted, so
`pip install .` inside a live dev checkout no longer wipes its external/ and
cinemabin/. A dependency whose stamp still matches its pin is skipped; delete
the deps root (or the dependency's stamp file) to force a rebuild.
"""
import os, sys
import subprocess
from pathlib import Path
import requests
import shutil
import platform
import hashlib

print(f'Pyproject side, using python at: {sys.executable}')

git_domain = "https://code.ihep.ac.cn/cinema-developers/"

# The private forks, pinned in one place (conda-forge cannot provide these).
# The keys are the build directory names used by install() below.
PINS = {
    "vecgeom":  {"git_url": "https://code.ihep.ac.cn/caixx/VecGeom.git", "ref": "cinema"},
    "KDSource": {"git_url": git_domain+"kdsource.git", "ref": "pt"},
    "gidiplus": {"url": "gidiplus/-/archive/v3.28.22_prompt/gidiplus-v3.28.22_prompt.tar.gz"},
}

cpu_count = os.cpu_count()

src_root = Path(__file__).parent.parent.parent.parent

def _pins_hash():
    blob = repr(sorted((name, sorted(pin.items())) for name, pin in PINS.items())).encode()
    return hashlib.sha256(blob).hexdigest()[:12]

def _deps_root():
    """Download/build/install root of the compiled private dependencies.

    PROMPT_DEPS_ROOT wins (the conda feedstock points it at its staging area);
    a plain conda build keeps the historical below-checkout external/ layout;
    anything else (i.e. `pip install .` in a dev checkout) builds in a per-pin
    cache directory outside the repository.
    """
    env_root = os.environ.get("PROMPT_DEPS_ROOT")
    if env_root:
        return Path(env_root)
    if os.environ.get("CONDA_BUILD"):
        return src_root/"external"
    cache = os.environ.get("XDG_CACHE_HOME", str(Path.home()/".cache"))
    return Path(cache)/"prompt-deps"/_pins_hash()

externalpath = _deps_root()
external_src_parent = externalpath/"src"
external_build_path = externalpath/"build"
install_root = externalpath/"install"
stamp_dir = externalpath/"stamps"
# the main cinema library is also configured/built inside the deps root, not
# in a build/ directory of the source tree
src_build_path = externalpath/"cinema-build"
print(f"Dependencies root: {externalpath}")

# conda build will only bundle those in $PREFIX
# to include kdsource when using conda build
if os.environ.get("CONDA_BUILD"):
    install_root_kds = os.environ.get("PREFIX")
else:
    install_root_kds = install_root

def download_package(url, save_path):
    dir = Path(save_path)
    dir.mkdir(parents=True, exist_ok=True)
    if platform.system() == 'Linux':
        pkgname = str(url).split("/")[-1]
    else:
        pkgname = None
        raise NotImplementedError("Only support platform Linux.")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(dir/pkgname, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"File downloaded to :{save_path}")
        return str(dir/pkgname)

    except requests.exceptions.RequestException as e:
        print(f"Failed on download: {str(e)}")

def config_deps_dir():
    try:
        result_nc = subprocess.run(["ncrystal-config", "--show", "cmakedir"], check=True, capture_output=True, text=True)
        result_mcpl_lib = subprocess.run(["mcpl-config", "--show", "cmakedir"], check=True, capture_output=True, text=True)
        result_mcpl_incdir = subprocess.run(["mcpl-config", "--show", "includedir"], check=True, capture_output=True, text=True)
        prefix = Path(result_mcpl_incdir.stdout).parent

        return result_nc.stdout, result_mcpl_lib.stdout, result_mcpl_incdir.stdout, prefix

    except Exception as e:
        print(f"Error messages: ")
        print(e)

ncdir, mcpldir, mcpl_incdir, prefix = config_deps_dir()

def create_folder(path : Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {str(path)}")
    except PermissionError:
        print(f"Permission error when create '{str(path)}'")
    except Exception as e:
        print(f"Not known error: {e}")
    return path

def _run(cmd, cwd, what):
    """Run one build command; print the captured output and abort on failure.

    A half-built dependency must not be stamped as done: aborting here is
    much easier to diagnose than a silently reused broken install.
    """
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to {what} (exit {result.returncode}): {' '.join(map(str, cmd))}")
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)
    return result

def download_from_url(git_domain, url, root: Path):
    result = download_package(git_domain+url, save_path=str(externalpath))
    print(f"Download from {git_domain+url} to {result}")
    shutil.unpack_archive(result, str(root))

    extract_upper = Path(result).stem
    extract_upper = Path(extract_upper).stem

    print(str(extract_upper))
    srcpath = root/extract_upper
    return srcpath

def download(name, url=None, git_url=None, git_branch="main"):
    create_folder(external_src_parent)
    src_path = external_src_parent/name

    if git_url:
        if (src_path/".git").exists():
            print(f"Using existing clone at: {src_path}")
        else:
            print("Using git repo: ", git_url)
            _run(["git", "clone", "-b", git_branch, git_url, name], cwd=external_src_parent,
                 what=f"clone {name}")
    else:
        if src_path.exists():
            print(f"Using existing extracted source at: {src_path}")
        else:
            print("Using url (released pkg): ", url)
            src_path = download_from_url(git_domain, url, external_src_parent)
    return src_path

def _stamp_content(name):
    """Identify the exact state of a dependency: its pin plus, for git pins,
    the commit currently checked out in the cached clone."""
    pin = PINS.get(name)
    if pin is None:
        return name
    if "git_url" in pin:
        head = "?"
        repodir = external_src_parent/name
        if (repodir/".git").exists():
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repodir),
                               capture_output=True, text=True)
            head = r.stdout.strip() or "?"
        return f'{pin["git_url"]}@{pin["ref"]}#{head}'
    return git_domain + pin["url"]

def _stamp_matches(name):
    stamp = stamp_dir/f"{name}.stamp"
    return stamp.exists() and stamp.read_text().strip() == _stamp_content(name)

def install(name, cmakeargs=None, makeargs=None, url=None, git_url=None, git_branch="main"):

    if _stamp_matches(name):
        print(f"----------Skipping {name} (up to date, stamp matches pin) ------------")
        return

    print(f"----------Processing {name} ------------")
    dep_root = download(name, url, git_url, git_branch)

    buildpath = create_folder(external_build_path/name)

    if not makeargs:
        cmd = ["cmake"] + cmakeargs + [str(dep_root)]
        print(f"Running command: {' '.join(map(str, cmd))}")
        _run(cmd, cwd=buildpath, what=f"configure {name}")
        _run(["make", f"-j{cpu_count}"], cwd=buildpath, what=f"build {name}")
        _run(["make", "install"], cwd=buildpath, what=f"install {name}")
    elif makeargs and cmakeargs:
        raise TypeError("Only one of cmakeargs and makeargs should be provided.")
    elif makeargs and not cmakeargs:
        cmd = ["make"] + makeargs
        print(f"Running command: {' '.join(map(str, cmd))}")
        _run(cmd, cwd=dep_root, what=f"install {name}")
    else:
        raise NotImplementedError("Not Implemented.")

    stamp_dir.mkdir(parents=True, exist_ok=True)
    (stamp_dir/f"{name}.stamp").write_text(_stamp_content(name) + "\n")

def prepare_dependencies():
    vecgeom_cmakeargs = [
        f"-DCMAKE_INSTALL_PREFIX={install_root}" ,
        "-DVECGEOM_BUILTIN_VECCORE=ON" ,
        "-DVECGEOM_FAST_MATH=OFF" ,
        "-DBUILD_TESTING=OFF" ,
        "-DVECGEOM_GDML=ON" ,
        "-DVECGEOM_USE_NAVINDEX=ON"
                         ]
    install("vecgeom", cmakeargs=vecgeom_cmakeargs,
            git_url=PINS["vecgeom"]["git_url"], git_branch=PINS["vecgeom"]["ref"])

    kds_cmakeargs = [
        f"-DCMAKE_INSTALL_PREFIX={install_root_kds}",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.24",
        f"-DCMAKE_PREFIX_PATH={prefix}"
        ]
    install("KDSource", cmakeargs=kds_cmakeargs,
            git_url=PINS["KDSource"]["git_url"], git_branch=PINS["KDSource"]["ref"])

    # fixme: dynamic SHELL
    gidiplus_makeargs = [
        "-s",
        "install4prompt",
        f"-j{cpu_count//2}",
        'SHELL=bash',
        'CXXFLAGS=-std=c++11 -fPIC',
        'CFLAGS=-fPIC',
        f"INSTALL_PREFIX={install_root}"
        ]
    install("gidiplus", makeargs=gidiplus_makeargs, url=PINS["gidiplus"]["url"])

def copy_sharedlib(pathfrom: Path, pathto: Path):
    pathfrom = pathfrom.resolve()
    pathto = pathto.resolve()
    shutil.copy2(str(pathfrom), str(pathto))

def main_build():
    print(f"----------Processing cinema ------------")
    create_folder(src_build_path)
    lib_path = install_root/"lib"
    cinema_cmakeargs = [
        f"-DCMAKE_PREFIX_PATH={install_root};{prefix}",
        f"-DKDS_LIB={lib_path}",
        f"-DGIDIPLUS_LIB={lib_path}",
        f"-DGIDIPLUS_INCDIR={lib_path}",
        f"-DMCPL_DIR={mcpldir}"
        ]
    _run(["cmake"] + cinema_cmakeargs + [str(src_root)], cwd=src_build_path, what="configure cinema")
    _run(["make", f"-j{cpu_count}"], cwd=src_build_path, what="build cinema")

    # the only intended write into the source tree: the freshly built core
    # library ships inside the wheel (hatch picks up src/python/Cinema/*.so)
    sharedlib_from = src_build_path/"src"/"cxx"/"libprompt_core.so"
    sharedlib_to = src_root/"src"/"python"/"Cinema"
    copy_sharedlib(sharedlib_from, sharedlib_to)

def main():
    prepare_dependencies()
    main_build()

if __name__ == "__main__":
    main()
