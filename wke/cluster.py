''' API encapsulating all the information from the cluster.toml file '''

from typing import Optional, Any
from subprocess import call, CalledProcessError

import shlex
import tomllib
import paramiko

from .slice import Slice
from .set import MachineSet
from .errors import RemoteExecutionError
from .machines import MachineInfo
from .errors import ClusterError


class Cluster:
    ''' Holds the contents of the cluster.toml file '''

    def __init__(self, path: str = 'cluster.toml'):
        if not isinstance(path, str) or len(path) == 0:
            raise ClusterError("Path for cluster file must be a non-empty string")

        try:
            with open(path, 'rb') as file:
                self.cluster_toml = tomllib.load(file)
        except OSError as err:
            raise ClusterError(f"Cannot open cluster file at {path}: {err}") from err
        except tomllib.TOMLDecodeError as err:
            raise ClusterError(f"Failed to parse cluster file at {path}: {err}") from err

        # Validate and print warnings/errors if needed
        for req in ["cluster", "machines"]:
            if req not in self.cluster_toml:
                raise ClusterError(f'{path} is missing required field "{req}"')

        for req in ["username"]:
            if req not in self.cluster_toml["cluster"]:
                raise ClusterError(f'{path} is missing required field "cluster.{req}"')

        machines_toml = self.cluster_toml["machines"]

        # Ordered list of all machines as they are defined in the toml file
        self._machines: list[MachineInfo] = []

        # Index of machines by name
        self._machine_names: dict[str, MachineInfo] = {}

        if isinstance(machines_toml, dict):
            for name, machine_def in machines_toml.items():
                self._parse_machine(name, machine_def)
        elif isinstance(machines_toml, list):
            for machine_def in machines_toml:
                self._parse_machine(None, machine_def)
        else:
            raise RuntimeError('"machines" is neither a dictionariy nor a list')

    def generate_metadata(self) -> dict[str, Any]:
        ''' Create a dictionary containing information about this cluster '''

        machines = {}
        for info in self._machines:
            machines[info.name] = info.generate_metadata()

        return {"machines": machines}

    def _parse_machine(self, name, machine_def):
        '''
        Reads the machine definiton (from disk) and adds it to the cluster
        '''

        if isinstance(machine_def, dict):
            if "external_addr" in machine_def:
                external_addr = machine_def["external_addr"]
            else:
                raise RuntimeError(f"Machine definition is missing external address: "
                                   f"{machine_def}")

            if "internal_addr" in machine_def:
                internal_addr = machine_def["internal_addr"]
            else:
                internal_addr = external_addr

        elif isinstance(machine_def, list):
            if len(machine_def) == 0:
                raise RuntimeError("Machine definition is an empty list")

            if len(machine_def) == 1:
                external_addr = internal_addr = machine_def[0]
            else:
                external_addr = machine_def[0]
                internal_addr = machine_def[1]

        elif isinstance(machine_def, str):
            external_addr = internal_addr = machine_def
        else:
            raise RuntimeError(f"Failed to parse machine definition: {machine_def}")

        if name is None:
            name = external_addr

        assert isinstance(name, str) and name != ""

        if len(name) == 0:
            raise RuntimeError("Machine name is an empty string")

        if len(external_addr) == 0:
            raise RuntimeError("Machine's external address is an empty string")

        if len(internal_addr) == 0:
            raise RuntimeError("Machine's internal address is an empty string")

        index = len(self._machines)
        minfo = MachineInfo(name, index, external_addr, internal_addr)
        self._machines.append(minfo)
        self._machine_names[name] = minfo

    @property
    def workdir(self) -> str:
        '''
            Returns the working directory that will be used when running scripts
            on the cluster
        '''
        workdir = self.cluster_toml["cluster"].get("workdir", None)
        if workdir:
            return workdir

        return "/home/" + self.username

    @property
    def username(self) -> str:
        '''
            Returns the default username that will be used when ssh-ing
            into the cluster
        '''
        return self.cluster_toml["cluster"]["username"]

    @property
    def ssh_port(self) -> int:
        '''
            Returns the default port that this cluster_toml
            will use when ssh-ing into the cluster
        '''
        if "ssh-port" in self.cluster_toml["cluster"]:
            return self.cluster_toml["cluster"]["ssh-port"]

        return 22

    @property
    def cluster(self):
        '''
            Returns this cluster.
            This function only exists so Slice and Cluster can be treated the same.
        '''
        return self

    def get_absolute_index(self, idx: int) -> int:
        ''' Used by slices '''
        return idx

    @property
    def num_machines(self) -> int:
        ''' Get the total number of machines in this cluster '''
        return len(self._machines)

    def create_slice(self) -> Slice:
        ''' Create a new slice containing all machines in this cluster '''
        return Slice(self, self, 0, len(self._machines))

    def create_subslice(self, offset: Optional[int], size: Optional[int]) -> Slice:
        ''' Create a new slice containing a range of machine from this cluster '''
        if offset is None and size is None:
            raise RuntimeError("Must either specficy offset or size")

        s = self.create_slice()

        if offset:
            s.advance_cursor(offset)

        if size is None:
            return s.create_subslice(s.remaining_size())

        return s.create_subslice(size)

    def get_machine(self, machine_name: str) -> MachineInfo:
        ''' Get the information for a machine with the specified name '''
        try:
            return self._machine_names[machine_name]
        except KeyError as err:
            raise ClusterError(f'No machine with name "{machine_name}"') from err

    def get_machine_by_index(self, index: int) -> MachineInfo:
        ''' Get the information for a machine with the specified index '''
        return self._machines[index]

    def get_machines_by_indices(self, indices: list[int]) -> MachineSet:
        ''' Get a set of machines from the specified indices '''
        return MachineSet(self, self, indices)

    def get_all_machines(self):
        ''' Get all machines '''
        return self._machines

    @property
    def machine_names(self) -> list[str]:
        ''' Get the names of all machines in this cluster '''
        return [minfo.name for minfo in self.get_all_machines()]

    def copy_to(self, machine: str, source: str, destination: str,
                username: Optional[str] = None):
        '''
            Copy a file from the local computer to a machine.

            The username flag determines as which user we invoke SSH
            (will be the clusters default user if not specified)
        '''

        if not username:
            username = self.username

        print(f"{source} -> {machine}:{destination}")

        cmd = (f'rsync -zrp --rsh="ssh -o UserKnownHostsFile=/dev/null '
               f'-p{self.ssh_port} -o StrictHostKeyChecking=no" {source} '
               f'{username}@{self.get_machine(machine).external_addr}:{destination}')

        try:
            call(shlex.split(cmd))
        except CalledProcessError as err:
            raise RemoteExecutionError(machine, cmd, "rsync failed: {err}") from err

    def copy_from(self, machine: str, source: str, destination: str,
                  username: Optional[str] = None):
        ''' Copy a file from a machine to the local computer '''

        print(f"{machine}:{source} -> {destination}")

        cmd = (f'rsync -zrp --rsh="ssh -o UserKnownHostsFile=/dev/null '
               f'-p{self.ssh_port} -o StrictHostKeyChecking=no" '
               f'{self.username}@{self.get_machine(machine).external_addr}:source '
               f'{destination}')

        try:
            call(shlex.split(cmd))
        except CalledProcessError as err:
            raise RemoteExecutionError(machine, cmd, "rsync failed: {err}") from err

    def execute_on(self, machine: str, cmd: str):
        ''' Execute a single command on a machine '''

        address = self.get_machine(machine).external_addr

        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_system_host_keys()

            # Connection setup can take quite long with a large cluster
            # better to be conservative here with the banner_timeout
            ssh.connect(address, username=self.username, port=self.ssh_port,
                        banner_timeout=60)

            transport = ssh.get_transport()
            if not transport:
                raise RuntimeError("Failed to establish transport")

            channel = transport.open_session()
            channel.get_pty()
            channel.set_combine_stderr(True)
            channel.setblocking(True)

            # set up the agent request handler to handle agent requests from the machine
            paramiko.agent.AgentRequestHandler(channel)

            cmdstr = ' '.join(cmd)
            print(f"Running command: {cmdstr}")

            channel.exec_command(cmdstr)
            stdout = channel.makefile()

            for line in stdout.readlines():
                print(line)

            stdout.close()

    def open_remote(self, filename: str, offset=0,
                    skip_missing=False, num_machines=None):
        '''
            Copy and open files that are stored on a remote machine.
            This returns a list of file handles.

            If you set set skip_missing to True, it will not throw
            an error when a file is missing.

            If you set num_machines to some value N, it will only open files
            on the first n machines.
        '''

        result = []

        all_machines = self.get_all_machines()
        if offset + num_machines > len(all_machines):
            raise RuntimeError("Invalid offset or num_machines")

        for minfo in all_machines[offset:offset + num_machines]:
            target = "/tmp/cluster_" + minfo.name
            print(f'{minfo.name}:{filename} -> {target}')

            cmd = (f'rsync -zrp --rsh="ssh -o UserKnownHostsFile=/dev/null '
                   f'-p{self.ssh_port} -o StrictHostKeyChecking=no" '
                   f'{self.username}@{minfo.external_addr}:{filename} {target}')

            if call(shlex.split(cmd)) != 0:
                msg = "command has non-zero returncode\n" + cmd

                if skip_missing:
                    print(f"Warning: {msg}")
                    continue

                raise RemoteExecutionError(minfo.name, cmd, msg)

            try:
                hdl = open(target, "r", encoding='utf-8')
                result.append(hdl)
            except OSError as exc:
                msg = f'no remote file "{filename}" on machine "{minfo.name}"'

                if skip_missing:
                    print(f'Warning: {msg}')
                else:
                    raise RemoteExecutionError(minfo.name, cmd, msg) from exc

        return result
