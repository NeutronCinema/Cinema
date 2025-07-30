#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI, Launcher, Visualiser
from Cinema.Prompt.gun import SurfaceSource
import argparse
import inspect
import importlib.util
from Cinema.Interface.Utils import findData
import os
import sys
from typing import Dict, Any, Type, Optional, List, Set, get_type_hints, Union, TypeVar

T = TypeVar('T')

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

def add_arguments_to_parser(parser : argparse.ArgumentParser):
    parser.add_argument('-v', '--visualize', action='store_true', dest='visualize', help='flag to visualize geometry model')
    parser.add_argument('-s', '--seed', action='store', type=int, default=4096,
                        dest='seed', help='random seed number')
    parser.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
                        dest='neutronNum', help='neutron number')
    parser.add_argument('-b', '--blacklist',  type=str, nargs='+', dest='blacklist', help='solid mesh blacklist to inform the geometry mesh loader ')
    parser.add_argument('-d', '--dumpmesh', action='store_true', dest='dumpmesh', help='dump mesh into disk')
    parser.add_argument('-m', '--mergemesh', action='store_true', dest='mergemesh', help='flag to merge mesh for efficient visualize')
    parser.add_argument('--nSeg', action='store', type=int, default=30,
                        dest='nSegments', help='number of verts a volume')
    
    #TODO:
    # parser.add_argument('-l', '--geoLayer', action='store', type=float, default=0,
    #                     dest='geoLayer', help='geometry tree layers to be shown')

    return parser

def quiry_help_msg(loc : int):
    return ('-h' in sys.argv[loc]) or ('--help' in sys.argv[loc])

def get_parser(parser : argparse.ArgumentParser):

    parser.add_argument('-g', '--geo', action='store', type=str, default='',
                        dest='geo', help='input geometry file. Support `.gdml` and `.py` file.' \
                        ' If `.py` file is given, the arguments defined in classes constructor is parsed.')
    
    args, _ = parser.parse_known_args()

    add_arguments_to_parser(parser)
    if args.geo.endswith('.py'):
        get_subparser_from_cls(args.geo, parser)
    
    if len(sys.argv) <= 1:
        parser.print_help()

    # add help here so as to parse parameters in `.py` scripts
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='show this help message and exit')
        
    return parser

def get_subparser_from_cls(pyScriptPath : str, subparser : argparse.ArgumentParser):
    clss = get_classes_from_filepath(pyScriptPath)
    for clsname, clsobj in clss.items():
        if PromptMPI in clsobj.mro():
            add_arguments_for_class(subparser, clsobj)

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

def add_arguments_for_class(parser: argparse.ArgumentParser, cls: Type):
    params_info = analyze_class_constructor(cls)
    # print(f"Simulation parameters number in total: {len(params_info)}")
    # print()
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
                parser.add_argument(f"--no-{param_name}", action='store_false', **arg_kwargs)
            else:
                parser.add_argument(arg_name, action='store_true', **arg_kwargs)
        else:
            args, _ = parser.parse_known_args()
            if param_name not in args:
                parser.add_argument(arg_name, **arg_kwargs)
    return parser


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

def instantiate_class_from_parser(targetBaseClass : Type[T], parser : argparse.ArgumentParser, args=None) -> T:
    if args is None:
        parsed_args = parser.parse_args()
    else:
        parsed_args = parser.parse_args(args)


    classes = get_classes_from_filepath(parsed_args.geo)
    targetChildClass = get_class_of_base_class(targetBaseClass, classes)

    # baseclasses = []
    # for cls in classes.values():
    #     baseclasses += cls.mro()

    # if targetClass not in baseclasses:
    #     available_classes = ', '.join(classes.keys())
    #     raise ValueError(f"Class '{targetClass}' does not exist in '{parsed_args.filepath}'." \
    #                     f"Availables: {available_classes}")
    
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

def get_class_of_base_class(targetClass : Type[T], classes : dict) -> T:
    baseclasses = []
    for cls in classes.values():
        baseclasses += cls.mro()
        if targetClass in cls.mro():
            outputClass = cls

    if (targetClass not in baseclasses) or outputClass==None:
        available_classes = ', '.join(classes.keys())
        raise ValueError(f"Class '{targetClass}' does not exist." \
                        f"Availables: {available_classes}")
    
    return outputClass

def main_py(parser : argparse.ArgumentParser):
    args=parser.parse_args()
    classes = get_classes_from_filepath(args.geo)

    sim = instantiate_class_from_parser(PromptMPI, parser)

    gun = instantiate_class_from_parser(SurfaceSource, parser)

    if not sim.l.worldExist:
        raise ValueError("World not made.")
    
    if args.visualize:
        sim.show(gun, int(args.neutronNum))
    else:
        sim.simulate(gun, int(args.neutronNum))
        sim.save_all_scorers()


def main_gdml(parser : argparse.ArgumentParser):
    args=parser.parse_args()
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

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser = get_parser(parser)
    args = parser.parse_args()
    if args.geo.endswith('.gdml'):
        main_gdml(parser)
    elif args.geo.endswith('.py'):
        main_py(parser)

if __name__ == '__main__':

    main()
