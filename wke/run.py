#!/usr/bin/env python3

''' Interfaces to run a target or built-in command on a set of selector '''

# pylint: disable=too-many-branches,too-many-locals,too-many-arguments
# pylint: disable=fixme,too-many-positional-arguments

import multiprocessing

from time import time

from .errors import RemoteExecutionError, RunTargetError
from .util import bash_wrap
from .tasks import Task, join_all
from .cluster import Cluster
from .config import Configuration
from .slice import Slice
from .set import MachineSet

def cleanup(selector, verbose: bool):
    ''' Clean up working directories on the specified selector '''

    if not isinstance(selector, (Slice, Cluster, MachineSet)):
        raise ValueError("selector is not a slice, cluster, or machine set")

    connections = []

    for minfo in selector.get_all_machines():
        if verbose:
            print(f'Cleaning up home directory "{selector.workdir}" on machine\"{minfo.name}"')

        # bash might not be the default shell
        cmd = bash_wrap([f"rm -rf {selector.workdir}/*"])
        machine = Task(0, minfo, "cleanup", cmd, selector.cluster,
                        verbose=verbose, username="root")
        machine.start()
        connections.append(machine)

    print(f"⌛ Waiting for {len(connections)} machine(s) to finish...")
    errors = join_all(connections)

    return len(errors) == 0

def _builtin_install_packages(selector, config: Configuration, verbose: bool,
        use_sudo=True, dry_run=False):
    '''
    Install all debian packages required by the config on the specified selector

    This uses sudo by default, but you can also run as root and without sudo by setting sudo=False
    '''

    if not isinstance(selector, (Slice, Cluster, MachineSet)):
        raise ValueError("selector is not a slice, cluster, or machine set")

    if use_sudo:
        sudo = "sudo "
        user = None
    else:
        sudo = ""
        user = "root"

    machines = selector.get_all_machines()

    tasks = []

    repos = config.required_ubuntu_repositories
    packages = config.required_ubuntu_packages

    if len(repos) == 0 and len(packages) == 0:
        print(("No required ubuntu repositiories or packages found. "
               "Will not install anything."))
        return

    print(f'Adding {len(repos)} repositories and {len(packages)} packages '
          f' to machines {[m.name for m in machines]}')

    if dry_run:
        print("Try run was requested. Will stop here.")
        return

    for minfo in machines:
        add_repos = [sudo+"apt-add-repository "+repo for repo in repos]

        # bash might not be the default shell
        command = bash_wrap(add_repos + [
            sudo+"apt-get update",
            sudo+"apt-get install -y " + " ".join(packages)
        ])

        task = Task(0, minfo, "install-packages", command,
                        selector.cluster, verbose=verbose, username=user)
        task.start()
        tasks.append(task)

    print(f"⌛ Waiting for {len(tasks)} machine(s) to finish...")
    errors = join_all(tasks)

    if len(errors) > 0:
        raise RunTargetError("install-package", errors)

def _parse_options(target, options) -> tuple[list[str], str]:
    '''
        Pick default values for arguments or the one specified in options
    '''

    argv = []
    argstr = []

    if options and not isinstance(options, dict):
        raise ValueError("options must be a dictionary")

    for argument in target.arguments:
        value = argument.default_value

        if options and argument.name in options:
            value = options[argument.name]
            del options[argument.name]

        if value is None:
            raise ValueError(f'No value set for required argument "{argument.name}"')

        argv.append(value)

        argstr.append(f'{argument.name}=`{value}`')

    # Check if there were any invalid options specified
    if options:
        for name in options.keys():
            raise ValueError(f'Got unexpected option "{name}" for target "{target.name}". '
                             f'Allowed options are {target.argument_names}')

    return (argv, ", ".join(argstr))

def run(selector, config, target_name, options=None, verbose=False,
        multiply=1, stdout=None, prelude=None, dry_run=False,
        log_dir=None, timeout=None, debug=False, workdir=None,
        quiet_fail=False) -> bool:
    ''' Runs the specified command(s) in the foreground '''
    try:
        check_run(selector, config, target_name, options=options,
            verbose=verbose, multiply=multiply, stdout=stdout,
            prelude=prelude, dry_run=dry_run, log_dir=log_dir,
            timeout=timeout, debug=debug, workdir=workdir)
        return True
    except RemoteExecutionError as err:
        if not quiet_fail:
            print('❗' + str(err))

        return False

def check_run(selector, config, target_name, options=None, verbose=False,
        multiply=1, stdout=None, prelude=None, dry_run=False,
        log_dir=None, timeout=None, debug=False, workdir=None):
    '''
        This behaves like `run` but, smilar to subprocess.check_call
        will throw an exception on failure
    '''

    if not isinstance(selector, (Slice, Cluster, MachineSet)):
        raise ValueError("selector is not a slice, cluster, or machine set")

    assert isinstance(config, Configuration)

    if target_name == "install-packages":
        if debug:
            print('Found built-in "install-packages"')

        _builtin_install_packages(selector, config,
                   dry_run=dry_run, verbose=verbose)
        return

    target = config.get_target(target_name)
    if target is None:
        raise ValueError(f'No such target "{target_name}"')

    argv, argstr = _parse_options(target, options)

    # Use default if not prelude is specified
    if prelude is None:
        prelude = config.default_prelude
    # User explicitly specified to not use a prelude
    elif prelude in ['None', 'none']:
        prelude = None

    start_time = time()

    if prelude:
        prelude_txt = f' and prelude="{prelude}"'
        prelude = config.get_prelude_cmd(prelude)
    else:
        prelude_txt = ""

    machines = selector.get_all_machines()
    tasks = []

    print((f'ℹ️  Running "{config.name}::{target.name}" on {len(machines)} machine(s) '
           f'with arguments=[{argstr}]') + prelude_txt)

    if dry_run:
        print("dry_run was specified, so I will stop here")
        return

    if not workdir:
        workdir = selector.workdir

    if multiply == 0:
        raise ValueError("`multiply` must be positive")

    if len(machines) == 0:
        raise ValueError("selector cannot be empty")

    # How many SSH connections in total?
    group_size = len(machines) * multiply

    for (pos, minfo) in enumerate(machines):
        for i in range(multiply):
            task = Task(pos*multiply+i, minfo,
                target.name, target.command,
                selector.cluster, args=argv, workdir=workdir,
                verbose=verbose, grp_size=group_size,
                prelude=prelude, log_dir=log_dir, debug=debug)

            task.stdout = stdout
            tasks.append(task)

    for task in tasks:
        task.start()

    errs = join_all(tasks, start_time=start_time, timeout=timeout)

    if len(errs) > 0:
        raise RunTargetError(target.name, errs)

def run_background(*args, **kwargs) -> multiprocessing.Process:
    ''' Runs the specified command(s) in the background '''

    # TODO check arguments before spawning the new process

    proc = multiprocessing.Process(target=run, args=args, kwargs=kwargs)
    proc.start()
    return proc
