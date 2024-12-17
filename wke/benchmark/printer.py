''' This is part of the benchmark scripts. See __init__.py for more details. '''

import sys

from time import localtime, strftime
from os.path import isfile, getmtime

from .plot import plot_lines, plot_bars, plot_script


class ResultPrinter:
    ''' This lazily creates results file only when there are results to print '''

    def __init__(self, file_name: str, variables: set[str], plots=None,
                 name=None, prev_results=None):
        self._uid = strftime("%y%m%d-%H%M%S", localtime())
        self.variables = variables
        self.created_file = prev_results is not None
        self._plots = plots
        self._name = name if name else self._uid
        self._exp_ids = []

        if prev_results is not None:
            for uid in prev_results['uid']:
                self._exp_ids.append(uid)

        if file_name:
            self._results_fname = file_name
        else:
            self._results_fname = f'results/results-{self.uid}.csv'

    @property
    def uid(self) -> str:
        ''' Unique id for this experiment based on the current time '''
        return self._uid

    def _create_file(self, param_keys: list[str], extra_params: dict, constants: dict):
        ''' Create the CSV file and write its header '''

        self.created_file = True

        constants_str = ' '.join(f"{k}={v}" for (k,v) in constants.items())

        try:
            with open(self._results_fname, 'w', encoding='utf-8') as results_file:
                # write command line arguments and csv header
                results_file.write(f"# command: {' '.join(sys.argv)}\n")
                # write constants as another command
                results_file.write(f'# constants: {constants_str}\n')
                results_file.write("# ----------------------------- \n")
                plabels = ', '.join(['uid'] + param_keys + list(extra_params.keys()))
                results_file.write(f"{plabels}\n")
            print(f"New file created: {self._results_fname}")
        except OSError as err:
            raise RuntimeError('Failed to create results file at '
                    f'"{self._results_fname}". Does the folder exist?') from err

    def print(self, uid: str, params: dict[str,str], extra_params: dict[str,str]):
        ''' Store a new result in the file '''

        assert len(params) > 0

        param_values = []
        param_keys = []
        constants = {}

        for key, value in params.items():
            if key in self.variables:
                param_keys.append(key)
                param_values.append(value)
            else:
                constants[key] = value

        if not self.created_file:
            self._create_file(param_keys, extra_params, constants)

        val_strs = map(str, param_values + list(extra_params.values()))

        with open(self._results_fname, 'a', encoding='utf-8') as results_file:
            results_file.write(f"{uid}, ")
            results_file.write(", ".join(val_strs) + '\n')
            results_file.flush()
            print(f'Wrote results to "{self._results_fname}"')

        self._exp_ids.append(uid)

        if self._plots is not None:
            self.update_plots()

    def update_plots(self, force=False):
        ''' Refresh all plots for this experiment '''

        # load pandas lazily
        from pandas import read_csv

        plots = self._plots
        had_main_plot = False
        labels = set()

        for plot_args in plots:
            if "label" in plot_args:
                label = plot_args["label"]
                if label in labels:
                    raise RuntimeError(f'Plot label "{label}" used more than once!')
                labels.update(label)

                outname = f"plots/{self._name}_{label}.pdf"
            else:
                if had_main_plot:
                    raise RuntimeError("Only one plot can have no label!")
                had_main_plot = True
                label = None
                outname = f"plots/{self._name}.pdf"

            if not force and isfile(outname) and \
               getmtime(self._results_fname) <= getmtime(outname):
                print(f'☑️  Plot "{label}" up to date')
                return

            x_label = plot_args.get("x-label", None)
            y_label = plot_args.get("y-label", None)
            title = plot_args.get("title", None)
            sort_by = plot_args.get("sort-by", None)
            sort_labels = plot_args.get("sort-labels", None)
            filter_by = plot_args.get("filter-by", None)
            plot_scale = plot_args.get("plot-scale", 1.0)
            font_size = plot_args.get("font-size", 12)
            maximize_by = plot_args.get("maximize-by", None)
            normalize_by = plot_args.get("normalize-by", None)
            set_xticks = plot_args.get("set-xticks", False)
            legend_location = plot_args.get("legend-location", "best")
            style = plot_args.get("style", None)
            x_scale = plot_args.get("x-scale", "linear")
            y_scale = plot_args.get("y-scale", "linear")

            if title is None:
                if label:
                    title = f"{self._name}: {label}"
                else:
                    title = self._name

            match plot_args["type"]:
                case "line":
                    x_axis = plot_args["x-axis"]
                    y_axis = plot_args["y-axis"]

                    plot_lines(self._results_fname, outname, x_axis, y_axis,
                          title, sort_by=sort_by, filter_by=filter_by,
                          maximize_by=maximize_by, x_scale=x_scale, y_scale=y_scale,
                          set_xticks=set_xticks, x_label=x_label, y_label=y_label,
                          sort_labels=sort_labels, font_size=font_size, style=style,
                          plot_scale=plot_scale, legend_location=legend_location)
                case "bar":
                    x_axis = plot_args["x-axis"]
                    y_axis = plot_args["y-axis"]

                    plot_bars(self._results_fname, outname, x_axis, y_axis,
                          title, sort_by=sort_by, filter_by=filter_by,
                          maximize_by=maximize_by, x_scale=x_scale, y_scale=y_scale,
                          normalize_by=normalize_by, x_label=x_label, y_label=y_label,
                          sort_labels=sort_labels, font_size=font_size, style=style,
                          plot_scale=plot_scale, legend_location=legend_location)
                case "script":
                    path = plot_args["path"]
                    args = []
                    for arg_in in plot_args["args"]:
                        if arg_in.startswith('@EXPFOLDER:'):
                            index = int(arg_in.replace('@EXPFOLDER:', ''))
                            arg = f"logs/experiment-{self._exp_ids[index]}"
                        elif arg_in.startswith('@VALUE:'):
                            index, key = arg_in.replace('@VALUE:', '').split(':')
                            data = read_csv(self._results_fname, comment='#',
                                            header=0, skipinitialspace=True)
                            arg = str(data.iloc[int(index)][key])
                        else:
                            arg = arg_in.replace('@PLOT_NAME', outname)
                        args.append(arg)
                    plot_script(path, args)
                case _:
                    raise RuntimeError(f"Unknown plot type: {plot_args['type']}")
