#!/usr/bin/env python3
"""
A python-based 3rd-party dependencies management for Prompt, intended to be cross-platform.
"""
import os, sys
import subprocess
from pathlib import Path
import requests
import shutil
import platform
import contextlib

print(f'Pyproject side, using python at: {sys.executable}')

git_domain = "https://code.ihep.ac.cn/cinema-developers/"
# kds_url = "kdsource/-/archive/v0.1.0_prompt/kdsource-v0.1.0_prompt.tar.gz"
gidiplus_url = "gidiplus/-/archive/v3.28.22_prompt/gidiplus-v3.28.22_prompt.tar.gz"
vecgeom_git = "https://code.ihep.ac.cn/caixx/VecGeom.git"
vecgeom_branch = "cinema"

kdsource_git = git_domain+"kdsource.git"
kdsource_branch = "pt"

cpu_count = os.cpu_count()

src_root = Path(__file__).parent.parent.parent.parent
src_build_path = src_root/"build"
externalpath = src_root/"external"
external_src_parent = externalpath/"src"
external_build_path = externalpath/"build"
install_root = externalpath/"install"
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
        print(e.stderr)

ncdir, mcpldir, mcpl_incdir, prefix = config_deps_dir()

def init_external_dir():
    if platform.system() == 'Linux':
        print("Running in", platform.system())
        result_git = subprocess.run(["rm","-rf", "build", "external"], cwd=str(src_root),
                                        capture_output=True, text=True)

def create_folder(path : Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {str(path)}")
    except PermissionError:
        print(f"Permission error when create '{str(path)}'")
    except Exception as e:
        print(f"Not known error: {e}")
    return path

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

    if git_url:
        print("Using git repo: ", git_url)
        try:
            result_git = subprocess.run(["git", "clone", "-b", git_branch, git_url, name], cwd=str(external_src_parent),
                                        check=True, capture_output=True,  text=True)
        except Exception as e:
            print(f"Error messages: ")
            print(e.stderr)
        src_path = external_src_parent/name
    else:
        print("Using url (released pkg): ", url)
        src_path = download_from_url(git_domain, url, external_src_parent)
    return src_path

def install(name, cmakeargs=None, makeargs=None, url=None, git_url=None, git_branch="main"):

    print(f"----------Processing {name} ------------")
    dep_root = download(name, url, git_url, git_branch)

    buildpath = create_folder(external_build_path/name)
    try:
        if not makeargs:
            # print("project uses cmake. ")
            cmd = ["cmake"] + cmakeargs + [str(dep_root)]
            cmd = " ".join(cmd)
            print(f"Running command: {cmd}")
            result = subprocess.run(["cmake"] + cmakeargs + [str(dep_root)], cwd=str(buildpath) ,
                                        check=True, capture_output=True,  text=True)

            result = subprocess.run(["make", f"-j{cpu_count}"], cwd=str(buildpath) ,
                                        check=True, capture_output=True,  text=True)
            result = subprocess.run(["make", "install"], cwd=str(buildpath) ,
                                        check=True, capture_output=True,  text=True)
        elif makeargs and cmakeargs:
            raise TypeError("Only one of cmakeargs and makeargs should be provided.")
        elif makeargs and not cmakeargs:
            cmd = ["make"]+makeargs+[str(dep_root)]
            cmd = " ".join(cmd)
            print(f"Running command: {cmd}")
            result = subprocess.run(["make"]+makeargs, cwd=str(dep_root) , check=True,capture_output=True,  text=True)
        else:
            raise NotImplementedError("Not Implemented.")
    except Exception as e:
        print(f"Error messages: ")
        print(e.stderr)

def prepare_dependencies():
    vecgeom_cmakeargs = [
        f"-DCMAKE_INSTALL_PREFIX={install_root}" ,
        "-DVECGEOM_BUILTIN_VECCORE=ON" ,
        "-DVECGEOM_FAST_MATH=OFF" ,
        "-DBUILD_TESTING=OFF" ,
        "-DVECGEOM_GDML=ON" ,
        "-DVECGEOM_USE_NAVINDEX=ON"
                         ]
    install("vecgeom", cmakeargs=vecgeom_cmakeargs, git_url=vecgeom_git, git_branch=vecgeom_branch)

    kds_cmakeargs = [
        f"-DCMAKE_INSTALL_PREFIX={install_root_kds}", 
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.24", 
        f"-DCMAKE_PREFIX_PATH={prefix}"
        ]
    install("KDSource", cmakeargs=kds_cmakeargs, git_url=kdsource_git, git_branch=kdsource_branch)

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
    install("gidiplus", makeargs=gidiplus_makeargs, url=gidiplus_url)

def copy_sharedlib(pathfrom: Path, pathto: Path):
    pathfrom = pathfrom.resolve()
    pathto = pathto.resolve()
    shutil.copy2(str(pathfrom), str(pathto))

def main_build():
    print(f"----------Processing cinema ------------")
    create_folder(src_build_path)
    lib_path = install_root/"lib"
    veccore_dir = install_root/"lib"/"cmake"/"VecCore"
    veccore_dir_option = install_root/"lib64"/"cmake"/"VecCore"
    cinema_cmakeargs = [
        f"-DCMAKE_PREFIX_PATH={install_root};{prefix}", 
        f"-DKDS_LIB={lib_path}",
        f"-DGIDIPLUS_LIB={lib_path}", 
        f"-DGIDIPLUS_INCDIR={lib_path}", 
        f"-DMCPL_DIR={mcpldir}"
        ]
    try:
        result = subprocess.run(["cmake"]+cinema_cmakeargs+[".."], cwd=str(src_build_path),check=True, capture_output=True,  text=True)
        result = subprocess.run(["make", f"-j{cpu_count}"], cwd=str(src_build_path),check=True, capture_output=True,  text=True)
    except Exception as e:
        print(f"Error messages: ")
        print(e.stderr)

    sharedlib_from = src_build_path/"src"/"cxx"/"libprompt_core.so"
    sharedlib_to = Path("src/python/Cinema")
    copy_sharedlib(sharedlib_from, sharedlib_to)

def main():
    libpath = src_build_path/"src"/"cxx"/"libprompt_core.so"
    # if libpath.exists():
    #     print("Aleary build. Skip. Remove build files to rebuild")
    #     return 0
    try:
        init_external_dir()
        prepare_dependencies()
        main_build()
    except Exception as e:
        print(f"Error messages: ")
        print(e.stderr)

if __name__ == "__main__":
    main()