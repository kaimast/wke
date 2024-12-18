"""
wsk helps deploying and executing experiments on a compute cluster
"""

from .errors import ConfigurationError, ClusterError, BenchmarkError
from .errors import MeasurementFailedError, RemoteExecutionError, RunTargetError
from .cluster import Cluster
from .config import Configuration
from .run import run, check_run, background_run
from .plot_loads import plot_loads
from .measurement import MeasurementSession, MeasurementResult
from .slice import Slice
from .set import MachineSet

# If we don't set this, the linter might complain
__all__ = [
    "ConfigurationError", "ClusterError", "BenchmarkError", "MeasurementFailedError",
    "RemoteExecutionError", "RunTargetError", "Cluster", "Configuration", "run",
    "check_run", "background_run", "plot_loads", "MeasurementSession",
    "MeasurementResult","Slice", "MachineSet"
]
