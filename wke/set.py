# pylint: disable=missing-module-docstring

from .machines import MachineInfo


class MachineSet:
    '''
    A set is a (potentially) no continuguous subset of a slice or cluster
    '''
    def __init__(self, cluster, parent, indices: list[int]):
        assert cluster

        for index in indices:
            assert index < parent.num_machines

        self._cluster = cluster
        self._parent = parent  # the parent slice (or cluster itself)
        self._indices = indices

    @property
    def cluster(self):
        ''' Get the associated cluster '''
        return self._cluster

    @property
    def workdir(self):
        ''' Get the working directory of the associated cluster '''
        return self._cluster.workdir

    def get_machine(self, machine_name: str) -> MachineInfo:
        ''' Get the information for a machine with the specified name '''
        return self._parent.get_machine(machine_name)

    def get_machine_by_index(self, index: int) -> MachineInfo:
        ''' Get the information for a machine with the specified index '''
        internal_idx = self._indices[index]
        return self._parent.get_machine_by_index(internal_idx)

    def get_all_machines(self):
        ''' Get the information for all machines in this slice '''
        pmachines = self._parent.get_all_machines()
        result = []
        for idx in self._indices:
            result.append(pmachines[idx])
        return result

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
