""" Data collection functionality for measurements """

#pylint: disable=too-many-instance-attributes,consider-using-with

from time import time
from threading import Thread, Condition, Lock
import select
import sys
import struct

from ..tasks import Task, join_all
from ..config import Configuration

from .sockets import SocketListener, MessageType

EPOLL_FLAGS = select.EPOLLERR | select.EPOLLHUP | select.EPOLLIN

LOG_INTERVAL = 0.1 #seconds

STATS = ['cpu', 'mem', 'disk-read', 'disk-write', 'netout', 'netin']

class DataCollector(Thread):
    ''' Collects data, e.g, CPU usage, from the machines '''

    def __init__(self, cluster, config, hostname, log_dir):
        assert isinstance(config, Configuration)

        Thread.__init__(self)
        self._is_okay = True
        self._ready = False
        self._cluster = cluster
        self._config = config
        self._hostname = hostname
        self._conns = {}
        self._log_dir = log_dir

        self._lock = Lock()
        self._cond_var = Condition(self._lock)

    def wait_ready(self):
        ''' Wait for all remote machines to connect to the data collector '''

        with self._lock:
            while not self._ready and self._is_okay:
                self._cond_var.wait()

            if not self._is_okay:
                raise RuntimeError("failed to set up data collector")

    def stop(self):
        ''' Stop data collection '''

        with self._lock:
            self._is_okay = False
            self._cond_var.notify_all()

    def _setup_connections(self):
        socket = SocketListener()
        monitor_port = 51515
        machines = self._cluster.all_machines()

        try:
            # Bind to IP_ANY
            socket.listen('', monitor_port)
        except OSError as err:
            print(str(err))

            with self._lock:
                self._is_okay = False
                self._cond_var.notify_all()

            sys.exit(-1)

        poll_set = select.epoll()

        print(f"Listening for connections on {self._hostname}:{monitor_port}")

        sockets = {}
        tasks = []

        for minfo in machines:
            command = self._config.get_run_cmd('monitor-client')
            args = [self._hostname, monitor_port, minfo.identifier]

            task = Task(0, minfo, "collect-data", command,
                                 self._cluster, args=args, verbose=True)
            task.start()
            tasks.append(task)

        while len(sockets) < len(machines):
            conn = socket.accept()

            if conn:
                fileno = conn.get_fileno()
                poll_set.register(fileno, EPOLL_FLAGS)
                sockets[fileno] = conn
            else:
                print("Still waiting for monitor client connections...")

        return poll_set, sockets, tasks


    def run(self):
        poll_set, sockets, tasks = self._setup_connections()

        load_file = open(f'{self._log_dir}/loads.csv', 'w', encoding='utf-8')
        start = time()
        last_write = start

        load_file.write(f"# start: {start}\n")

        while self._is_okay:
            self._poll_events(sockets, poll_set, load_file)

            # Write to CSV periodically
            if self._ready and time() - last_write >= LOG_INTERVAL:
                last_write = time()
                load_file.write(str(last_write - start))

                for conn in self._conns.values():
                    for stat in STATS:
                        load_file.write(',')
                        load_file.write(str(conn["last_" +stat]))

                load_file.write('\n')

        # cleanup
        for _, socket in sockets.items():
            socket.close()

        join_all(tasks, verbose=False, use_sighandler=False)
        print("Data collector shut down")

    def _poll_events(self, sockets, poll_set, load_file):
        events = poll_set.poll(0.2, maxevents=1)
        num_machines = len(sockets)

        for fileno, _ in events:
            sock = sockets[fileno]

            msgtype, data = sock.receive()

            if msgtype == MessageType.HI:
                conn = {}
                conn["name"] = bytes.decode(data, "utf-8")

                for stat in STATS:
                    conn["last_" + stat] = 0.0
                    conn["sum_" + stat] = 0.0

                conn["count"] = 0
                self._conns[fileno] = conn

                if len(self._conns) == num_machines:
                    print("Got all connections")

                    # create CSV file
                    with self._lock:
                        load_file.write("time")

                        for _, conn in self._conns.items():
                            for stat in STATS:
                                load_file.write(',')
                                load_file.write(conn['name'] + '-' + stat)

                        load_file.write('\n')

                        self._ready = True
                        self._cond_var.notify_all()

            elif msgtype == MessageType.LOAD:
                load = struct.unpack("ffffff", data)
                conn = self._conns[fileno]

                pos = 0

                for stat in STATS:
                    conn["last_" + stat] = load[pos]
                    conn["sum_" + stat] += load[pos]
                    pos += 1

                conn["count"] += 1
            else:
                raise RuntimeError(f"Got unexpected message type: {msgtype}")
