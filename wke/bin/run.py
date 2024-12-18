''' Allows running a target from the commmand line '''

import os
import sys

from .helper import parse_selector, fatal_error, try_get_cluster, try_get_config
from wke.errors import RemoteExecutionError
from wke.run import run, DEFAULT_PRELUDE


def set_up_run(subparsers):
    ''' Set up arguments for the `run` command '''

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
        help=("Do not actually run the command but just check whether "
              " the input looks valid"))
    parser.add_argument('--workdir', type=str,
        help="Use a different working directory than the default one to run the command")
    parser.add_argument('--multiply', type=int, default=1,
        help="Run more than one command per machine?")
    parser.add_argument('--cwd', type=str, help="Change the working directory. \
        Useful if you invoke the command from outside the cluster folder")
    parser.add_argument('--prelude', type=str)
    parser.add_argument('--cluster-file', type=str, default='cluster.toml')
    parser.add_argument('-D', action='append', type=str, dest='options',
        help="Set/overwrite arguments")

    parser.set_defaults(func=_run_command)


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

    cluster = try_get_cluster(args.cluster_file)
    config = try_get_config(args.config_name)

    machines = parse_selector(args.selector, cluster)
    targets = _parse_targets(args.targets, config)

    options = {}

    if args.options:
        if len(targets) > 1:
            raise RuntimeError(("Cannot set non-default options with more "
                                "than one target (yet)"))

        for option in args.options:
            try:
                name, value = option.split('=')
                options[name] = value
            except ValueError:
                print(
                    f'Invalid arguments. '
                    f'Should be of form "<key>=<value>", but was "{option}"'
                )
                sys.exit(1)

    for target in targets:
        if args.prelude:
            prelude = args.prelude
        else:
            prelude = DEFAULT_PRELUDE

        try:
            success = run(machines, config, target, options=options,
                verbose=args.verbose, multiply=args.multiply, prelude=prelude,
                debug=args.debug, dry_run=args.dry_run, workdir=args.workdir)
        except RemoteExecutionError as err:
            print(f"[ERROR] {err}")
            success = False
        except ValueError as err:
            print(f"[ERROR] {err}")
            success = False

        if not success:
            print("Abort.")
            sys.exit(1)

    sys.exit(0)
