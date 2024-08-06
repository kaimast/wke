#! /usr/bin/env python3

"""
The command line interface for wke
"""

# Lazy load pandas to increase startup speed
# pylint: disable=import-outside-toplevel

import os
import sys
import argparse
import subprocess
import json

from sys import stdout
from time import sleep

from .. import run, Configuration, Cluster, ConfigurationError
from .. import ClusterError, plot_loads

def _generate_run_args_parser(subparsers):
    parser = subparsers.add_parser('run', help='Run a target on one or multiple machines')

    parser.add_argument("config_name",
        help="What is the name of the configuration to use? \
            Must be a subfolder of the current directory.")
    parser.add_argument('selector',
        help='Where to run the target? Can be "all", a slice (e.g., [1..5]), \
           or name (e.g., "node5")')
    parser.add_argument('targets',
        help='The target(s) to execute. Can be a single target, "all", or a list')
    parser.add_argument('--verbose', action='store_true',
        help="Print all output of machines to stdout?")
    parser.add_argument('--debug', action='store_true',
        help="Print additional debug information")
    parser.add_argument('--dry-run', action='store_true',
        help="Do not actually run the command but just check whether the input looks valid")
    parser.add_argument('--multiply', type=int, default=1,
        help="Run more than one command per machine?")
    parser.add_argument('--cwd', type=str, help="Change the working directory. \
        Useful if you invoke the command from outside the cluster folder")
    parser.add_argument('--prelude', type=str, default=None)
    parser.add_argument('--cluster-file', type=str, default='cluster.toml')
    parser.add_argument('-D', action='append', type=str, dest='options',
        help="Set/overwrite arguments")

    parser.set_defaults(func=_run_command)

def _generate_get_machine_attribute_args_parser(subparsers):
    parser = subparsers.add_parser('get-machine-attribute',
        help='Show the value of an attribute of a machine in the cluster')
    parser.add_argument('machine_name')
    parser.add_argument('attribute', help='The attribute to show, e.g., "external-addr"')
    parser.add_argument('--cluster-file', '-f', type=str, default='cluster.toml')
    parser.add_argument('--cwd', type=str,
        help=("Change the working directory. "
              "Useful if you invoke the command from outside the cluster folder"))
    parser.set_defaults(func=_get_machine_attribute)

def _generate_show_machine_args_parser(subparsers):
    parser = subparsers.add_parser('show-machine',
        help='Print information about a specific machine in the cluster')
    parser.add_argument('machine_name')
    parser.add_argument('--cluster-file', '-f', type=str, default='cluster.toml')
    parser.add_argument('--cwd', type=str,
        help=("Change the working directory. "
              "Useful if you invoke the command from outside the cluster folder"))
    parser.add_argument("--json", action='store_true',
        help="Instead of a human-readable output, generate a JSON file")
    parser.set_defaults(func=_show_machine)

def _generate_show_cluster_args_parser(subparsers):
    parser = subparsers.add_parser('show-cluster',
        help='Print information about the cluster')
    parser.add_argument('--cluster-file', '-f', type=str, default='cluster.toml')
    parser.add_argument('--cwd', type=str,
        help=("Change the working directory. "
              "Useful if you invoke the command from outside the cluster folder"))
    parser.add_argument("--json", action='store_true',
        help="Instead of a human-readable output, generate a JSON file")
    parser.set_defaults(func=_show_cluster)

def _generate_connect_args_parser(subparsers):
    parser = subparsers.add_parser('connect',
        help='Connect (using SSH) to a machine in the cluster')
    parser.add_argument('machine_name')
    parser.add_argument('--cluster-file', '-f', type=str, default='cluster.toml')
    parser.set_defaults(func=_connect)

def _generate_show_config_args_parser(subparsers):
    parser = subparsers.add_parser('show-config',
        help='Print information about a configuration')
    parser.add_argument("config_name")
    parser.add_argument("--verbose", action='store_true',
        help="Add even morei informatio")
    parser.add_argument("--json", action='store_true',
        help="Instead of a human-readable output, generate a JSON file")
    parser.add_argument('--cwd', type=str,
        help=("Change the working directory. "
              "Useful if you invoke the command from outside the cluster folder"))
    parser.set_defaults(func=_show_config)

