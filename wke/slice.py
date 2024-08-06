# pylint: disable=line-too-long,too-few-public-methods,too-many-arguments,missing-module-docstring

from __future__ import annotations

from .machines import MachineInfo

class Slice:
    '''
    A slice is a set of machines that you can run tasks on.
    When execution multiple tasks concurrently, the slice ensures no machine executes more than one task at once.

    Slices can be a subset of another slice or the cluster itself
    '''
    def __init__(self, cluster, parent, offset: int, size: int):
        assert offset >= 0
        assert size >= 0 # Slices can be empty
        assert cluster

        assert offset+size <= parent.num_machines

        self._cluster = cluster
        self._parent = parent # the parent slice (or cluster itself)
        self._offset = offset
        self._size = size

        # The cursor is used to figure out where to generate the next subslice
        self._cursor = 0

    @property
    def workdir(self):
        ''' Get the working directory of the associated cluster '''
        return self._cluster.workdir

    @property
    def cluster(self):
        ''' Get the associated cluster '''
        return self._cluster

    def open_remote(self, filename: str, skip_missing=False, num_machines=None):
        ''' Open a file on all machines in this slice '''

        if num_machines:
            assert num_machines <= self._size
        else:
            num_machines = self._size

        return self._cluster.open_remote(filename, skip_missing=skip_missing, num_machines=num_machines, offset=self._offset)

    def get_all_machines(self):
        ''' Get the information for all machines in this slice '''
        return self._parent.get_all_machines()[self._offset:self._offset+self._size]

    @property
    def machine_names(self) -> list[str]:
        ''' Get the names of all machines in this slice '''
        return [minfo.name for minfo in self.get_all_machines()]

    def get_external_addrs(self) -> list[str]:
        ''' Get the public addresses for all machines in this slice '''
        return [minfo.external_addr for minfo in self.get_all_machines()]

    def get_internal_addrs(self) -> list[str]:
        ''' Get the internal addresses for all machines in this slice '''
        return [minfo.internal_addr for minfo in self.get_all_machines()]

    def get_machine(self, machine_name: str) -> MachineInfo:
        ''' Get the information for a machine with the specified name '''
        return self._parent.get_machine(machine_name)

    def get_machine_by_index(self, index: int) -> MachineInfo:
        ''' Get the information for a machine with the specified index '''
        return self._parent.get_machine_by_index(self._offset+index)

    def advance_cursor(self, advance_by: int):
        ''' Advance the internal cusor by the specified number of steps '''
        if self._cursor + advance_by > self._size:
            raise RuntimeError("Not enough machines left!")
        self._cursor += advance_by

    def create_subslice(self, subslice_size: int) -> Slice:
        '''
            Create a subslice containing a subset of machines in this slice.
            This will advance the internal cursor.
        '''

        if self._cursor + subslice_size > self._size:
            raise RuntimeError("Not enough machines left in this slice!")

        subslice = Slice(self._cluster, self, self._cursor, subslice_size)
        self._cursor = subslice_size

        return subslice

    @property
    def num_machines(self):
        ''' How many machines are in this slice? '''
        return self._size

    @property
    def remaining_size(self):
        ''' How many machines are in this slice? '''
        return self._size - self._cursor

    def get_absolute_index(self, idx: int) -> int:
        ''' Get the absolute position in the list of all machines from an index in this slice ''' 
        return self._parent.get_absolute_index(self._offset + idx)

    def get_address_by_index(self, idx: int) -> list[str]:
        ''' Get the public addresses for all machines in this subslice '''
        return self.get_all_machines()[idx]

    def get_internal_address_by_index(self, idx: int) -> list[str]:
        ''' Get the internal addresses for all machines in this subslice '''
        return self.get_all_machines()[idx].internal_addr


    def open_remote_at_index(self, index: int, source: str):
        ''' Opens a file at the machine with the specified index '''

        addr = self.get_address_by_index(index)
        destination = "/tmp/remote_open"

        self._cluster.copy_from(addr, source, destination)
        return open(destination, "r", encoding='utf-8')
