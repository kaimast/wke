''' Test the `run` command '''

from wke import Configuration, Cluster, run, background_run


def test_valid_option():
    ''' Pass a valid option and see that no error is thrown '''

    config = Configuration('basic', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/cluster.toml')

    run(cluster, config, 'setup-rust', options={'channel': 'nightly'}, dry_run=True)


def test_invalid_option_choice():
    ''' Give an invalid choice for an option '''

    config = Configuration('basic', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/cluster.toml')

    try:
        run(cluster, config, 'setup-rust', options={'channel': 'cbs'}, dry_run=True)
        assert False
    except ValueError:
        pass


def test_invalid_option_type():
    ''' Give an invalid type for an option '''

    config = Configuration('basic', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/cluster.toml')

    try:
        # Option should be str but we pass float
        run(cluster, config, 'setup-rust', options={'channel': 52.0}, dry_run=True)
        assert False
    except ValueError:
        pass


def test_backround_run():
    ''' Do dry run and see that it terminates evenutally '''

    config = Configuration('basic', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/cluster.toml')

    proc = background_run(cluster, config, 'setup-rust', options={'channel': 'stable'},
                          dry_run=True)

    proc.join()
    assert proc.exitcode == 0
