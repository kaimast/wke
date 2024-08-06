# pylint: disable=too-many-public-methods,fixme,too-many-instance-attributes

''' API encapsulating all the information from the config.toml file '''

from typing import Any
from os.path import isfile

import tomllib

from .errors import ConfigurationError

TARGET_FOLDER = "targets"
PRELUDE_FOLDER = "preludes"
PROTECTED_NAMES = ["all", "help", "copy-data"]

class Argument:
    ''' Representation of an argument for a specific target '''

    def __init__(self, name: str, default: Any):
        self._name = name
        self._default = default

    @property
    def name(self) -> str:
        ''' The name for this argument '''
        return self._name

    @property
    def required(self) -> bool:
        ''' Does this argument have to be set? '''
        return self._default is None

    @property
    def default_value(self) -> Any:
        ''' The default value, if any is given '''
        return self._default

class Prelude:
    ''' Prelude prepare execution of a targets, e.g., by setting environmetn variables '''

    def __init__(self, name, path, about):
        self._name = name
        self._path = path
        self._about = about

    @property
    def name(self) -> str:
        ''' The name of this prelude '''
        return self._name

    @property
    def path(self):
        ''' The path where the associated script is located '''
        return self._path

    @property
    def about(self):
        ''' Description of this prelude '''
        return self._about

    def get_command(self) -> str:
        ''' Get the code for this prelude '''
        cmd = ""

        with open(self.path, encoding='utf-8') as cmdfile:
            for (pos, line) in enumerate(cmdfile.readlines()):
                line = line.replace('\n', '')

                if pos == 0:
                    if not '#!' in line:
                        raise ConfigurationError(
                            f'First line of prelude in {self.path} not a shebang: {line}')

                    if not 'bash' in line:
                        raise ConfigurationError(
                            f'Only bash preludes are supported, but {self.path} is not')
                else:
                    if line != "" and line[0] != '#':
                        cmd += f'{line} && '

        return cmd

class Target:
    ''' A make or run target '''

    def __init__(self, name, toml_config, path):
        self._name = name
        self._path = path
        self._about = "No description"

        # Keep argument as a list, because their order defines
        # how they are passed to the target
        self._arguments = []

        if isinstance(toml_config, list):
            for entry in toml_config:
                self._parse_argument(entry)
        elif isinstance(toml_config, dict):
            for key in toml_config.keys():
                if key not in ["about", "arguments"]:
                    print(f'WARN: Unexpected key "{key}" for target "{name} at {path}')

            if "arguments" in toml_config:
                args = toml_config["arguments"]
                if not isinstance(args, list):
                    raise ConfigurationError(f'Invalid target arguments at {self._path}: '
                                             f'Arguments must be a list')

                for entry in args:
                    self._parse_argument(entry)
            if "about" in toml_config:
                self._about = toml_config["about"]
        else:
            raise RuntimeError(f"Target at {path} is neither a dict nor a list")

    def _parse_argument(self, toml_entry):
        if isinstance(toml_entry, list):
            if len(toml_entry) == 1:
                name = toml_entry[0]
                default = None
            elif len(toml_entry):
                name, default = toml_entry
            else:
                raise ConfigurationError(f'Invalid target argument at {self._path}: '
                                         f'Must contain one or two entries if specified as a list')
        elif isinstance(toml_entry, str):
            name = toml_entry
            default = None
        elif isinstance(toml_entry, dict):
            try:
                name = toml_entry["name"]
            except KeyError as err:
                raise ConfigurationError(f'Invalid target argument at {self._path}: '
                                         f'Must contain "name" if specified as a dict') from err


            default = toml_entry.get("default", None)
        else:
            raise ConfigurationError(f'Invalid target argument at {self._path}: '
                                     f'Not a string, dict, or list')

        self._arguments.append(Argument(name, default))

    @property
    def name(self) -> str:
        ''' The name of this target '''
        return self._name

    @property
    def about(self):
        ''' A description of this target '''
        return self._about

    @property
    def path(self):
        ''' The path where the associated script is located '''
        return self._path

    @property
    def arguments(self) -> list[Argument]:
        ''' Get all arguments for this target and their default values '''
        return self._arguments

    @property
    def argument_names(self) -> list[str]:
        ''' Get the names of all arguments '''
        return [arg.name for arg in self._arguments]

    def get_default_value(self, name) -> Any:
        ''' Get the default value for the specified argument '''

        for arg in self._arguments:
            if arg.name == name:
                return arg.default_value
        raise ConfigurationError(f"No such argument {name}")

    @property
    def command(self) -> str:
        ''' Get the command to execute for this target '''
        if self.path is None:
            raise ConfigurationError(f'No script found for command "{self.name}"')

        with open(self.path, encoding='utf-8') as cmdfile:
            return cmdfile.read()

