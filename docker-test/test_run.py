''' Connects to the local machine to run tests '''

from wke import Configuration, Cluster, check_run


def test_create_file():
    ''' Give an invalid type for an option '''

    config = Configuration('local', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/local-cluster.toml')

    check_run(cluster, config, 'create-dir')
    check_run(cluster, config, 'create-file')

    files = cluster.create_slice().open_remote('/tmp/testfile.txt')

    assert len(files) == 1
    assert files[0].readlines()[0] == "hello wke!\n"
