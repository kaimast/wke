# wke: A benchmarking tool for distributed systems  

[![ci-badge](https://github.com/kaimast/wke/actions/workflows/ci.yml/badge.svg)](https://github.com/kaimast/wke/actions)
[![PyPI](https://img.shields.io/pypi/v/PACKAGE?label=wke)](https://pypi.org/project/wke/)

This tool can deploy and measure the behavior of distributed systems. However, it is not a general framework for running things on remote machines but tailored to the specific task of running experiments/benchmarks.

See [this blogpost](https://kaimast.com/notes/wickie/) for a detailed description of wke.

## Installation

You need a recent version of Python (the scripts were only tested with python3.10 and above) and `pip`.

Then, simply run `make install` to install the wke library and command.

## Clusters and Configurations

A *cluster* is a set of machines (physical or virtual) that will be used to run experiments.
Clusters groups machines into *classes*. Each class should represent a role in your distributed system.
For example, a simple benchmark might have two classes: clients and servers.

A *configuration* is a set of scripts for a specific project (or variant of a project). You can set up multiple configurations for a single cluster.

Each configuration resides in a dedicated folder that has the following layout:

### {CONFIG}/config.toml

A TOML file that describes all targets and settings specific to that configuration. Targets are scripts that can be run on machines of the cluster.

### {CONFIG}/targets

Targets are scripts that execute as part of your experiment or to set up the experiment. For example, it could be script that runs your server process, or one that issues client requests.

You will execute them using the `wke run` command.

### {CONFIG}/preludes

Preludes are not targets, but can help reducing boilerplate code in a target. For example, they can be used to export environment variables before running experiments.

In most cases as single engine file should suffice to run your experiments.
