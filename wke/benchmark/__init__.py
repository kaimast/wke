''' Helper scripts to build benchmarks '''

# pylint: disable=too-many-locals,too-many-arguments,fixme,line-too-long
# pylint: disable=too-many-nested-blocks,too-many-positional-arguments

import sys
import argparse
import copy
import tomllib

from typing import Any
from time import localtime, strftime, sleep
from copy import deepcopy
from os import path, rename
from os.path import isfile, getmtime

from seaborn import lineplot, set_theme #type: ignore
from matplotlib import pyplot

from ..errors import BenchmarkError, ClusterError, ConfigurationError
from .printer import ResultPrinter
from .params import parse_parameters, ExponentialSteps, LinearSteps, ListSteps, Parameter, ParameterSet, SubparamSteps
from .toml import parse_toml

# TODO move this into result printer
def _run_benchmark(benchmark_func, parameters: dict[str, Parameter],
                   collect_statistics: bool, result_printer, verbose=False,
                   num_iterations=1, cooldown_time=5, prev_results=None,
                   hill_climb=False):

    if hill_climb:
        # TODO implement hill climbing
        raise RuntimeError("Hill climbing is not implemented yet")

    if num_iterations < 1:
        raise RuntimeError("Need at least one benchmark iteration")

    # re-use previous results?
    if prev_results is not None:
        conditions = []
        for name, value in parameters.items():
            #TODO also check constants
            if name in result_printer.variables:
                conditions.append((prev_results[name] == value))

        if len(conditions) == 0:
            matching_entries = min(num_iterations, len(prev_results))
        else:
            df_cond = True
            for condition in conditions:
                df_cond = df_cond & condition
            matching_entries = min(num_iterations, len(prev_results[df_cond]))
    else:
        matching_entries = 0

    # run experiments
    for _ in range(num_iterations - matching_entries):
        # ensure whatever benchmark func does will not modify parameters
        bench_params = copy.deepcopy(parameters)

        success = benchmark_func(bench_params, collect_statistics, result_printer,
                                 verbose=verbose)

        if not success:
            sys.exit(-1)

        # give some time to wind down
        sleep(cooldown_time)

def parse_constants(config: dict[str, Parameter], args: dict[str, Any]):
    ''' Parses parameters set to a constant value '''

    constant_set = {}

    for string in args:
        try:
            key, value = string.split('=')
        except ValueError:
            print(f'ERROR: constant command does not contain an equals sign: "{string}"')
            sys.exit(-1)

        try:
            parameter = config[key]
        except KeyError:
            print(f'ERROR: cannot set constant "{key}": no such parameter')
            sys.exit(-1)

        parameter.value = value
        print(f'🔬 Setting "{key}" to constant value "{value}" (type: {parameter.type_name})')
        parameter.value = value
        constant_set[key] = value

    return constant_set

def parse_linear_steps(variables: set[str], steps: list[Any], default_config: dict[str, Parameter], linear_args):
    ''' Converts an argument specification of linear steps in to LinearSteps objects '''

    for string in linear_args:
        try:
            key, value = string.split('=')
        except ValueError:
            print(f'💥 Step command does not contain an equals sign: "{string}"')
            sys.exit(-1)

        try:
            parameter = default_config[key]
        except KeyError:
            print(f'💥 Cannot step "{key}": no such parameter')
            sys.exit(-1)

        if parameter.type != int:
            print(f'💥 Cannot step "{key}", because its not an integer')
            sys.exit(-1)

        step_args = tuple(map(int, value.split(':')))

        if len(step_args) != 3:
            print(f'💥 Linear ranges need three arguments (like so "start:end:step_size"). '
                  f'Got "{value}" for key "{key}"')
            sys.exit(-1)

        start, end, step_size = step_args

        if step_size <= 0:
            print(f"💥 Not a valid step size for {key}")
            sys.exit(-1)

        if key in variables:
            print(f"💥 Steps for key {key} specified more than once")

        steps.append(LinearSteps(key, start, end, step_size))
        variables.add(key)

