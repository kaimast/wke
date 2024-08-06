'''
Basic wrapper around TCP sockets to make connecting to machines easier

Only used by a DataCollector
'''

from enum import IntEnum

import socket as bsdsocks
import struct
import errno

TIMEOUT = 10

class MessageType(IntEnum):
    ''' Message types supported '''

    # Establish initial connection
    HI = 1
    # Send load information
    LOAD = 2

class Peer:
    ''' Represents the connection to another machine/server '''

    def __init__(self, socket, addr):
        self.socket = socket
        self.address = addr
        self.connected = True
        self.messages = []
        self.prev = bytes()

        self.socket.setsockopt(bsdsocks.IPPROTO_TCP, bsdsocks.TCP_NODELAY, True)
        self.socket.setblocking(0)

        assert not self.has_messages()

    def is_connected(self):
        ''' Are we (still) connected to the peer '''
        return self.connected

    def get_fileno(self):
        ''' Get the underlying file descriptor of this TCP connection '''
        return self.socket.fileno()

    def _get_messages(self):
        '''
            Try to fetch messages from the socket and return messages if there are any.
            Returns true if there are no more messages.
        '''
        try:
            data = self.socket.recv(1024)
        except bsdsocks.timeout:
            return True
        except bsdsocks.error as err:
            if err.errno == errno.ECONNRESET:
                self.close()
                return True

            if err.errno == errno.EWOULDBLOCK:
                return True

            raise

        if len(data) == 0:
            self.messages.append((None, None))
            self.close()
            return True

        pos = 0
        data = self.prev + data
        self.prev = bytes()

        while data and (pos < len(data)):
            header_len = struct.calcsize("IH")

            if (len(data)-pos) < header_len:
                self.prev = data[pos:]
                data = None
                break

            array = struct.unpack("IH", data[pos:pos+header_len])
            msg_len = array[0]
            msgtype = array[1]
            start = pos
            pos += header_len

            if msg_len > 0:
                if len(data) < pos+msg_len:
                    self.prev = data[start:]
                    break

                content = data[pos:pos+msg_len]
                pos += msg_len

                self.messages.append((msgtype, content))
            else:
                self.messages.append((msgtype, ""))

        return False

    def has_messages(self):
        ''' Are there any messages queue up? '''
        return len(self.messages) > 0

    def receive(self):
        '''
            Blocks until we receive data or the connection is closed

            If a full message is receive, the function returns its type and content
            If the connection was closed it returns (None, None)
        '''

        if not self.is_connected():
            raise RuntimeError("Cannot receive on invalid socket")

        while self.is_connected():
            done = self._get_messages()
            if done:
                break

        if self.has_messages():
            val = self.messages.pop(0)
            return val

        assert not self.is_connected()
        return (None, None)

    def close(self):
        ''' Close this connection '''

        self.socket.close()
        self.connected = False

class SocketListener:
    ''' Allows accept connections from a TCP socket '''

    def __init__(self):
        self.socket = bsdsocks.socket(bsdsocks.AF_INET, bsdsocks.SOCK_STREAM)
        self.address = None

    def listen(self, name, port):
        ''' Listen on the specified hostname and port '''

        self.address = (name, port)

        self.socket.setsockopt(bsdsocks.SOL_SOCKET, bsdsocks.SO_REUSEADDR, 1)
        self.socket.bind((name, port))
        self.socket.listen()
        self.socket.setblocking(1)
        self.socket.settimeout(TIMEOUT)

        self.address = (name, self.socket.getsockname()[1])

    def set_timeout(self, seconds):
        ''' Set the timeout for this socket '''
        self.socket.settimeout(seconds)

    def valid(self):
        ''' Is this a valid socket? '''
        return self.address is not None

    def accept(self):
        '''
            Try to accept a new connection. You have to call listen() before doing this.
            Will return a Peer object if a new connection was established, otherwise None.
        '''
        try:
            conn, addr = self.socket.accept()
            return Peer(conn, addr)
        except bsdsocks.timeout:
            return None
        except bsdsocks.error as err:
            if err.errno != errno.EWOULDBLOCK:
                raise
            return None

    def fileno(self):
        ''' Get the underlying file descriptor of this TCP socket '''
        return self.socket.fileno()

    def get_port(self):
        ''' Get the port number this socket is listening on '''
        return self.address[1]

    def get_socket(self):
        ''' Get the underlying BSD socket'''
        return self.socket

    def close(self):
        ''' Close this TCP socket '''
        self.socket.close()
        self.address = None
