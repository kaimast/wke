''' Command to generate load plots '''

from sys import stdout
from time import sleep

from wke import plot_loads

def set_up_plot_loads(subparsers):
    ''' Set up arguments for the `plot-loads` command '''

    parser = subparsers.add_parser('plot-loads', help="Plot statistics aggregated by machine class")

    parser.add_argument("logfolder", help="The folder containing the experiments log files")
    parser.add_argument("--follow", '-f', action="store_true",
            help="If this is set, the script will periodically update \
                the loads file instead of terminating after creating it")
    parser.add_argument("--out", default="loads.pdf")
    parser.add_argument("--update-interval", type=int, default=60,
            help="If follow is set, how often should the results file be updated?")
    parser.add_argument("--machine-index", type=int)

    parser.set_defaults(func=_plot_loads_command)

def _plot_loads_command(args):
    print(f'Writing plot to "{args.out}"')

    if args.follow:
        while True:
            plot_loads(args.logfolder, args.out, machine_index=args.machine_index)
            stdout.write('.')
            stdout.flush()
            sleep(args.update_interval)
    else:
        plot_loads(args.logfolder, args.out)
