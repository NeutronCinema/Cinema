#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI, Launcher, Visualiser
from Cinema.Prompt.gun import Gun
import argparse
import inspect
import importlib.util
from Cinema.Interface.Utils import findData
import os
import sys
from typing import Dict, Any, Type, Optional, List, Set, get_type_hints, Union, TypeVar

T = TypeVar('T')

def str_or_float(value: str):
    import re
    quote_match = re.match(r'^["\'](.*)["\']$', value)
    if quote_match:
        return quote_match.group(1)
    else:
        try:
            return float(value)
        except ValueError:
            return value

def load_module_from_file(file_path: str):
    spec = importlib.util.spec_from_file_location("module.name", file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import file: {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_classes_from_module(module):
    return {
        name: obj for name, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__ == module.__name__
    }

def get_classes_from_filepath(pyScriptPath : str):
    """Get classes defined in a `.py` file located at path

    Parameters
    ----------
    pyScriptPath : str
        Simulation definition Python script.
    """
    
    module = load_module_from_file(pyScriptPath)
    if module is None:
        raise ValueError(f"Cannot load file: {pyScriptPath}")
    
    classes = get_classes_from_module(module)
    return classes

def get_classes_from_base_class(targetClass : Type[T], classes : dict) -> T:
    baseclasses =[]
    # outputClass = []
    for cls in classes.values():
        baseclasses += cls.mro()
        if targetClass in cls.mro():
            outputClass = cls

    if (targetClass not in baseclasses) or outputClass==None:
        available_classes = ', '.join(classes.keys())
        raise ValueError(f"Class '{targetClass}' does not exist." \
                        f"Availables: {available_classes}")
    
    return outputClass

def analyze_class_constructor(cls):
    sig = inspect.signature(cls.__init__)
    type_hints = get_type_hints(cls.__init__)
    
    params_info = {}
    
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
            
        param_info = {
            'default': param.default,
            'required': param.default is inspect.Parameter.empty,
            'type': type_hints.get(param_name, Any),
            'annotation': param.annotation
        }
        
        params_info[param_name] = param_info
        
    return params_info

def build_argument_help(info: Dict[str, Any]) -> str:
    help_parts = []
    
    # type_name = info['type'].__name__ if hasattr(info['type'], '__name__') else str(info['type'])
    # help_parts.append(f"Type: {type_name}")
    
    if info['default'] is not inspect.Parameter.empty:
        default_value = info['default']
        if isinstance(default_value, str):
            default_value = f"'{default_value}'"
        help_parts.append(f"Default: {default_value}")
    
    # if info['docstring']:
    #     help_parts.append(info['docstring'])
    
    return " | ".join(help_parts)

def parser_factory():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-g', '--geo', action='store', type=str, default='',
                        dest='geo', help='Input geometry file. Support `.gdml` and `.py` file.' )

    args, unknown = parser.parse_known_args()

    try:
        if len(sys.argv) <= 1:
            raise ValueError("Not enough arguments!")
        elif args.geo == '':
            raise ValueError("Prompt simulation can not run without a geometry file!")
        elif args.geo.endswith('.py'):
            parser = PromptPyScriptParser(add_help = False, parents = [parser])
        elif args.geo.endswith('.gdml'):
            parser = PromptGdmlParser(add_help = False, parents = [parser])
        else:
            raise ValueError("Command line input is NOT correct, simulation not run.")
    except Exception as e:
        parser.print_help()
        print()
        print(f'PromptCLI Error: {e}')
        exit(1)
    # add help here so as to parse parameters in `.py` scripts
    # cannot move because it is intended to parse all arguments before print help message
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='show this help message and exit')
    
    return parser

