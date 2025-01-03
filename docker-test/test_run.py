''' Connects to the local machine to run tests '''

from wke import Configuration, Cluster, check_run


def test_create_file():
    '''
        Tests copying a file to a remote machine and
        also creating a file through a target.
    '''

    config = Configuration('local', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/local-cluster.toml')
    s = cluster.create_slice()

    with open('/tmp/myfile.txt', 'w') as file:
        file.write("this is a test\n")

    cluster.copy_to(s.machine_names[0], "/tmp/myfile.txt", "/tmp/mycopiedfile.txt")

    files1 = s.open_remote('/tmp/mycopiedfile.txt')
    assert len(files1) == 1
    assert files1[0].readlines()[0] == "this is a test\n"

    check_run(s, config, 'create-dir')
    check_run(s, config, 'create-file')

    files2 = s.open_remote('/tmp/test-dir/testfile.txt')

    assert len(files2) == 1
    assert files2[0].readlines()[0] == "hello wke!\n"
