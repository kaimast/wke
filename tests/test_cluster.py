'''
Unit tests for loading cluster configurations
'''

# pylint: disable=missing-function-docstring,line-too-long

from wke.cluster import Cluster

def test_basic():
    cluster = Cluster(path='test-files/configs/cluster.toml')
    assert cluster.num_machines == 4
    assert cluster.get_machine_by_index(1).external_addr == "128.105.144.200"
