''' Information about machines in the cluster '''


class MachineInfo:
    ''' Describes on specific machine'''

    def __init__(self, name, index, external, internal):
        self._name = name
        self._index = index
        self._external_addr = external
        self._internal_addr = internal

    @property
    def index(self) -> str:
        ''' The index of this machine within the cluster '''
        return self._index

    @property
    def name(self) -> str:
        ''' Get the human-readable name of this machine '''
        return self._name

    @property
    def external_addr(self) -> str:
        ''' Get the address we connect to the machine using SSH '''
        return self._external_addr

    @property
    def internal_addr(self) -> str:
        ''' Get the address that other machines connect to '''
        return self._internal_addr

    def generate_metadata(self) -> dict:
        ''' Create a dict that contains information about this machine '''
        return {
            "external-addr": self.external_addr,
            "internal-addr": self.internal_addr
        }
