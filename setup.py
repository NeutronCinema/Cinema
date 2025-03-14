import glob 
from setuptools import setup, find_packages
import os
import subprocess
from setuptools import Extension, setup
from distutils.command.build import build as _build
from setuptools.command.build_ext import build_ext

class CMakeExtension(Extension):
    def __init__(self, name):
        super().__init__(name, sources=[])

class CMakeBuild(build_ext):

    def run(self):     
        self.copy_shlib_to_proot('libprompt_core')

    def build_cmake_extension(self, ext):
        pass
        # build_temp = os.path.join(self.build_temp, ext.name)
        # subprocess.check_call("bash", "buildscript.sh", cwd=build_temp)
        # print(f'build_temp : {build_temp}')
        # temp = vars(ext)
        # for item in temp:
        #     print(item, ':', temp[item])

        # if not os.path.exists(build_temp):
        #     os.makedirs(build_temp)
            
        # build_temp = os.path.abspath(build_temp)
        # print(f'build_temp: {build_temp}')

        # numcpu = os.cpu_count() - 1
                
        # extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))

        # if not extdir.endswith(os.path.sep):
        #     extdir += os.path.sep

        # if not os.path.exists(os.path.join(build_temp, 'install')):
        #     subprocess.check_call(['mkdir', 'install'] , cwd=build_temp)
        # subprocess.check_call(["cmake", ext.sourcedir] , cwd=build_temp+'/install')
        # subprocess.check_call(['make', '-j'+str(numcpu)] , cwd=build_temp+'/install')
    
    def copy_shlib_to_proot(self, name):
        import os
        from setuptools import find_packages
        if os.getenv('CONDA_BUILD'):
            buildpath = os.path.join(os.getenv('SRC_DIR'))
        pkg = find_packages(where = os.path.join("src", "python"))[0]
        for dir, _, filenames in os.walk(buildpath):
            for files in filenames:
                if files==f'{name}.so':
                    src = os.path.join(dir, files)
                    dest = os.path.join(os.path.abspath('.'), self.build_lib, pkg, files)
                    self.copy_file(src, dest)

class Recorder(_build):
    def run(self):
        self.record_commit_hash()
        super().run()

    def record_commit_hash(self):
        import subprocess
        hash_value = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
        with open('hash.txt', 'w') as f:
            f.write(hash_value)

def package_files(directory):

    dirs = []
    datalist = []
    for (path, directories, filenames) in os.walk(directory):
        datalist.append((os.path.join('/Cinema', path), 
                         [os.path.join(path, f) for f in filenames]))
        print((os.path.join('/Cinema', path), filenames))
    return datalist

datalist = package_files('gdml')

setup(
    
    packages=['Cinema', 
              'Cinema.Interface', 
              'Cinema.Prompt', 
              'Cinema.Prompt.histogram', 
              'Cinema.Experiment', 
              'Cinema.Experiment.Analyser'],

    package_dir={
        'Cinema': os.path.join('.','src','python') + os.path.sep + 'Cinema',
        'Cinema.Experiment': os.path.join('.','src','python') + os.path.sep + os.path.join('Cinema', 'Experiment'),
        'Cinema.Experiment.Analyser': os.path.join('.','src','python') + os.path.sep + os.path.join('Cinema', 'Experiment', 'Analyser'),
        'Cinema.Interface': os.path.join('.','src','python') + os.path.sep + os.path.join('Cinema', 'Interface'),
        'Cinema.Prompt': os.path.join('.','src','python') + os.path.sep + os.path.join('Cinema', 'Prompt'),
        'Cinema.Prompt.histogram': os.path.join('.','src','python') + os.path.sep + os.path.join('Cinema', 'Prompt', 'histogram'),
        },
    
    scripts=[os.path.join('.', 'scripts', 'prompt') ],

    data_files=[
        ('/Cinema/ncmat', glob.glob('./ncmat/*')),
        ('/Cinema/ncmat', glob.glob('./data_ncrystal/data/*')),
        ('/Cinema', glob.glob('./hash*')),
        ('/Cinema/test', glob.glob('./src/pythontests/test_prompt_gun.py')),
        ('/Cinema/test', glob.glob('./src/pythontests/test_prompt.py')),
        ('/Cinema/test', glob.glob('./src/pythontests/test_prompt_scorer.py')),
        ('/Cinema/examples', glob.glob('./scripts/guide.py')),
        ] + datalist,

    # outdated argument: install_requires=['pyvista', 'matplotlib', 'mcpl', 'scipy', 'h5py', 'optuna'],

    ext_modules=[CMakeExtension(name="Cinema")],

    cmdclass={
        'build_ext': CMakeBuild,
        'build': Recorder,
        },
)
