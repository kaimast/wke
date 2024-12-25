''' Utilities to handle connections to a remote machine '''

from threading import Thread, Event
from time import time, sleep
from typing import Optional

import signal
import socket
import select
import paramiko

from .errors import RemoteExecutionError
from .logging import MachineLogger


# TODO break this apart into multiple classes
# TODO don't use a dedicated thread for every ssh connection
class Task(Thread):
    '''
    Represents the connection to a machine in the cluster.

    Usually, you will not use this directly, but use something like run() instead.
    '''

    def __init__(self, grp_index: int, machine_info, task_name: str, command: str,
                cluster, prelude=None, options: list[str] = [], workdir="",
                verbose=False, grp_size=1, username="", log_dir=None, debug=False):

        # assert isinstance(cluster, Cluster) Creates cyclic dependency

        self._machine_info = machine_info
        self._task_name = task_name
        self._command = command
        self._cluster = cluster
        self._workdir = workdir
        self._options = options
        self._verbose = verbose
        self._group_index = grp_index
        self._group_size = grp_size
        self._username = cluster.username if username in [None, ""] else username
        self._exitcode = None
        self._abort = Event()
        self._was_aborted = False
        self._log_dir = log_dir
        self._prelude = prelude
        self._debug = debug
        self.exception = None

        Thread.__init__(self)

    @property
    def machine_name(self) -> str:
        ''' The name of the associated machine '''
        return self._machine_info.name

    @property
    def group_size(self) -> int:
        '''
        If there are multiple machine executing at once, this indcates,
        how many there are in total
        '''
        return self._group_size

    @property
    def group_index(self) -> int:
        '''
        If there are multiple machine executing at once, this indcates,
        the position/index within that group
        '''
        return self._group_index

    @property
    def name(self):
        ''' Overwrites Thread.name '''
        return f"Connection to {self.machine_name}"

    @property
    def username(self) -> str:
        ''' The username that will be used by the SSH connection '''
        return self._username

    @property
    def external_addr(self):
        ''' Get the public IP/hostname this machine is known by '''
        return self._machine_info.external_addr

    @property
    def task_name(self) -> str:
        '''
            Returns a name/description of the associated task, e.g.,
            the target name.
        '''
        return self._task_name

    @property
    def command(self) -> str:
        ''' Returns the full command, e.g., the contents of the target file '''
        return self._command

    @property
    def exitcode(self) -> Optional[int]:
        '''
        The command's exitcode.
        Only exists if the command finished and was not aborted
        '''
        return self._exitcode

    @property
    def internal_addr(self):
        ''' Get the internal IP/hostname this machine is known by '''
        return self._machine_info.internal_addr

    @property
    def was_aborted(self):
        '''
        Was this task aborted? Will return True after the abort()
        call has been processed by the background Thread.
        '''
        return self._was_aborted

    def abort(self):
        ''' Stop whatever command is running right now '''
        self._abort.set()

    def _generate_options(self) -> str:
        ''' Creates the argument string to pass to the command '''

        options = ""

        for option in self._options:
            options += " "

            # TODO use an enum here
            if isinstance(option, str) and len(option) > 0 and option[0] == "@":
                if option == "@GROUP_INDEX":
                    options += str(self.group_index)
                elif option == "@NAME":
                    options += self._machine_info.name
                elif option == "@EXTERNAL":
                    options += self._machine_info.external_addr
                elif option == "@GROUP_SIZE":
                    options += str(self.group_size)
                elif option == "@INTERNAL":
                    options += self._machine_info.internal_addr
                elif option == "@USERNAME":
                    options += self.username
                else:
                    raise RuntimeError(f'Unknown macro: "{option}"')
            else:
                options += str(option).replace('(', '\\(').replace(')', '\\)')

        return options

    def _generate_command(self):
        ''' Converts the command into a form that can be passed through ssh '''

        if self._workdir != "":
            cmd = f'cd {self._workdir} && '
        else:
            cmd = ""

        if self._prelude and self._prelude != "":
            cmd += self._prelude

        first_line = self.command.splitlines()[0]

        if '#!' not in first_line:
            raise RuntimeError(f"First line of script is not a shebang: {first_line}")

        options = self._generate_options()

        if 'python' in first_line:
            for seq in ["'''", "\"'", "'\""]:
                if seq in self.command:
                    raise RuntimeError(f'Python scripts containing <{seq}> are '
                                       'not supported yet, use <"""> instead')

            code = self.command.replace('"', "'''")
            cmd += f'python3 -c "{code}" {options}'
        elif 'bash' in first_line:
            code = self.command.replace('"', '\\"').replace("'", "\'").replace('$', '\\$')
            # for bash we need to explicitly set argument 0
            cmd += f' printf "{code}" | bash -s {options}'
        else:
            raise RuntimeError(f"Unsupported shebang: {first_line}")

        return cmd

    def run(self):
        '''
            Run the command passed in the constructor.
            This is usually called by Thread.start()
        '''
        try:
            cmd = self._generate_command()
        except RuntimeError as err:
            self.exception = RemoteExecutionError(
                self.machine_name, self.task_name, str(err))
            return

        logger = MachineLogger(self._log_dir, self.machine_name, self._verbose)

        if self._debug:
            logger.log_meta(f'Executing command on "{self.machine_name}": {cmd}')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self._machine_info.external_addr, self._cluster.ssh_port))

            # Prevents initial delay when setting up the connection
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_system_host_keys()

                try:
                    ssh.connect(self._machine_info.external_addr,
                        username=self.username,
                        sock=sock, banner_timeout=60)
                except paramiko.ssh_exception.AuthenticationException as err:
                    print(f"ERROR: Failed to connect to {self.machine_name}: {err}")
                    self.exception = RemoteExecutionError(
                        self.machine_name, self.task_name, str(err))
                    return

                transport = ssh.get_transport()
                channel = transport.open_session()
                channel.set_combine_stderr(False)
                channel.settimeout(1.0)

                # Enabling pseudo terminal breaks stderr forwarding and should
                # not be needed because we always only run a single command
                # channel.get_pty()

                # set up the agent request handler to handle agent
                # requests from the server
                paramiko.agent.AgentRequestHandler(channel)

                channel.exec_command(cmd)

                epoll = select.epoll()
                epoll.register(channel, select.POLLIN)

                stdout_data = bytes()
                stderr_data = bytes()

                while transport.is_active():
                    # Abort the task if we were ask to stop
                    if self._abort.is_set():
                        self._abort.clear()
                        self._was_aborted = True

                        try:
                            channel.shutdown_write()
                            print(f"INFO: Closed channel for {self.machine_name}")
                        except socket.error as err:
                            logger.log_meta(f'Failed to send '
                                f'Ctrl+C to "{self.name}": {err}')

                    changed, stdout_data, stderr_data = self._poll_ssh_connection(
                            stdout_data, stderr_data,
                            logger, channel, epoll)

                    # If the command terminated, close the channel
                    if channel.exit_status_ready():
                        self._exitcode = channel.recv_exit_status()
                        channel.close()

                    # Stop polling if the commmand terminated
                    # or the task was aborted
                    if self.exitcode or (not changed and self.was_aborted):
                        break

            channel.close()
            logger.close()

    def _wait_for_data(self, func):
        ''' Helper to read stdout or stderr output '''
        try:
            return func(1024)
        except socket.timeout:
            return bytes()

    @staticmethod
    def _split_lines(data: bytes, log_func):
        ''' See if data contains full line(s) and log them '''

        lines = data.splitlines(keepends=True)
        newline1 = '\n'.encode()
        newline2 = '\r'.encode()

        for line in lines:
            if newline1 not in line and newline2 not in line:
                # not a complete line yet
                return line

            try:
                # Remove newline and backspace characters
                string = line.decode('utf-8') \
                    .replace('\r','').replace('\n','').replace('\b', '')
                log_func(string)
            except UnicodeDecodeError:
                # Cannot decode yet
                return line

        return bytes()

    def _poll_ssh_connection(self, stdout_data, stderr_data, logger, channel, epoll):
        '''
        Check for any new output to stdout or stderr from the SSH connection

        Output will be passed to split_lines and any complete lines will be processed.
        Incomplete lines are returned by this function and should be passed to it again
        on the next poll.
        '''

        # Poll every second
        events = epoll.poll(timeout=1.0)

        # noop if there is no output
        if len(events) == 0:
            return (False, stdout_data, stderr_data)

        while channel.recv_ready():
            stdout_data += self._wait_for_data(channel.recv)

            if len(stdout_data) > 0:
                stdout_data = self._split_lines(stdout_data, logger.log_info)

        while channel.recv_stderr_ready():
            stderr_data += self._wait_for_data(channel.recv_stderr)

            if len(stderr_data) > 0:
                stderr_data = self._split_lines(stderr_data, logger.log_error)

        return (True, stdout_data, stderr_data)


