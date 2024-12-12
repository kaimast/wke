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

class RunTargetError(Exception):
    ''' Error created when calling check_run. Captures errors on multiple machines '''
    def __init__(self, target: str, errors: list[str]):
        assert len(errors) > 0, "at least one failure must have happened"

        self._target = target
        self._errors = errors

    def __str__(self) -> str:
        msg = f"Error while running target {self.target}: \n"
        msg += '\n'.join(f'\t💥 {err}' for err in self._errors)
        return msg

    @property
    def target(self) -> str:
        ''' The target that we failed to execute '''
        return self._target

    @property
    def machine_errors(self) -> list[str]:
        ''' Get the individual per-machine errors '''
        return self._errors

class MeasurementFailedError(Exception):
    ''' Indicates the measurement was not successful '''

class ConfigurationError(Exception):
    ''' Errors generated when parsing a config or target file '''

class BenchmarkError(Exception):
    ''' Errors generated when running benchmarks '''

class ClusterError(Exception):
    ''' Errors generated when parsing a cluster.toml file '''
