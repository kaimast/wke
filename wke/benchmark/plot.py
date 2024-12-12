''' This is part of the benchmark scripts. See __init__.py for more details. '''

# pylint: disable=too-many-locals,too-many-branches,too-many-arguments,line-too-long,too-many-statements,too-many-positional-arguments

from subprocess import call

from pandas import read_csv
from seaborn import lineplot, barplot, set_theme # type: ignore
from matplotlib import pyplot

def _parse_equation(equation, data):
    if isinstance(equation, str):
        return data[equation]

    left = _parse_equation(equation["left"], data)
    right = _parse_equation(equation["right"], data)

    match equation["op"]:
        case "mul":
            return left*right
        case "div":
            return left/right
        case "add":
            return left+right
        case "sub":
            return left-right
        case _:
            raise RuntimeError("Unsupported operation: {equation['op']}")

def plot_script(path: str, args: list[str]):
    ''' Calls a custom script to create a plot '''
    call([path] + args)

def _maximize_data_by(data, x_axis, y_axis, maximize_by, sort_by=None):
    sort_vals = [None] if sort_by is None else data[sort_by].unique()

    for sort_val in sort_vals:
        if sort_val is None:
            x_vals = data[x_axis]
        else:
            x_vals = data[(data[sort_by] == sort_val)][x_axis]

        for x_val in x_vals.unique():
            prev_val = None
            prev_mean = None

            if sort_val is None:
                subset = data[(data[x_axis] == x_val)]
            else:
                subset = data[(data[x_axis] == x_val) & (data[sort_by] == sort_val)]

            for val in subset[maximize_by].unique():
                mean = subset[subset[maximize_by] == val][y_axis].mean()

                if not prev_mean or mean > prev_mean:
                    prev_mean = mean
                    prev_val = val

            assert prev_val

            # Remove other entries
            if sort_val is None:
                pred = (data[x_axis] != x_val) | (data[maximize_by] == prev_val)
            else:
                pred = (data[x_axis] != x_val) | (data[sort_by] != sort_val) | (data[maximize_by] == prev_val)

            data = data[pred]

    return data

def plot_bars(infile: str, outfile: str, x_axis: str, y_axis, title: str, legend_location="best",
              sort_by=None, maximize_by=None, filter_by=None, x_scale="linear", y_scale="linear", sort_labels=None,
              normalize_by=None, x_label=None, y_label=None, font_size=12, plot_scale=1.0, style="whitegrid"):
    ''' Creates a bar plot for an experiment '''

    print("📈 Generating line plot")

    data = read_csv(infile, comment='#', header=0, skipinitialspace=True)

    if filter_by is not None:
        key = filter_by["key"]
        value = filter_by["value"]

        data = data[(data[key] == value)]

    if isinstance(y_axis, list):
        if len(y_axis) == 0:
            raise RuntimeError("Need at least one y axis")
    else:
        y_axis = [y_axis]

    if len(data.index) == 0:
        print("No data yet. Will not create plot")
        return

    for (pos, suby) in enumerate(y_axis):
        data[f"_y_val{pos}"] = _parse_equation(suby, data)

    if maximize_by is not None:
        data = _maximize_data_by(data, x_axis, "_y_val0", maximize_by, sort_by=sort_by)

    set_theme(style=style)

    pyplot.figure(figsize=(4*plot_scale,3*plot_scale))
    pyplot.tight_layout()
    pyplot.title(title)

    if sort_labels:
        assert isinstance(sort_labels, dict)
        for key in data[sort_by].unique():
            if key not in sort_labels:
                print(f'WARN: Label is missing for sort key "{key}"')
        data[sort_by] = data[sort_by].replace(sort_labels)

    for (pos, suby) in enumerate(y_axis):
        axis = pyplot.subplot(len(y_axis), 1, pos+1)
        barplot(x=x_axis, y=f'_y_val{pos}', errorbar='sd', ax=axis, hue=sort_by, data=data,
                native_scale=True, hue_norm=normalize_by)
        axis.set_xscale(x_scale)
        axis.set_yscale(y_scale)

        if y_scale == "log":
            axis.set_ylim(bottom=1)
        else:
            axis.set_ylim(bottom=0)

        axis.legend(fontsize=font_size, loc=legend_location)

        at_end = pos+1 == len(y_axis)

        if at_end:
            if x_label is None:
                axis.set_xlabel(x_axis, fontsize=font_size)
            else:
                axis.set_xlabel(x_label, fontsize=font_size)
        else:
            axis.set_xlabel("")

        if y_label is None:
            axis.set_ylabel(suby, fontsize=font_size)
        else:
            axis.set_ylabel(y_label, fontsize=font_size)

        pyplot.tick_params(labelsize=font_size)

    _save_plot(outfile)