class Configuration:
    ''' Holds the contents of the config.toml file '''

    def __init__(self, config_name: str, base_path=".", children=None):
        self._name = config_name
        self._base_path = base_path
        path = f'{base_path}/{config_name}/config.toml'

        try:
            with open(path, 'rb') as toml_file:
                config_toml = tomllib.load(toml_file)
        except OSError as err:
            raise ConfigurationError(f"Cannot open config file at {path}: {err}") from err
        except tomllib.TOMLDecodeError as err:
            raise ConfigurationError(f"Failed to parse config file at {path}: {err}") from err

        self._preludes: dict[str, Prelude] = {}
        self._targets: dict[str, Target] = {}
        self._config_toml = config_toml

        if 'targets' in config_toml:
            self._parse_targets(config_toml["targets"])

        if 'preludes' in config_toml:
            self._parse_preludes(config_toml["preludes"])

        if "config" in config_toml:
            meta = config_toml["config"]
            if "inherits" in meta:
                self._process_inheritance(config_toml, base_path, children)
            else:
                self._parent_name = None
                self._default_prelude = meta.get('default-prelude', None)
        else:
            self._parent_name = self._default_prelude = None

    def _process_inheritance(self, config_toml, base_path, children):
        # pylint: disable=W0212

        pname = config_toml['config']['inherits']
        assert isinstance(pname, str)
        assert pname != ""

        if children:
            if pname in children:
                raise ConfigurationError("Circular dependency!")
            children = children + [self._name]
        else:
            children = [self._name]

        parent = Configuration(pname, base_path=base_path,
                               children=children)
        self._parent_name = pname

        self._override_config("", parent._config_toml, config_toml)
        self._config_toml = parent._config_toml

        preludes = self._preludes
        self._preludes = parent._preludes
        targets = self._targets
        self._targets = parent._targets

        for name, value in preludes.items():
            if name in self._preludes:
                print(f'Overriding parents prelude "{name}"')
            self._preludes[name] = value

        for name, value in targets.items():
            if name in self._targets:
                print(f'Overriding parents target "{name}"')
            self._targets[name] = value

    def _parse_preludes(self, preludes):
        assert isinstance(preludes, dict)

        for name, value in preludes.items():
            if isinstance(value, str):
                about = value
            elif isinstance(value, dict):
                if "about" in value:
                    about = value["about"]
                else:
                    about = "No description"
            else:
                raise RuntimeError("Prelude has invalid type")

            if name in PROTECTED_NAMES:
                raise ConfigurationError(f"Prelude uses reserved name: {name}")

            path = self._get_prelude_path(name)
            if isfile(path):
                self._preludes[name] = Prelude(name, path, about)
            else:
                print(f'WARNING: Prelude "{self.name}::{name}" is missing script!')
                self._preludes[name] = Prelude(name, None, about)

    def _parse_targets(self, targets):
        assert isinstance(targets, dict)

        for (name, config) in targets.items():
            if name in PROTECTED_NAMES:
                raise ConfigurationError(f"Make target uses reserved name: {name}")

            bash_path = self._get_target_bash_path(name)
            python_path = self._get_target_python_path(name)

            if isfile(bash_path):
                self._targets[name] = Target(name, config, bash_path)
            elif isfile(python_path):
                self._targets[name] = Target(name, config, python_path)
            else:
                print(f'WARNING: Target "{self.name}::{name}" is missing script!')
                self._targets[name] = Target(name, config, None)

    def _override_config(self, _path, parent, child: dict):
        for key, value in child.items():
            if isinstance(value, dict) and key in parent:
                #print(f"Merging {path}.{key}")
                assert isinstance(parent[key], dict)
                path = f"{_path}.{key}"
                self._override_config(path, parent[key], value)
            else:
                parent[key] = value

    def generate_metadata(self, verbose=False):
        ''' Generate a dict, containing information about this config '''

        if verbose:
            targets = {
               'install-packages': {
                    'about': 'Install the required debian packages',
                    'arguments': []
                }
            }
        else:
            targets = {
               'install-packages': 'Install the required debian packages',
            }

        for info in self.targets:
            if verbose:
                args = []
                for arg in info.arguments:
                    if arg.required:
                        args.append({"name": arg.name, "required": True})
                    else:
                        args.append({"name": arg.name, "required": False,
                                "default-value": arg.default_value })

                targets[info.name] = {
                    'about': info.about,
                    'arguments': args, 
                }
            else:
                targets[info.name] = info.about

        preludes = {}
        for prelude in self.preludes:
            preludes[prelude.name] = prelude.about

        result = {
            "preludes": preludes,
            "targets": targets,
        }

        if self._default_prelude:
            result["default-prelude"] = self._default_prelude

        if "ubuntu" in self._config_toml:
            result["ubuntu"] = self._config_toml["ubuntu"]

        return result

    @property
    def has_parent(self) -> bool:
        ''' Does this config have a parent configuration? '''
        return self._parent_name is not None

    @property
    def name(self) -> str:
        ''' Returns the name of this configuration '''
        return self._name

    @property
    def base_path(self):
        ''' Returns the parent folder of where the config is located '''
        return self._base_path

    def _get_prelude_path(self, script):
        return f"{self.base_path}/{self.name}/{PRELUDE_FOLDER}/{script}"

    def _get_target_bash_path(self, script):
        return f"{self.base_path}/{self.name}/{TARGET_FOLDER}/{script}"

    def _get_target_python_path(self, script):
        return f"{self.base_path}/{self.name}/{TARGET_FOLDER}/{script.lower().replace('-', '_')}.py"

    @property
    def default_prelude(self):
        ''' Get the default prelude for this config. Returns none if none was specified. '''
        return self._default_prelude

    @property
    def prelude_names(self):
        ''' Get the names of all preludes this config '''
        return list(self._preludes.keys())

    @property
    def preludes(self):
        ''' Get all preludes '''
        return list(self._preludes.values())

    def get_prelude_cmd(self, name):
        ''' Convert an prelude file into a command line command '''

        prelude = self._preludes[name]
        if prelude is None:
            raise ConfigurationError(f"No such prelude: {name}")

        return prelude.get_command()

    def get_target(self, target_name):
        '''
            Get a target by its name. 
            Returns None if no such target exists
        '''
        return self._targets.get(target_name, None)

    def get_target_cmd(self, target_name):
        ''' Get the contents of a make command script '''
        target = self._targets.get(target_name)
        if target is None:
            raise ConfigurationError(f"No such target: {target_name}")

        if target.path is None:
            search_paths = [
                self._get_target_bash_path(target_name),
                self._get_target_python_path(target_name),
            ]

            raise ConfigurationError(
                f'For target "{target_name}" no valid script exists '
                f' at any of these locations: {search_paths}'
            )

        return target.get_command()

    def get_target_args(self, target_name):
        ''' Get arguments for a target '''
        return self._targets[target_name].arguments

    @property
    def required_ubuntu_repositories(self) -> list[str]:
        ''' What additional repositories does this config need? '''
        ubuntu = self._config_toml.get("ubuntu", None)

        if not ubuntu:
            return []

        return ubuntu.get("required-repositories", [])

    @property
    def required_ubuntu_packages(self):
        ''' What packages are needed to run this config? '''
        ubuntu = self._config_toml.get("ubuntu", None)

        if not ubuntu:
            return []

        return ubuntu.get("required-packages", [])

    @property
    def target_names(self) -> list[str]:
        ''' Get the names of all targets '''
        return list(self._targets.keys())

    @property
    def targets(self) -> list[Target]:
        ''' Get a list of all targets '''
        return list(self._targets.values())
