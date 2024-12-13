''' Functions to print information in the command line '''

import os
import json

from .helper import try_get_cluster, try_get_config

def set_up_show_machine(subparsers):
    ''' Set up arguments for the `show-machine` commmand '''

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

def set_up_show_cluster(subparsers):
    ''' Set up arguments for the `show-cluster` command '''

    parser = subparsers.add_parser('show-cluster',
        help='Print information about the cluster')
    parser.add_argument('--cluster-file', '-f', type=str, default='cluster.toml')
    parser.add_argument('--cwd', type=str,
        help=("Change the working directory. "
              "Useful if you invoke the command from outside the cluster folder"))
    parser.add_argument("--json", action='store_true',
        help="Instead of a human-readable output, generate a JSON file")
    parser.set_defaults(func=_show_cluster)

def set_up_show_config(subparsers):
    ''' Set up arguments for the `show_config` command '''

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

def _list_level1(content: str):
    print(f' ⦿ {content}')

def _list_level2(content: str):
    print(f'   - {content}')

def _list_level3(content: str):
    print(f'      • {content}')

def _print_targets_verbose(targets: dict):
    for name, target in targets.items():
        _list_level1(name)
        if "about" in target:
            _list_level2(f"About: {target['about']}")

        if len(target["arguments"]) == 0:
            _list_level2("No arguments")
            continue

        _list_level2("Arguments:")
        for arg in target["arguments"]:
            if arg['required']:
                _list_level3(f"{arg['name']} [required]")
            else:
                _list_level3(f"{arg['name']} [default: '{arg['default-value']}']")

def _print_targets(targets: dict):
    for name, about in targets.items():
        print(f" ⦿ {name}: {about}")



def _show_config(args):
    ''' Show information about the configuration '''

    if args.cwd:
        os.chdir(args.cwd)

    config = try_get_config(args.config)
    meta = config.generate_metadata(verbose=args.verbose)

    if args.json:
        print(json.dumps(meta))
    else:
        if len(meta["preludes"]) == 0:
            print("Preludes: None")
        else:
            print("Preludes:")
            for name, description in meta["preludes"].items():
                _list_level1(f"{name}: {description}")
        print('')
        print('Targets:')
        if args.verbose:
            _print_targets_verbose(meta["targets"])
        else:
            _print_targets(meta["targets"])

def _show_machine(args):
    if args.cwd:
        os.chdir(args.cwd)

    cluster = try_get_cluster(args.cluster_file)
    machine= cluster.get_machine(args.machine_name).generate_metadata()

    if args.json:
        print(json.dumps(machine))
    else:
        print(f"external-addr={machine['external_addr']}")
        print(f"internal-addr={machine['internal_addr']}")

def _show_cluster(args):
    ''' Print informmation about a givne cluster '''

    if args.cwd:
        os.chdir(args.cwd)

    cluster = try_get_cluster(args.cluster_file)
    meta = cluster.generate_metadata()
    if args.json:
        print(json.dumps(meta))
        return

    _list_level2("Machines")
    for name, machine in meta["machines"].items():
        _list_level3(f"{name}: external-addr={machine['external-addr']}"
            f"internal-addr={machine['internal-addr']}")