def _generate_plot_loads_args_parser(subparsers):
    parser = subparsers.add_parser('plot-loads', help="Plot statistics aggregated by machine class")

    parser.add_argument("logfolder", help="The folder containing the experiments log files")
    parser.add_argument("--follow", '-f', action="store_true",
            help="If this is set, the script will periodically update \
                the loads file instead of terminating after creating it")
    parser.add_argument("--out", default="loads.pdf")
    parser.add_argument("--update-interval", type=int, default=60,
            help="If follow is set, how often should the results file be updated?")
    parser.add_argument("--machine-index", type=int)

    parser.set_defaults(func=_plot_loads)

def _generate_merge_csv_args_parser(subparsers):
    parser = subparsers.add_parser('merge-csv',
            help="Allows to combine two CSV files into a new CSV file")

    parser.add_argument('infile1', type=str)
    parser.add_argument('infile2', type=str)
    parser.add_argument('outfile', type=str)

    parser.set_defaults(func=_merge_csv)

def _show_config(args):
    if args.cwd:
        os.chdir(args.cwd)

    config = Configuration(args.config_name)
    meta = config.generate_metadata(verbose=args.verbose)

    if args.json:
        print(json.dumps(meta))
    else:
        if len(meta["preludes"]) == 0:
            print("\t- Preludes: None")
        else:
            print("\t- Preludes:")
            for name, description in meta["preludes"].items():
                print(f"\t\t* {name}: {description}")
        print('\t- Targets:')

        _print_targets(meta["targets"], args.verbose)

def _show_machine(args):
    if args.cwd:
        os.chdir(args.cwd)

    try:
        cluster = Cluster(path=args.cluster_file)
    except ClusterError as err:
        fatal_error(err)

    machine= cluster.get_machine(args.machine_name).generate_metadata()

    if args.json:
        print(json.dumps(machine))
    else:
        print(f"external-addr={machine['external_addr']}")
        print(f"internal-addr={machine['internal_addr']}")

def _get_machine_attribute(args):
    if args.cwd:
        os.chdir(args.cwd)

    try:
        cluster = Cluster(path=args.cluster_file)
    except ClusterError as err:
        fatal_error(err)

    machine = cluster.get_machine(args.machine_name).generate_metadata()
    value = machine.get(args.attribute, None)

    if value:
        print(value)
    else:
        print(f'ERROR: No such attribute "{args.attribute}"')

def _show_cluster(args):
    if args.cwd:
        os.chdir(args.cwd)

    try:
        cluster = Cluster(path=args.cluster_file)
    except ClusterError as err:
        fatal_error(err)

    meta = cluster.generate_metadata()
    if args.json:
        print(json.dumps(meta))
    else:
        print("\t- Machines")
        for name, machine in meta["machines"].items():
            print(f"\t\t* {name}: external-addr={machine['external-addr']} "
                  f"internal-addr={machine['internal-addr']}")

def _connect(args):
    try:
        cluster = Cluster(path=args.cluster_file)
    except ClusterError as err:
        fatal_error(err)

    minfo = cluster.get_machine(args.machine_name)
    print("Found machine. Launching SSH.")

    subprocess.run(['ssh', f'{cluster.username}@{minfo.external_addr}',
         f'-P{cluster.ssh_port}'], check=False)

def _print_targets(targets: dict, verbose: bool):
    if verbose:
        for name, target in targets.items():
            print(f"\t\t* {name}")
            if "about" in target:
                print(f"\t\t\t- About: {target['about']}")

            if len(target["arguments"]) == 0:
                print("\t\t\t- No arguments")
            else:
                print("\t\t\t- Arguments:")
                for arg in target["arguments"]:
                    if arg['required']:
                        print(f"\t\t\t\t- {arg['name']} [required]")
                    else:
                        print(f"\t\t\t\t- {arg['name']} [default: '{arg['default-value']}']")
    else:
        for name, about in targets.items():
            print(f"\t\t* {name}: {about}")

def fatal_error(message):
    ''' Show an error message and terminate the program '''
    print(f"ERROR: {message}")
    sys.exit(1)

