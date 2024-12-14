#! /usr/bin/python3

''' Utility to restart machines in the cluster '''

import argparse

from .cluster import Cluster
from .tasks import Task, join_all


def _main():
    parser = argparse.ArgumentParser(description='reboot a set of machines')
    _ = parser.parse_args()

    cluster = Cluster()

    target_machines = cluster.get_all_machines()

    tasks = []

    for minfo in target_machines:
        task = Task(0, minfo, "reboot", "reboot", cluster)
        task.start()
        tasks.append(task)

    join_all(tasks)


if __name__ == "__main__":
    _main()
