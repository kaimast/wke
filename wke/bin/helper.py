''' Helper functions for the commmand line interface '''

import sys

from typing import NoReturn

from wke import Configuration, Cluster, ClusterError, ConfigurationError

def try_get_config(config_name: str) -> Configuration:
    ''' Fetch the specified config and generate an error if
        reading it fails '''
    try:
        return Configuration(config_name)
    except ConfigurationError as err:
        fatal_error(err)

def try_get_cluster(cluster_file: str) -> Cluster:
    '''
        Fetch the specified cluster and generate an error if
        reading it fails
    '''
    try:
        return Cluster(path=cluster_file)
    except ClusterError as err:
        fatal_error(err)

def fatal_error(message) -> NoReturn:
    ''' Show an error message and terminate the program '''
    print(f"[ERROR] {message}")
    sys.exit(1)

def parse_selector(selector, cluster):
    ''' Figure out what machines the user specified '''
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
