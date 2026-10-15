#!/usr/bin/env python3

from Cinema.Prompt import Prompt, PromptMPI, Visualiser
from Cinema.Prompt.launcher import Launcher
from Cinema.Prompt.gun import Gun
import argparse
import ast
import inspect
import importlib.util
import types
from Cinema.Interface.Utils import findData
import os
import sys
from typing import Dict, Any, Type, Optional, List, Set, get_type_hints, get_origin, get_args, Union, TypeVar

T = TypeVar('T')

# get_origin markers of both union spellings: `typing.Union[...]` and PEP 604 `X | None`
_UNION_ORIGINS = {Union}
if hasattr(types, 'UnionType'):
    _UNION_ORIGINS.add(types.UnionType)

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

def parse_literal(value: str):
    """Parse a python literal (the parser attached to list/dict options)

    Raises
    ------
    ValueError
        If `value` is not a valid python literal.
    """
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError) as e:
        raise ValueError(f"invalid literal: {value!r}") from e

def _web_kwargs(args):
    """Map the --web* CLI flags onto Visualiser web kwargs ({} if --web is off)."""
    if not getattr(args, 'web', False):
        return {}
    return dict(web=True, web_mode=args.web_mode, web_port=args.web_port,
                web_host=args.web_host, web_open_browser=args.web_open_browser,
                web_timeout=args.web_timeout)

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

def resolve_hint_kind(hint, default=inspect.Parameter.empty):
    """Degrade a constructor type hint to the plain builtin kind the CLI parses

    `Optional[X]` drops its NoneType member and degrades to `X`, list/dict
    generics (e.g. `List[float]`) degrade to `list`/`dict`, and an `Any` or
    missing hint borrows the kind of the default value. Returns None when no
    builtin kind applies (the option then stays a plain string, coerced later
    by `str_or_float`).
    """
    if hint is Any or hint is inspect.Parameter.empty:
        if default is not inspect.Parameter.empty and \
                type(default) in (list, dict, int, float, str, bool):
            return type(default)
        return None
    if get_origin(hint) in _UNION_ORIGINS:
        members = [a for a in get_args(hint) if a is not type(None)]
        if len(members) != 1:
            return None
        hint = members[0]
    origin = get_origin(hint)
    if origin in (list, dict):
        return origin
    return hint if hint in (list, dict, int, float, str, bool) else None

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
    parser.add_argument('--debug', action='store_true', dest='debug', help='flag to enable traceback')

    args, unknown = parser.parse_known_args()

    if len(sys.argv) <= 1:
        parser = PromptBaseParser(parents=[parser])
        parser.print_help()
        sys.exit(1)
    elif args.geo == '':
        parser = PromptBaseParser(parents=[parser])
        raise ValueError("Prompt simulation can not run without a geometry file!")
    elif args.geo.endswith('.py'):
        if any(a in ('-h', '--help') for a in sys.argv):
            # loading the script is unavoidable here: the per-class command line
            # options are parsed from the classes it defines, so -h is not
            # import-safe. Warn before the side effect instead of hiding it.
            print("NOTE: with a `.py` geometry file, -h/--help first executes the "
                  "script's module level (per-class options are parsed from the "
                  "loaded classes). Keep makeWorld in the simulation constructor, "
                  "not at module level, if the script is imported elsewhere.")
        parser = PromptPyScriptParser(add_help = False, parents = [parser])
    elif args.geo.endswith('.gdml'):
        parser = PromptGdmlParser(add_help = False, parents = [parser])
    else:
        raise ValueError("Command line input is NOT correct, simulation not run.")

    # add help here so as to parse parameters in `.py` scripts
    # cannot move because it is intended to parse all arguments before print help message
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='show this help message and exit')
    
    return parser

class RawNoMetavarFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action_invocation(self, action):
        if action.option_strings:
            return ', '.join(action.option_strings)
        else:
            return action.dest


