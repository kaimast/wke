''' Utilities to generate plots about the load in the cluster '''

# pylint: disable=too-many-locals

# Lazy load pandas and matplotlib to increase startup speed
# pylint: disable=import-outside-toplevel

from os import path

import json

from .cluster import Cluster


def _find_start_end(statsfile, logfile):
    mstart = -1
    mend = -1

    if path.isfile(statsfile):
        absolute_start = 0

        with open(logfile, "r", encoding='utf-8') as hdl:
            line = hdl.readline()
            line.replace('\n', '')

            prefix_len = len("# start: ")
            absolute_start = float(line[prefix_len:])

        with open(statsfile, "r", encoding='utf-8') as hdl:
            dat = json.load(hdl)
            mstart = dat["start_time"] - absolute_start
            mend = dat["end_time"] - absolute_start

            if mstart < 0:
                print("Start is < 0!")

    return (mstart, mend)


def plot_loads(logfolder, outfile, machine_index=None):
    ''' Creates a plot from a loads.csv file '''

    from pandas import read_csv
    import matplotlib.pyplot as plt
    import matplotlib

    matplotlib.use("agg")
    matplotlib.rcParams.update({'font.size': 5})

    cluster = Cluster()

    logfile = logfolder + "/loads.csv"
    statsfile = logfolder + "/stats.json"

    try:
        data = read_csv(logfile, header=0, sep=",", decimal=".", index_col=0,
                skipinitialspace=True, comment='#')

        if len(data) == 0:
            print("No data yet...")
            return
    except IOError as err:
        print(str(err))
        return

    titles = ["CPU load", "Memory Usage", "Disk (read)",
              "Disk (write)", "Network (in)", "Network (out)"]
    ylabels = ["Percent", "Percent", "Mbits/s", "Mbits/s", "Mbits/s", "Mbits/s"]

    mstart, mend = _find_start_end(statsfile, logfile)

    for pos, stat in enumerate(["cpu", "mem", "disk-read",
                                "disk-write", "netin", "netout"]):
        loads = {}

        for (idx, minfo) in enumerate(cluster.get_all_machines()):
            if machine_index is not None and idx != machine_index:
                continue

            raw_val = data[f"{minfo.name}_{stat}"]
            machine_vals = []

            for val in raw_val:
                try:
                    if pos == 1:
                        val = val * 100.0
                    elif pos in [2, 3, 4, 5]:
                        val = val / (1024 * 1024)
                except TypeError:
                    print(f"Failed to parse '{val}'. Not a number?")
                    val = 0.0

                machine_vals.append(val)

            loads[minfo.name] = machine_vals

        colors = ['r', 'g', 'b', 'y', 'black', 'grey']
        linestyles = ['-', '--', '-.', ':']

        plt.subplot(len(titles), 1, pos + 1)

        for idx, (name, values) in enumerate(loads.items()):
            plt.plot(data.index, values, colors[idx % len(colors)], label=name,
                    linestyle=linestyles[idx % len(linestyles)])

        if mstart >= 0:
            plt.axvline(x=mstart, color='g')

        if mend >= 0:
            plt.axvline(x=mend, color='r')

        plt.ylabel(ylabels[pos])
        plt.title(titles[pos])
        plt.legend()

    plt.tight_layout()
    plt.savefig(outfile)

    plt.close()
