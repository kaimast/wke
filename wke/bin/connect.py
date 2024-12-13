''' Command to SSH into a machine'''

import subprocess

from . import try_get_cluster

def set_up_connect(subparsers):
    ''' Set up arguments for the `connect` command '''
    parser = subparsers.add_parser('connect',
        help='Connect (using SSH) to a machine in the cluster')
    parser.add_argument('machine_name')
    parser.add_argument('--cluster-file', '-f', type=str, default='cluster.toml')
    parser.set_defaults(func=_connect)

def _connect(args):
    cluster = try_get_cluster(args.cluster_file)
    minfo = cluster.get_machine(args.machine_name)
    print("Found machine. Launching SSH.")

    subprocess.run(['ssh', f'{cluster.username}@{minfo.external_addr}',
         f'-P{cluster.ssh_port}'], check=False)
