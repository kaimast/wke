"""
The command line interface for wke
"""

import sys
import os
import argparse

from typing import NoReturn

from wke import Cluster, ClusterError, Configuration, ConfigurationError

from .helper import try_get_cluster, fatal_error
from .csv import set_up_merge_csv
from .plot import set_up_plot_loads
from .show import set_up_show_config, set_up_show_machine, set_up_show_cluster
from .connect import set_up_connect
from .run import set_up_run


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

def _get_machine_attribute(args):
    if args.cwd:
        os.chdir(args.cwd)

    cluster = try_get_cluster(args.cluster_file)
    machine = cluster.get_machine(args.machine_name).generate_metadata()
    value = machine.get(args.attribute, None)

    if value:
        print(value)
    else:
        print(f'[ERROR] No such attribute "{args.attribute}"')

def main():
    ''' The main logic for the command line utilities '''

    parser = argparse.ArgumentParser(
            description='Run wke commands to manage a cluster and execute experiments')
    subparsers = parser.add_subparsers(title="Commands", required=True)

    _generate_get_machine_attribute_args_parser(subparsers)

    set_up_run(subparsers)
    set_up_merge_csv(subparsers)
    set_up_plot_loads(subparsers)
    set_up_connect(subparsers)
    set_up_show_machine(subparsers)
    set_up_show_cluster(subparsers)
    set_up_show_config(subparsers)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
