'''' Logging utilities for wke '''

import re

from sys import stdout, stderr

from time import strftime, localtime


class MetaLogger():
    '''
        Handles logging from the experiment itself; not a
        specific machine or experiment run
    '''

    def __init__(self, logfolder):
        self._path = f"{logfolder}/META.log"
        self.outfile = open(self._path, 'w', encoding='utf-8')

    def print(self, message):
        ''' Log and print a new message '''
        timestr = strftime("[META %H:%M:%S]:", localtime())

        self.outfile.write(f"{timestr} {message}\n")
        print(f"# {timestr} {message}")

        self.outfile.flush()

    @property
    def path(self):
        ''' Get the path of the output file '''
        return self._path

    def __str__(self):
        return f'Meta logger for file "{self._path}"'


class MachineLogger:
    ''' Logger for a specific machine '''

    def __init__(self, log_dir, name: str, verbose: bool):
        self._name = name
        self._log_file = None
        self._has_error = False
        self._verbose = verbose

        if log_dir:
            self._log_file_name = f"{log_dir}/{name}.log"
            self._log_file = open(self._log_file_name, "a", encoding='utf-8')

            self._log_file.write(f"Output for machine: {name}\n")

    def log_meta(self, msg):
        ''' Log some meta information, e.g. the machine has started '''
        if len(msg) == 0:
            return  # ignore

        self._log(stdout, 'META', msg, True)

    def log_info(self, msg):
        ''' Log a regular message '''
        if len(msg) == 0:
            return  # ignore

        self._log(stdout, 'I', msg, self._verbose)

    def log_error(self, msg):
        ''' Log an error '''
        if len(msg) == 0:
            return  # ignore

        self._has_error = True
        self._log(stderr, 'E', msg, True)

    def _log(self, console, level: str, msg: str, verbose: bool):
        ''' Write output to console and log file '''

        # Remove control codes
        msg = msg.replace('\x08', '')

        if verbose:
            console.write(f"[{self._name} {level}] {msg}\n")

        if self._log_file:
            # Remove color codes
            ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
            msg = ansi_escape.sub('', msg)
            self._log_file.write(msg + "\n")
            self._log_file.flush()

    def close(self):
        ''' Close the log file and stop logging '''
        if self._log_file:
            self._log_file.close()
