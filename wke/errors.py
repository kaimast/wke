''' Error types used by wsk '''

class RemoteExecutionError(Exception):
    ''' Errors generated when running a command on another machine '''
    def __init__(self, machine: str, command: str, msg: str):
        self._machine = machine
        self._command = command
        self._message = msg

    @property
    def message(self):
        ''' The error message generated '''
        return self._message

    @property
    def command(self):
        ''' The command that was executed '''
        return self._command

    @property
    def machine(self):
        ''' The name of the machine where the error occurred '''
        return self._machine

    def __str__(self):
        return f"Error on {self.machine} for command {self.command}: {self.message}"

class MeasurementFailedError(Exception):
    ''' Indicates the measurement was not successful '''

class ConfigurationError(Exception):
    ''' Errors generated when parsing a config or target file '''

class BenchmarkError(Exception):
    ''' Errors generated when running benchmarks '''

class ClusterError(Exception):
    ''' Errors generated when parsing a cluster.toml file '''