def _stop_all(tasks: list[Task]):
    ''' Stops all tasks in the given list '''
    for task in tasks:
        task.abort()


def _try_join_task(task: Task, all_tasks: list[Task],
            all_errors: list[str], start_time: float,
            verbose: bool) -> bool:
    ''' Returns True if the tasks finished '''
    task.join(timeout=0.0)

    if task.is_alive():
        return False  # still running

    if task.exitcode is None:
        print(f"⚠️  No exitcode for machine {task.machine_name}")

    if not task.was_aborted and task.exitcode != 0:
        all_errors.append(f'Machine {task.machine_name} had '
                          f'non-zero exitcode {task.exitcode}')
        # stop all others if one failes
        _stop_all(all_tasks)

    if start_time and verbose:
        elapsed = time() - start_time
        print(f'ℹ️ Machine "{task.machine_name}" took {elapsed} seconds to complete.')

    all_tasks.remove(task)

    if len(all_tasks) > 0 and verbose:
        print("Still pending: " + ' '.join([other.machine_name for other in all_tasks]))

    if task.exception:
        raise task.exception

    return True


def join_all(tasks: list[Task], start_time=None, verbose=True,
        timeout=None, use_sighandler=True, poll_interval=0.1) -> list[str]:
    '''
        Blocks until the given tasks have terminated.
        This function returns a list of errors
    '''

    errors: list[str] = []
    has_timed_out = False

    if not start_time:
        start_time = time()

    def signal_handler(_signum, _frame):
        # gracefully shutdown and unmount everything
        print("🛑 Got kill signal. Stopping all machines...")
        _stop_all(tasks)

    if poll_interval < 0.0:
        raise ValueError("Poll interval must be positive or zero")

    if use_sighandler:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    while len(tasks) > 0:
        for task in list(tasks):
            _try_join_task(task, tasks, errors, start_time, verbose)

        elapsed = time() - start_time
        if timeout and elapsed > timeout:
            print("⚠️  Timeout reached: stopping machines")
            has_timed_out = True
            _stop_all(tasks)

        sleep(poll_interval)  # stop all if one fails

    if has_timed_out:
        return []

    return errors