class PromptBaseParser(argparse.ArgumentParser):
    def __init__(self, des="", *args, **kwargs):
        description = """
        Particle transport and ray-tracing simulation by Prompt.
        There are 2 ways to run simulation configurations:
            1. via a `.gdml` file, which is the only supported xml input format in version 1, as introduced in http://doi.org/10.1016/j.cpc.2023.109004.
            2. via a `.py` file, a newly added method for defining simulations through Python scripts that offers greater flexibility and more functionalities.
        Please refer to the paper for the method to run a `.gdml` file.  
        In either case, run `prompt -g <yourScript.py or .gdml> -h` for available arguments.
        """ + des
        super().__init__(*args, **kwargs, description=description, formatter_class=RawNoMetavarFormatter)
        self.general_arguments = self.set_general_arguments()
        self.debug = getattr(self.general_arguments, 'debug', False)

    def set_visualize_arguments(self):
        g = self.add_argument_group('Visualization Arguments')
        g.add_argument('-v', '--visualize', action='store_true', dest='visualize', help='flag to visualize geometry model')
        g.add_argument('-Z', '--zscale', action='store', type=float, default=1., dest='zscale',
                          help='Set visulization scale factor along Z direction. Must used along with "-v" flag')
        g.add_argument('-b', '--blacklist',  type=str, nargs='+', dest='blacklist', help='solid mesh blacklist to inform the geometry mesh loader ')
        g.add_argument('-m', '--mergemesh', action='store_true', dest='mergemesh', help='flag to merge mesh for efficient visualize')
        g.add_argument('-d', '--dumpmesh', action='store_true', dest='dumpmesh', help='dump mesh into disk')
        g.add_argument('--nSeg', action='store', type=int, default=30,
                            dest='nSegments', help='number of verts a volume')
        g.add_argument('--web', action='store_true', dest='web',
                            help='serve the visualisation in a browser (trame) instead of a desktop window')
        g.add_argument('--web-mode', dest='web_mode', default=None, choices=['client', 'server', 'trame'],
                            help='browser rendering mode: client renders in the browser via vtk.js and needs no GL on this host (default); '
                                 'server/trame render on this host and need GL (use xvfb-run on headless hosts)')
        g.add_argument('--web-port', dest='web_port', type=int, default=0,
                            help='port to serve the web visualisation on (0 = pick a free port)')
        g.add_argument('--web-host', dest='web_host', default=None,
                            help='interface to bind (default 127.0.0.1; 0.0.0.0 to expose)')
        g.add_argument('--web-no-browser', action='store_false', dest='web_open_browser',
                            help='do not auto-open the browser, just print the URL')
        g.add_argument('--web-timeout', dest='web_timeout', type=int, default=3,
                            help='auto-exit N seconds after the last browser client disconnects (0 = serve until Ctrl+C); '
                                 'useful when the visualisation is a one-shot service')
        self.viz_args_group = g

    def set_general_arguments(self):
        #TODO:
        # parser.add_argument('-l', '--geoLayer', action='store', type=float, default=0,
        #                     dest='geoLayer', help='geometry tree layers to be shown')
        self.set_visualize_arguments()
        g = self.add_argument_group('Particle Gun Arguments')
        g.add_argument('-s', '--seed', action='store', type=int, default=4096,
                            dest='seed', help='random seed number')
        g.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
                            dest='neutronNum', help='neutron number')
        self.gun_args_group = g
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
            v = Visualiser(args.blacklist, printWorld=False, nSegments=args.nSegments, mergeMesh=args.mergemesh, doDumpMesh=args.dumpmesh, **_web_kwargs(args))
            for i in range(int(args.neutronNum)):
                myLcher.go(1, recordTrj=True, timer=False, save2Disk=False)
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
        Two derived classes are required in the Python script: 
            1. One and only one simulation class. Derived from either `PromptMPI` or `Prompt` and defines the materials, geometries, and scorers.
            2. One or multiple Gun classes derived from `Gun` and samples the initial particles positions, directions, and energies.
        An ideal instrument with an almost 4pi detector configuration and monitors can be found in `example/instrument.py`.
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
        self.gun_args_group.add_argument('--gun', action='store', type=str, default=None,
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
            kind = resolve_hint_kind(info['type'], info['default'])
            if kind in (int, float, str, bool):
                arg_kwargs['type'] = kind
            elif kind in (list, dict):
                arg_kwargs['type'] = parse_literal
                arg_kwargs['help'] += " (eg.: '[1, 2, 3]')" if kind is list else " (eg.: '{'key': 'value'}')"

            if info['default'] is not inspect.Parameter.empty:
                arg_kwargs['default'] = info['default']
            else:
                arg_kwargs['required'] = True

            if kind is bool:
                # store_true/store_false actions do not accept the `type` kwarg
                arg_kwargs.pop('type', None)
                if info['default'] is True:
                    group.add_argument(f"--no-{param_name}", action='store_false', **arg_kwargs)
                else:
                    group.add_argument(arg_name, action='store_true', **arg_kwargs)
            else:
                if param_name not in self.general_arguments:
                    group.add_argument(arg_name, **arg_kwargs)
        return group

    def _check_args(self, args):
        if not args.gun:
            raise ValueError(f"Gun class is NOT specified. Please use option '--gun' to specify a gun class. Available: {self.guns}")
        if args.gun not in self.guns:
            raise ValueError(f"Gun class '{args.gun}' is NOT defined. Available: {self.guns}")
        
    def instantiate(self, targetBaseClass : Type[T]) -> T:
        parsed_args = self.parse_args()

        targetChildClass = get_classes_from_base_class(targetBaseClass, self.classes_defined)
        
        init_params = {}
        
        sig = inspect.signature(targetChildClass.__init__)
        params_info = analyze_class_constructor(targetChildClass)
        for param_name in sig.parameters:
            if param_name == 'self':
                continue

            info = params_info[param_name]

            if hasattr(parsed_args, param_name):
                parsedvalue = getattr(parsed_args, param_name)
                kind = resolve_hint_kind(info['type'], info['default'])
                if kind in (list, dict) and isinstance(parsedvalue, str):
                    # belt and braces: a raw string here reaches the C++ gun
                    # and aborts without any traceback, so coerce it (or fail
                    # naming the option) even if the argparse parser was bypassed
                    try:
                        parsedvalue = parse_literal(parsedvalue)
                    except ValueError:
                        raise ValueError(f"--{param_name} expects a {kind.__name__}, got '{parsedvalue}'")
                elif isinstance(parsedvalue, str):
                    parsedvalue = str_or_float(parsedvalue)
                init_params[param_name] = parsedvalue
            else:
                param = sig.parameters[param_name]
                if param.default is not inspect.Parameter.empty:
                    init_params[param_name] = param.default
                else:
                    raise ValueError(f"Missing parameters: {param_name}")
        
        return targetChildClass(**init_params)

    def simulate(self):
        args = self.parse_args()
        self._check_args(args)
        sim = self.instantiate(Prompt)
        gun = self.instantiate(self.classes_defined[args.gun])

        if not sim.l.worldExist:
            raise ValueError("World not made.")
        
        if args.visualize:
            sim.show(gun, int(args.neutronNum), zscale=args.zscale, **_web_kwargs(args))
        else:
            sim.simulate(gun, int(args.neutronNum))
            sim.save_all_scorers()
    
def main():
    parser = None
    try:
        parser = parser_factory()
        parser.simulate()
    except Exception as e:
        print(f'PromptCLI Error: {e}')
        # `parser` is None when parser_factory() itself failed (e.g. the user
        # script raised at module level); fall back to the raw flag in argv.
        if getattr(parser, 'debug', False) or (parser is None and '--debug' in sys.argv):
            import traceback
            traceback.print_exc()
        if parser is not None:
            print()
            parser.print_help()
        sys.exit(1)

if __name__ == '__main__':

    main()