def parse_exponential_steps(variables: set[str], steps: list[Any], default_config: dict[str, Parameter], linear_args):
    ''' Converts an argument specification of exponential in to ExponentialSteps objects '''

    for string in linear_args:
        try:
            key, value = string.split('=')
        except ValueError:
            print(f'💥 Step command does not contain an equals sign: "{string}"')
            sys.exit(-1)

        try:
            parameter = default_config[key]
        except KeyError:
            print(f'💥 Cannot step "{key}": no such parameter')
            sys.exit(-1)

        if parameter.type != int:
            print(f'💥 Cannot step "{key}", because its not an integer')
            sys.exit(-1)

        step_args = tuple(map(int, value.split(':')))

        if len(step_args) != 4:
            print(f'💥 Exponential ranges need four arguments (like so "base:start:end:step_size"). '
                  f'Got "{value}" for key "{key}"')
            sys.exit(-1)

        base, start, end, step_size = step_args

        if step_size <= 0:
            print(f"💥 Not a valid step size for {key}")
            sys.exit(-1)

        if key in variables:
            print(f"💥 Steps for key {key} specified more than once")

        steps.append(ExponentialSteps(key, base, start, end, step_size))
        variables.add(key)


def parse_list_steps(variables: set[str], steps: list, default_config: dict[str, Parameter], list_args):
    ''' Converts an arguments of parameter list steps into a ListStep objects '''

    for string in list_args:
        try:
            key, value = string.split('=')
        except ValueError:
            print(f'💥 Step command does not contain an equals sign: "{string}"')
            sys.exit(-1)

        try:
            parameter = default_config[key]
        except KeyError:
            print(f'💥 Cannot step "{key}": no such parameter')
            sys.exit(-1)

        if key in variables:
            print(f"💥 Steps for key {key} specified more than once")

        list_steps = value.split(',')
        steps.append(ListSteps(key, list_steps, parameter.type))
        variables.add(key)

def plot_from_toml(default_config: dict[str, Parameter], args):
    ''' Generate plots for a toml file without re-running experiments '''

    result = parse_toml(args.filename, default_config)
    (_steps, variables, _hill_climb, name, _num_iterations, plots) = result

    outfile = f"results/{name}.csv"
    prev_results = parse_previous_results(args, outfile)

    result_printer = ResultPrinter(outfile, variables, name=name,
                                   prev_results=prev_results,
                                   plots=plots)

    result_printer.update_plots(force=True)

def parse_previous_results(args, outfile: str):
    ''' Checks if there are results from a previous run and attempts to reuse them '''

    # load pandas lazily
    from pandas import read_csv # pylint: disable=import-outside-toplevel

    if outfile is None or not isfile(outfile):
        return None

    if args.force_rerun:
        print(f"ℹ️ Found existing file {outfile}, but rerun was forced. "
              f"Will not use results and rename it to {outfile}.old")
        rename(outfile, outfile + ".old")
        return None

    if getmtime(args.filename) > getmtime(outfile):
        if args.force_reuse:
            print(f"ℹ️  Existing file {outfile} appears to be outdated, but reuse was forced!")
        else:
            print(f"ℹ️  Found existing file {outfile}, but appears to be outdated. "
                  f"Will not use results and rename it to {outfile}.old")
            rename(outfile, outfile + ".old")
            return None
    else:
        print(f"ℹ️  Found existing file {outfile}. Will reuse results.")

    return read_csv(outfile, comment='#', header=0,
                        skipinitialspace=True)


def run_from_toml(default_config: dict[str, Parameter], benchmark_func, args, cooldown_time: int):
    ''' Run experiments as defined in a toml file '''

    (steps, variables, hill_climb, name, num_iterations, plots) = parse_toml(args.filename, default_config)

    outfile = f"results/{name}.csv"
    prev_results = parse_previous_results(args, outfile)

    if hill_climb:
        if plots is None:
            print('ERROR: hill climbing only works with an associated plot')
            sys.exit(-1)

        if len(plots) != 1:
            print('ERROR: need exactly one plot for hill climbing')
            sys.exit(-1)

        hill_climb = (plots[0]["y-axis"], plots[0].get("sort-by", None))


    result_printer = ResultPrinter(outfile, variables, name=name,
                                   prev_results=prev_results,
                                   plots=plots)

    params = ParameterSet(steps, variables, default_config)
    config = params.next()

    while config:
        _run_benchmark(benchmark_func, config, args.collect_statistics,
                       result_printer, verbose=args.verbose,
                       num_iterations=num_iterations, hill_climb=hill_climb,
                       cooldown_time=cooldown_time, prev_results=prev_results)
        config = params.next()