def _parse_selector(selector, cluster):
    ''' Figure out what machines to run on from user input '''

    if selector == "all":
        return cluster

    if selector[0] == "[":
        if selector[-1] != "]":
            fatal_error(("Selector starts with angled bracket, "
                         "but does not end with one."))

        inner = selector[1:-1]

        if ":" in inner:
            start, end = inner.split(":")
            if end <= start:
                fatal_error(f"Invalid range: end({end}) <= start({start})")

            offset = int(start)
            end = int(end)
            num_machines = end - offset

            return cluster.create_subslice(offset, num_machines)

        if "," in inner:
            indices = [int(i) for i in inner.split(',')]
        else:
            indices = [int(inner)]

        return cluster.get_machines_by_indices(indices)

    # This is a single machine
    try:
        machine = cluster.get_machine(selector)
    except ClusterError as err:
        fatal_error(f'{err}')

    return cluster.get_machines_by_indices([machine.index])

def _parse_targets(targets, config):
    ''' Parse targets from user input '''
    if ',' in targets:
        return targets.split(',')
    if '+' in targets:
        fatal_error(('Invalid character "+" in targets. '
                     'Use "," if you want to combine multiple targets'))
    if targets == "all":
        return config.target_names

    return [targets]

def _run_command(args):
    ''' Run a commnad specified by the user '''

    machines = None

    if args.cwd:
        os.chdir(args.cwd)

    try:
        cluster = Cluster(path=args.cluster_file)
        config = Configuration(args.config_name)
    except (ClusterError, ConfigurationError) as err:
        fatal_error(err)

    machines = _parse_selector(args.selector, cluster)
    targets = _parse_targets(args.targets, config)

    options = {}

    if args.options:
        if len(targets) > 1:
            raise RuntimeError("Cannot ovewrite arguments with more than one target (yet)")

        for oarg in args.options:
            try:
                name, value = oarg.split('=')
                options[name] = value
            except ValueError:
                print(
                    f'Invalid arguments. '
                    f'Should be of form "<key>=<value>", but was "{oarg}"'
                )
                sys.exit(1)

    for target in targets:
        try:
            success = run(machines, config, target, options=options,
                verbose=args.verbose, multiply=args.multiply, prelude=args.prelude,
                debug=args.debug, dry_run=args.dry_run)
        except ValueError as err:
            print(f"ERROR: {err}")
            success = False

        if not success:
            print("Abort.")
            sys.exit(1)

    sys.exit(0)

def _plot_loads(args):
    print(f'Writing plot to "{args.out}"')

    if args.follow:
        while True:
            plot_loads(args.logfolder, args.out, machine_index=args.machine_index)
            stdout.write('.')
            stdout.flush()
            sleep(args.update_interval)
    else:
        plot_loads(args.logfolder, args.out)

def _merge_csv(args):
    from pandas import read_csv, concat

    def _extract_constants(path):
        with open(path, 'r', encoding='utf-8') as infile:
            for line in infile.readlines():
                if line.startswith('# constants:'):
                    return line
        fatal_error(f"No constants found in file {path}")
        return ""

    consts1 = _extract_constants(args.infile1)
    consts2 = _extract_constants(args.infile2)

    if consts1 != consts2:
        fatal_error("Cannot merge CSV files: Constants do not match!")

    df1 = read_csv(args.infile1, comment='#', skipinitialspace=True)
    df2 = read_csv(args.infile2, comment='#', skipinitialspace=True)

    merged = concat([df1, df2])

    with open(args.outfile, 'w', encoding='utf-8') as outfile:
        outfile.write(consts1)
        merged.to_csv(outfile, index=False)

def main():
    ''' The main logic for the command line utilities '''

    parser = argparse.ArgumentParser(
            description='Run wke commands to manage a cluster and execute experiments')
    subparsers = parser.add_subparsers(title="Commands", required=True)

    _generate_run_args_parser(subparsers)
    _generate_connect_args_parser(subparsers)
    _generate_get_machine_attribute_args_parser(subparsers)
    _generate_show_machine_args_parser(subparsers)
    _generate_show_cluster_args_parser(subparsers)
    _generate_show_config_args_parser(subparsers)
    _generate_merge_csv_args_parser(subparsers)
    _generate_plot_loads_args_parser(subparsers)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