def _save_plot(outfile):
    try:
        pyplot.savefig(outfile, bbox_inches='tight')
        pyplot.clf()
        print(f"📈 Wrote plot to {outfile}")
    except FileNotFoundError as err:
        raise RuntimeError(f'Failed to write plot to "{outfile}". Does the folder exist?') from err

def plot_lines(infile: str, outfile: str, x_axis: str, y_axis, label: str, legend_location='best',
               sort_by=None, maximize_by=None, filter_by=None, x_scale="linear", y_scale="linear", sort_labels=None,
               set_xticks=False, x_label=None, y_label=None, font_size=12, plot_scale=1.0, style='whitegrid'):
    ''' Creates a line plot for an experiment '''

    print("📈 Generating line plot")

    data = read_csv(infile, comment='#', header=0, skipinitialspace=True)

    if filter_by is not None:
        key = filter_by["key"]
        value = filter_by["value"]

        data = data[(data[key] == value)]

    if isinstance(y_axis, list):
        if len(y_axis) == 0:
            raise RuntimeError("Need at least one y axis")
    else:
        y_axis = [y_axis]

    if len(data.index) == 0:
        print("No data yet. Will not create plot")
        return

    for (pos, suby) in enumerate(y_axis):
        data[f"_y_val{pos}"] = _parse_equation(suby, data)

    if maximize_by is not None:
        data = _maximize_data_by(data, x_axis, "_y_val0", maximize_by, sort_by=sort_by)

    set_theme(style=style)

    pyplot.figure(figsize=(4*plot_scale,3*plot_scale))
    pyplot.tight_layout()
    pyplot.title(label)

    if sort_labels:
        assert isinstance(sort_labels, dict)
        for key in data[sort_by].unique():
            if key not in sort_labels:
                print(f'WARN: Label is missing for sort key "{key}"')
        data[sort_by] = data[sort_by].replace(sort_labels)

    for (pos, suby) in enumerate(y_axis):
        axis = pyplot.subplot(len(y_axis), 1, pos+1)
        lineplot(x=x_axis, y=f'_y_val{pos}', errorbar='sd', ax=axis, hue=sort_by, style=sort_by, data=data,
                 sort=True, markers=True)
        axis.set_xscale(x_scale)
        axis.set_yscale(y_scale)

        if y_scale == "log":
            axis.set_ylim(bottom=1)
        else:
            axis.set_ylim(bottom=0)

        axis.legend(fontsize=font_size, loc=legend_location)

        at_end = pos+1 == len(y_axis)

        if at_end:
            if x_label is None:
                axis.set_xlabel(x_axis, fontsize=font_size)
            else:
                axis.set_xlabel(x_label, fontsize=font_size)
        else:
            axis.set_xlabel("")

        if y_label is None:
            axis.set_ylabel(suby, fontsize=font_size)
        else:
            axis.set_ylabel(y_label, fontsize=font_size)

        if set_xticks:
            axis.set_xticks(data[x_axis].unique())

        pyplot.tick_params(labelsize=font_size)

    _save_plot(outfile)