def run_from_cmdline(base_config: dict[str, Any], benchmark_func, args, cooldown_time: int):
    ''' Run directly from the command line and do not parse a toml file '''

    print("## Arguments:")
    constant_map = {}
    if args.C:
        for key in parse_constants(base_config, args.C):
            constant_map[key] = base_config[key]

    steps: list = []
    variables: set[str] = set()

    if args.L:
        parse_list_steps(variables, steps, base_config, args.L)

    if args.R:
        parse_linear_steps(variables, steps, base_config, args.R)

    if args.E:
        parse_exponential_steps(variables, steps, base_config, args.E)

    print("##----------")

    result_printer = ResultPrinter(args.outfile, variables)


    params = ParameterSet(steps, variables, constant_map)
    config = params.next()

    prev_results = parse_previous_results(args, args.outfile)

    while config:
        _run_benchmark(benchmark_func, config, args.collect_statistics,
                       result_printer, verbose=args.verbose,
                       num_iterations=args.num_iterations,
                       cooldown_time=cooldown_time, prev_results=prev_results)
        config = params.next()

def benchmark_main(base_config: dict[str, Any], benchmark_func, cooldown_time=5):
    ''' Runs benchmark_func across all specified parameters '''

    base_config = parse_parameters(base_config)
    parser = argparse.ArgumentParser(description="Script to run one or a set of automated benchmarks")
    parser.add_argument("--collect-statistics", required=False, type=str,
                        help="If you want to collect metrics about the CPU and network utilization of individual machines, set this to the hostname of the machine running the benchmark script.")

    subparser = parser.add_subparsers(dest='command')

    subparser.add_parser("print-parameters",
                         help="Shows all benchmark parameters and their default value")

    cmd_parser = subparser.add_parser("cmdline")
    cmd_parser.add_argument("--outfile", type=str,
                            help="Don't start a new log file but append to an existing one (or create a new one with a custom name)")
    cmd_parser.add_argument("--verbose", action="store_true",
                            help="Print output from individual machines to stdout")
    cmd_parser.add_argument("--num-warmups", default=0, type=int,
                            help="How many warmup iterations per configuration.")
    cmd_parser.add_argument("--num-iterations", default=1, type=int,
                            help="How many iterations per configuration. This is useful if you want to capture deviations or percentiles")
    cmd_parser.add_argument("-C", action='append', type=str,
                            help="Set a constant value for a specific parameter")
    cmd_parser.add_argument("-R", action='append', type=str,
                            help="Set a linear rnage for a specific parameter. The script will run a separate experiment for each of them")
    cmd_parser.add_argument("-E", action='append', type=str,
                            help="Set a exponential range for a specific parameter. The script will run a separate experiment for each of them")
    cmd_parser.add_argument("-L", action='append', type=str, help="Set a list of values for a specific parameter. The script will run a separate experiment for each of them")

    toml_parser = subparser.add_parser("toml")
    toml_parser.add_argument("filename", type=str)
    toml_parser.add_argument("--verbose", action="store_true",
                            help="Print output from individual machines to stdout")
    toml_parser.add_argument("--refresh-plots", action='store_true',
                            help='Do no run experiments and just regenerate the plots')

    rerun_group = toml_parser.add_mutually_exclusive_group()
    rerun_group.add_argument("--force-rerun", action='store_true',
                           help='Do not reuse existing results')
    rerun_group.add_argument("--force-reuse", action='store_true',
                           help='Always reuse existing results if any exist')

    args = parser.parse_args()

    try:
        match args.command:
            case "print-parameters":
                print("Base Configuration:")
                for (key, param) in base_config.items():
                    print(f"\t{key}:")
                    if param.type == str:
                        print(f'\t\tDefault Value: "{param.default_value}" '
                              f'(type: {param.type_name})')
                    else:
                        print(f'\t\tDefault Value: {param.default_value} '
                              f'(type: {param.type_name})')
                    print(f"\t\tAbout: {param.about}")
            case "toml":
                if args.refresh_plots:
                    plot_from_toml(base_config, args)
                else:
                    run_from_toml(base_config, benchmark_func, args, cooldown_time)
            case "cmdline":
                run_from_cmdline(base_config, benchmark_func, args, cooldown_time)
            case _:
                raise RuntimeError(f"Unexpected command: {args.command}")
    except (RuntimeError,ClusterError,ConfigurationError) as err:
        print(f"ERROR: {err}")
        sys.exit(1)

    sys.exit(0)