class PromptBaseParser(argparse.ArgumentParser):
    def __init__(self, des="", *args, **kwargs):
        description = """
        Particle tracing simulation via Prompt.
        There are 2 ways to input simulation configurations:
            1. by `.py` file.
            2. by `.gdml` file.
        If a `.py` file is the way, run `prompt -g <yourScript.py> -h` for available arguments.
        """ + des
        super().__init__(*args, **kwargs, description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
        self.general_arguments = self.set_general_arguments()

    def set_visualize_arguments(self):
        self.add_argument('-v', '--visualize', action='store_true', dest='visualize', help='flag to visualize geometry model')
        self.add_argument('-Z', '--zscale', action='store', type=float, default=1., dest='zscale',
                          help='Set visulization scale factor along Z direction. Must used along with "-v" flag')

    def set_general_arguments(self):
        #TODO:
        # parser.add_argument('-l', '--geoLayer', action='store', type=float, default=0,
        #                     dest='geoLayer', help='geometry tree layers to be shown')
        self.set_visualize_arguments()
        self.add_argument('-s', '--seed', action='store', type=int, default=4096,
                            dest='seed', help='random seed number')
        self.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
                            dest='neutronNum', help='neutron number')
        self.add_argument('-b', '--blacklist',  type=str, nargs='+', dest='blacklist', help='solid mesh blacklist to inform the geometry mesh loader ')
        self.add_argument('-d', '--dumpmesh', action='store_true', dest='dumpmesh', help='dump mesh into disk')
        self.add_argument('-m', '--mergemesh', action='store_true', dest='mergemesh', help='flag to merge mesh for efficient visualize')
        self.add_argument('--nSeg', action='store', type=int, default=30,
                            dest='nSegments', help='number of verts a volume')
        return self.parse_known_args()[0]

    def simulate(self):
        raise NotImplementedError("Simulation logic not defined!")
    
