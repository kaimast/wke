''' Code to load experiment definitions from TOMl files '''

import sys
import tomllib

from os import path

from .params import ExponentialSteps, LinearSteps
from .params import ListSteps, Parameter, ParameterSet, SubparamSteps

def parse_toml(filename: str, default_config: dict[str, Parameter]):
    ''' Read the experiment definition from a TOML file '''

    hill_climb = False

    try:
        with open(filename, 'rb') as file:
            toml_file = tomllib.load(file)
    except OSError as err:
        raise RuntimeError(f"Cannot open TOML file at {filename}: {err}") from err
    except tomllib.TOMLDecodeError as err:
        raise RuntimeError(f'Experiment file "{filename}" is not a valid TOML file: {err}') from err

    print("## Arguments:")
    num_iterations = toml_file["experiment"].get("num_iterations", 1)
    name = toml_file["experiment"].get("name", None)

    if not name:
        name = path.splitext(path.basename(filename))[0]

    steps, variables, base_config = _parse_parameters(toml_file, default_config,
                            toml_file["parameters"], hill_climb)

    for key, value in base_config.items():
        default_config[key] = value
    print("##----------")

    plots = toml_file.get('plots', None)

    return (steps, variables, hill_climb, name, num_iterations, plots)

def _parse_subparameters(toml_file, default_config: dict[str, Parameter],
        variables: set[str], hill_climb, value):
    '''
    Parameters sets can contain iterations of subparameters.
    Each subparameter set is another TOML table containing more parameter values.

    Take a look at "test-files/experiment/subparams.toml" for an example.
    '''

    subparams = []
    for subparam_key in value:
        print(f'Parsing subparameter set "{subparam_key}"')

        sub_steps, sub_vars, sub_base_config = _parse_parameters(toml_file,
            default_config, toml_file[subparam_key], hill_climb)

        for sstep in sub_steps:
            if sstep.is_subparams():
                variables.update(sstep.get_variables())
            else:
                variables.add(sstep.key())

        for subvar in sub_base_config:
            variables.add(subvar)

        subparams.append(ParameterSet(sub_steps, sub_vars, sub_base_config))

    return SubparamSteps(subparams)

def _parse_parameters(toml_file, default_config: dict[str, Parameter], params, hill_climb):
    '''
    Reads a parameter set from a TOML table.
    This can either be the "main" set or a subparameter set.
    '''

    variables: set[str] = set()
    steps = []
    config = {}

    for key, value in params.items():
        if hill_climb:
            print('💥 Hill climb must be the last specified parameter!')
            sys.exit(-1)

        if key == "sub-parameters":
            assert isinstance(value, list)

            if isinstance(value[0], list):
                # Multiple subparameters
                for subval in value:
                    substeps = _parse_subparameters(toml_file, default_config,
                                variables, hill_climb, subval)
                    steps.append(substeps)
            else:
                substeps = _parse_subparameters(toml_file, default_config,
                                variables, hill_climb, value)
                steps.append(substeps)
            continue

        try:
            parameter = default_config[key]
        except KeyError:
            print(f'💥 No such parameter "{key}"')
            sys.exit(-1)

        if isinstance(value, dict):
            if "base" in value:
                exp_steps = ExponentialSteps(key, value["base"], value["start"],
                    value["end"], value.get("step-size", 1))
                steps.append(exp_steps)
            else:
                linear_steps = LinearSteps(key, value["start"], value["end"],
                    value.get("step-size", 1))
                steps.append(linear_steps)

            hill_climb = value.get("hill-climb", False)
            variables.add(key)
        elif isinstance(value, list):
            list_steps = ListSteps(key, value, parameter.type)
            steps.append(list_steps)
            variables.add(key)
        else:
            config[key] = value

    return (steps, variables, config)