class PromptGdmlParser(PromptBaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def simulate(self):
        args=self.parse_args()
        inputfile=args.geo
        printTraj=False
        rdseed=args.seed

        myLcher=Launcher()
        myLcher.setSeed(rdseed)

        if inputfile=='':
            myLcher.loadFakeGeoPhysics()
        else:
            if not os.path.isfile(inputfile):
                inputfile=findData(f'gdml/{inputfile}', '.')
                if not os.path.isfile(inputfile):
                    raise IOError(f'The input GDML file {args.geo} is not found.')
            myLcher.loadGeometry(inputfile)

        if args.visualize is True:
            v = Visualiser(args.blacklist, printWorld=False, nSegments=args.nSegments, mergeMesh=args.mergemesh, dumpMesh=args.dumpmesh)
            for i in range(int(args.neutronNum)):
                myLcher.go(1, recordTrj=True, timer=False, save2Dis=False)
                trj = myLcher.getTrajectory()
                try:
                    v.addTrj(trj)
                except ValueError:
                    print("skip ValueError in File '/Prompt/scripts/prompt', in <module>, v.addLine(trj)")
            v.show()
        else:
            myLcher.go(int(args.neutronNum), recordTrj=False)

class PromptPyScriptParser(PromptBaseParser):
    def __init__(self, *args, **kwargs):
        description = """
        Provide a `.py` file to define a simulation, where 2 ingredients are required: 
        1. A Simulation object. Derived from `PromptMPI` and defines the materials, geometries, and scorers.
        2. A Gun object. Derived from `Gun` and defines the particles positions, directions, and energies.
        """
        super().__init__(des = description, *args, **kwargs)
        self.args,_ = self.parse_known_args()
        self.pyScriptPath = self.args.geo
        self.classes_defined = get_classes_from_filepath(self.pyScriptPath)
        self._preprocess_parse()

    def _preprocess_parse(self):
        self.sim = self._preprocess_check(Prompt, duplication_allowed=False)
        self._construct_argument_groups(self.sim[0], self.classes_defined[self.sim[0]])
        
        self.guns = self._preprocess_check(Gun, duplication_allowed=True)
        self.add_argument('--gun', action='store', type=str, default=None,
                            dest='gun', help=f'gun class name. Available: {self.guns}')
        for g in self.guns:
                self._construct_argument_groups(g, self.classes_defined[g])

    def _preprocess_check(self, req_cls , duplication_allowed=False):
        num_found = 0
        available_classes = []
        for name, obj in self.classes_defined.items():
            if req_cls in obj.mro():
                num_found += 1
                available_classes.append(name)
        if num_found == 0:
            raise ValueError(f"No class '{req_cls.__name__}' is defined.")
        if not duplication_allowed and num_found > 1:
            raise ValueError(f"Class '{req_cls.__name__}' is duplicated in {num_found} classes")
        return available_classes

    def _construct_argument_groups(self, clsname, clsobj):
        group = self.add_argument_group(f"{clsname}")
        params_info = analyze_class_constructor(clsobj)
        for param_name, info in params_info.items():
            arg_name = f"--{param_name}"
            arg_kwargs = {
                'dest': param_name,
                'help': build_argument_help(info)
            }
            if info['type'] in (int, float, str, bool):
                arg_kwargs['type'] = info['type']
            elif info['type'] is list:
                arg_kwargs['type'] = lambda x: eval(x)
                arg_kwargs['help'] += " (eg.: '[1, 2, 3]')"
            elif info['type'] is dict:
                arg_kwargs['type'] = lambda x: eval(x)
                arg_kwargs['help'] += " (eg.: '{'key': 'value'}')"
            
            if info['default'] is not inspect.Parameter.empty:
                arg_kwargs['default'] = info['default']
            else:
                arg_kwargs['required'] = True
            
            if info['type'] is bool:
                if info['default'] is True:
                    group.add_argument(f"--no-{param_name}", action='store_false', **arg_kwargs)
                else:
                    group.add_argument(arg_name, action='store_true', **arg_kwargs)
            else:
                if param_name not in self.general_arguments:
                    group.add_argument(arg_name, **arg_kwargs)
        return group

    def _check_args(self):
        if not self.args.gun:
            raise ValueError(f"Gun class is NOT specified. Please use option '--gun' to specify a gun class. Available: {self.guns}")
        if self.args.gun not in self.guns:
            raise ValueError(f"Gun class '{self.args.gun}' is NOT defined. Available: {self.guns}")
        
    def instantiate(self, targetBaseClass : Type[T]) -> T:
        parsed_args = self.parse_args()

        targetChildClass = get_classes_from_base_class(targetBaseClass, self.classes_defined)
        
        init_params = {}
        
        sig = inspect.signature(targetChildClass.__init__)
        for param_name in sig.parameters:
            if param_name == 'self':
                continue
            
            if hasattr(parsed_args, param_name):
                parsedvalue = getattr(parsed_args, param_name)
                if isinstance(parsedvalue, str):
                    parsedvalue_typeconversed = str_or_float(parsedvalue)
                else:
                    parsedvalue_typeconversed = parsedvalue
                init_params[param_name] = parsedvalue_typeconversed
            else:
                param = sig.parameters[param_name]
                if param.default is not inspect.Parameter.empty:
                    init_params[param_name] = param.default
                else:
                    raise ValueError(f"Missing parameters: {param_name}")
        
        return targetChildClass(**init_params)

    def simulate(self):
        args = self.parse_args()
        self._check_args()
        sim = self.instantiate(Prompt)
        gun = self.instantiate(self.classes_defined[self.args.gun])

        if not sim.l.worldExist:
            raise ValueError("World not made.")
        
        if args.visualize:
            sim.show(gun, int(args.neutronNum), zscale=args.zscale)
        else:
            sim.simulate(gun, int(args.neutronNum))
            sim.save_all_scorers()
    
def main():
    parser = parser_factory()
    try:
        parser.simulate()
    except Exception as e:
        parser.print_help()
        print()
        print(f'PromptCLI Error: {e}')

if __name__ == '__main__':

    main()
